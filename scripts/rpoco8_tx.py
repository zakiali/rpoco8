#! /usr/bin/env python2
import time
import spead as S
import argparse, sys, rpoco8
import logging; logger = logging.getLogger('rpoco8')

o = argparse.ArgumentParser()
o.add_argument('pid', nargs='?', type=int, help='Process ID of .bof file.')
o.add_argument('-p','--port', required=True, dest='port', type=int,help='SPEAD port for tx/rx')
o.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Be verbose')
opts = o.parse_args(sys.argv[1:])

if opts.verbose:
    logging.basicConfig(level=logging.DEBUG)
else:
    stream = logging.basicConfig(level=logging.INFO)
logging.getLogger('spead').setLevel(logging.WARN)

if opts.pid:
    pid = opts.pid
else:
    pid = rpoco8.start_bof()
logger.info('RPOCO8-RX: Started %s with pid=%d' % (rpoco8.BOFFILE, pid))

try:
  bss = rpoco8.BorphSpeadServer(pid)
  bss.add_item(name='data_timestamp', description='time stamp for data in ms',fmt=S.mkfmt(('u',64)), shape=[1])
  while True:
    logger.info('RPOCO8-RX: Listening to port %d' % (opts.port))
    bss.listen(opts.port)
    logger.info('RPOCO8-RX: Waiting for client...')
    client = bss.get_client(opts.port)
    for heap in bss.iterheaps():
        logger.debug('RPOCO8-RX: Sending a heap')
        client.send_heap(heap)
        logger.debug('RPOCO8-RX: Heap sent')
    logger.info('RPOCO8-RX: Client disconnected')
    bss.stop()
    time.sleep(1)
except(OSError): logger.fatal('RPOCO8-RX: Cannot start RPOCO8. FPGA already programmed')
except(KeyboardInterrupt):
    logger.info('RPOCO8-RX: Got KeyboardInterrupt.  Stopping')
    bss.stop()
finally: rpoco8.end_bof(pid)
