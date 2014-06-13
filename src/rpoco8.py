import spead as S, numpy as N
import os, threading, time
import logging; logger = logging.getLogger('rpoco8')

__VERSION__ = '0.0.3'
BOFFILE = '/boffiles/rpoco8_2048ch_v007.bof'
BASE_RX_ID = 0x8000
BASE_TX_ID = 0x9000
TIMESTAMP_ID = 0x7000
NCHAN = 1024
NANT = 8
SW_REG_LEN = 4
EQ_ADDR_RANGE = 2**6
TMP_FILE = 'uv.tmp'
ANTS = 'abcdefgh'
BLS = [ai+aj for i,ai in enumerate(ANTS) for aj in ANTS[i:]]

UV_VAR_TYPES = {
    'source':   'a', 'operator': 'a', 'version':  'a', 'telescop': 'a',
    'antpos':   'd', 'freq':     'd', 'inttime':  'r', 'nants':    'i',
    'nchan':    'i', 'nspect':   'i', 'sfreq':    'd', 'sdf':      'd',
    'ischan':   'i', 'nschan':   'i', 'restfreq': 'd', 'npol':     'i',
    'epoch':    'r', 'veldop':   'r', 'vsource':  'r', 'longitu':  'd',
    'latitud':  'd', 'dec':      'd', 'obsdec':   'd', 'nspect':   'i',
    'ischan':   'i', 'epoch':    'r', 'veldop':   'r', 'vsource':  'r',
    'ra':       'd', 'obsra':    'd', 'lst':      'd', 'pol':      'i',
}

FPGA_RX_RESOURCES = {
    BASE_RX_ID+0: ('ctrl_sw', S.DEFAULT_FMT),
    BASE_RX_ID+1: ('acc_length', S.DEFAULT_FMT),
    BASE_RX_ID+2: ('eq_coeff', S.mkfmt(('u',2),('u',10),('u',3),('u',17))),
    BASE_RX_ID+3: ('Sync_sync_sel', S.DEFAULT_FMT),
    BASE_RX_ID+4: ('Sync_sync_pulse', S.DEFAULT_FMT),
    BASE_RX_ID+5: ('insel_insel_data', S.DEFAULT_FMT)
 # 0-16 coeff, 17 coeff_en, 20-25 coeff_addr, 30-31 ant_select
}

FPGA_TX_RESOURCES = { BASE_TX_ID+0: ('acc_num','acc_num', S.DEFAULT_FMT, []) }
_cnt = 1
for b in ['aa','bb','cc','dd']:
    FPGA_TX_RESOURCES[BASE_TX_ID+_cnt] = ('xengine8_muxed_%s_real' % b, '%s_r'%b, S.mkfmt(('i',32)), [2*NCHAN])
    _cnt += 1
for b in ['ab','ac','ad','ae','af','bc','bd','be','bf','cd','cg','ch','dg','dh']:
    FPGA_TX_RESOURCES[BASE_TX_ID+_cnt] = ('xengine8_muxed_%s_real' % b, '%s_r'%b, S.mkfmt(('i',32)), [2*NCHAN])
    _cnt += 1
    FPGA_TX_RESOURCES[BASE_TX_ID+_cnt] = ('xengine8_muxed_%s_imag' % b, '%s_i'%b, S.mkfmt(('i',32)), [2*NCHAN])
    _cnt += 1

def start_bof(boffile=BOFFILE):
    return os.spawnv(os.P_NOWAIT, boffile, [boffile])

def end_bof(pid):
    os.kill(pid,15)

class BorphSpeadServer(S.ItemGroup):
    def __init__(self, pid=None, dir=None, fpga_rx_resources=FPGA_RX_RESOURCES, fpga_tx_resources=FPGA_TX_RESOURCES):
        S.ItemGroup.__init__(self)

        if not pid is None: self.dir = '/proc/%d/hw/ioreg/' % pid
        else: self.dir = dir

        # Resources that may need writing to
        self.fpga_rx = {}
        for id,(filename,fmt) in fpga_rx_resources.iteritems():
            filename = self.dir + filename
            self.fpga_rx[id] = (filename, SW_REG_LEN)
            logger.debug('BorphSpeadServer: Adding RX resource id=%d filename=%s size=%d' % ((id,) + self.fpga_rx[id]))
        self.is_connected = False

        # Resources associated with transmission
        self.brams = {}
        for id,(filename,name,fmt,shape) in fpga_tx_resources.iteritems():
            filename = self.dir + filename
            logger.debug('BorphSpeadServer: Adding TX resource id=%d filename=%s' % (id, filename))
            if name == 'acc_num': self.acc_num = open(filename)
            else: self.brams[id] = open(filename)

        self._tx_heap = {}

    def update(self, heap):
        items = heap.get_items()
        # First process items that are linked to FPGA resources
        for id in self.fpga_rx.keys():
            #logger.debug('BorphSpeadServer.update: Trying id=%d in %s' % (id, items.keys()))
            try: val = items[id]
            except(KeyError): continue
            filename,size = self.fpga_rx[id]
            logger.info('BorphSpeadServer.update: Updating id=%d (filename=%s) val=0x%s' % (id, filename, S.hexify(val)))
            logger.debug('BorphSpeadServer.update: Updating id=%d with value of length=%d' % (id, len(val)))
            if len(val) < size:
                logger.warn('BorphSpeadServer.update: Did not get enough data for id=%d (needed %d, got %d)' % (id, size, len(val)))
                continue
            f = open(filename,'w')
            f.write(val[-size:])
            f.close()
        S.ItemGroup.update(self, heap)
    def _listen(self):
        for heap in S.iterheaps(self.rx):
            logger.debug('BorphSpeadServer._listen: Got a heap')
            self.is_connected = True
            self.update(heap)
        logger.debug('BorphSpeadServer._listen: Listening thread ended')
        self.is_connected = False
    def listen(self, port):
        logger.info('BorphSpeadServer.start: Starting server on port=%d' % (port))
        try: self['ip'] = ''
        except(KeyError): pass
        self.rx = S.TransportUDPrx(port)
        self._listen_thread = threading.Thread(target=self._listen)
        self._listen_thread.daemon = True
        self._listen_thread.start()
    def stop(self):
        logger.info('BorphSpeadServer.stop: Halting server')
        try:
            logger.debug('BorphSpeadServer.stop: Stopping receiver')
            self.rx.stop()
            logger.debug('BorphSpeadServer.stop: Joining listening thread')
            self._listen_thread.join()
        except(AttributeError): pass
    def get_client(self, port):
        logger.info('BorphSpeadServer.get_client: Waiting for a client')
        #while self.is_connected and (not 'ip' in self.keys() or len(self['ip']) == 0):
        while (not 'ip' in self.keys() or len(self['ip']) == 0):
            time.sleep(.1)
            continue
        #if not self.is_connected:
        #    logger.debug('BorphSpeadServer.get_client: Listen thread died before client connected')
        #    raise RuntimeError('Listen thread died before client connected')
        ip = ''.join([s[0] for s in self['ip']])
        logger.info('BorphSpeadServer.get_client: Got a connection from %s' % ip)
        return S.Transmitter(S.TransportUDPtx(ip, port))
    def iterheaps(self):
        while self.is_connected:
            self.acc_num.seek(0)
            heap_cnt = '\x00' + self.acc_num.read()
            if heap_cnt == self._tx_heap.get(S.HEAP_CNT_ID,'XX')[1]:
                #logger.debug('BorphSpeadServer.iterheaps: Waiting for HEAP_CNT=%s (currently %s)' % (S.hexify(self._tx_heap.get(S.HEAP_CNT_ID,'XX')[1]), S.hexify(heap_cnt)))
                time.sleep(.001)
                continue
            tme = time.time()
            tme = int(tme*1000)
            htme = S.pack(S.mkfmt(('u',64)),[[tme]])
            self._tx_heap[TIMESTAMP_ID] = (S.DIRECTADDR,htme)    
            logger.info('BorphSpeadServer.iterheaps: Sending HEAP_CNT=%s' % S.hexify(heap_cnt))
            self._tx_heap[S.HEAP_CNT_ID] = (S.IMMEDIATEADDR, heap_cnt)
            for id,bram in self.brams.iteritems():
                bram.seek(0)
                self._tx_heap[id] = (S.DIRECTADDR, bram.read())
            yield self._tx_heap
        return

class SimSpeadServer(BorphSpeadServer):
    '''
        Simulation server for when a roach 
        is not available to be tested.
    '''
    def __init__(self, dir='/tmp/', fpga_rx_resources=FPGA_RX_RESOURCES,
                            fpga_tx_resources=FPGA_TX_RESOURCES,
                            integration_time=5):
        S.ItemGroup.__init__(self)

        self.dir = dir
        self.brams = {}
        self.integration_time = integration_time

        #These are resources that may need writing to on the roach.
        self.fpga_rx = {}
        for id,(filename,fmt) in fpga_rx_resources.iteritems():
            filename = self.dir + filename
            self.fpga_rx[id] = (filename, SW_REG_LEN)
            logger.debug('BorphSpeadServer: Adding RX resource id=%d filename=%s size=%d' % ((id,) + self.fpga_rx[id]))
        self.is_connected = False

        #resources that may need reading from, from the raoch.
        for id, (filename,name,fmt,shape) in fpga_tx_resources.iteritems():
            filename = self.dir + filename
            logger.debug('SimSpeadServer: Creating file %s' % (filename))
            f = open(filename, 'w')
            f.close()
            if name == 'acc_num':
                #acc_num starts with a 0 count.
                self.acc_num = open(filename, 'w+b')
                n_zero = N.array(0, dtype=N.uint32).tostring()
                self.acc_num.write(n_zero)
            else: self.brams[id] = open(filename, 'w+b')
        self._tx_heap = {}


    def write(self):
        '''
           Write thread that will pretend it is 
           the roach updating the files every 
           integration seconds.
        '''
        logger.info('Writing:')
        self._write_thread = threading.Thread(target=self._write)
        self._write_thread.daemon = True
        self._write_thread.start()

    def _write(self):
        '''Simulates a writing of data into the 
           brams on the roach. Along with acc_num'''
        logger.debug('SimSpeadServer._write: Writing to resources. Integration time = %f'%self.integration_time)
        while True:
            for id,bram in self.brams.iteritems():
                bram.seek(0)
                d = N.random.randint(2**32 - 1,size=2048) 
                d.dtype = N.uint32
                d = d[::2]
                d = d.tostring()
                bram.write(d)
                
            #increase acc_num by one
            self.acc_num.seek(0)
            anum = N.array(N.fromstring(self.acc_num.read(), dtype=N.uint32)[0] + 1, dtype=N.uint32)
            self.acc_num.seek(0)
            self.acc_num.write(anum.tostring())
            logger.debug('Writing integration number %d'%anum) 

            time.sleep(self.integration_time)
        logger.debug('SimSpeadServer._write: Stopping write thread.')
        

   

class BorphSpeadClient(S.ItemGroup):
    def __init__(self, client_ip, tx, fpga_rx_resources=FPGA_RX_RESOURCES,
            fft_shift=0x155, acc_length=0x8000000, eq_coeff=1500, sync_sel=1,
            input_sel=0x00000000):
        S.ItemGroup.__init__(self)
        self.tx = tx
        self.add_item('ip', fmt=S.STR_FMT, shape=-1, init_val=client_ip)
        for id in fpga_rx_resources:
            name, fmt = fpga_rx_resources[id]
            self.add_item(name, id=id, fmt=fmt, shape=[])
        self.input_selector(input_sel)
        self.set_fft_shift(fft_shift)
        self.acc_length(acc_length)
        self.set_eq_coeff(eq_coeff)
        self.send()
        self.Sync_sync_sel(sync_sel)

    def set_fft_shift(self, fft_shift):
        logger.info('BorphSpeadClient.set_fft_shift: fft_shift=%x' % (fft_shift))
        self['ctrl_sw'] = fft_shift 

    def acc_length(self, acc_length):
        logger.info('BorphSpeadClient.acc_length: acc_length=%x' % (acc_length))
        self['acc_length'] = acc_length

    def set_eq_coeff(self, eq_coeff):
    #    "0-16 coeff, 17 coeff-en, 20-25 coeff-addr, 30-31 ant-pair-sel"
        logger.info('BorphSpeadClient.set_eq_coeff: eq_coeff=%d' % (eq_coeff))
        for ant_sel in range(NANT/2):
            for addr in range(EQ_ADDR_RANGE):
                logger.debug('BorphSpeadClient.set_eq_coeff: ant_sel=%d, addr=%d, eq_coeff=%d' % (ant_sel, addr, eq_coeff))
                self['eq_coeff'] = (ant_sel, addr, 1, eq_coeff)
                self.send()

    def Sync_sync_sel(self, sync_sel):
        logger.info('BorphSpeadClient.sync_sel: sync_sel=%d' % (sync_sel))
        self['Sync_sync_sel'] = sync_sel
        self.send()
        if sync_sel == 1: 
            for i in range(2):     
                self['Sync_sync_pulse'] = i
                logger.info('BorphSpeadClient.sync_pulse: Sending sync pulse %d' %i)
                self.send()  
                time.sleep(1)
            self['Sync_sync_pulse'] = 0
            self.send()

    def input_selector(self, input_sel):
        logger.info('BorphSpeadClient.input_select: input_sel=%d' % (input_sel))
        self['insel_insel_data'] = input_sel
        self.send()

    def send(self):
        logger.info('BorphSpeadClient.send: Sending a heap')
        heap = self.get_heap()
        #for id, val in heap.iteritems():
        #    logger.debug('BorphSpeadClient.send: id=%d len(val)=%d' % (id, len(val[1])))
        #    #logger.debug('BorphSpeadClient.send: id=%d val=%s' % (id, [val]))
        self.tx.send_heap(heap)

A = None
try: import aipy as A
except(ImportError): pass

class DataRecorder(S.ItemGroup):
    def __init__(self, aa, base_id=0x8000):
        S.ItemGroup.__init__(self)
        self.aa = aa
        for bl in BLS:
            self.add_item(name=bl, id=base_id, shape=-1, fmt='i\x00\x00\x20')
            base_id += 1
        self.add_item(name='acc_num', id=base_id)
        self.add_item(name='t0', id=base_id+1, fmt='f\x00\x00\x40')
    def open_uv(self, sdf, sfreq, nchan, inttime, bandpass=None):
        '''Open a Miriad UV file for writing.  Bandpass is the digital 
        equalization that needs to be divided from the output data, with
        dimensions (nant, nchans) and dtype complex64.'''
        uv = A.miriad.UV(TMP_FILE, 'new')
        uv['history'] = 'RPOCO8: version=%s\n' % __VERSION
        uv['obstype'] = 'crosscorrelation'
        for v in UV_VAR_TYPES.iterkeys():
            if v in A.miriad.itemtable: continue
            uv.add_var(v, UV_VAR_TYPES[v])
        uv['source'] = 'zenith'
        uv['operator'] = uv['telescop'] = 'RPOCO8'
        uv['version'] = __VERSION__
        ants = N.array([aa[i].pos for i in range(NANT)]).transpose()
        uv['antpos'] = ants.flatten()
        uv['nants'] = NANT
        uv['npol'] = 1
        uv['nspect'] = uv['ischan']  = 1
        uv['epoch'] = 2000.
        uv['veldop'] = uv['vsource'] = 0.
        uv['longitu'] = self.aa.long
        uv['latitud'] = uv['dec'] = uv['obsdec'] = self.aa.lat
        uv['sfreq'] = uv['freq'] = uv['restfreq'] = sfreq
        uv['sdf'] = sdf
        uv['nchan'] = uv['nschan'] = nchan
        uv['inttime'] = inttime
        if not bandpass is None:
            assert(bandpass.shape == (nants, nchan))
            uv['bandpass']= bandpass.flatten()
            uv['nspect0'] = NANT
            uv['nchan0'] = nchan
            uv['ntau'] = uv['nsols'] = 0
            uv['nfeeds'] = 1
            uv['ngains'] = NANT * (uv['ntau'] + uv['nfeeds'])
            uv['freqs'] = (NANT,) + (nchan, sfreq, sdf) * NANT
        self.uv = uv
    def close_uv(self, filename):
        '''Close the current UV file and rename it to filename'''
        del(self.uv)
        os.rename(TMP_FILE, filename)
    def get_preamble(self, jd, i, j):
        '''Return Miriad preamble info (uvw,t,(i,j))'''
        return (self.aa.get_baseline(i,j), jd, (i,j))
    def get_jd(self, acc_num, t0):
        # XXX
        return ephem.julian_date()
    def update(self, heap):
        S.ItemGroup.update(self, heap)
        jd = get_jd(self['acc_num'], self['t0'])
        self.aa.set_jultime(jd)
        lst = self.aa.sidereal_time()
        self.uv['ra'] = self.uv['obsra'] = self.uv['lst'] = lst
        self.uv['pol'] = A.miriad.str2pol['xx']
        zeros = N.zeros(self['aa'].shape, dtype=N.int)
        for bl in BLS:
            i,j = ANTS.index(bl[0]), ANTS.index(bl[1])
            p = self.get_preamble(jd, i, j)
            self.uv.write(p, self[bl], zeros)
