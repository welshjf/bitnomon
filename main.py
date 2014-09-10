import sys
import os
import time
import math

from qtwrapper import QtCore, QtGui, QtNetwork
import numpy
import pyqtgraph

from ui_main import Ui_MainWindow
from ui_about import Ui_aboutDialog
import bitcoinconf
import perfprobe
import qbitcoinrpc
import rrdmodel
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

class MainWindow(QtGui.QMainWindow):
    def __init__(self, conf={}, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._setupMenus()
        self._setupStatusBar()
        self._setupPlots()

        if conf.get('testnet','0') == '1':
            self.setWindowTitle(self.windowTitle() + ' [testnet]')

        self.byteFormatter = ByteCountFormatter()

        self.proxy = qbitcoinrpc.RPCProxy(conf)
        self.busy = False
        self.missedSamples = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
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

    def _setupPlots(self):
        # Keep 10 minutes of one-second resolution traffic counter data.
        # (Actually one poll interval, which is assumed to be one second)
        traf_samples = 600
        traf_intervals = traf_samples - 1
        self.trafSent = rrdmodel.RRA(traf_samples)
        self.trafRecv = rrdmodel.RRA(traf_samples)
        # Plot speeds using descending age in minutes, to match mempool
        self.trafPlotDomain = numpy.array(
                tuple(seconds/60. for seconds in xrange(-traf_intervals+1,1)))

        # Keep a long-term database of traffic data using RRDtool.
        self.trafRRD = rrdmodel.RRDModel()

        # Keep the last ~4 hours of block arrival times, as seen by Bitnomon,
        # since the bitcoin API doesn't provide this.
        self.lastBlockCount = None
        self.blockRecvTimes = rrdmodel.RRA(24)

        self.networkPlot = pyqtgraph.PlotItem(
                name='traffic',
                left=(self.tr('Traffic'), 'B/s')
                )
        self.networkPlot.showGrid(y=True)
        self.networkPlot.hideAxis('bottom')
        self.trafSentPlot = rrdplot.RRDPlotItem(numpy.zeros(traf_intervals),
                pen=(255,0,0), fillLevel=0, brush=(255,0,0,100))
        self.trafRecvPlot = rrdplot.RRDPlotItem(numpy.zeros(traf_intervals),
                pen=(0,255,0), fillLevel=0, brush=(0,255,0,100))
        self.networkPlot.addItem(self.trafSentPlot)
        self.networkPlot.addItem(self.trafRecvPlot)
        self.ui.networkPlotView.setCentralWidget(self.networkPlot)

        self.memPoolPlot = pyqtgraph.PlotItem(
                name='mempool',
                left=(self.tr('Fee'), 'BTC/kB'),
                bottom=(self.tr('Age (minutes)'),),
                )
        self.memPoolPlot.setXLink('traffic')
        self.memPoolPlot.showGrid(x=True, y=True)
        # Use the scatter plot API directly, because going through PlotDataItem
        # has strange complications.
        self.memPoolScatterPlot = pyqtgraph.ScatterPlotItem([],
            symbol='t', size=10, brush=(255,255,255,50), pen=None, pxMode=True)
        self.memPoolPlot.addItem(self.memPoolScatterPlot)
        self.ui.memPoolPlotView.setCentralWidget(self.memPoolPlot)

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
        if self.lastBlockCount is None:
            self.lastBlockCount = blocks
        else:
            if blocks > self.lastBlockCount:
                self.lastBlockCount = blocks
                self.blockRecvTimes.update(time.time())

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

        def format_speed(byte_count, seconds):
            if byte_count is None:
                return '-'
            else:
                return self.byteFormatter.format(
                        byte_count/float(seconds)) + '/s'

        # Update in-memory RRAs for high-resolution traffic data and averages
        recv = totals['totalbytesrecv']
        self.ui.lRecvTotal.setText(self.byteFormatter.format(recv))
        self.trafRecv.update(recv)
        self.ui.lRecv1s.setText(
                format_speed(self.trafRecv.difference(-1, -2), 1))
        self.ui.lRecv10s.setText(
                format_speed(self.trafRecv.difference(-1, -11), 10))
        self.ui.lRecv1m.setText(
                format_speed(self.trafRecv.difference(-1, -61), 60))

        sent = totals['totalbytessent']
        self.ui.lSentTotal.setText(self.byteFormatter.format(sent))
        self.trafSent.update(sent)
        self.ui.lSent1s.setText(
                format_speed(self.trafSent.difference(-1, -2), 1))
        self.ui.lSent10s.setText(
                format_speed(self.trafSent.difference(-1, -11), 10))
        self.ui.lSent1m.setText(
                format_speed(self.trafSent.difference(-1, -61), 60))

        # Update RRDtool database for long-term traffic data
        self.trafRRD.update(totals['timemillis'], (recv, sent))

        self.trafSentPlot.setData(
                self.trafPlotDomain,
                self.trafSent.differences(0))
        self.trafRecvPlot.setData(
                self.trafPlotDomain,
                self.trafRecv.differences(0))

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

        # Clear previous block lines
        self.memPoolPlot.clear()
        self.memPoolScatterPlot.setData(pos=positions, pen=pens)
        # Re-add the scatter plot after clearing
        self.memPoolPlot.addItem(self.memPoolScatterPlot)
        # Draw block lines
        for blockTime in self.blockRecvTimes:
            if blockTime is not None:
                self.memPoolPlot.addLine(x=(blockTime - now)/60.)

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
