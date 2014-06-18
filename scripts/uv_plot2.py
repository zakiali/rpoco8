#!/usr/bin/env python2
import aipy as A
import numpy as N
import optparse, sys, math
import matplotlib
import pylab as p
import time
'''This program integrates along spectra stored in uv files and across uv files. various options in for plotting ( use -h)'''
o = optparse.OptionParser()
A.scripting.add_standard_options(o, ant=True)
o.add_option('-m','--mode', dest = 'mode', type= 'string', help = 'different plotting modes. log scale by default. r = real part, i = imag part, a = amplitude, db = db')
o.add_option('-x','--xmode', dest = 'xmode', type= 'string', help = 'different plotting modes for x-axis. frequency by default(accurate only for poco).ch = channel')
o.add_option('-i', '--integrations', dest='num', type='string', help='pick number of files to integrate')
o.add_option('--reim',dest = 'reim', action = 'store_true', help = 'make real,imaginary plot')
o.add_option('--xtalk',dest = 'xtalk', action = 'store_true', help = 'plot corr coeff in dB. only works on one base line with both autos given.')
opts,args = o.parse_args(sys.argv[1:])
print args
print A.scripting.parse_ants(opts.ant,8)
NANT = 8
NCHAN = 1024
ANTS = 'abcdefgh'
BLS = [ai+aj for i,ai in enumerate(ANTS) for aj in ANTS[i:]]

freq = N.arange(1024,dtype = float)
c = 100/1024.
freq = freq*c
freq = freq + 100
#p.figure()
#ax1 = p.subplot(121)
#ax2 = p.subplot(122)
#ax1.get_xtitle='frequency (MHz)'
#ax1.ytitle='log(power)'
#ax1.title='power vs frequncy'
#ax2.xtitle='frequency (MHz)'
#ax2.ytitle='phase'
#ax2.title='phase vs frequency'

psum = {}
for i in BLS:
    psum['%d%d' %((ANTS.index(i[0])),(ANTS.index(i[1])))] = N.zeros(1024, dtype=N.complex64)
    #psum['%d%d_avg' %((ANTS.index(i[0])),(ANTS.index(i[1])))] = []
#psum['all'] = [zeros,0]
#psum['al'] = zeros
def convert_arg(arg):
    '''returns argument in a more suitable form'''
    arg = arg.split(',')
    return arg

def get_data():
    '''Goes through uv file for a single baseline and averages all the data for that base       line. '''
    f = 0
    for uvfile in args:
        c = 0
        print 'Reading', uvfile
        uv = A.miriad.UV(uvfile)
        #A.scripting.uv_selector(uv, ante)
        for (uvw, t, (i,j)), d, flag in uv.all(raw=True):
            bl = '%d%d' %(i,j)
            psum[bl] += d
            c+=1
    #        if c %100 == 0:
    #            psum[bl+'_avg'].append(math.log10((psum[bl]/c).mean()))
    #    if opts.all != True : psum['%d%d' %(i,j)] /= c
#        if opts.all == True:
#            psum['all'][0] += psum['%d%d'%(i,j)]
#            psum['all'][1] += c
#            if uvfile == args[-1]:
#                psum['all'][0] /= psum['all'][1]
#                psum['al'] = psum['all'][0]
        print c
        del(uv)
        f+=1
        if str(f) == opts.num:
         #   print f
            break
    print f
        #if opts.all != True:plot(ante,f)
    #if opts.all == True:plot('all', 1)
    #if opts.xtalk == True:
    #    p.figure(2)
    #    p.plot(psum['04_avg'])
def plot(ante):
    d = psum[ante[0]+ante[2]]
    #mask = d.mask
    #w = N.where(mask != True)
    #w = w[0]
    #data = d.data[w[0]:w[-1]+1]
    #x_axis = N.arange(NCHAN)[w[0]:w[-1]+1]
    #y_axis = data
    #y_axis = N.log10(data)
    if opts.xmode == 'ch': freq = N.arange(1024)[::-1]
    else:
        freq = N.arange(1024,dtype = float)
        c = 100/1024.
        freq = freq*c
        freq = freq + 100
    p.subplot(121)
    p.plot(freq,N.angle(d,deg=1)[::-1],'.',label = 'line %s'%ante)
    p.xlabel('frequency (MHz)')
    p.ylabel('Phase (degrees)')
    p.title('Phase vs frequency')
#    p.legend(loc='best')
    p.subplot(122)
    if opts.reim == True:
        p.plot(N.real(d[::-1]),N.imag(d[::-1]),'.',label = 'line %s'%ante)
        print 'minimum of real=', min(N.abs(N.real(d)))
        print 'minimum of imag=',min(N.abs(N.imag(d)))
        print 'minimumof absolute=',min(N.abs(d))
        p.ylabel('Imaginary')
        p.xlabel('Real')
        p.title('The real...imaginary plot')
        leg=p.legend(loc='best')
    else:
        if opts.mode == 'a':p.plot(freq,N.abs(d)[::-1],label = 'line %s'%ante)
        elif opts.mode == 'r':p.plot(freq,N.real(d)[::-1],label = 'line %s'%ante)
        elif opts.mode == 'i':p.plot(freq,N.imag(d)[::-1],label = 'line %s'%ante)
        #fix : need to fix db plot.
        #elif opts.mode == 'db':p.plot(freq,10*N.log10(N.abs(d))[::-1], label='line %s'%ante)
        else:
            p.semilogy(freq,N.abs(d)[::-1],label = 'line %s'%ante)
            p.ylabel('log(power)')
            p.xlabel('frequency (MHz)')
            p.title('Power Spectrum vs Frequency')
            leg=p.legend(loc=8)
            for t in leg.get_texts():
                t.set_fontsize(12)
            fr = leg.get_frame()
            fr.set_bounds(1,0,4,4)

def corr_coeff():
    freq = N.arange(1024,dtype = float)
    c = 100/1024.
    freq = freq*c
    freq = freq + 100
    c = 0
    for i in convert_arg(opts.ant):
        if i[0] != i[2] and i[0]+'_'+i[0] and i[2]+'_'+i[2] in convert_arg(opts.ant):
            auto_avg = 10*N.log10((N.abs(psum[i[0] + i[0]]) + N.abs(psum[i[2]+i[2]]))/2.)
            data = 10*N.log10(N.abs(psum[i[0]+i[2]]))
            corr_coeff = data - auto_avg
            avg_val = N.average(corr_coeff[2:-2])
            print 'average value ='+str(avg_val)
            fig = p.figure(c)
            ax1 = fig.add_subplot(111)
            ax1.plot(freq,corr_coeff[::-1])
            ax1.set_ylim((-70.,-10.))
            ax1.axhline(avg_val,color='k')
            p.title('Correlation coefficient of inputs ' + i +' and phase',color='b')
            ax1.set_ylabel('Correlation coefficient (dB)')
            p.xlabel('frequecy (MHz)')
            p.grid()

            ax2=ax1.twinx()
            ax2.plot(freq,N.angle(psum[i[0]+i[2]],deg=1)[::-1],'.',color='r')
            ax2.set_ylabel('Phase (degrees)')
        else: print 'not enough data'
        c+=1

t_start = time.time()
names = []
get_data()
#print convert_arg(opts.ant)

if opts.xtalk == True: corr_coeff()
else:
    for i in convert_arg(opts.ant):
        plot(i)
        names.append(i)

t_finish  = time.time()
t_work = t_finish - t_start
print t_work, 'seconds = ', t_work/60., 'minutes'

p.show()
N.savez('test1_avg', x0_0=psum['00'], x2_2=psum['22'], x5_5=psum['55'], x7_7=psum['77'], x0_2=psum['02'], x0_5=psum['05'], x0_7=psum['07'], x2_5=['25'], x1_7=psum['17'], x5_7=psum['57'])











