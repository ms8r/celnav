from celnav import celnav as cn



f = cn.Fix(COG=145, SOG=4.5, UT=(2013, 06, 28, 6, 2, 30))

f.lopList.append(cn.LOP(fix=f, body='star', starName='Arcturus', indexError=0.0, heightOfEye=1.8,
        lat=-(18+36.0/60), lon=-(178+56.0/60), elevation=0, pressure=1013, temp=27))

f.lopList[0].sightList.append(cn.Sight(Hs=(43 + 39.5/60), UT=(2013, 06, 28, 05, 55, 33)))

f.lopList.append(cn.LOP(fix=f, body='Venus', starName=None, indexError=0.0, heightOfEye=1.8,
        lat=-(18+36.0/60), lon=-(178+56.0/60), elevation=0, pressure=1013, temp=27))

f.lopList[1].sightList.append(cn.Sight(Hs=(18 + 38.8/60), UT=(2013, 06, 28, 05, 45, 36)))

f.lopList[0].lopSightIndex = 0
f.lopList[1].lopSightIndex = 0

for s in f.lopList:
    print
    s.lopSightIndex = 0
    s.calcIcAz()
    print s
    print
    for a in s.sightList:
        print a

f.calc2LOPFix()

print
print f
print
