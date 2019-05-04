from __future__ import print_function
from math import degrees
from celnav import celnav as cn


f = cn.Fix(COG=260, SOG=6., UT=(2012, 4, 14, 12, 45, 0))

f.lopList.append(cn.LOP(fix=f, body='Moon LL', starName=None, indexError=3.6,
    heightOfEye=1.8, lat=-8.316666667, lon=-106.3666667, elevation=0,
    pressure=1010, temp=27))

f.lopList[0].sightList.append(cn.Sight(Hs=66.49333333, UT=(2012, 4, 14, 12, 39,
    48)))

f.lopList.append(cn.LOP(fix=f, body='star', starName='Rigil Kentaurus',
    indexError=3.6, heightOfEye=1.8, lat=-8.316666667, lon=-106.3666667,
    elevation=0, pressure=1010, temp=27))

f.lopList[1].sightList.append(cn.Sight(Hs=19.58333333, UT=(2012, 4, 14, 12, 31,
    53)))

f.lopList[0].lopSightIndex = 0
f.lopList[1].lopSightIndex = 0

for i, lop in enumerate(f.lopList):
    print('# LOP {}'.format(i + 1))
    print("'body': '{}',".format(lop.body))
    print("'starName': '{}',".format(lop.starName))
    print("'indexError': {},".format(lop.observer.indexError.decD * 60))
    print("'heightOfEye': {},".format(lop.observer.heightOfEye))
    print("'lat': {},".format(degrees(lop.observer.lat)))
    print("'lon': {},".format(degrees(lop.observer.lon)))
    print("'elevation': {},".format(lop.observer.elevation))
    print("'temp': {},".format(lop.observer.temp))
    print("'pressure': {},".format(lop.observer.pressure))
    lop.calcIcAz()
    for j, s in enumerate(lop.sightList):
        print('# Sight {}'.format(j + 1))
        print("'Hs': {},".format(s.Hs.decD))
        print("'UT': {},".format(s.UT))
        print('# Outputs')
        print("'Ic': {}".format(s.Ic))
        print("'Az': {}".format(s.Az.decD))
        print("'srfIc': {}".format(s.srfIc))
f.calc2LOPFix()
print('# Fix')
print("'UT': {}".format(f.UT))
print("'COG': {}".format(f.COG.decD))
print("'SOG': {}".format(f.SOG))
print('# Outputs')
print("'lat': {}".format(f.lat.decD))
print("'lon': {}".format(f.lon.decD))


