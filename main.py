import sys
import os
import time
import math
from collections import deque

from qtwrapper import QtCore, QtGui, QtNetwork
import numpy
import pyqtgraph

from ui_main import Ui_MainWindow
from ui_about import Ui_aboutDialog
import bitcoinconf
import perfprobe
import qbitcoinrpc
import rrdplot
from formatting import *

if sys.version_info[0] > 2:
    unicode = str
    xrange = range

# Bitnomon global settings (these don't go in bitcoinconf because they're not
# part of Bitcoin Core)
# TODO: move these out of global scope.
debug = False
# QDesktopServices.DataLocation doesn't give the desired result.
# QStandardPaths.DataLocation in Qt5 does, so mimic that for now.
# TODO: support other platforms
data_dir = os.path.expanduser('~/.local/share/Bitnomon')

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
        self._setupStatusBar()

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
        self.trafSentPlot = rrdplot.RRDPlotItem([],
                pen=(255,0,0), fillLevel=0, brush=(255,0,0,100))
        item.addItem(self.trafSentPlot)
        self.trafRecvPlot = rrdplot.RRDPlotItem([],
                pen=(0,255,0), fillLevel=0, brush=(0,255,0,100))
        item.addItem(self.trafRecvPlot)

        item = self.ui.memPoolPlot.getPlotItem()
        item.showGrid(x=True, y=True)
        item.setLabel('left', text='Fee', units='BTC/kB')
        item.setLabel('bottom', text='Age (minutes)')
        # Use the scatter plot API directly, because going through PlotDataItem
        # has strange complications.
        self.memPoolScatterPlot = pyqtgraph.ScatterPlotItem([],
            symbol='t', size=10, brush=(255,255,255,50), pen=None, pxMode=True)
        item.addItem(self.memPoolScatterPlot)

        self.proxy = qbitcoinrpc.RPCProxy(conf)
        self.busy = False
        self.missedSamples = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(poll_interval_ms)
        QtCore.QTimer.singleShot(0, self.update)

        if debug:
            self.perfProbe = perfprobe.PerfProbe(self)
            self.perfProbe.updated.connect(self.updateStatusRSS)

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

    def _setupStatusBar(self):
        self.statusNetwork = QtGui.QLabel()
        self.ui.statusBar.addWidget(self.statusNetwork, 1)
        self.statusMissedSamples = QtGui.QLabel()
        self.ui.statusBar.addWidget(self.statusMissedSamples, 0)
        if debug:
            self.statusRSS = QtGui.QLabel()
            self.ui.statusBar.addWidget(self.statusRSS, 0)

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
        if self.busy:
            self.missedSamples += 1
            self.updateStatusMissedSamples()
        else:
            self.infoReply = self.proxy.getinfo()
            self.infoReply.finished.connect(self.updateInfo)
            self.infoReply.error.connect(self.netError)
            self.busy = True

    @QtCore.Slot(object)
    def updateInfo(self, info):
        # chain next request
        self.miningInfoReply = self.proxy.getmininginfo()
        self.miningInfoReply.finished.connect(self.updateMiningInfo)
        self.miningInfoReply.error.connect(self.netError)

        self.ui.lConns.setText(str(info['connections']))
        blocks = info['blocks']
        self.ui.lBlocks.setText(str(blocks))
        if self.lastBlockCount != -1:
            if blocks > self.lastBlockCount:
                self.lastBlockCount = blocks
                self.blockRecvTimes.append(time.time())
        else:
            self.lastBlockCount = blocks

    @QtCore.Slot(object)
    def updateMiningInfo(self, info):
        # chain next request
        self.netTotalsReply = self.proxy.getnettotals()
        self.netTotalsReply.finished.connect(self.updateNetTotals)
        self.netTotalsReply.error.connect(self.netError)

        self.ui.lDifficulty.setText(u'%.3g' % info['difficulty'])
        self.ui.lPooledTx.setText(str(info['pooledtx']))

    @QtCore.Slot(object)
    def updateNetTotals(self, totals):
        # chain next request
        self.rawMemPoolReply = self.proxy.getrawmempool(True)
        self.rawMemPoolReply.finished.connect(self.updateMemPool)
        self.rawMemPoolReply.error.connect(self.netError)

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

    @QtCore.Slot(object)
    def updateMemPool(self, pool):
        # end of chain: unlock for next sample and show stats
        self.busy = False
        self.statusNetwork.setText('RTT: %d %d %d %d' % (
            self.infoReply.rtt,
            self.miningInfoReply.rtt,
            self.netTotalsReply.rtt,
            self.rawMemPoolReply.rtt))

        now = time.time()
        transactions = pool.values()
        minFreePriority = bitcoinconf.COIN * 144 // 250
        redPen = pyqtgraph.mkPen((255,0,0,100))
        pens = [None]*len(transactions)
        positions = numpy.empty((len(transactions), 2))
        idx_iter = iter(xrange(len(transactions)))
        for tx in transactions:
            age = (float(tx['time']) - now) / 60.
            fee = float(tx['fee']) / math.ceil(float(tx['size'])/1000.)
            i = next(idx_iter)
            positions[i] = (age,fee)
            if int(tx['currentpriority']) >= minFreePriority:
                pens[i] = redPen

        item = self.ui.memPoolPlot.getPlotItem()
        # Clear previous block lines
        item.clear()
        self.memPoolScatterPlot.setData(pos=positions, pen=pens)
        # Re-add the scatter plot after clearing
        item.addItem(self.memPoolScatterPlot)
        # Draw block lines
        for blockTime in self.blockRecvTimes:
            item.addLine(x=(blockTime - now)/60.)

    @QtCore.Slot(QtNetwork.QNetworkReply.NetworkError, str)
    def netError(self, err, err_str):
        err_str = 'Network error: {}'.format(err_str)
        if debug:
            sys.stderr.write(err_str + '\n')
        self.statusNetwork.setText(err_str)
        self.busy = False

    @QtCore.Slot()
    def updateStatusMissedSamples(self):
        self.statusMissedSamples.setText('Missed samples: %d' %
            self.missedSamples)

    @QtCore.Slot()
    def updateStatusRSS(self):
        self.statusRSS.setText('RSS: %s' %
            self.byteFormatter.format(self.perfProbe.rss))

def main(argv):

    # pyqtgraph's exit crash workaround seems to do more harm than good.
    pyqtgraph.setConfigOption('exitCleanup', False)

    # Parse arguments
    datadir = None
    conffile = 'bitcoin.conf'
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
                conffile = parts[1]
            else:
                sys.stderr.write('Warning: empty -conf, needs "="\n')
        elif arg == '-testnet':
            testnet = True
        elif arg == '-d' or arg == '-debug':
            global debug
            debug = True
        else:
            sys.stderr.write('Warning: unknown argument ' + arg + '\n')

    # Load Bitcoin configuration
    conf = bitcoinconf.Conf()
    conf.load(datadir, conffile)
    if testnet:
        # CLI overrides config file
        conf['testnet'] = '1'

    # Load Bitnomon configuration
    QtGui.qApp.setOrganizationName('eemta.org')
    QtGui.qApp.setOrganizationDomain('eemta.org')
    QtGui.qApp.setApplicationName('Bitnomon')
    # QSettings stuff goes here
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Enter event loop
    try:
        mainWin = MainWindow(conf)
        mainWin.show()
        return QtGui.qApp.exec_()
    except:
        # PyQt4 segfaults if there's an uncaught exception after
        # Ui_MainWindow.setupUi.
        import traceback
        traceback.print_exc()
        return 1
