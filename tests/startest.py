"""
Generate test data for stars based on aa
"""

from __future__ import print_function

from math import pi
from math import degrees
import os
import re
import tempfile
import logging
import argparse


logging.basicConfig(level=logging.DEBUG)

AA_EXE_FILE = '/usr/bin/aa'
AA_STAR_CAT_FILE = '/usr/share/aa/star.cat'


def _conv_sha(raw):
    s = raw.replace('h', '').replace('m', '').replace("s", "").split()
    # convert RA hrs to rad:
    r = (float(s[0]) + float(s[1]) / 60 + float(s[2]) / 3600) * pi / 12.0

    return 360 - degrees(r)


def _conv_dec(raw):
    s = raw.replace('d', '').replace('"', '').replace("'", "").split()
    if len(s) == 4:
        offs = 1
        sign = -1
    else:
        offs = 0
        sign = 1

    return sign * (float(s[0 + offs]) + float(s[1 + offs]) / 60 +
            float(s[2 + offs]) / 3600)


DATA_COLS = [
    ('sha', r'^[ ]*Apparent:[ ]*R\.A\.[^0-9]*(?P<sha>[0-9][^s]*s)',
        _conv_sha),
    ('dec', r'^[ ]*Apparent[^D]*Dec\.[^0-9\-]*(?P<dec>[0-9\-][^"]*")',
        _conv_dec),
    ('mag', r'^approx\. visual magnitude (?P<mag>[-.0-9 ]*)',
        lambda k: float(k)),
    ('alt', r'^Topocentric:  Altitude (?P<alt>[^ ]*) deg, Azimuth [^ ]* deg$',
        lambda k: float(k)),
    ('az', r'^Topocentric:  Altitude [^ ]* deg, Azimuth (?P<az>[^ ]*) deg$',
        lambda k: float(k)),
]


def main(args):
    ut = tuple([int(i) for i in args.ut.split()])
    delta_t = args.deltat if abs(args.deltat) > 0.01 else 0

    # dictionary to match aa output lines containing R.A., declination, magnitude,
    # topocentric altitude and azimuth
    re_dict = {k: (re.compile(r), c) for k, r, c in DATA_COLS}

    stars = mk_star_list(AA_STAR_CAT_FILE)

    print('UT:\t%s' % args.ut)
    print('deltaT:\t%s' % args.deltat)
    print('lat:\t%s' % args.lat)
    print('lon:\t%s' % args.lon)
    print('hoe:\t%s' % args.hoe)
    print('temp:\t%s' % args.temp)
    print('pressure:\t%s' % args.pressure)
    print('---')
    print('star\t' + '\t'.join([k for k, _, _ in DATA_COLS]))
    for i, star in enumerate(stars):
        out = aa_stars(re_dict, AA_STAR_CAT_FILE, i + 1, ut, delta_t, args.lat,
                args.lon, args.hoe, args.temp, args.pressure)
        out = [str(out[key]) for key, _, _ in DATA_COLS]
        print(star + '\t' + '\t'.join(out))


def mk_star_list(star_cat):
    """
    Returns list of star names generated from aa star catalog `star_cat`.
    """
    star_name_re = re.compile(r'[^(]*\((?P<star>[^)]*)\)')
    out = []
    with open(star_cat) as fp:
        for line in fp:
            m = star_name_re.match(line)
            if m:
                out.append(m.group('star'))
    return out


def aa_stars(re_dict, starCatFile, starNum, ut=None, deltat=0, lat=0, lon=0,
        hoe=0, temp=20, pressure=1010):
    """
    Provides an interface to Sephen Moshier's aa program for star data.
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
    ut          -   Tuple (Y, M, D, h, m, s)
    deltat      -   deltaT in seconds (will be extrapolated for years > 2011 if
                    0)
    lat         -   Observer latitude in degress (incl. decimal fraction); S = -
    lon         -   Observer longitude in degress (incl. decimal fraction); E = -
    hoe         -   Height of eye in meters
    temp        -   Temperature in deg C
    pressure    -   Atmospheric pressure in mbar
    """

    AA_INI = 'aa.ini'
    AA_INPUT = 'aa.input'
    AA_OUTPUT = 'aa.out'

    if ut == None:
        ut = dt.datetime.utcnow().timetuple()[:6]

    # create and change into working directory and write aa.ini file
    current_dir = os.getcwd()
    aa_work_dir = tempfile.mkdtemp()
    os.chdir(aa_work_dir)

    with open(AA_INI, 'w') as fp:
        fp.write("%f\n" % lon)
        fp.write("%f\n" %  lat)
        fp.write("%.1f\n" % hoe)
        fp.write("%d\n" % int(round(temp)))
        fp.write("%d\n" % int(round(pressure)))
        fp.write("2\n")
        fp.write("%f\n" % deltat)

    with open(AA_INPUT, 'w') as fp:
        # first Y/M/D/h/m/s:
        for v in ut:
            fp.write("%d\n" % v)
        # 1 tabulation, 1 day intervall:
        fp.write("1\n1\n")
        # 88 for star and catalogue:
        fp.write("88\n%s\n" % starCatFile)
        # star number:
        fp.write("%d\n" % starNum)

    # call aa and write to aaOutfile:
    os.system(AA_EXE_FILE + ' < ' + AA_INPUT + ' > ' + AA_OUTPUT)

    # process aa output
    with open(AA_OUTPUT, 'r') as fp:
        out_dict = {}
        for line in fp:
            for key, (regex, conv) in re_dict.items():
                m = regex.match(line)
                if not m:
                    continue
                raw = line[m.start(key) : m.end(key)]
                out_dict[key] = conv(raw)

    # clean-up
    os.remove(AA_INI)
    os.remove(AA_INPUT)
    os.remove(AA_OUTPUT)
    os.rmdir(aa_work_dir)
    os.chdir(current_dir)

    return out_dict


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('--lat', type=float, default=0., help="""latitude as
            decimal fraction""")
    parser.add_argument('--lon', type=float, default=0., help="""longitude as
            decimal fraction""")
    parser.add_argument('--ut', required=True, help="""UT as string 'Y M D h m s'""")
    parser.add_argument('--deltat', type=float, default=0, help="""deltaT value as
            decimal fraction (extrapolated if 0)""")
    parser.add_argument('--hoe', type=float, default=0, help="""height of eye in
            meters""")
    parser.add_argument('--pressure', type=float, default=1010, help="""atmospheric
            pressure in mbar""")
    parser.add_argument('--temp', type=float, default=20, help="""temperature in
            deg Celsius""")

    args = parser.parse_args()
    main(args)
