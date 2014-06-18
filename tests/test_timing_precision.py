#! /usr/bin/env python2
import time, os, numpy as N, pylab as P

f = open('/dev/random', 'r')

dt = []
err = []
for i in range(250):
    t0 = time.time()
    f.seek(0); f.read(4)
    t1 = time.time()
    f.seek(0); f.read(4)
    t2 = time.time()
    err.append(t1-.5*(t0+t2))
    dt.append(t1 - t0)
    dt.append(t2 - t1)

dt = N.array(dt) * 1e3
err = N.array(err) * 1e3

print 'dT Average:', N.average(dt), 'ms'
print 'dT Sigma:', N.std(dt), 'ms'
print
print 'eT Average:', N.average(err), 'ms'
print 'eT Sigma:', N.std(err), 'ms'
dthist,dtbins = N.histogram(dt, bins=100)
erhist,erbins = N.histogram(err, bins=100)
P.subplot(121)
P.bar(dtbins[:-1], dthist, width=dtbins[1]-dtbins[0], log=True)
P.subplot(122)
P.bar(erbins[:-1], erhist, width=erbins[1]-erbins[0], log=True)
P.show()
