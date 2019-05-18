from __future__ import print_function
import pytest

from celnav import celnav as cn
from celnav import cn_data as DATA


def test_Angle():
    """
    Tests for `Angle` class in celnav
    """

    # basics, incl. removal of 360 multiples:
    a = cn.Angle(-742.5)
    b = cn.Angle(192.4)

    assert a.decD == pytest.approx(-22.5)
    assert b.decD == pytest.approx(192.4)
    assert a.rad == pytest.approx(-0.39269908169872414)
    assert b.rad == pytest.approx(3.3580134808370903)
    assert a.degMin == (22, pytest.approx(30.0), -1)
    assert b.degMin == (192, pytest.approx(24.0), 1)
    assert a.latStr() == 'S 22 30.0'
    assert b.latStr() == 'N 192 24.0'
    assert a.latStrDeg() == 'S23'
    assert b.latStrDeg() == 'N192'
    assert a.lonStr() == 'W 022 30.0'
    assert b.lonStr() == 'E 192 24.0'
    assert a.absStr() == '22 30.0'
    assert b.absStr() == '192 24.0'
    assert a.signStr() == '-22 30.0'
    assert b.signStr() == '+192 24.0'
    assert a.intStr() == '-23'
    assert b.intStr() == '192'

    # edge case:
    c = cn.Angle(180.)
    assert c.lonStr() == 'E 180 00.0'

    # updates:
    a.decD += 45
    assert a.decD == pytest.approx(22.5)
    assert a.rad == pytest.approx(0.39269908169872414)
    assert a.degMin == (22, pytest.approx(30.0), 1)

    b.rad -= 0.3
    assert b.rad == pytest.approx(3.0580134808370903)
    assert b.decD == pytest.approx(175.21126614607533)
    assert b.degMin == (175, pytest.approx(12.675968764519894), 1)


def test_ghaAries():
    # `data`: time tuple, scale, exp. res. degrees, exp. res. minutes (rounded
    # to 1 decimal) expected result taken from 2005 Nautical Almanac
    data = [((2005, 5, 10, 15, 0, 0), 'ut1', 93, 30.5),
            ((2005, 5, 10, 15, 0, 0.6030142307281494), 'utc', 93, 30.5),
            ((2005, 5, 12, 3, 0, 0), 'ut1', 274, 59.2),]
    for time, scale, exp_deg, exp_minutes in data:
        gha_aries =  cn.ghaAries(time, scale)
        gha_deg = int(gha_aries)
        gha_minutes = (gha_aries - gha_deg) * 60.
        assert gha_deg == exp_deg
        assert round(gha_minutes, 1) == pytest.approx(exp_minutes)

def test_semidiameter():
    # `data`: target body, time of observation, eexpected SD in arc min
    # Needs more data points, also for topocentric SD!
    data = [(DATA.planets['sun'], DATA.ts.ut1(2005, 5, 11, 12, 0, 0), 15.9),
            (DATA.planets['sun'], DATA.ts.ut1(2018, 1, 4, 12, 0, 0), 16.3),
            (DATA.planets['moon'], DATA.ts.ut1(2005, 5, 10, 12, 0, 0), 15.1),
            (DATA.planets['moon'], DATA.ts.ut1(2005, 5, 11, 12, 0, 0), 15.0),
            (DATA.planets['moon'], DATA.ts.ut1(2005, 5, 12, 12, 0, 0), 14.9),
    ]
    for body, t, exp_sd in data:
        sd = cn.semidiameter(body, t)
        assert round(sd, 1) == pytest.approx(exp_sd)


def setup_fix(fix_param, lop_params, sight_params):
    """
    Takes three dicts (resp. list of dicts for LOPs and Sights) with init
    paramaters for Fix, LOPs, and Sights (one for each LOP).
    Calls `calcIcAz` on each sight and returns the `Fix` object.
    """
    f = cn.Fix(**fix_param)
    for lop_param, sight_param in zip(lop_params, sight_params):
        f.lopList.append(cn.LOP(fix=f, **lop_param))
        f.lopList[-1].sightList.append(cn.Sight(**sight_param))
        f.lopList[-1].lopSightIndex = 0
        f.lopList[-1].calcIcAz()
    return f


def check_outputs(objects, exp_results, labels=None):
    """
    Checks each object in list `objects` vs the parameter dicts in
    `exp_results` (a list). For `Angle` instances in an object the `decD` float
    value will be used. `labels` allows passing a list of IDs for each object
    that will be printed in case of test failure to indicate which object
    failed.
    """
    if labels is None:
        labels = range(1, len(objects) + 1)
    for lbl, exp_res, obj in zip(labels, exp_results, objects):
        for key, val in exp_res.items():
            out = getattr(obj, key)
            out = out.decD if isinstance(out, cn.Angle) else out
            assert out == pytest.approx(val, rel=1e-6), \
                    "{} '{}': assertion failed on {}".format(
                            obj.__class__.__name__, lbl, key)

@pytest.mark.skip
def test_Fix():
    """
    Sets up LOP and Sight, check Ic, Az, and short runf fix Ic.
    Data taken from Namani 2012 fixes calculated by spreadsheet.
    """

    fix_labels = ['SightReduction+Fix_20120414_0130',
                  'SightReduction+Fix_20120414_1245',
    ]
    fix_params = [
            {'utc': (2012, 4, 14, 1, 42, 0), 'COG': 260, 'SOG': 5.5},
            {'utc': (2012, 4, 14, 12, 45, 0), 'COG': 260, 'SOG': 6.0},
    ]
    fix_exp_res = [
            # note: almanac based manual calculation yields
            # lat == -8.223641,  lon == -105.299139
            {'lat': -8.2248923649, 'lon': -105.298504556},
            # note: almanac based manual calculation yields
            # lat == -8.443068, lon == -106.367446
            {'lat': -8.44568335689, 'lon': -106.366544057},
    ]
    lop_params = [
            [{'body': 'Venus', 'starName': None, 'indexError': 3.6,
                'hoe': 1.8, 'lat': -8.233333333, 'lon': -105.35,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0},
             {'body': 'star', 'starName': 'Canopus', 'indexError': 3.6,
                'hoe': 1.8, 'lat': -8.233333333, 'lon': -105.35,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0}],
            [{'body': 'Moon LL', 'starName': None, 'indexError': 3.6,
                'hoe': 1.8, 'lat': -8.316666667, 'lon': -106.3666667,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0},
             {'body': 'star', 'starName': 'Rigil Kentaurus', 'indexError': 3.6,
                'hoe': 1.8, 'lat': -8.316666667, 'lon': -106.3666667,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0}]
    ]
    sight_params = [
            [{'Hs': 29.11666667, 'utc': (2012, 4, 14, 1, 24, 29)},
             {'Hs': 41.53333333, 'utc': (2012, 4, 14, 1, 29, 21)}],
            [{'Hs': 66.49333333, 'utc': (2012, 4, 14, 12, 39, 48)},
             {'Hs': 19.58333333, 'utc': (2012, 4, 14, 12, 31, 53)}]
    ]
    sight_exp_results= [
            [# note: almanac based manual calculation yields
             # Ic == -3.214669, srfIc == -2.10005
             {'Ic': -3.2892414756, 'Az': 306.04014953, 'srfIc':
                 -2.174642047},
             # note: almanac based manual calculation yields
             # Ic == -2.088328, srfIc == -1.528076
             {'Ic': -2.0294285228, 'Az': 198.89034115, 'srfIc':
                 -1.469193470}],
            [# note: almanac based manual calculation yields
             # Ic == 2.496984,  srfIc == 2.029086
             {'Ic': 2.5918335371, 'Az': 105.870957909, 'srfIc':
                 2.12394842094},
             # note: almanac based manual calculation yields
             # Ic == 5.928307,   srfIc == 6.731798
             {'Ic': 6.04229687576, 'Az': 207.774381873, 'srfIc':
                 6.84576314265}]
    ]

    for f_lbl, fix_par, lop_par, sight_par, f_exp_res, s_exp_res in zip(
            fix_labels, fix_params, lop_params, sight_params, fix_exp_res,
            sight_exp_results):
        f = setup_fix(fix_par, lop_par, sight_par)
        # check sight outputs Ic, Az, srfIc:
        sights = [lop.sightList[0] for lop in f.lopList]
        labels = ['{} - {}'.format(f_lbl, lop.starName if lop.starName else
            lop.body) for lop in f.lopList]
        check_outputs(sights, s_exp_res, labels)
        # check fix lat/lon
        f.calc2LOPFix()
        check_outputs([f], [f_exp_res], [f_lbl])


@pytest.mark.skip
def test_sun_sights():
    """
    Test against four sunsights listed in *Celestial Navigation in the GPS Age*
    by John Karl. The four sights cover different LHA and Azimuth rule
    scenarios.
    """
    labels = ['NW of Hawaii', 'NE of Brisbane', 'SE of Canary Islands',
            'W of Australia']
    # dummy fix
    fix_param = {
            'utc': (2005, 5, 12, 0, 0, 0),
            'COG': 0.,
            'SOG': 0
    }
    lop_params = [
            {'body': 'Sun LL', 'starName': None, 'indexError': -3.2,
                'hoe': 3.14, 'lat': 24.0, 'lon': -153.8233333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun LL', 'starName': None, 'indexError': -1.3,
                'hoe': 2.6, 'lat': -24.0, 'lon': 161.5283333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun UL', 'starName': None, 'indexError': 2.4,
                'hoe': 6.5, 'lat': 24.0, 'lon': -22.42, 'elevation':
                0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun LL', 'starName': None, 'indexError': -2.9,
                'hoe': 4.6, 'lat': -24.0, 'lon': 112.1083333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
    ]
    sight_params = [
            # Examples in Karl's book have ties in UT with whole seconds;
            # converted to utc below.
            {'Hs': 59.44833333, 'utc': (2005, 5, 11, 0, 19, 39.6)},
            {'Hs': 37.755, 'utc': (2005, 5, 12, 3, 18, 13.6)},
            {'Hs': 59.675, 'utc': (2005, 5, 10, 11, 18, 3.6)},
            {'Hs': 37.69166667, 'utc': (2005, 5, 11, 2, 19, 55.6)},
    ]
    exp_results = [
            {'Ic': 2.54888354105, 'Az': 264.53918248},
            {'Ic': 22.2824044642, 'Az': 320.561978656},
            {'Ic': -8.71465356815, 'Az': 95.7245069913},
            {'Ic': 3.46574723513, 'Az': 39.6443201504},
    ]

    f = setup_fix(fix_param, lop_params, sight_params)
    sights = [lop.sightList[0] for lop in f.lopList]
    check_outputs(sights, exp_results, labels)
