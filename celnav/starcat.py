"""starcat: support module for celnav
Calls ephem to construct dictionary that has star names as keys and
maps the corresponding ephem star objects against these. Exports a fumction
'navStar()' that can be called with a star name as argument and will return the
corresponding ephem star object. Also exports:

    navStarNum  -   dictionary that contains a {star name : number} mapping
                    where 'number' is the star's number in the Nautical Almanac
                    (based on sequence of stars sorted by descending SHA). 

    navStarName -   dictionary that maps star names to their respective numbers
                    in the NA

The constant DB_SOURCE below determines which source will be used for star
catalogue data. The value for DB_SOURCE can be overwritten in celnav.ini. Valid
values are:

    'hip'       -   J2000 RA, Dec and proper motion parameters are taken from
                    hip_main.dat.

    'aa'        -   J2000 RA and Dec are taken from the output of Steve
                    Moshier's AA Ephemeris Program. Proper motion values for RA
                    and Dec are retained from hip_main.dat.

The 'aa' option provides a better match between apparent topocentric altitudes
computed by ephem vis-a-vis aa (see "Notes on Underlying Star Data" below).

__author__ = "markus@namaniatsea.net"
__version__ = "0.2.0"
__revision__ = "$Id: starcat.py,v 1.5 2013/08/02 06:14:55 markus Exp markus $"

NOTES ON UNDERLYING STAR DATA:

    The data in navStarDB below represents a subset of the star data included in
    the PyEphem distribution (file star.py, taking only navigational stars).
    This subset has been augmented by the follwing navigational stars that were
    missing in the PyEphem distribution:

        Acamar, Acrux, Adhara, Aldebara, Alkaid, Al Na'ir, Alpheratz, Ankaa,
        Atria, Avior, Diphda, Eltanin, Gacrux, Gienah, Hadar, Kaus Australis,
        Menkent, Miaplacidus, Mirfak, Rigil Kentaurus, Sabik, Suhail,
        Zubenelgenubi
    
    Data for these stars was taken from the hip_main.dat catalogue (downloaded
    in June 2013). Based on this data outputs from PyEphem and Steve
    Moshier's AA Ephemeris Program have been compared for the following
    parameters:
        
        Latitudes:  -30, 0, 30 deg
        Longitude:  -178 deg
        UT in hourly intervals from 0 to 23 on:
                    30JUN 2012, 
                    30SEP 2014, 
                    31DEC 2016, 
                    31MAR 2018

    Results:

        -   For apparent topocentric altitudes (Ha) >= 12 deg the difference
            between Ha output from ephem (based on 'hip' data) and aa is less
            than 0.25' with the exception of Rigil Kentaurus (up to 0.64') and
            Arcturus (up to 0.34'). These differences can be reduced to less
            than 0.15' for all stars if DB_SOURCE is set to 'aa'. 

        -   For Ha below 12deg the differences between ephem and aa outputs
            increase across virtually all stars as Ha approaches 0. For
            DB_SOURCE == 'hip'the max. difference is 0.82' (Rigil Kentaurus).
            For DB_SOURCE == 'aa' the max. difference is 0.35' (Achernar).

        -   For Ha values between 0 and -8 deg there are substantial
            differences between aa and ephem outputs across virtually all
            stars. For either DB_SOURCE ('hip' or 'aa') the max. difference
            reaches 87' at Ha values around -4 deg for a number of stars (no
            discernable pattern). For altitudes <= -8 deg the differences are
            in a range similar to the one for altitudes >= 12 deg for either
            DB_SOURCE. 

        -   For DB_SOURCE == 'hip' Arcturus is the only star for which values
            for declination differ by more than 0.25' between aa and ephem.
            Sirius and Procyon have differences in excess of 0.1' but less than
            0.25'. For DB_SOURCE == 'aa' Rigil Kentaurus is the only star with
            declination difference of more than 0.02' between aa and ephem
            outputs (0.057').

        -   For DB_SOURCE == 'hip' Rigil Kentaurus is the only star for which SHA
            values differ by more than 0.55' between aa and ephem (max. 1.2').
            Polaris shows differences up to 0.54', all other stars' differences
            remain below 0.2'. For DB_SOURCE == 'aa' Polaris shows a SHA
            difference of up to =.46', all other stars' differences remain
            below 0.05'.

        -   Values for magnitude of stars differ by more than 0.1 between aa
            and ephem for Acamar (aa: 3.4, ephem: 2.9) and Acrux (aa: 1.6,
            ephem: 0.9).

    In summary both data sources for ephem ('hip' and 'aa') should work for
    practical values of Ha (>= 12 deg), with DB_SOURCE == 'aa' giving a better
    match to the values published in/derived from the Nautical Almanac (given
    that ephem outputs for DB_SOURCE == 'aa' more closely track AA outputs
    which are said to have been tested extensively against NA data). Of course,
    'hip' may be right and the NA may be wrong....
    
    I have no idea what drives the big differences between ephem and aa outputs
    for both DB_SOURCE values at Ha around -4 deg (perhaps different refraction
    models?). 

    I'm also curious why the J2000 epoch RA and Dec values in hip are different
    from what's shown in aa (and presumably matches the USNO refernce data).
    This difference is most notable for Rigil Kentaurus:
    
        hip: 
            RA:     14:39:40.90
            Dec:    -60:50:06.5

        aa:
            RA:     14:39:35.967
            Dec:    -60:50:07.30

    If anyone can educate me regarding these differences I'd appreciate your
    comments at markus@namaniatsea.net - thanks!
""" 

import configparser
import ephem

# import cncfg to get access to ConfigParser obejct:
import celnav.cncfg as cncfg

SECTION_ID = 'starcat'

#-----------------------------------------------------------------------------
# The constant DB_SOURCE can be overritten in celnav.ini in section [starcat].
# Valid values are 'hip' for J2000 RA and Dec data from hip_main.dat or 'aa'
# for J2000 RA and Dec taken from aa output.
#-----------------------------------------------------------------------------
DB_SOURCE = 'hip'
if cncfg.cncfg.has_option(SECTION_ID, 'DB_SOURCE'):
    DB_SOURCE = cncfg.cncfg.get(SECTION_ID, 'DB_SOURCE')

if DB_SOURCE == 'hip':

    navStarDB = [
        (  7, "Acamar,f|S|A4,02:58:15.72|-53.53,-40:18:17.0|25.71,2.88,2000,0" ),
        (  5, "Achernar,f|S|B3,1:37:42.8|88.02,-57:14:12|-40.08,0.45,2000,0" ),
        ( 30, "Acrux,f|S|B1,12:26:35.9|-35.37,-63:05:56.73|-14.73,0.77,2000,0" ),
        ( 19, "Adhara,f|S|B2,6:58:37.6|2.63,-28:58:20|2.29,1.50,2000,0" ),
        ( 10, "Aldebaran,f|S|K5,4:35:55.2|62.78,16:30:35|-189.36,0.87,2000,0" ),
        ( 32, "Alioth,f|S|A0,12:54:01.6|111.74,55:57:35|-8.99,1.76,2000,0" ),
        ( 34, "Alkaid,f|S|B3,13:47:32.55|-121.23,49:18:47.9|-15.56,1.85,2000,0" ),
        ( 55, "Al Na'ir,f|S|B7,22:08:13.88|127.60,-46:57:38.2|-147.91,1.73,2000,0" ),
        ( 15, "Alnilam,f|S|B0,5:36:12.8|1.49,-1:12:07|-1.06,1.69,2000,0" ),
        ( 25, "Alphard,f|S|K3,9:27:35.3|-14.49,-8:39:31|33.25,1.99,2000,0" ),
        ( 41, "Alphecca,f|S|A0,15:34:41.2|120.38,26:42:54|-89.44,2.22,2000,0" ),
        (  1, "Alpheratz,f|S|B,00:08:23.17|135.68,29:05:27.0|-162.95,2.07,2000,0" ),
        ( 51, "Altair,f|S|A7,19:50:46.7|536.82,8:52:03|385.54,0.76,2000,0" ),
        (  2, "Ankaa,f|S|K0,00:26:16.87|232.76,-42:18:18.4|-353.64,2.40,2000,0" ),
        ( 42, "Antares,f|S|M1,16:29:24.5|-10.16,-26:25:55|-23.21,1.06,2000,0" ),
        ( 37, "Arcturus,f|S|K2,14:15:40.35|-1093.45,19:11:14.2|-1999.4,-0.05,2000,0" ),
        ( 43, "Atria,f|S|K2,16:48:39.87|17.85,-69:01:39.5|-32.92,1.91,2000,0" ),
        ( 22, "Avior,f|S|K3,8:22:30.86|-25.34,-59:30:34.3|22.72,1.86,2000,0" ),
        ( 13, "Bellatrix,f|S|B2,5:25:07.9|-8.75,6:20:59|-13.28,1.64,2000,0" ),
        ( 16, "Betelgeuse,f|S|M2,5:55:10.3|27.33,7:24:25|10.86,0.45,2000,0" ),
        ( 17, "Canopus,f|S|F0,6:23:57.1|19.99,-52:41:45|23.67,-0.62,2000,0" ),
        ( 12, "Capella,f|S|M1,5:16:41.3|75.52,45:59:57|-427.13,0.08,2000,0" ),
        ( 53, "Deneb,f|S|A2,20:41:25.9|1.56,45:16:49|1.55,1.25,2000,0" ),
        ( 28, "Denebola,f|S|A3,11:49:03.9|-499.02,14:34:20|-113.78,2.14,2000,0" ),
        (  4, "Diphda,f|S|K0,0:43:35.23|232.79,-17:59:12.1|32.71,2.04,2000,0" ),
        ( 27, "Dubhe,f|S|F7,11:03:43.8|-136.46,61:45:04|-35.25,1.81,2000,0" ),
        ( 14, "Elnath,f|S|B7,5:26:17.5|23.28,28:36:28|-174.22,1.65,2000,0" ),
        ( 47, "Eltanin,f|S|K5,17:56:36.38|-8.52,51:29:20.2|-23.05,2.24,2000,0" ),
        ( 54, "Enif,f|S|K2,21:44:11.14|30.02,9:52:30.0|1.38,2.38,2000,0" ),
        ( 56, "Fomalhaut,f|S|A3,22:57:38.8|329.22,-29:37:19|-164.22,1.17,2000,0" ),
        ( 31, "Gacrux,f|S|M4,12:31:09.93|27.94,-57:06:45.2|-264.33,1.59,2000,0" ),
        ( 29, "Gienah,f|S|B8,12:15:48.5|-159.58,-17:32:31|22.31,2.58,2000,0" ),
        ( 35, "Hadar,f|S|B1,14:03:49.44|-33.96,-60:22:22.7|-25.06,0.61,2000,0" ),
        (  6, "Hamal,f|S|K2,2:07:10.3|190.73,23:27:46|-145.77,2.01,2000,0" ),
        ( 48, "Kaus Australis,f|S|B9,18:24:10.4|-39.61,-34:23:04|-124.05,1.79,2000,0" ),
        ( 40, "Kochab,f|S|K4,14:50:42.4|-32.29,74:09:20|11.91,2.07,2000,0" ),
        ( 57, "Markab,f|S|B9,23:04:45.6|61.1,15:12:19|-42.56,2.49,2000,0" ),
        (  8, "Menkar,f|S|M2,3:02:16.8|-11.81,4:05:24|-78.76,2.54,2000,0" ),
        ( 36, "Menkent,f|S|K0,14:06:41.32|-519.29,-36:22:07.3|-517.87,2.06,2000,0" ),
        ( 24, "Miaplacidus,f|S|A2,9:13:12.24|-157.66,-69:43:02.9|108.91,1.67,2000,0" ),
        (  9, "Mirfak,f|S|F5,3:24:19.35|24.11,49:51:40.5|-26.01,1.79,2000,0" ),
        ( 50, "Nunki,f|S|B2,18:55:15.9|13.87,-26:17:48|-52.65,2.05,2000,0" ),
        ( 52, "Peacock,f|S|B2,20:25:38.9|7.71,-56:44:06|-86.15,1.94,2000,0" ),
        ( 58, "Polaris,f|S|F7,2:31:47.1|44.22,89:15:51|-11.74,1.97,2000,0" ),
        ( 21, "Pollux,f|S|K0,7:45:19.4|-625.69,28:01:35|-45.95,1.16,2000,0" ),
        ( 20, "Procyon,f|S|F5,7:39:18.5|-716.57,5:13:39|-1034.58,0.40,2000,0" ),
        ( 46, "Rasalhague,f|S|A5,17:34:56.0|110.08,12:33:38|-222.61,2.08,2000,0" ),
        ( 26, "Regulus,f|S|B7,10:08:22.5|-249.4,11:58:02|4.91,1.36,2000,0" ),
        ( 11, "Rigel,f|S|B8,5:14:32.3|1.87,-8:12:06|-0.56,0.18,2000,0" ),
        ( 38, "Rigil Kentaurus,f|S|G2,14:39:40.90|-3678.19,-60:50:06.5|481.84,-0.01,2000,0" ),
        ( 44, "Sabik,f|S|A2,17:10:22.66|41.16,-15:43:30.5|97.65,2.43,2000,0" ),
        (  3, "Schedar,f|S|K0,0:40:30.4|50.36,56:32:15|-32.17,2.24,2000,0" ),
        ( 45, "Shaula,f|S|B1,17:33:36.5|-8.9,-37:06:13|-29.95,1.62,2000,0" ),
        ( 18, "Sirius,f|S|A0,6:45:09.3|-546.01,-16:42:47|-1223.08,-1.44,2000,0" ),
        ( 33, "Spica,f|S|B1,13:25:11.6|-42.5,-11:09:40|-31.73,0.98,2000,0" ),
        ( 23, "Suhail,f|S|K4,09:07:59.78|-23.21,-43:25:57.4|14.28,2.23,2000,0" ),
        ( 49, "Vega,f|S|A0,18:36:56.2|201.02,38:46:59|287.46,0.03,2000,0" ),
        ( 39, "Zubenelgenubi,f|S|A3,14:50:52.78|-105.69,-16:02:29.8|-69.00,2.75,2000,0" )
    ]

elif DB_SOURCE == 'aa':

    # RA and Dec modified to match aa output:
    navStarDB = [
        (  7, "Acamar,f|S|A4,2:58:15.694|-53.53,-40:18:16.99|25.71,2.88,2000,0" ),
        (  5, "Achernar,f|S|B3,1:37:42.850|88.02,-57:14:12.19|-40.08,0.45,2000,0" ),
        ( 30, "Acrux,f|S|B1,12:26:35.871|-35.37,-63:05:56.58|-14.73,0.77,2000,0" ),
        ( 19, "Adhara,f|S|B2,6:58:37.548|2.63,-28:58:19.50|2.29,1.50,2000,0" ),
        ( 10, "Aldebaran,f|S|K5,4:35:55.235|62.78,16:30:33.38|-189.36,0.87,2000,0" ),
        ( 32, "Alioth,f|S|A0,12:54:01.749|111.74,55:57:35.47|-8.99,1.76,2000,0" ),
        ( 34, "Alkaid,f|S|B3,13:47:32.437|-121.23,49:18:47.93|-15.56,1.85,2000,0" ),
        ( 55, "Al Na'ir,f|S|B7,22:08:13.997|127.60,-46:57:39.58|-147.91,1.73,2000,0" ),
        ( 15, "Alnilam,f|S|B0,5:36:12.809|1.49,-1:12:07.02|-1.06,1.69,2000,0" ),
        ( 25, "Alphard,f|S|K3,9:27:35.248|-14.49,-8:39:31.16|33.25,1.99,2000,0" ),
        ( 41, "Alphecca,f|S|A0,15:34:41.278|120.38,26:42:52.91|-89.44,2.22,2000,0" ),
        (  1, "Alpheratz,f|S|B,0:08:23.263|135.68,29:05:25.57|-162.95,2.07,2000,0" ),
        ( 51, "Altair,f|S|A7,19:50:46.999|536.82,8:52:05.93|385.54,0.76,2000,0" ),
        (  2, "Ankaa,f|S|K0,0:26:17.027|232.76,-42:18:21.82|-353.64,2.40,2000,0" ),
        ( 42, "Antares,f|S|M1,16:29:24.440|-10.16,-26:25:55.15|-23.21,1.06,2000,0" ),
        ( 37, "Arcturus,f|S|K2,14:15:39.682|-1093.45,19:10:56.67|-1999.4,-0.05,2000,0" ),
        ( 43, "Atria,f|S|K2,16:48:39.871|17.85,-69:01:39.81|-32.92,1.91,2000,0" ),
        ( 22, "Avior,f|S|K3,8:22:30.833|-25.34,-59:30:34.51|22.72,1.86,2000,0" ),
        ( 13, "Bellatrix,f|S|B2,5:25:07.856|-8.75,6:20:58.73|-13.28,1.64,2000,0" ),
        ( 16, "Betelgeuse,f|S|M2,5:55:10.307|27.33,7:24:25.35|10.86,0.45,2000,0" ),
        ( 17, "Canopus,f|S|F0,6:23:57.119|19.99,-52:41:44.52|23.67,-0.62,2000,0" ),
        ( 12, "Capella,f|S|M1,5:16:41.351|75.52,45:59:52.92|-427.13,0.08,2000,0" ),
        ( 53, "Deneb,f|S|A2,20:41:25.917|1.56,45:16:49.31|1.55,1.25,2000,0" ),
        ( 28, "Denebola,f|S|A3,11:49:03.585|-499.02,14:34:19.33|-113.78,2.14,2000,0" ),
        (  4, "Diphda,f|S|K0,0:43:35.368|232.79,-17:59:11.84|32.71,2.04,2000,0" ),
        ( 27, "Dubhe,f|S|F7,11:03:43.670|-136.46,61:45:03.22|-35.25,1.81,2000,0" ),
        ( 14, "Elnath,f|S|B7,5:26:17.511|23.28,28:36:26.67|-174.22,1.65,2000,0" ),
        ( 47, "Eltanin,f|S|K5,17:56:36.367|-8.52,51:29:20.19|-23.05,2.24,2000,0" ),
        ( 54, "Enif,f|S|K2,21:44:11.164|30.02,9:52:29.92|1.38,2.38,2000,0" ),
        ( 56, "Fomalhaut,f|S|A3,22:57:39.046|329.22,-29:37:20.12|-164.22,1.17,2000,0" ),
        ( 31, "Gacrux,f|S|M4,12:31:09.929|27.94,-57:06:47.50|-264.33,1.59,2000,0" ),
        ( 29, "Gienah,f|S|B8,12:15:48.366|-159.58,-17:32:30.97|22.31,2.58,2000,0" ),
        ( 35, "Hadar,f|S|B1,14:03:49.410|-33.96,-60:22:22.79|-25.06,0.61,2000,0" ),
        (  6, "Hamal,f|S|K2,2:07:10.400|190.73,23:27:44.65|-145.77,2.01,2000,0" ),
        ( 48, "Kaus Australis,f|S|B9,18:24:10.327|-39.61,-34:23:04.73|-124.05,1.79,2000,0" ),
        ( 40, "Kochab,f|S|K4,14:50:42.352|-32.29,74:09:19.76|11.91,2.07,2000,0" ),
        ( 57, "Markab,f|S|B9,23:04:45.656|61.1,15:12:18.89|-42.56,2.49,2000,0" ),
        (  8, "Menkar,f|S|M2,3:02:16.773|-11.81,4:05:22.93|-78.76,2.54,2000,0" ),
        ( 36, "Menkent,f|S|K0,14:06:40.955|-519.29,-36:22:12.04|-517.87,2.06,2000,0" ),
        ( 24, "Miaplacidus,f|S|A2,9:13:11.961|-157.66,-69:43:01.98|108.91,1.67,2000,0" ),
        (  9, "Mirfak,f|S|F5,3:24:19.363|24.11,49:51:40.35|-26.01,1.79,2000,0" ),
        ( 50, "Nunki,f|S|B2,18:55:15.924|13.87,-26:17:48.23|-52.65,2.05,2000,0" ),
        ( 52, "Peacock,f|S|B2,20:25:38.852|7.71,-56:44:06.38|-86.15,1.94,2000,0" ),
        ( 58, "Polaris,f|S|F7,2:31:48.675|44.22,89:15:50.72|-11.74,1.97,2000,0" ),
        ( 21, "Pollux,f|S|K0,7:45:18.948|-625.69,28:01:34.27|-45.95,1.16,2000,0" ),
        ( 20, "Procyon,f|S|F5,7:39:18.117|-716.57,5:13:29.97|-1034.58,0.40,2000,0" ),
        ( 46, "Rasalhague,f|S|A5,17:34:56.077|110.08,12:33:36.11|-222.61,2.08,2000,0" ),
        ( 26, "Regulus,f|S|B7,10:08:22.317|-249.4,11:58:01.88|4.91,1.36,2000,0" ),
        ( 11, "Rigel,f|S|B8,5:14:32.268|1.87,-8:12:05.99|-0.56,0.18,2000,0" ),
        ( 38, "Rigil Kentaurus,f|S|G2,14:39:35.967|-3678.19,-60:50:07.30|481.84,-0.01,2000,0" ),
        ( 44, "Sabik,f|S|A2,17:10:22.682|41.16,-15:43:29.72|97.65,2.43,2000,0" ),
        (  3, "Schedar,f|S|K0,0:40:30.448|50.36,56:32:14.46|-32.17,2.24,2000,0" ),
        ( 45, "Shaula,f|S|B1,17:33:36.534|-8.9,-37:06:13.72|-29.95,1.62,2000,0" ),
        ( 18, "Sirius,f|S|A0,6:45:08.871|-546.01,-16:42:58.23|-1223.08,-1.44,2000,0" ),
        ( 33, "Spica,f|S|B1,13:25:11.588|-42.5,-11:09:40.72|-31.73,0.98,2000,0" ),
        ( 23, "Suhail,f|S|K4,9:07:59.777|-23.21,-43:25:57.39|14.28,2.23,2000,0" ),
        ( 49, "Vega,f|S|A0,18:36:56.332|201.02,38:47:01.06|287.46,0.03,2000,0" ),
        ( 39, "Zubenelgenubi,f|S|A3,14:50:52.716|-105.69,-16:02:30.43|-69.00,2.75,2000,0" )
    ]


navStarObj = {}
navStarNum = {}
navStarName = {}

def build_navStars():

    global navStarObj, navStarNum, navStarName
    
    for line in navStarDB:
        star = ephem.readdb(line[1])
        navStarObj[star.name] = star
        navStarNum[star.name] = line[0]
        navStarName[line[0]] = star.name


build_navStars()
del build_navStars
del navStarDB

def navStar(name, *args, **kwargs):
    star = navStarObj[name].copy()
    if args or kwargs:
        star.compute(*args, **kwargs)
    return star
