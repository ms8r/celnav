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
