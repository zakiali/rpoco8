#! /usr/bin/env python
import spead as S
import optparse, sys, rpoco8
import logging; logger = logging.getLogger('rpoco8')
import time

o = optparse.OptionParser()
o.add_option('-p','--port', dest='port', type='int',help='SPEAD port for tx/rx')
o.add_option('-v', '--verbose', dest='verbose', action='store_true', help='Be verbose') 
o.add_option('-w', '--walsh', dest = 'walsh', type = 'string', default = '0', help = 'type of walsh pattern. 0=zeroes, all = 8 orth. patterns')
o.add_option('--walshon', action='store_true', help='Turn on walshing')
opts,args = o.parse_args(sys.argv[1:])

print opts.walsh
print type(opts.walsh)
if opts.verbose:
    logging.basicConfig(level=logging.DEBUG)
else:
    stream = logging.basicConfig(level=logging.INFO)    
logging.getLogger('spead').setLevel(logging.WARN)

#pid = rpoco8.start_bof()
try:
    pid = int(args[0])                                                 
except:
    pid=None
#logger.info('RPOCO8-RX: Started %s with pid=%d' % (rpoco8.BOFFILE, pid))

if opts.walshon:
    import walsh_rx
    walsh_rx.write_walsh(pid,pattern = opts.walsh)

try:                                        
  sss = rpoco8.SimSpeadServer(dir='/tmp/')
  sss.add_item(name='data_timestamp', description='time stamp for data in ms',fmt=S.mkfmt(('u',64)), shape=[1]) 
  while True:
    logger.info('RPOCO8-RX: Listening to port %d' % (opts.port))    
    sss.listen(opts.port)                                          
    sss.write()
    logger.info('RPOCO8-RX: Waiting for client...')               
    client = sss.get_client(opts.port+1)
    for heap in sss.iterheaps():   
        logger.debug('RPOCO8-RX: Sending a heap')    
        client.send_heap(heap)
        time.sleep(.2)
        logger.debug('RPOCO8-RX: Heap sent on port %d'%(opts.port+1))
    logger.info('RPOCO8-RX: Client disconnected')
    sss.stop()                                      
    time.sleep(1)
except(OSError): logger.fatal('RPOCO8-RX: Cannot start RPOCO8. FPGA already programmed')
except(KeyboardInterrupt):
    logger.info('RPOCO8-RX: Got KeyboardInterrupt.  Stopping')
    sss.stop()
#finally: rpoco8.end_bof(pid)
 
