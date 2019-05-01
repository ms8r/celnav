from celnav import celnav as cn


f = cn.Fix(COG=255, SOG=4.5, UT=(2012, 4, 12, 12, 8, 18))

f.lopList.append(cn.LOP(fix=f, body='star', starName='Rigil Kentaurus', indexError=2.6, heightOfEye=1.8,
        lat=-(7+46.0/60.), lon=-(102+13.0/60.), elevation=0, pressure=1010, temp=27))

f.lopList[0].sightList.append(cn.Sight(Hs=(20 + 44/60.), UT=(2012, 4, 12, 12, 8, 18)))

f.lopList.append(cn.LOP(fix=f, body='star', starName='Arcturus', indexError=2.6, heightOfEye=1.8,
        lat=-(7+46.0/60.), lon=-(102+13.0/60.), elevation=0, pressure=1010, temp=27))

f.lopList[1].sightList.append(cn.Sight(Hs=(21 + 35.8/60.), UT=(2012, 4, 12, 11, 56, 29)))

f.lopList[0].lopSightIndex = 0
f.lopList[1].lopSightIndex = 0

for lop in f.lopList:
    print
    lop.calcIcAz()
    print lop
    print
    for s in lop.sightList:
        print s

f.calc2LOPFix()

print
print f
print
