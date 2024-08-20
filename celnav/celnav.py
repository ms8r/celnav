"""Celestial Navigation

Functions to compute intercepts and azimuths for celestial sights of
sun, moon, celestial planets and stars.

Uses PyEphem library for sun, moon, stars and planets. Steve Moshier's
Astronomical Almanac ("aa") can be used alternatively for star ephemeris
calculation (parameter "STAR_CALC" below. In this case the path to aa
executable must be specified in constant AA_EXE_FILE below, and the path to the
aa star catalogue file mus be specified in AA_STAR_CAT_FILE below.
"""

__author__ = "markus@namaniatsea.org"
__version__ = "0.2.2"

# import standard libraries
from math import *
# import time
import datetime as dt
import os
import re
import tempfile
import configparser

# import PyEphem (see http://rhodesmill.org/pyephem/index.html)
import ephem

# celestial body list
bodyList = ["Sun LL", "Sun UL", "Moon LL", "Moon UL", "Venus", "Mars", "Jupiter", "Saturn", "star"]

# import starcat which will provide function navStar() that returns an ephem
# star object for the star name passed to navStar; also provides dictionary
# navStarNum that maps the numbers of 57 navigational stars + Polaris to their
# names.
import celnav.starcat as starcat

starList = list(starcat.navStarNum.keys())
starList.sort()

# import cncfg to get access to ConfigParser obejct:
import celnav.cncfg as cncfg

#-----------------------------------------------------------------------------
# The following three constants can be overritten in celnav.ini in section
# [celnav].
#-----------------------------------------------------------------------------

SECTION_ID = 'celnav'

# path to aa executable and star catalog
AA_EXE_FILE = "/usr/bin/aa"
if cncfg.cncfg.has_option(SECTION_ID, 'AA_EXE_FILE'):
    AA_EXE_FILE = cncfg.cncfg.get(SECTION_ID, 'AA_EXE_FILE')

AA_STAR_CAT_FILE = "/usr/share/aa/star.cat"
if cncfg.cncfg.has_option(SECTION_ID, 'AA_STAR_CAT_FILE'):
    AA_STAR_CAT_FILE = cncfg.cncfg.get(SECTION_ID, 'AA_STAR_CAT_FILE')

# ephemeris calculator to be used for stars ("aa" -> Stephen Mosher's
# Astronomical Almanac, "ephem" = PyEphem)
STAR_CALC = "ephem"
if cncfg.cncfg.has_option(SECTION_ID, 'STAR_CALC'):
    STAR_CALC = cncfg.cncfg.get(SECTION_ID, 'STAR_CALC')

#-----------------------------------------------------------------------------

# assemble start-up log-string (can be written to log-file by other module):
START_UP_LOG_MSG = ('### celnav.STAR_CALC == \'%s\' ###  starcat.DB_SOURCE == \'%s\' ###'
        % (STAR_CALC, starcat.DB_SOURCE))

# import generic print overloader
import celnav.classprint as classprint


class Angle(classprint.AttrDisplay):
    """Stores Angle as
        - decD: degrees as decimal fraction
        - rad: radians
        - degMin: as a tuple (deg, min, sign) containing whole
          degrees, minutes (incl. fraction) and a sign (+1 / -1)
    Setting one attribute will automatically update the others.
    Values >= 360 or <= -360 will automatically be reduced by
    multiples of 360
    """

    signDict = {}
    signDict['lat'] = { 1 : 'N', -1:'S' }
    signDict['lon'] = { 1 : 'E', -1:'W' }
    signDict['generic'] = { 1 : '+', -1:'-' }

    def __init__(self, decD = 0):
        """Initializes decimal degree attribute of Angle;
        __setattr__ will take care of the other attributes
        """
        self.decD = decD


    def __setattr__(self, name, value):
        """Keep rad and deg values in synch, remove 360 multiples
        """

        self.__dict__[name] = value

        if name == "degMin":
            if self.degMin[0] >= 360:
                n = int(self.degMin[0] / float(360))
                self.__dict__["degMin"] = ((self.degMin[0] - n*360), ) + self.degMin[1:]

            self.__dict__["decD"] = (self.degMin[0] + self.degMin[1]/60.0) * self.degMin[2]
            self.__dict__["rad"] = radians(self.decD)

        elif name == "rad":
            if abs(self.rad) >= 2*pi:
                n = int(self.rad / (2*pi))
                self.__dict__["rad"] = self.rad - n*2*pi
            decD = degrees(self.rad)
            d = abs(int(decD))
            m = (abs(degrees(self.rad)) - d) * 60
            if self.rad != 0:
                sign =  int(abs(self.rad)/self.rad)
            else:
                sign = 1
            self.__dict__["degMin"] = (d, m, sign)
            self.__dict__["decD"] = decD

        elif name == "decD":
            if abs(self.decD) >= 360:
                n = int(self.decD / float(360))
                self.__dict__["decD"] = self.decD - n*360
            self.__dict__["rad"] = radians(self.decD)
            d = abs(int(self.decD))
            m = (abs(self.decD) - d) * 60
            if self.decD != 0:
                sign =  int(abs(self.decD)/self.decD)
            else:
                sign = 1
            self.__dict__["degMin"] = (d, m, sign)

    def latStr(self):
        """Returns angle as latitude string (e.g. 'N 20 34.5')
        """
        return '%s %02d %04.1f' % (Angle.signDict['lat'][self.degMin[2]], self.degMin[0], self.degMin[1])

    def latStrDeg(self):
        """Returns angle as latitude string, rounded to full degrees (e.g. 'N30')
        """
        return '%s%02d' % (Angle.signDict['lat'][self.degMin[2]], int(round(abs(self.decD))))

    def lonStr(self):
        """Returns angle as longitude string (e.g. 'E 178 34.5')
        """
        return '%s %03d %04.1f' % (Angle.signDict['lon'][self.degMin[2]], self.degMin[0], self.degMin[1])

    def absStr(self):
        """Returns angle as string without sign (e.g. '178 34.5')
        """
        return '%d %04.1f' % (self.degMin[0], self.degMin[1])

    def signStr(self):
        """Returns angle as +/- signed string (e.g. '-178 34.5')
        """
        return '%s%d %04.1f' % (Angle.signDict['generic'][self.degMin[2]], self.degMin[0], self.degMin[1])

    def intStr(self):
        """Returns angle as an integer string (e.g. '178').
        Fractional degrees will be rounded and a '-' will be shown for negative
        values.
        """
        return '%3d' % int(round(self.decD))


class Sight(classprint.AttrDisplay):
    """Wrapper for sextant height, apparent height, UT, Ic and Az
    """
    def __init__(self, Hs = 0, UT = None, Ic = 0, Az = 0):
        """Initializes Sight object
        Hs: uncorrected sextant altitude in degrees
            with decimal fraction
        UT: UT date and time of Sight as
            (Y, M, D, h, m, s)
        Ic: Intercept in nm
        Az: Azimuth in decD
        Ha: needs to be calculated outside this class
        """
        self.Hs = Angle(Hs)         # sextant altitude
        self.Ha = Angle()           # apparent altitude
        if UT == None:              # set to current UT, ignoring weekday, yearday and DST
            UT = dt.datetime.utcnow().timetuple()[:6]
        self.UT = UT

        self.Ic = Ic                # Intercept in nm
        self.srfIc = Ic             # Ic corrected for short run fix (based on vessel SOG, COG)
        self.Az = Angle(Az)         # Azimuth


class MyObserver(ephem.Observer, classprint.AttrDisplay):
    """Customizes PyEphem's Observer class to allow initialization and lat/lon in
    decimal degrees and minutes with decimal fraction. Also add index error and
    height of eye
    """
    def __init__(self, lat = 0, lon = 0, elevation = 0, heightOfEye = 0, indexError = 0,
            temp = 20, pressure = 1010):
        """Initializes Vessel object with
        lat:                latitude in degrees as decimal fraction (S = -)
        lon:                longitude in degrees as decimal fraction (W = -)
        elevation:          above sea level in meters
        indexError:         in arc minutes
        heightOfEye:        in m
        temp:               in degrees C
        pressure:           in mb
        """
        # Observer does not take arguments => call __init__ empty,
        # then add assigments here:
        ephem.Observer.__init__(self)
        self.lat = Angle(lat).rad
        self.lon = Angle(lon).rad
        self.elevation = elevation
        self.temp = temp
        self.pressure = pressure

        self.indexError =  Angle(indexError/60.0)

        self.heightOfEye = heightOfEye

        self.dip = Angle()
        self.calcDip()

    def calcDip(self):
        """Returns dip in radians (calculated from heightOfEye)
        and sets self.dip.
        """
        self.dip.decD = -(0.0293 * sqrt(self.heightOfEye))
        return self.dip.rad

    def latTuple(self):
        return Angle(self.lat * 180 / pi).degMin

    def lonTuple(self):
        return Angle(self.lon * 180 / pi).degMin

    def latDecD(self):
        return self.lat * 180 / pi

    def lonDecD(self):
        return self.lon * 180 / pi


class LOP(classprint.AttrDisplay):
    """Data structure to store/manipulate parameters of a sextant sight:
    observed body, sextant altitude, index error, height of eye,
    apparent topocentric altitude
    """

    # dictionary for aa calculation of Ha and Az (see aaStars() below)
    if STAR_CALC == 'aa':
        aaReDict = {}
        aaReDict['alt'] = re.compile(r"^Topocentric:  Altitude (?P<alt>[^ ]*) deg, Azimuth [^ ]* deg$")
        aaReDict['az'] = re.compile(r"^Topocentric:  Altitude [^ ]* deg, Azimuth (?P<az>[^ ]*) deg$")

    def __init__(self, fix = None, body = "Sun LL", starName = None, indexError = 0, heightOfEye = 0,
            lat = 0, lon = 0, elevation = 0, temp = 20, pressure = 1010):
        """Initialization values for
        lat:                latitude in degrees as decimal fraction (S = -)
        lon:                longitude in degrees as decimal fraction (W = -)
        elevation:          above sea level in meters
        indexError:         in arc minutes
        heightOfEye:        in m
        temp:               in degrees C
        pressure:           in mb
        """

        self.fix = fix          # fix to which LOP belongs;
                                # can be used to access SOG/COG/UT from Fix for MOO correction

        self.body = body        # Observed body; possible values:
                                #   - Sun UL, Sun LL, Moon UL, Moon LL
                                #   - Venus, Mars, Jupiter, Saturn
                                #   - star
                                # If "star", starName must be a star name that
                                # is known to PyEphem


        self.starName = starName
                                # star name (see under "body" above)

        if starName != None:
            self.starNum = starcat.navStarNum[starName]
        else:
            self.starNum = None

        self.sightList = []     # list of Sight objects (to be appended with each shot
        self.lopSightIndex = -1
                                # index for Sight in self.sightList to be used for fix calculation

        self.observer =  MyObserver(lat = lat, lon = lon, elevation = elevation, indexError = indexError,
                heightOfEye = heightOfEye, temp = temp, pressure = pressure)
                                # needs to be updated with time of shot before call to
                                # PyEphem for computation of topocentric apparent
                                # altitude



    def calcHa(self):
        """Calculates and sets apparent altitudes in sightList based on Hs,
        indexError and dip; calls calcDip() just in case...
        """
        MyObserver.calcDip(self.observer)
        for s in self.sightList:
            s.Ha.rad = s.Hs.rad + self.observer.indexError.rad + self.observer.dip.rad


    def calcIcAz(self):
        """Calculates intercept Ic and azimuth Az for all shots in self.sightList
        and updates Ic and Az attributes of each shot accordingly. Also updates
        srfIc for short-run fix calculation from multiple LOPs. To correct Ic for
        MOO COG, SOG and UT from class Fix are used (shared attributes at class level).
        Uses PyEphem to calculate ephemeris data (or aa if STAR_CALC == 'aa').
        PyEphem provides apparent topocentric altitudes which are compared
        to sextant altitude corrected for index error and dip in order to calculate
        intercepts. For sun and moon, PyEphem also provides radii which are used to
        adjust computed apparen topocentric altitudes to yield values that can be compared
        to upper or lower limb sights.
        """
        splitBody = self.body.split()   # split off "LL" or "UL" for sun and moon

        self.calcHa()                   # calculate apparent observed altitude for
                                        # all shots

        for s in self.sightList:

            self.observer.date = s.UT

            # create ephem object instance for body;
            if splitBody[0] == 'star':

                if STAR_CALC == 'ephem':

                    e = starcat.navStar(self.starName)
                    e.compute(self.observer)    # computing with Observer argument will
                                                # yield topocentric apparent altitude
                    Hc = Angle(e.alt * 180 / pi)
                                                # calculated topocentric apparent altitude
                                                # incl. refraction
                    s.Az = Angle(e.az * 180 / pi)

                elif STAR_CALC == 'aa':

                    d = aaStars(LOP.aaReDict, AA_STAR_CAT_FILE, self.starNum, ut = s.UT,
                            lat = degrees(self.observer.lat), lon = degrees(self.observer.lon),
                            hoe = self.observer.heightOfEye, temp = self.observer.temp,
                            pressure = self.observer.pressure)

                    # extract Hc and Az:
                    Hc = Angle(float(d['alt']))
                    s.Az = Angle(float(d['az']))

            else:

                e = ephem.__dict__[splitBody[0]]()

                e.compute(self.observer)    # computing with Observer argument will
                                            # yield topocentric apparent altitude
                s.Az = Angle(e.az * 180 / pi)
                Hc = Angle(e.alt * 180 / pi)
                                            # calculated topocentric apparent altitude
                                            # incl. refraction
                if len(splitBody) > 1:      # Sun or Moon with "LL" or "UL"
                    if splitBody[1] == "UL":
                        Hc.rad += e.radius  # add semidiamter to calc. altitude to make
                                            # it comparable to observed Ha
                    else:
                        Hc.rad -= e.radius  # same logic for lower limb sight
                                            # Note: this radius is topocentric since the
                                            # intercept calculation is done with all topo-
                                            # centric values. The value of e.radius will
                                            # will differ from the SD value listed in the
                                            # NA (geocentric).

            s.Ic = (s.Ha.decD - Hc.decD) * 60

            # calculate short-run fix intercept, corrected for MOO:
            # calculate difference between fix and sight times:
            dT = dt.datetime(*self.fix.UT) - dt.datetime(*s.UT) # as dt.timedelta
            dT_hrs = dT.days * 24 + dT.seconds / 3600.0         # in hours

            # now calculate MOO corrected Intercept based on Fix SOG/COG
            s.srfIc = s.Ic + cos(self.fix.COG.rad - s.Az.rad) * self.fix.SOG * dT_hrs


class Fix(classprint.AttrDisplay):
    """Top-level class: a Fix consists of multiple LOPs which in turn
    each consist of one or more Sights. Also defines vessel's SOG and COG
    for short-run running fixes, fix lat/lon and UT.

    SOG:        speed over ground in kn
    COG:        course over ground in decD true
    UT:         date and time for fix (UT) as (Y, M, D, h, m, s);
                will be initialized to current UT if empty
    lat:        fix latitude in decimal degrees
    lon:        fix longitude in decimal degrees
    Also initializes lopList as []
    """
    def __init__(self, SOG = 0, COG = 0, UT = None, lat = 0, lon = 0):

        if UT == None:
            UT = dt.datetime.utcnow().timetuple()[:6]
        self.UT = UT

        self.SOG = float(SOG)
        self.COG = Angle(COG)

        self.lopList = []

        self.lat = Angle(lat)
        self.lon = Angle(lon)


    def calc2LOPFix(self):
        """Calculates fix from two LOPs by using plane trig. For each LOP the sight indicated
        by LOP.lopSightIndex will be used. Intercepts will be MOO adjusted based on Fix.SOG and
        Fix.COG. Works only if both LOPs use same AP. Raises FixLOPError if number of LOPs
        (and selected Sights) is != 2 or the two LOPs use different APs
        """

        # check if 2 LOPs have 1 Sight selected each to be used for fix:
        if len(self.lopList) != 2:
            raise FixLOPError
        for i in [0, 1]:
            if self.lopList[i].lopSightIndex < 0:
                raise FixLOPError

        # determine LOP with greater Azimuth (will be index 1 in following calculations, lesser
        # Azimuth will be index 2)
        if (self.lopList[0].sightList[self.lopList[0].lopSightIndex].Az >
                self.lopList[1].sightList[self.lopList[1].lopSightIndex].Az):
            maxIndex = 0
            minIndex = 1
        else:
            maxIndex = 1
            minIndex = 0

        # assign sight values (lower case i is Ic uncorrected for MOO)
        sight1 = self.lopList[maxIndex].sightList[self.lopList[maxIndex].lopSightIndex]
        sight2 = self.lopList[minIndex].sightList[self.lopList[minIndex].lopSightIndex]
        I1 = sight1.srfIc
        I2 = sight2.srfIc
        Z1 = sight1.Az.rad
        Z2 = sight2.Az.rad
        t1 = sight1.UT
        t2 = sight2.UT

        # check if both LOPs use same AP (must be less than 0.1' apart):
        maxDiff = pi / (60 * 180)
        AP_Lat = self.lopList[maxIndex].observer.lat
        AP_Lon = self.lopList[maxIndex].observer.lon
        if abs(AP_Lat - self.lopList[minIndex].observer.lat) > maxDiff:
            raise FixLOPError
        if abs(AP_Lon - self.lopList[minIndex].observer.lon) > maxDiff:
            raise FixLOPError


        deltaZ = Z1 - Z2
        alpha1 = atan((I2 - I1 * cos(deltaZ)) / (I1 * sin(deltaZ)))
        Z_alpha1 = Z1 - alpha1
        R = I1 / cos(alpha1)
        deltaLat = radians((R * cos(Z_alpha1)) / 60)
        deltaLon = radians((R * sin(Z_alpha1)/cos(self.lopList[0].observer.lat)) / 60)

        self.lat.rad = AP_Lat + deltaLat
        self.lon.rad = AP_Lon + deltaLon


class FixLOPError(Exception):
    """Exception to be used if Fix calculation is requested with something other than 2 LOPs with
    1 Sight selected each.
    """
    pass


class SunMoonRiseSet(classprint.AttrDisplay):
    """Calculates and stores data for Sun and Moon rise and set,
    meridian passage, twighlight, and moonphase for a given UT
    and lat/lon. All times provided by SunMoonRiseSet are in UT. See __init__
    doc string for attributes. Exports calcData() which updates all attributes
    based on lat, lon, and date.
    """
    def __init__(self, lat = 0, lon = 0, ut = None):
        """lat/lon in degrees (incl. decimal fraction);
        ut is a (Y, M, D, h, m, c) tuple; local midnight preceeding ut will be
        used as starting reference point for calculating subsequent rise/set
        data. Hence the time for sunrise will always precede sunset but moon
        set may precede moon rise. For ut-lat combinations where the sun is
        always or never up above the polar circle values for all sun events
        will be None. Moon events will still be sought with ut as a starting
        reference time.

        Attributes:
            sun         -   ephem Sun object; sun will have a dictionary
                            sunData containing (Y, M, D, h, m, s)
                            tuples for the following keys (exceptions: eot is a
                            triple with (min, sec, sign), sd is an Angle object):
                                twl_naut_am
                                twl_civil_am
                                rise
                                mer_pass
                                set
                                twl_civil_pm
                                twl_naut_pm
                                eot
                                sd
                            Associated values can be None if sun will not
                            rise/set at given lat and date.

            moon        -   ephem Moon object; moon will have a dictionary
                            moonData containing (Y, M, D, h, m, s)
                            tuples for the following keys (for new/full
                            moon only (Y, M, D)). 'age' is an integer for the
                            number of days since the previous new moon. 'sd' is
                            an Angle object:
                                rise
                                mer_pass
                                set
                                prev_full
                                prev_new
                                next_full
                                next_new
                                age
                                sd
                            Values associated with rise/mer_pass/set can be
                            None if moon will not rise/set at given date

            observer    -   ephem Observer object; used to store
                            lat/lon and utDate; self.observer.date
                            will store UT for midnight preceeding ut argument
                            at lon. If midnight is undefined above the Poalr
                            Circle observer.date will be set to ut.
        """
        self.sun = ephem.Sun()
        self.sunData = {}

        self.moon = ephem.Moon()
        self.moonData = {}

        self.observer = ephem.Observer()
        self.observer.lat = radians(lat)
        self.observer.lon = radians(lon)

        if ut == None:
            ut = dt.datetime.utcnow().timetuple()[:6]

        self.ut = ut

        # and now we begin...
        self.calcData()


    def calcData(self):
        """Updates sun and moon data dictionaries (see __init__ doc string for
        detail). Important: self.observer.date must be local midnight at
        self.observer.lon in UT. If user input changes lon the callback for
        associated widgets must handle the update of date prior to calling
        calcData().
        """
        # calculate local midnight:
        self.observer.date  = self.ut
        try:
            self.observer.date = self.observer.previous_antitransit(self.sun)
        except ephem.CircumpolarError:
            self.observer.date = self.ut

        # switch off ephem's atmospheric refraction correction by setting pressure to 0
        # and moving horizon down 34' (as per US Naval Observatory standard)
        self.observer.pressure = 0
        self.observer.horizon = '-0:34'

        # Moon first: all events after local midnight (= observer.date)
        try:
            t = self.observer.next_rising(self.moon).tuple()
        except ephem.CircumpolarError:
            self.moonData['rise'] = None
        else:
            self.moonData['rise'] = t[:5] + (int(t[5]),)

        try:
            t = self.observer.next_setting(self.moon).tuple()
        except ephem.CircumpolarError:
            self.moonData['set'] = None
        else:
            self.moonData['set'] = t[:5] + (int(t[5]),)

        try:
            t = self.observer.next_transit(self.moon).tuple()
        except ephem.CircumpolarError:
            self.moonData['mer_pass'] = None
        else:
            self.moonData['mer_pass'] = t[:5] + (int(t[5]),)

        # full/new moon:
        self.moonData['prev_full'] = ephem.previous_full_moon(self.observer.date).triple()
        self.moonData['prev_new'] = ephem.previous_new_moon(self.observer.date).triple()
        self.moonData['next_full'] = ephem.next_full_moon(self.observer.date).triple()
        self.moonData['next_new'] = ephem.next_new_moon(self.observer.date).triple()

        # days into lunar cycle: move date to local noon in UT
        # note: we live with the potetnial inaccurracy if local noon is
        # undefined beyond the polar circle...
        origObsDate = self.observer.date
        self.observer.date += 0.5
        age = self.observer.date - ephem.Date(self.moonData['prev_new'])
        self.moonData['age'] = int(round(age)) % 30

        # now Sun: start with local noon in UT (already set for moon age above)
        # to get previous sunrise:
        # note: we live with the potetnial inaccurracy if local noon is
        # undefined beyond the polar circle...
        try:
            t = self.observer.previous_rising(self.sun).tuple()
        except ephem.CircumpolarError:
            self.sunData['rise'] = None
        else:
            self.sunData['rise'] = t[:5] + (int(t[5]),)

        # now move date to rise to get meridian passage and set:
        if self.sunData['rise'] != None:

            self.observer.date = self.sunData['rise']

            try:
                t = self.observer.next_transit(self.sun).tuple()
            except ephem.CircumpolarError:
                self.sunData['mer_pass'] = None
            else:
                self.sunData['mer_pass'] = t[:5] + (int(t[5]),)

            try:
                t = self.observer.next_setting(self.sun).tuple()
            except ephem.CircumpolarError:
                self.sunData['set'] = None
            else:
                self.sunData['set'] = t[:5] + (int(t[5]),)

        else:
            self.sunData['mer_pass'] = None
            self.sunData['set'] = None

        # EoT:
        if self.sunData['mer_pass'] != None:

            # meridian angle of self.observer.lon in days (negative for east lon):
            ma = dt.timedelta(-self.observer.lon * 180/pi / (15.0 * 24.0))
            # now Greenwich noon (1200 UT on date):
            gn = dt.datetime(*(self.sunData['mer_pass'][:3] + (12, 0, 0)))

            localUTnoon = gn + ma

            eot = dt.datetime(*self.sunData['mer_pass']) - localUTnoon  # dt.timedelta object
            # NOTE: Python 2.6 doesn't provide dt.timedelta.total_seconds
            # -> revert to manual calculation
            # eot = eot.total_seconds()                                   # seconds as float
            eot = eot.microseconds / 1e6 + eot.seconds + eot.days * 24 * 3600
            eot_min = int(abs(eot) / 60)
            self.sunData['eot'] = (eot_min, int(round(abs(eot)-eot_min*60)), eot/abs(eot))  # (min, sec, sign)
        else:
            self.sunData['eot'] = None


        # next: twilight stuff - move date to meridian passage first
        # TODO: fix logic - possible to have no sunrise but mer pass during summer above polar circle
        if self.sunData['mer_pass'] != None:
            self.observer.date = self.sunData['mer_pass']

            # civil twilight (body center 6 deg below horizon):
            self.observer.horizon = '-6'
            try:
                t = self.observer.previous_rising(self.sun, use_center = True).tuple()
                self.sunData['twl_civil_am'] = t[:5] + (int(t[5]),)
            except ephem.CircumpolarError:
                self.sunData['twl_civil_am'] = None

            try:
                t = self.observer.next_setting(self.sun, use_center = True).tuple()
                self.sunData['twl_civil_pm'] = t[:5] + (int(t[5]),)
            except ephem.CircumpolarError:
                self.sunData['twl_civil_pm'] = None

            # naut. twilight (body center 12 deg below horizon):
            self.observer.horizon = '-12'
            try:
                t = self.observer.previous_rising(self.sun, use_center = True).tuple()
                self.sunData['twl_naut_am'] = t[:5] + (int(t[5]),)
            except ephem.CircumpolarError:
                self.sunData['twl_naut_am'] = None

            try:
                t = self.observer.next_setting(self.sun, use_center = True).tuple()
                self.sunData['twl_naut_pm'] = t[:5] + (int(t[5]),)
            except ephem.CircumpolarError:
                self.sunData['twl_naut_pm'] = None
        else:
            self.sunData['twl_civil_am'] = None
            self.sunData['twl_civil_pm'] = None
            self.sunData['twl_naut_am'] = None
            self.sunData['twl_naut_pm'] = None

        # semidiamter (at local noon):
        # self.sun.compute(self.observer)
        # changed to get geocentric SD:
        self.sun.compute(self.observer.date)
        self.sunData['sd'] = Angle(self.sun.radius * 180 / pi)
        # self.moon.compute(self.observer)
        # changed to get geocentric SD:
        self.moon.compute(self.observer.date)
        self.moonData['sd'] = Angle(self.moon.radius * 180 / pi)

        # move observer.date back to local midnight
        self.observer.date = origObsDate


class AlmanacPage(classprint.AttrDisplay):
    """Caluclates hourly GHA and Dec data for self.date for Sun, Moon, Venus,
    Mars, Jupiter and Saturn. Data for each body is stored in a dictionary with
    keys 'gha' and 'dec' and a list with 24 Angle objects stored against either
    key.  For the Moon 24 Angle objects for HP are also provided under key
    'hp'. Also provides hourly GHA for Aries for self.date which is stored in a
    list with 24 Angle items.
    """
    def __init__(self, date = None):
        """Sets up data structures and initializes these with values provided
        by PyEphem for <date> (see class doc string for details). date is a (Y,
        M, D) triple. If no date is provided datetime.datetime.utcnow() will be
        used, with hour, minute and second set to 0.
        """
        self.aries = []
        self.sun = { 'ephemClass' : 'Sun', 'gha' : [], 'dec' : [] }
        self.moon = { 'ephemClass' : 'Moon', 'gha' : [], 'dec' : [], 'hp' : [] }
        self.venus = { 'ephemClass' : 'Venus', 'gha' : [], 'dec' : [] }
        self.mars = { 'ephemClass' : 'Mars', 'gha' : [], 'dec' : [] }
        self.jupiter = { 'ephemClass' : 'Jupiter', 'gha' : [], 'dec' : [] }
        self.saturn = { 'ephemClass' : 'Saturn', 'gha' : [], 'dec' : [] }

        if date == None:
            date = dt.datetime.utcnow().timetuple()[:3]

        self.date = date

        # start with Aries:
        for h in range(24):
            t = self.date + (h, 0, 0)
            self.aries.append(Angle(ghaAries(t)))

        # now planets...
        for body in ('sun', 'moon', 'venus', 'mars', 'jupiter', 'saturn'):

            p = ephem.__dict__[self.__dict__[body]['ephemClass']]()

            for h in range(24):
                t = self.date + (h, 0, 0)
                p.compute(t)
                self.__dict__[body]['dec'].append(Angle(degrees(p.dec)))
                self.__dict__[body]['gha'].append(Angle(gha(p.ra, t)))
                if body == 'moon':
                    self.__dict__[body]['hp'].append(Angle(hpMoon(degrees(p.radius))))


    def updateData(self):
        """Updates Aries list and planet dictionaries based on self.date
        """
        # start with Aries:
        for h in range(24):
            t = self.date + (h, 0, 0)
            self.aries[h].decD = ghaAries(t)

        # now planets...
        for body in ('sun', 'moon', 'venus', 'mars', 'jupiter', 'saturn'):

            p = ephem.__dict__[self.__dict__[body]['ephemClass']]()

            for h in range(24):
                t = self.date + (h, 0, 0)
                p.compute(t)
                self.__dict__[body]['dec'][h].decD = degrees(p.dec)
                self.__dict__[body]['gha'][h].decD = gha(p.ra, t)
                if body == 'moon':
                    self.__dict__[body]['hp'][h].decD = hpMoon(degrees(p.radius))


class StarFinder(classprint.AttrDisplay):
    """Provides a list for navigational stars with altitude, azimuth and
    magnitude for a given UT and lat/lon. Also provides Dec and SHA. A list of
    star names known to PyEphem must be passed to the constructor. Dictionary
    self.starData will have the star names provided in StarList as keys and map
    each of these star names to a dictionary with the keys 'mag', 'alt', 'az',
    'dec' and 'sha'. 'mag' will be mapped to a float giving the star's
    magnitude. All other keys will be mapped to Angle objects providing
    topocentric apparent altitude and azimuth, and declination and SHA
    repsctively.  Exports method updateStarData().
    """

    # shared dictionary to match aa output lines containing magnitude,
    # topocentric altitude and azimuth
    reDict = {}
    reDict['mag'] = re.compile(r"^approx\. visual magnitude (?P<mag>[^ ]*)[ ]*$")
    reDict['alt'] = re.compile(r"^Topocentric:  Altitude (?P<alt>[^ ]*) deg, Azimuth [^ ]* deg$")
    reDict['az'] = re.compile(r"^Topocentric:  Altitude [^ ]* deg, Azimuth (?P<az>[^ ]*) deg$")
    reDict['dec'] = re.compile(r'^[ ]*Apparent[^D]*Dec\.[^0-9\-]*(?P<dec>[0-9\-][^"]*")[ ]*$')
    reDict['sha'] = re.compile(r'^[ ]*Apparent:[ ]*R\.A\.[^0-9]*(?P<sha>[0-9][^s]*s).*$')

    def __init__(self, starList, lat = 0, lon = 0, ut = None, pressure = 1010, temp = 20,
            elevation = 0, hoe = 0):
        """Assigns (default) values and creates initial starData list
            starList    -   list with star names for which data is to be computed;
                            star names must be known to PyEphem
            lat         -   latitide in degrees (incl. decimal fraction); S = -
            lon         -   longitude in degrees (incl. decimal fraction); W = -
            ut          -   UT as tuple (Y. M. D, h, m, s), will default to
                            datetime.utcnow if not provided
            pressure    -   atmospheric pressure in mbar
            temp        -   temperature in deg C
            elevation   -   elevation in meter above sea level
            hoe         -   height of eye in m
        """

        self.starList = starList
        if ut == None:
            ut = dt.datetime.utcnow().timetuple()[:6]

        self.ut = ut

        self.lat = Angle(lat)
        self.lon = Angle(lon)
        self.pressure = pressure
        self.temp = temp
        self.elevation = elevation
        self.starData = {}
        self.hoe = hoe

        self.updateStarData()


    def updateStarData(self):
        """Wrapper that calls either self.__ephemUpdateStarData() or
        self.__aaUpdateStarData(), depending on the value of STAR_CALC.
        """
        if STAR_CALC == 'ephem':
            self.__ephemUpdateStarData()
        elif STAR_CALC == 'aa':
            self.__aaUpdateStarData()


    def __ephemUpdateStarData(self):
        """Creates dictionary self.starData for stars in self.starList based on
        current values of self.ut, self.lat, self.lon, ...
        Dictionary will have keys
            'mag'   -   Magnitude as float
            'alt'   -   Apparent topocentric altitude as Angle object
            'az'    -   Azimuth as Angle object
            'dec'   -   Declination as Angle object
            'sha'   -   Sideral hour angle as celnav object
        """
        self.starData = {}
        obs = ephem.Observer()
        obs.date = self.ut
        obs.lat = self.lat.rad
        obs.lon = self.lon.rad
        obs.temp = self.temp
        obs.pressure = self.pressure
        for starName in self.starList:
            s = starcat.navStar(starName)
            s.compute(obs)
            self.starData[starName] = { 'mag' : s.mag, 'alt' : Angle(s.alt*180/pi),
                    'az' : Angle(s.az*180/pi), 'dec' : Angle(s.dec*180/pi),
                    'sha' : Angle(sha(s.ra)) }


    def __aaUpdateStarData(self):
        """Updates self.starData based on current values of self.UT, self.lat,
        self.lon, ... ; uses aa
        """
        self.starData = {}
        for star in self.starList:
            i = starNum(star)
            odRaw = aaStars(StarFinder.reDict, AA_STAR_CAT_FILE, i, ut =
                    self.ut, lat = self.lat.decD, lon = self.lon.decD, hoe =
                    self.hoe, temp = self.temp, pressure = self.pressure)
            od = {}
            for key in odRaw:
                if key == 'dec':
                    s = odRaw[key].replace('d', '').replace('"', '').replace("'", "").split()
                    if len(s) == 4:
                        offs = 1
                        sign = -1
                    else:
                        offs = 0
                        sign = 1
                    od[key] = Angle(sign * (float(s[0+offs]) + float(s[1+offs])/60 + float(s[2+offs])/3600))
                elif key == 'sha':
                    s = odRaw[key].replace('h', '').replace('m', '').replace("s", "").split()
                    # convert RA hrs to rad:
                    r = (float(s[0]) + float(s[1])/60 + float(s[2])/3600) * pi / 12.0
                    od[key] = Angle(sha(r))
                elif key == 'mag':
                    od[key] = float(odRaw[key])
                else:
                    od[key] = Angle(float(odRaw[key]))

            self.starData[star] = od


def aaStars(reDict, starCatFile, starNum, ut = None, lat = 0, lon = 0, hoe = 0,
        temp = 20, pressure = 1010):
    """Provides an interface to Sephen Moshier's aa program for star data.
    Receives pairs of group IDs and (compiled) regex's containing these group
    IDs to be matched against aa's output. Will return a dictionary with the
    same group IDs as keys and the corresponding matches as associated values.

    reDict      -   Dictionary in which keys are regex group IDs and associated
                    value are compiled regexes containing these group IDs (one
                    group ID per regex). aaStars will match each line in aa's
                    out put against each of the regexes in the dictionary.
                    Matches will be put in a dictionary with the same group IDs
                    as keys.
    starCatFile -   String with full path to star catalogue to be used
    starNum     -   Star catalogue line number of star for which data is
                    requested
    UT          -   Tuple (Y, M, D, h, m, s)
    lat         -   Observer latitude in degress (incl. decimal fraction); S = -
    lon         -   Observer longitude in degress (incl. decimal fraction); E = -
    hoe         -   Height of eye in meters
    temp        -   Temperature in deg C
    pressure    -   Atmospheric pressure in mbar
    """

    if ut == None:
        ut = dt.datetime.utcnow().timetuple()[:6]

    # create and change into working directory and write aa.ini file
    currentDir = os.getcwd()
    aaWorkDir = tempfile.mkdtemp()
    os.chdir(aaWorkDir)

    aaIni = open("aa.ini", 'w')
    aaIni.write("%f\n" % lon)
    aaIni.write("%f\n" %  lat)
    aaIni.write("%.1f\n" % hoe)
    aaIni.write("%d\n" % int(round(temp)))
    aaIni.write("%d\n" % int(round(pressure)))
    aaIni.write("2\n")
    aaIni.write("0.0\n")
    aaIni.close()

    aaInfile = open("aa.infile", 'w')
    # first Y/M/D/h/m/s:
    for i in range(6):
        aaInfile.write("%d\n" % ut[i])
    # 1 tabulation, 1 day intervall:
    aaInfile.write("1\n1\n")
    # 88 for star and catalogue:
    aaInfile.write("88\n%s\n" % starCatFile)
    # star number:
    aaInfile.write("%d\n" % starNum)
    # -1 for graceful exit
    aaInfile.write("-1\n")

    aaInfile.close()

    # call aa and write to aaOutfile:
    os.system(AA_EXE_FILE + " < " + aaInfile.name + " > aa.outfile")

    # process aa output
    aaOutfile = open("aa.outfile", 'r')
    outDict = {}
    for line in aaOutfile:
        for key in reDict:
            m = reDict[key].match(line)
            if m:
                outDict[key] = line[m.start(key) : m.end(key)]

    aaOutfile.close()

    # clean-up
    os.remove(aaIni.name)
    os.remove(aaInfile.name)
    os.remove(aaOutfile.name)
    os.rmdir(aaWorkDir)
    os.chdir(currentDir)

    return outDict


class aaStarFinder(classprint.AttrDisplay):
    """Provides a mapping for all 57 navigational stars plus Polaris with
    altitude, azimuth, magnitude, SHA and dec for a given UT and lat/lon. Will
    interface with aa to get data via call to aaStars().  Dictionary
    self.starData will have star names as keys and map each of these star names
    to a dictionary with the keys 'mag', 'alt', 'az', 'dec' and 'sha'. 'mag'
    will be mapped to a float giving the star's magnitude. All other keys will
    be mapped to Angle objects providing topocentric apparent altitude and
    azimuth, and declination and SHA repsctively.  Exports method
    updateStarData().
    """

    noStars = 58        # number of stars = number of lines to read in aa star catalogue

    # shared dictionary to match aa output lines containing magnitude,
    # topocentric altitude and azimuth
    reDict = {}
    reDict['mag'] = re.compile(r"^approx\. visual magnitude (?P<mag>[^ ]*)[ ]*$")
    reDict['alt'] = re.compile(r"^Topocentric:  Altitude (?P<alt>[^ ]*) deg, Azimuth [^ ]* deg$")
    reDict['az'] = re.compile(r"^Topocentric:  Altitude [^ ]* deg, Azimuth (?P<az>[^ ]*) deg$")
    reDict['dec'] = re.compile(r'^[ ]*Apparent[^D]*Dec\.[^0-9\-]*(?P<dec>[0-9\-][^"]*")[ ]*$')
    reDict['sha'] = re.compile(r'^[ ]*Apparent:[ ]*R\.A\.[^0-9]*(?P<sha>[0-9][^s]*s).*$')

    def __init__(self, starList, lat = 0, lon = 0, ut = None, pressure = 1010, temp = 20, hoe = 0):
        """Assigns (default) values and creates initial starData list
            starList    -   list with star names for which data is to be computed;
                            star names must be defined in starcat.py and
                            associated stars must exist in aa star catalogue
            lat         -   latitide in degrees (incl. decimal fraction); S = -
            lon         -   longitude in degrees (incl. decimal fraction); W = -
            ut          -   UT as tuple (Y. M. D, h, m, s), will default to
                            datetime.utcnow if not provided
            pressure    -   atmospheric pressure in mbar
            temp        -   temperature in deg C
            hoe         -   height of eye in m
        """

        self.starList = starList
        if ut == None:
            ut = dt.datetime.utcnow().timetuple()[:6]

        self.UT = ut

        self.lat = Angle(lat)
        self.lon = Angle(lon)
        self.pressure = pressure
        self.temp = temp
        self.hoe = hoe
        starData = {}

        self.updateStarData()   # each item in starData will subsequently be a dictionary
                                # with key equal to the ones in StarFinder.reDict
                                # and associated values as floats


    def updateStarData(self):
        """Updates self.starData based on current values of self.UT, self.lat,
        self.lon, ...
        """
        self.starData = {}
        for s in self.starList:
            i = starNum(s)
            odRaw = aaStars(aaStarFinder.reDict, AA_STAR_CAT_FILE, i, ut =
                    self.UT, lat = self.lat.decD, lon = self.lon.decD, hoe =
                    self.hoe, temp = self.temp, pressure = self.pressure)
            od = {}
            for key in odRaw:
                if key == 'dec':
                    s = odRaw[key].replace('d', '').replace('"', '').replace("'", "").split()
                    if len(s) == 4:
                        offs = 1
                        sign = -1
                    else:
                        offs = 0
                        sign = 1
                    od[key] = Angle(sign * (float(s[0+offs]) + float(s[1+offs])/60 + float(s[2+offs])/3600))
                elif key == 'sha':
                    s = odRaw[key].replace('h', '').replace('m', '').replace("s", "").split()
                    # convert RA hrs to rad:
                    r = (float(s[0]) + float(s[1])/60 + float(s[2])/3600) * pi / 12.0
                    od[key] = Angle(sha(r))
                elif key == 'mag':
                    od[key] = float(odRaw[key])
                else:
                    od[key] = Angle(float(odRaw[key]))

            self.starData[s] = od


def aaBuildStarList(starList):
    """Reads in aa star catalogue pointed to in celnav.AA_STAR_CAT_FILE and appends entries to
    starList[] as '<starNum> - <starName>'
    """
    r = re.compile(r"^[^(]*\((?P<star>[^)]*)\).*$")     # extracts star name from catalogue line
    i = 1
    starCat = open(AA_STAR_CAT_FILE, 'r')
    for line in starCat:
        m = r.match(line)
        if m:
            starName = line[m.start('star') : m.end('star')]
            starList.append("%d - %s" % (i, starName))
            i += 1

    starCat.close()

class PlanetFinder(classprint.AttrDisplay):
    """Calculates and stores UT for rise, set and meridian passage as well as
    azimuth at rise and set and altitude at meridian passage for nav. planets
    and moon for a given UT and lat/lon. Also calculates and stores twilight
    data.  See __init__ doc string for attributes. Exports calcData() which
    updates all attributes based on lat, lon, and UT.
    Note: if UT provided is after local sunrise the times for the above events
    will be claculated for the following night. If UT provided is before local
    sunrise, times will be calculated for current night.
    """
    def __init__(self, lat = 0, lon = 0, ut = None):
        """lat/lon in degrees (incl. decimal fraction);
        date is a (Y, M, D) triple; date is interpreted as a local
        date at lon since ephem will calculate utc for rise, set, etc.
        at lon.
        Attributes:
            observer    -   ephem Observer object; used to store
                            lat/lon and utDate; self.observer.date
                            will store UT for midnight at lon
            planets     -   Compound dictionary, keyed by planet names 'Venus',
                            'Mars', 'Jupiter', 'Saturn' plus 'Moon'. For each
                            planet it contains a dictionary with the following
                            keys:
                                rise
                                set
                                mer_pass
                                rise_az
                                set_az
                                mer_pass_alt
                            The first three items are (Y, M, D, h, m, s)
                            tuples. The last thres are Angle objects.
            twilight    -   Dictionary with keys
                                pm_start
                                pm_end
                                am_start
                                am_end
                            Values will be (Y, M, D, h, m, s) tuples with the
                            corresponding UTs. pm  values are associated with
                            the sunset preceding local midnight on <date>, am
                            values are associated with sunrise following local
                            midnight on <date>.
        """
        self.planets = {
                'Venus'     :   {},
                'Mars'      :   {},
                'Jupiter'   :   {},
                'Saturn'    :   {},
                'Moon'      :   {}
                }

        self.twilight = {}

        self.observer = ephem.Observer()
        self.observer.lat = radians(lat)
        self.observer.lon = radians(lon)

        if ut == None:
            ut = dt.datetime.utcnow().timetuple()[:6]

        self.ut = ut

        self.calcData()


    def calcData(self):
        """Updates values in self.planets and self twilight.
        """
        try:
            self.observer.date = localMidnightUT(degrees(self.observer.lat),
                    degrees(self.observer.lon), self.ut)
        except:
            self.observer.date = 0
            for key in self.twilight:
                self.twilight[key] = None
            for p in self.planets:
                for key in self.planets[p]:
                    self.planets[p][key] = None
            return None

        sun = ephem.Sun()

        # switch off ephem's atmospheric refraction correction by setting pressure to 0...
        self.observer.pressure = 0

        # calculate ut for events based on self.observer.date ==
        # local midnight ... start with twilight:

        # note: ephem's tuple() method returns seconds with a decimal fraction
        # which causes depreciation warnings when these tuples are used in
        # datetime operations... hence we'll truncate the seconds element manually
        # in the following assignments

        # naut. twilight (body center 12 deg below horizon):
        self.observer.horizon = '-12'
        try:
            t = self.observer.previous_setting(sun, use_center = True).tuple()
        except ephem.CircumpolarError:
            self.twilight['pm_end'] = None
        else:
            self.twilight['pm_end'] = t[:5] + (int(t[5]),)

        try:
            t = self.observer.next_rising(sun, use_center = True).tuple()
        except ephem.CircumpolarError:
            self.twilight['am_start'] = None
        else:
            self.twilight['am_start'] = t[:5] + (int(t[5]),)


        # now rise/set: moving horizon down 34' (as per US Naval Observatory standard)
        self.observer.horizon = '-0:34'
        try:
            t = self.observer.previous_setting(sun).tuple()
        except ephem.CircumpolarError:
            self.twilight['pm_start'] = None
        else:
            self.twilight['pm_start'] = t[:5] + (int(t[5]),)

        try:
            t = self.observer.next_rising(sun).tuple()
        except ephem.CircumpolarError:
            self.twilight['am_end'] = None
        else:
            self.twilight['am_end'] = t[:5] + (int(t[5]),)

        # and now... the planets (plus Moon)... horizon kept at -34'

        # save local midnight:
        localMidn = self.observer.date

        for bn in self.planets:

            body = ephem.__dict__[bn]()

            # look for events from previous local noon onwards
            self.observer.date = localMidn - 0.5

            # note that events may be out of order (e.g. setting before rising and
            # may happen more than 24 hrs after previous local noon

            # first rise
            try:
                t =  self.observer.next_rising(body).tuple()
            except ephem.CircumpolarError:
                self.planets[bn]['rise'] = None
                self.planets[bn]['rise_az'] = None
            else:
                self.planets[bn]['rise'] = t[:5] + (int(t[5]),)
                self.observer.date = self.planets[bn]['rise']
                body.compute(self.observer)
                self.planets[bn]['rise_az'] = Angle(body.az * 180 / pi)

            self.observer.date = localMidn - 0.5

            # then mer_pass
            try:
                t =  self.observer.next_transit(body).tuple()
            except ephem.CircumpolarError:
                self.planets[bn]['mer_pass'] = None
                self.planets[bn]['mer_pass_alt'] = None
            else:
                self.planets[bn]['mer_pass'] = t[:5] + (int(t[5]),)
                self.observer.date = self.planets[bn]['mer_pass']
                body.compute(self.observer)
                self.planets[bn]['mer_pass_alt'] = Angle(body.alt * 180 / pi)

            self.observer.date = localMidn - 0.5

            # and finally setting
            try:
                t =  self.observer.next_setting(body).tuple()
            except ephem.CircumpolarError:
                self.planets[bn]['set'] = None
                self.planets[bn]['set_az'] = None
            else:
                self.planets[bn]['set'] = t[:5] + (int(t[5]),)
                self.observer.date = self.planets[bn]['set']
                body.compute(self.observer)
                self.planets[bn]['set_az'] = Angle(body.az * 180 / pi)

        self.observer.date = localMidn


#----------------------------------------------------------------------------
#   Some utility functions
#----------------------------------------------------------------------------

def bigT(ut):
    """Returns number of days (incl. fraction) since 2000-01-01 12:00:00 UT; ut
    is a tuple (Y, M, D, h, m, s)
    """

    t = dt.datetime(*ut)

    utHrs = t.hour + t.minute/60.0 + t.second/3600.0

    # T = 367 * t.year - floor(1.75 * (t.year + floor((t.month+9)/12.0)))
    # T += floor(275 * t.month/9.0) + t.day + utHrs/24.0 - 730531.5
    refT = dt.datetime(2000, 1, 1, 12, 0, 0)

    deltaT = t - refT
    T = deltaT.days + float(deltaT.seconds)/(3600*24)

    return T


def normAngle(angle):
    """Returns angle with multiples of 360 removed; angle is float in degrees.
    Does not preserve sign: normAngle(-370) will return 350.
    """
    return 360 * (angle/360.0 - floor(angle/360.0))


def ghaAries(ut):
    """Returns GHA Aries for ut (Y, M, D, h, m, s) as degrees incl. decimal fraction
    """
    st = Angle()
    utcz = ephem.Observer()
    utcz.lon = 0
    utcz.date = ut
    st.rad = utcz.sidereal_time()

    return st.decD


def sha(ra):
    """Returns SHA for Right Ascension ra (in radians which is how ephem stores them).
    SHA is provided in degrees incl., decimal fraction.
    """
    return 360 - degrees(ra)


def gha(ra, ut):
    """Returns GHA for Right Ascension ra (in radians which is how ephem stores them)
    and ut as (Y, M, D, h, m, s). SHA is provided in degrees incl. decimal fraction.
    """
    return normAngle(ghaAries(ut) + sha(ra))


def hpMoon(sd):
    """Returns a float with horizontal parallax for moon in degrees (incl.
    decimal fraction) for a given semidiameter sd (in degrees). Formula taken
    from 2012 UK NA (Commercial Edition).
    """
    return sd / (0.2724)


def starNum(starName):
    """Returns an integer star number between 1 (Alpheratz) and 58 (Polaris)
    for each of the navigational stars. The numbering reflects a sorting of the
    57 standard navigational stars by descending SHA. Polaris is slapped on at
    the end despite its SHA in excess of 300deg so it does not upset the
    numbering. If the star name passed to starNum is not found in
    starcat.navStarNum the function returns None.
    """
    if starName in starcat.navStarNum.keys():
        return starcat.navStarNum[starName]
    else:
        return None

def starName(starNum):
    """Returns the name of star with number starNum in the Nautical Almanac for
    57 standard navigational stars plus Polaris as number 58.
    Returns None if starNum is not between 1 and 58 incl.
    """
    if starNum in starcat.navStarName.keys():
        return starcat.navStarName[starNum]
    else:
        return None


def localMidnightUT(lat, lon, ut):
    """Returns a tuple (Y, M, D, h, m, s) representing local midnight in UT at
    lat/lon based on ut: If ut is between sunset and sunrise (i.e. during local
    night) the function will return local midnight for the same night that ut
    is "in". If ut is between sunrise and sunset (i.e. during local day) the
    function will return local midnight for the night following self.ut.  lat,
    lon are in degress (incl. decimal fraction), ut is (Y, M, D, h, m, s)
    tuple.  My propagate ephem AlwaysUpError exception if sun is always
    above/below horizon.
    """
    sun = ephem.Sun()
    obs = ephem.Observer()
    obs.date = ut
    obs.lat = radians(lat)
    obs.lon = radians(lon)

    nsr = obs.next_rising(sun)
    nss = obs.next_setting(sun)

    if nss > nsr:       # self.ut during local night
        pat = obs.previous_antitransit(sun)
        pss = obs.previous_setting(sun)
        if pat > pss:   # pat is this night's midnight
            utMn = pat.tuple()
        else:
            utMn = obs.next_antitransit(sun).tuple()
    else:               # self.ut during local day
        utMn = obs.next_antitransit(sun).tuple()

    return utMn[:5] + (int(utMn[5]),)




if __name__ == '__main__':
    #    import doctest
    #    doctest.testmod( )

    pf = PlanetFinder(lat = -18, lon = -179, ut = (2013, 7, 25, 3, 30, 0))
    print ('Twilight:')
    for key in pf.twilight:
        try:
            print ('%s:  %s' % (key, dt.datetime(*pf.twilight[key]).ctime()))
        except:
            print ('%s: None' % key)

    print
    print ('Planets:')
    for p in pf.planets:
        for key in ['rise', 'set', 'mer_pass']:
            try:
                print ('%s - %s: %s' % (p, key, dt.datetime(*pf.planets[p][key]).ctime()))
            except:
                print ('%s - %s: None' % (p, key))
        for key in ['rise_az', 'set_az', 'mer_pass_alt']:
            try:
                print ('%s - %s: %d' % (p, key, int(round(pf.planets[p][key].decD))))
            except:
                print ('%s - %s: None' % (p, key))

    print (pf.observer.date)

    """
    for STAR_CALC in ['aa', 'ephem']:

        outFile = open(STAR_CALC + "_out.csv", 'w')

        for lat in [-30, 0, 30]:

            for date in [ (2012, 6, 30), (2014, 9, 30), (2016, 12, 31), (2018, 3, 31) ]:

                for h in range(24):

                    sf = StarFinder(list(starcat.navStarObj.keys()), lat = lat, lon = -178,
                        ut = date + (h, 0, 0))

                    for s in sf.starData:
                        sd = sf.starData[s]
                        outFile.write('%04d,%02d,%02d,%02d,%s,%02d,%s,%f,%f,%f,%f,%f\n' %
                                (date[0], date[1], date[2], h, Angle(lat).latStrDeg(),
                                    starcat.navStarNum[s], s, sd['sha'].decD,
                                    sd['dec'].decD, sd['mag'], sd['alt'].decD,
                                    sd['az'].decD))

        outFile.close()
    """

    """"
    aaOutFile = open("aa_out.csv", 'w')

    for lat in [-30, 0, 30]:
        for h in range(24):
            aaSf = aaStarFinder(lat = lat, lon = -178, ut = (2012, 06, 30, h, 0, 0))
            for i in range(58):
                sd = aaSf.starData[i]
                aaOutFile.write("%d, %d, %d, %f, %f, %f, %f, %f\n" % (lat, h, i+1,
                    sd['sha'].decD, sd['dec'].decD, sd['mag'], sd['alt'], sd['az']))

    aaOutFile.close()
    """

    """ old stuff
    a = AlmanacPage((2012, 9, 17))

    for h in range(24):
        print (a.sun['dec'][h])

    a.date = (2012, 5, 22)
    a.updateData()

    for h in range(24):
        print (a.sun['dec'][h])

    r = SunMoonRiseSet(lat = 0, lon = 0, date = (2012, 9, 17))

    print r
    """
    """
    f = Fix(COG = 145, SOG = 4.5, UT = (2013, 06, 28, 6, 2, 30))

    f.lopList.append(LOP(fix = f, body = "star", starName = "Arcturus", indexError = 0.0, heightOfEye = 1.8,
            lat = -(18+36.0/60), lon = -(178+56.0/60), elevation = 0, pressure = 1013, temp = 27))

    f.lopList[0].sightList.append(Sight(Hs = (43 + 39.5/60), UT = (2013, 06, 28, 05, 55, 33)))

    f.lopList.append(LOP(fix = f, body = "Venus", starName = None, indexError = 0.0, heightOfEye = 1.8,
            lat = -(18+36.0/60), lon = -(178+56.0/60), elevation = 0, pressure = 1013, temp = 27))

    f.lopList[1].sightList.append(Sight(Hs = (18 + 38.8/60), UT = (2013, 06, 28, 05, 45, 36)))

    f.lopList[0].lopSightIndex = 0
    f.lopList[1].lopSightIndex = 0

    for s in f.lopList:
        print
        s.lopSightIndex = 0
        s.calcIcAz()
        print (s, "\n")
        for a in s.sightList:
            print (a)

    f.calc2LOPFix()

    print ("\n", f, "\n")
    """
