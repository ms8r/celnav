from __future__ import print_function
import pytest

from celnav import celnav as cn


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


def check_sights(sights, exp_results, labels=None):
    """
    Checks each `Sight` objects in list `sights` vs the parameter dicts in
    `exp_results` (a list). For `Angle` instances in a Sight the `decD` float
    value will be used. `labels` allows passing a list of IDs for each sight
    that will be printed in case of test failure to indicate which sight
    failed.
    """
    if labels is None:
        labels = range(1, len(sights) + 1)
    for label, exp_res, s in zip(labels, exp_results, sights):
        for key, val in exp_res.items():
            out = getattr(s, key)
            out = out.decD if isinstance(out, cn.Angle) else out
            assert out == pytest.approx(val, rel=1e-6), \
                    "Sight '{}': Sight assertion failed on {}".format(label,
                            key)





def test_Fix():
    """
    Sets up LOP and Sight, check Ic, Az, and short runf fix Ic.
    Data taken from Namani 2012 fixes calculated by spreadsheet.
    """
    def check_fix(fix_param, lop_params, sight_params, fix_exp_res,
            sight_exp_res_list):
        """
        Takes three dicts (resp. list of dicts for LOPs and Sights) with init
        paramaters for Fix, 2 LOPs, 2 Sights (one for each LOP). Last two args
        are expected results.
        """
        f = cn.Fix(**fix_param)
        for lop_param, sight_param in zip(lop_params, sight_params):
            f.lopList.append(cn.LOP(fix=f, **lop_param))
            f.lopList[-1].sightList.append(cn.Sight(**sight_param))
            f.lopList[-1].lopSightIndex = 0
            f.lopList[-1].calcIcAz()
        f.calc2LOPFix()
        for key, val in fix_exp_res.items():
            out = f.__dict__[key]
            out = out.decD if isinstance(out, cn.Angle) else out
            assert out == pytest.approx(val, rel=1e-6), \
                    'Fix assertion failed on {}'.format(key)
        sight_outputs = [lop.sightList[0].__dict__ for lop in f.lopList]
        for s_exp_res, s_output in zip(sight_exp_res_list, sight_outputs):
            for key, val in s_exp_res.items():
                out = s_output[key]
                out = out.decD if isinstance(out, cn.Angle) else out
                assert out == pytest.approx(val, rel=1e-6), \
                    'Sight assertion failed on {}'.format(key)

    #------------------------------------------------
    # source: Namani SightReduction+Fix_20120414_0130
    #------------------------------------------------
    fix_param = {
            'UT': (2012, 4, 14, 1, 42, 0),
            'COG': 260,
            'SOG': 5.5
    }
    fix_exp_res = {
            'lat': -8.2248923649,
            'lon': -105.298504556
            # note: almanac based manual calculation yields
            # lat == -8.223641,  lon == -105.299139
    }
    lop_params = [
            {'body': 'Venus', 'starName': None, 'indexError': 3.6,
                'heightOfEye': 1.8, 'lat': -8.233333333, 'lon': -105.35,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0},
            {'body': 'star', 'starName': 'Canopus', 'indexError': 3.6,
                'heightOfEye': 1.8, 'lat': -8.233333333, 'lon': -105.35,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0}
    ]
    sight_params = [
            {'Hs': 29.11666667, 'UT': (2012, 4, 14, 1, 24, 29)},
            {'Hs': 41.53333333, 'UT': (2012, 4, 14, 1, 29, 21)}
    ]
    sight_exp_res_list= [
            {'Ic': -3.2892414756, 'Az': 306.04014953, 'srfIc':
                -2.174642047},
            # note: almanac based manual calculation yields
            # Ic == -3.214669, srfIc == -2.10005
            {'Ic': -2.0294285228, 'Az': 198.89034115, 'srfIc':
                -1.469193470}
            # note: almanac based manual calculation yields
            # Ic == -2.088328, srfIc == -1.528076
    ]

    check_fix(fix_param, lop_params, sight_params, fix_exp_res,
            sight_exp_res_list)

    #------------------------------------------------
    # source: Namani SightReduction+Fix_20120414_1245
    #------------------------------------------------
    fix_param = {
            'UT': (2012, 4, 14, 12, 45, 0),
            'COG': 260,
            'SOG': 6.0
    }
    fix_exp_res = {
            'lat': -8.44568335689,
            'lon': -106.366544057
            # note: almanac based manual calculation yields
            # lat == -8.443068, lon == -106.367446
    }
    lop_params = [
            {'body': 'Moon LL', 'starName': None, 'indexError': 3.6,
                'heightOfEye': 1.8, 'lat': -8.316666667, 'lon': -106.3666667,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0},
            {'body': 'star', 'starName': 'Rigil Kentaurus', 'indexError': 3.6,
                'heightOfEye': 1.8, 'lat': -8.316666667, 'lon': -106.3666667,
                'elevation': 0.0, 'temp': 27.0, 'pressure': 1010.0}
    ]
    sight_params = [
            {'Hs': 66.49333333, 'UT': (2012, 4, 14, 12, 39, 48)},
            {'Hs': 19.58333333, 'UT': (2012, 4, 14, 12, 31, 53)}
    ]
    sight_exp_res_list= [
            {'Ic': 2.5918335371, 'Az': 105.870957909, 'srfIc': 2.12394842094},
            # note: almanac based manual calculation yields
            # Ic == 2.496984,  srfIc == 2.029086
            {'Ic': 6.04229687576, 'Az': 207.774381873, 'srfIc': 6.84576314265}
            # note: almanac based manual calculation yields
            # Ic == 5.928307,   srfIc == 6.731798
    ]

    check_fix(fix_param, lop_params, sight_params, fix_exp_res,
            sight_exp_res_list)


def test_sun_sights():
    """
    Test against four sunsights listed in *Celestial Navigation in the GPS Age*
    by John Karl. The four sights cover different LHA and Azimuth rule
    scenarios.
    """
    labels = ['NW of Hawaii', 'NE of Brisbane', 'SE of Canary Islands',
            'W of Australia']
    fix_param = {
            'UT': (2005, 5, 12, 0, 0, 0),
            'COG': 0.,
            'SOG': 0
    }
    lop_params = [
            {'body': 'Sun LL', 'starName': None, 'indexError': -3.2,
                'heightOfEye': 3.14, 'lat': 24.0, 'lon': -153.8233333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun LL', 'starName': None, 'indexError': -1.3,
                'heightOfEye': 2.6, 'lat': -24.0, 'lon': 161.5283333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun UL', 'starName': None, 'indexError': 2.4,
                'heightOfEye': 6.5, 'lat': 24.0, 'lon': -22.42, 'elevation':
                0.0, 'temp': 10.0, 'pressure': 1010.0},
            {'body': 'Sun LL', 'starName': None, 'indexError': -2.9,
                'heightOfEye': 4.6, 'lat': -24.0, 'lon': 112.1083333,
                'elevation': 0.0, 'temp': 10.0, 'pressure': 1010.0},
    ]
    sight_params = [
            {'Hs': 59.44833333, 'UT': (2005, 5, 11, 0, 19, 39)},
            {'Hs': 37.755, 'UT': (2005, 5, 12, 3, 18, 13)},
            {'Hs': 59.675, 'UT': (2005, 5, 10, 11, 18, 3)},
            {'Hs': 37.69166667, 'UT': (2005, 5, 11, 2, 19, 55)},
    ]
    exp_results = [
            {'Ic': 2.54888354105, 'Az': 264.53918248},
            {'Ic': 22.2824044642, 'Az': 320.561978656},
            {'Ic': -8.71465356815, 'Az': 95.7245069913},
            {'Ic': 3.46574723513, 'Az': 39.6443201504},
    ]

    f = cn.Fix(**fix_param)
    for lop_par, sight_par in zip(lop_params, sight_params):
        f.lopList.append(cn.LOP(fix=f, **lop_par))
        f.lopList[-1].sightList.append(cn.Sight(**sight_par))
        f.lopList[-1].lopSightIndex = 0
        f.lopList[-1].calcIcAz()
    sight_outputs = [lop.sightList[0].__dict__ for lop in f.lopList]
    for label, s_exp_res, s_output in zip(labels, exp_results, sight_outputs):
        for key, val in s_exp_res.items():
            out = s_output[key]
            out = out.decD if isinstance(out, cn.Angle) else out
            assert out == pytest.approx(val, rel=1e-6), \
                    '{}: Sight assertion failed on {}'.format(label, key)
