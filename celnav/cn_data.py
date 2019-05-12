"""
Builds required data for planets, stars, etc.
"""

from __future__ import division
from __future__ import print_function

import os
from skyfield.api import Loader
from skyfield.units import Distance

_data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'data')
_load = Loader(_data_dir)
planets = _load('de421.bsp')
ts = _load.timescale()

# from Henning Umland's guide (differs from skyfield/data/horizons.py):
_radii_km = [
    ('Sun', 696260.),
    ('Mercury', 2440.),
    ('Venus', 6052.),
    ('Earth', 6378.),
    ('Mars', 3397.),
    ('Jupiter', 71398.),
    ('Saturn', 60268.),
    ('Moon', 1378.),
]

radius = {name.lower().split()[-1]: Distance(km=r) for name, r in _radii_km}
