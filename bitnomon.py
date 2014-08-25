#!/usr/bin/python3
# Jacob Welsh, March 2014

import sys
import signal
import time
import math
from collections import deque

from qtwrapper import QtCore, QtGui
import pyqtgraph

from ui_main import Ui_MainWindow
from ui_about import Ui_aboutDialog
import bitcoinconf
import perfprobe
from qbitcoinrpc import *
from formatting import *

if sys.version_info[0] > 2:
    unicode = str

class TrafficLog:
    def __init__(self, history, pollInterval):
        """Arguments:
        history - length of time to store samples, in minutes
        pollInterval - time between samples, in milliseconds
        """
        self.pollInterval = pollInterval/1000.
        self.samplesPerSecond = 1./self.pollInterval
        self.totalSamples = int(history * 60 * self.samplesPerSecond)
        self.totalSent = deque([0]*self.totalSamples, self.totalSamples)
        self.totalRecv = deque([0]*self.totalSamples, self.totalSamples)
        self.oldestValidSample = 0

    def append(self, totalSent, totalRecv):
        if totalSent < self.totalSent[-1] or totalRecv < self.totalRecv[-1]:
            # discontinuity: totals not monotonically increasing
            self.oldestValidSample = 0
        elif self.oldestValidSample < self.totalSamples:
            self.oldestValidSample += 1
        self.totalSent.append(totalSent)
        self.totalRecv.append(totalSent)

    def _sampleTotal(self, age, totals):
        # FIXME interpolate
        ageInSamples = int(age*self.samplesPerSecond)
        if ageInSamples > self.oldestValidSample:
            ageInSamples = self.oldestValidSample
        elif ageInSamples < 0:
            ageInSamples = 0
        return ageInSamples/self.samplesPerSecond, totals[ageInSamples]

    def sampleTotalSent(self, age):
        self._sampleTotal(age, self.totalSent)
    def sampleTotalRecv(self, age):
        self._sampleTotal(age, self.totalRecv)

    def _sampleInterval(self, start, end, totals):
        startAge, startTotal = self._sampleTotal(start, totals)
        endAge, endTotal = self._sampleTotal(end, totals)
        return startAge - endAge, endTotal - startTotal

    def sampleIntervalSent(self, start, end):
        self._sampleInterval(start, end, self.totalSent)
    def sampleIntervalRecv(self, start, end):
        self._sampleInterval(start, end, self.totalRecv)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, conf={}, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._setupMenus()

        if conf.get('testnet','0') == '1':
            self.setWindowTitle(self.windowTitle() + ' [testnet]')

        self.byteFormatter = ByteCountFormatter()

        #self.trafficLog = TrafficLog(10, 2000)
        minutes = 10
        poll_interval_ms = 1000
        trafSamples = minutes * 60000 // poll_interval_ms
        self.lastSent = -1
        self.lastRecv = -1
        self.trafSent = deque([0]*trafSamples, trafSamples)
        self.trafRecv = deque([0]*trafSamples, trafSamples)
        self.lastBlockCount = -1
        self.blockRecvTimes = deque([], 24)

        item = self.ui.networkPlot.getPlotItem()
        item.setMouseEnabled(x=False)
        #item.setMenuEnabled(False)
        item.showGrid(y=True)
        item.setLabel('left', text='Traffic', units='B/s')
        item.hideAxis('bottom')
        self.trafSentPlot = item.plot(self.trafSent,
                pen=(255,0,0), fillLevel=0, brush=(255,0,0,100))
        self.trafRecvPlot = item.plot(self.trafRecv,
                pen=(0,255,0), fillLevel=0, brush=(0,255,0,100))

        item = self.ui.memPoolPlot.getPlotItem()
        item.showGrid(x=True, y=True)
        item.setLabel('left', text='Fee', units='BTC/kB')
        item.setLabel('bottom', text='Age (minutes)')
        self.memPoolScatterPlot = pyqtgraph.ScatterPlotItem([],
            symbol='t', size=10, brush=(255,255,255,50), pen=None, pxMode=True)
        item.addItem(self.memPoolScatterPlot)

        self.proxy = RPCProxy(conf)
        self.busy = False
        self.update()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(poll_interval_ms)
        self.perfProbe = perfprobe.PerfProbe(self)

    def _setupMenus(self):
        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('application-exit'));
        self.ui.action_Quit.setIcon(icon);
        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('view-fullscreen'));
        self.ui.action_FullScreen.setIcon(icon);
        self.ui.action_FullScreen.toggled.connect(self.toggleFullScreen)
        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('help-about'));
        self.ui.action_About.setIcon(icon);
        self.ui.action_About.triggered.connect(self.about)

        self.ui.action_NetUnits.setSeparator(True)
        self.ui.netUnitGroup = QtGui.QActionGroup(self)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitBitSI)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitByteSI)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitByteBinary)
        self.ui.action_NetUnitByteSI.setChecked(True)
        self.ui.action_NetUnitBitSI.triggered.connect(self.netUnitBitSI)
        self.ui.action_NetUnitByteSI.triggered.connect(self.netUnitByteSI)
        self.ui.action_NetUnitByteBinary.triggered.connect(self.netUnitByteBinary)

    def about(self):
        about = QtGui.QDialog(self)
        Ui_aboutDialog().setupUi(about)
        about.show()

    def netUnitBitSI(self):
        self.byteFormatter.setUnitBits()
        self.byteFormatter.setPrefixSI()
    def netUnitByteSI(self):
        self.byteFormatter.setUnitBytes()
        self.byteFormatter.setPrefixSI()
    def netUnitByteBinary(self):
        self.byteFormatter.setUnitBytes()
        self.byteFormatter.setPrefixBinary()

    @QtCore.Slot(bool)
    def toggleFullScreen(self, enable):
        if enable:
            self.showFullScreen()
        else:
            self.showNormal()

    # Chain requests sequentially (doesn't seem to work reliably if
    # QNetworkAccessManager parallelizes them)

    def update(self):
        if not self.busy:
            self.infoReply = self.proxy.getinfo()
            self.infoReply.finished.connect(self.updateInfo)
            self.infoReply.error.connect(self.netError)
            self.busy = True

    @QtCore.Slot(object)
    def updateInfo(self, info):
        self.ui.lConns.setText(unicode(info['connections']))
        blocks = info['blocks']
        self.ui.lBlocks.setText(unicode(blocks))
        if self.lastBlockCount != -1:
            if blocks > self.lastBlockCount:
                self.lastBlockCount = blocks
                self.blockRecvTimes.append(time.time())
        else:
            self.lastBlockCount = blocks

        # chain next request
        self.miningInfoReply = self.proxy.getmininginfo()
        self.miningInfoReply.finished.connect(self.updateMiningInfo)
        self.miningInfoReply.error.connect(self.netError)

    @QtCore.Slot(object)
    def updateMiningInfo(self, info):
        self.ui.lDifficulty.setText(u'%.3g' % info['difficulty'])
        self.ui.lPooledTx.setText(unicode(info['pooledtx']))

        # chain next request
        self.netTotalsReply = self.proxy.getnettotals()
        self.netTotalsReply.finished.connect(self.updateNetTotals)
        self.netTotalsReply.error.connect(self.netError)

    @QtCore.Slot(object)
    def updateNetTotals(self, totals):
        recv = totals['totalbytesrecv']
        self.ui.lRecvTotal.setText(self.byteFormatter.format(recv))
        if self.lastRecv != -1:
            recv1s = recv - self.lastRecv
            self.ui.lRecv1s.setText(self.byteFormatter.format(recv1s))
            self.trafRecv.append(recv1s)
        self.lastRecv = recv

        sent = totals['totalbytessent']
        self.ui.lSentTotal.setText(self.byteFormatter.format(sent))
        if self.lastSent != -1:
            sent1s = sent - self.lastSent
            self.ui.lSent1s.setText(self.byteFormatter.format(sent1s))
            self.trafSent.append(sent1s)
        self.lastSent = sent

        self.trafSentPlot.setData(self.trafSent)
        self.trafRecvPlot.setData(self.trafRecv)

        # chain next request
        self.rawMemPoolReply = self.proxy.getrawmempool(True)
        self.rawMemPoolReply.finished.connect(self.updateMemPool)
        self.rawMemPoolReply.error.connect(self.netError)
    
    @QtCore.Slot(object)
    def updateMemPool(self, pool):
        now = time.time()
        transactions = pool.values()
        spots = []
        minFreePriority = bitcoinconf.COIN * 144 // 250
        redPen = pyqtgraph.mkPen((255,0,0,100))
        for tx in transactions:
            age = (float(tx['time']) - now) / 60.
            fee = float(tx['fee']) / math.ceil(float(tx['size']/1000.))
            if int(tx['currentpriority']) >= minFreePriority:
                pen = redPen
            else:
                pen = None
            spots.append({'pos': (age, fee), 'pen': pen})
        item = self.ui.memPoolPlot.getPlotItem()
        item.clear()
        self.memPoolScatterPlot.setData(spots)
        item.addItem(self.memPoolScatterPlot)
        for blockTime in self.blockRecvTimes:
            item.addLine(x=(blockTime - now)/60.)

        # end of chain; show stats
        self.ui.statusBar.showMessage(u'JSON-RPC RTTs: %d %d %d %d' % (
            self.infoReply.rtt,
            self.miningInfoReply.rtt,
            self.netTotalsReply.rtt,
            self.rawMemPoolReply.rtt))

        self.busy = False
    
    @QtCore.Slot(QtNetwork.QNetworkReply.NetworkError)
    def netError(self, err):
        err_str = u'Network error: ' + unicode(err)
        sys.stderr.write(err_str + '\n')
        self.ui.statusBar.showMessage(err_str)

def main(argv):
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtGui.QApplication(argv)
    datadir = None
    conf = None
    testnet = False
    for arg in argv[1:]:
        parts = arg.split('=',1)
        if parts[0] == '-datadir':
            if len(parts) == 2:
                datadir = parts[1]
            else:
                sys.stderr.write('Warning: empty -datadir, needs "="\n')
        elif parts[0] == '-conf':
            if len(parts) == 2:
                conf = parts[1]
            else:
                sys.stderr.write('Warning: empty -conf, needs "="\n')
        elif arg == '-testnet':
            testnet = True
        else:
            sys.stderr.write('Warning: unknown argument ' + arg + '\n')
    if datadir is not None:
        bitcoinconf.datadir = datadir
    if conf is not None:
        bitcoinconf.conf = conf
    conf = bitcoinconf.read()
    if testnet:
        conf['testnet'] = '1'
    mainWin = MainWindow(conf)
    mainWin.show()
    app.exec_()

if __name__ == '__main__':
    main(sys.argv)
