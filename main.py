#pylint: disable=invalid-name, star-args, no-member
# no-member gives too much trouble with numpy and pyqtgraph idioms.

"""Main window and program entry point"""

import sys
import os
import time
import math
import traceback
import signal

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
import formatting
from age import ageOfTime, AgeAxisItem

if sys.version_info[0] > 2:
    #pylint: disable=redefined-builtin
    unicode = str
    xrange = range

# Must be global to avoid crash at exit
qApp = None

# Bitnomon global settings (these don't go in bitcoinconf because they're not
# part of Bitcoin Core)
DEBUG = False
DATA_DIR = ''

# API requests are chained sequentially (doesn't seem to work reliably if
# QNetworkAccessManager parallelizes them).
commandChain = []
def chainRequest(method, *args):
    """Decorator to register an API request in the chain. Parameters are the
    API method name and optional arguments. The decorated function is the slot
    that handles the reply."""
    #pylint: disable=bare-except,missing-docstring
    def decorator(responseHandler):
        def handlerWrapper(self, data):
            try:
                responseHandler(self, data)
            except:
                traceback.print_exc()
            self.nextChainedRequest()
        commandChain.append((method, args, handlerWrapper))
        return handlerWrapper
    return decorator

class MainWindow(QtGui.QMainWindow):
    #pylint: disable=missing-docstring, too-many-instance-attributes
    #pylint: disable=too-many-public-methods

    def __init__(self, conf, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.label_logo.hide()

        if conf.get('testnet', '0') == '1':
            self.setWindowTitle(self.windowTitle() + ' [testnet]')

        self.byteFormatter = formatting.ByteCountFormatter()

        self.rpc = qbitcoinrpc.RPCManager(conf)
        self.busy = False
        self.chainIndex = 0
        self.replies = []
        self.tempReply = None
        self.missedSamples = 0
        self.isFullScreen = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(2000)
        QtCore.QTimer.singleShot(0, self.update)

        self._setupMenus()
        self._setupStatusBar()
        self._setupPlots()
        self.resetZoom()
        self.readSettings()

        if DEBUG:
            self.perfProbe = perfprobe.PerfProbe(self)
            self.perfProbe.updated.connect(self.updateStatusRSS)

    def _setupMenus(self):
        #pylint: disable=attribute-defined-outside-init
        self.ui.action_ClearTraffic.triggered.connect(self.clearTraffic)

        self.ui.action_ShutDownQuit.triggered.connect(self.shutdown)

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('application-exit'))
        self.ui.action_Quit.setIcon(icon)

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('view-fullscreen'))
        self.ui.action_FullScreen.setIcon(icon)
        self.ui.action_FullScreen.toggled.connect(self.toggleFullScreen)

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('zoom-original'))
        self.ui.action_ResetZoom.setIcon(icon)
        self.ui.action_ResetZoom.triggered.connect(self.resetZoom)

        icon = QtGui.QIcon(QtGui.QIcon.fromTheme('help-about'))
        self.ui.action_About.setIcon(icon)
        self.ui.action_About.triggered.connect(self.about)

        icon = QtGui.QIcon(':/trolltech/qmessagebox/images/qtlogo-64.png')
        self.ui.action_AboutQt.setIcon(icon)
        self.ui.action_AboutQt.triggered.connect(QtGui.qApp.aboutQt)

        self.ui.action_NetUnits.setSeparator(True)
        self.ui.netUnitGroup = QtGui.QActionGroup(self)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitBitSI)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitByteSI)
        self.ui.netUnitGroup.addAction(self.ui.action_NetUnitByteBinary)
        self.ui.action_NetUnitByteSI.setChecked(True)
        self.ui.action_NetUnitBitSI.triggered.connect(self.netUnitBitSI)
        self.ui.action_NetUnitByteSI.triggered.connect(self.netUnitByteSI)
        self.ui.action_NetUnitByteBinary.triggered.connect(
                self.netUnitByteBinary)

        # Any actions with keyboard shortcuts need to be added to the main
        # window to keep working when the menu bar is hidden :(
        self.addAction(self.ui.action_Quit)
        self.addAction(self.ui.action_FullScreen)
        self.addAction(self.ui.action_ResetZoom)

    def _setupStatusBar(self):
        #pylint: disable=attribute-defined-outside-init
        self.statusNetwork = QtGui.QLabel()
        self.ui.statusBar.addWidget(self.statusNetwork, 1)
        self.statusMissedSamples = QtGui.QLabel()
        self.ui.statusBar.addWidget(self.statusMissedSamples, 0)
        self.updateStatusMissedSamples()
        if DEBUG:
            self.statusRSS = QtGui.QLabel()
            self.ui.statusBar.addWidget(self.statusRSS, 0)

    def _setupPlots(self):
        #pylint: disable=attribute-defined-outside-init

        # Keep 10 minutes of high resolution traffic counter data.
        poll_interval = 2 # seconds
        traf_samples = int(600./poll_interval)
        traf_intervals = traf_samples - 1
        self.trafSent = rrdmodel.RRA(traf_samples)
        self.trafRecv = rrdmodel.RRA(traf_samples)
        # Plot traffic and mempool on a consistent scale
        self.trafPlotDomain = tuple(
            poll_interval*ageOfTime(traf_intervals, s)
            for s in xrange(1, traf_intervals+1)
        )

        # Keep a long-term database of traffic data using RRDtool.
        self.trafRRD = rrdmodel.RRDModel(DATA_DIR)

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
                pen=(255, 0, 0), fillLevel=0, brush=(255, 0, 0, 100))
        self.trafRecvPlot = rrdplot.RRDPlotItem(numpy.zeros(traf_intervals),
                pen=(0, 255, 0), fillLevel=0, brush=(0, 255, 0, 100))
        self.networkPlot.addItem(self.trafSentPlot)
        self.networkPlot.addItem(self.trafRecvPlot)
        self.networkPlot.invertX()
        self.ui.networkPlotView.setCentralWidget(self.networkPlot)

        self.memPoolPlot = pyqtgraph.PlotItem(
                name='mempool',
                left=(self.tr('Fee'), 'BTC/kB'),
                bottom=(self.tr('Age'), self.tr('d:h:m')),
                axisItems={'bottom': AgeAxisItem('bottom')},
                )
        self.memPoolPlot.setXLink('traffic')
        self.memPoolPlot.showGrid(x=True, y=True)
        self.memPoolPlot.invertX()
        # Use the scatter plot API directly, because going through PlotDataItem
        # has strange complications.
        self.memPoolScatterPlot = pyqtgraph.ScatterPlotItem([],
            symbol='t', size=10, brush=(255, 255, 255, 50),
            pen=None, pxMode=True)
        self.memPoolPlot.addItem(self.memPoolScatterPlot)
        self.ui.memPoolPlotView.setCentralWidget(self.memPoolPlot)

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup('MainWindow')
        if settings.contains('size'):
            self.resize(settings.value('size').toSize())
        if settings.contains('pos'):
            self.move(settings.value('pos').toPoint())
        if settings.value('fullScreen').toBool():
            self.ui.action_FullScreen.setChecked(True)
        self.ui.action_StatusBar.setChecked(
                settings.value('statusBar').toBool())
        settings.endGroup()

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup('MainWindow')
        settings.setValue('size', self.size())
        settings.setValue('pos', self.pos())
        settings.setValue('fullScreen', self.isFullScreen)
        settings.setValue('statusBar', self.ui.action_StatusBar.isChecked())
        # TODO: net units and zoom
        settings.endGroup()

    def closeEvent(self, _):
        self.writeSettings()

    def about(self):
        about = QtGui.QDialog(self)
        Ui_aboutDialog().setupUi(about)
        about.show()

    def netUnitBitSI(self):
        self.byteFormatter.unit_bits = True
        self.byteFormatter.prefix_si = True
    def netUnitByteSI(self):
        self.byteFormatter.unit_bits = False
        self.byteFormatter.prefix_si = True
    def netUnitByteBinary(self):
        self.byteFormatter.unit_bits = False
        self.byteFormatter.prefix_si = False

    def plotNetTotals(self):
        # Find boundary between RRD averages and full-resolution data
        oldestFullResAge = 0
        for oldestFullResIndex in xrange(len(self.trafPlotDomain)):
            if self.trafRecv[oldestFullResIndex] is not None:
                oldestFullResAge = self.trafPlotDomain[oldestFullResIndex]
                break

        # Load the RRD averages
        ages = []
        recv = []
        sent = []
        removeNone = lambda v: 0 if v is None else v
        now = int(time.time())
        for (t, values) in self.trafRRD.fetch_all():
            age = ageOfTime(now, t)
            if age > oldestFullResAge:
                ages.append(age)
                recv.append(removeNone(values[0]))
                sent.append(removeNone(values[1]))
            else:
                break

        # Interpolate with next average to avoid jumpy lines at the boundary
        if len(ages) > 0:
            prevAge = ages[-1]
            if age != prevAge:
                #pylint: disable=undefined-loop-variable
                ages.append(oldestFullResAge)
                blend = (oldestFullResAge - age) / (prevAge - age)
                interpolate = lambda a, b: a*(1.0-blend) + b*blend
                recv.append(interpolate(removeNone(values[0]), recv[-1]))
                sent.append(interpolate(removeNone(values[1]), sent[-1]))
                oldestFullResIndex += 1

        # Add the full-resolution data (dividing counter differences by the
        # polling interval to get speeds)
        ages.extend(self.trafPlotDomain[oldestFullResIndex:])
        sliceScale = lambda i: numpy.array(tuple(i)[oldestFullResIndex:]) / 2
        recv.extend(sliceScale(self.trafRecv.differences(0)))
        sent.extend(sliceScale(self.trafSent.differences(0)))

        # Plot it all
        self.trafRecvPlot.setData(ages, recv)
        self.trafSentPlot.setData(ages, sent)

    @QtCore.Slot(QtGui.QResizeEvent)
    def resizeEvent(self, _):
        # Synchronize with being full-screened by the window manager
        fullScreen = bool(self.windowState() & QtCore.Qt.WindowFullScreen)
        if fullScreen != self.isFullScreen:
            self.ui.action_FullScreen.setChecked(fullScreen)

    @QtCore.Slot(bool)
    def toggleFullScreen(self, enable):
        self.isFullScreen = enable
        if enable:
            self.showFullScreen()
            self.installEventFilter(self)
        else:
            self.showNormal()
            self.removeEventFilter(self)
        self.ui.label_logo.setVisible(enable)
        self.menuBar().setVisible(not enable)

    def eventFilter(self, _, event):
        # Show the menu bar when hovering at top of screen in full-screen mode
        if event.type() == QtCore.QEvent.HoverMove:
            menuBar = self.menuBar()
            if menuBar.isVisible():
                if event.pos().y() > menuBar.height():
                    menuBar.setVisible(False)
            else:
                if event.pos().y() < 1:
                    menuBar.setVisible(True)
        return False

    @QtCore.Slot()
    def resetZoom(self):
        self.networkPlot.setXRange(0, 10, padding=.02)
        self.networkPlot.enableAutoRange(axis=pyqtgraph.ViewBox.YAxis)
        self.memPoolPlot.enableAutoRange(axis=pyqtgraph.ViewBox.YAxis)

    @QtCore.Slot()
    def clearTraffic(self):
        ret = QtGui.QMessageBox.question(self, self.tr('Clear Traffic Data'),
                self.tr('Clear the long-term network traffic history?'),
                buttons=(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No))
        if ret == QtGui.QMessageBox.Yes:
            self.trafRRD.create()
            self.trafRecv.clear()
            self.trafSent.clear()
            self.plotNetTotals()

    @QtCore.Slot()
    def shutdown(self):
        ret = QtGui.QMessageBox.question(self,
                self.tr('Shut Down Node and Quit'),
                self.tr('Stop the monitored Bitcoin node as well as Bitnomon?'),
                buttons=(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No))
        if ret == QtGui.QMessageBox.Yes:
            self.tempReply = self.rpc.request('stop')
            self.tempReply.finished.connect(self.close)
            self.tempReply.error.connect(self.netError)

    def update(self):
        if self.busy:
            self.missedSamples += 1
            self.updateStatusMissedSamples()
        else:
            self.startChain()

    def startChain(self):
        self.chainIndex = 0
        self.replies = []
        # Lock the chain to avoid sending more requests if the previous ones
        # haven't finished
        self.busy = True
        self.nextChainedRequest()

    def nextChainedRequest(self):
        if self.chainIndex >= len(commandChain):
            # End of chain: unlock for next sample and show stats
            self.busy = False
            self.statusNetwork.setText('RTT: ' + ' '.join(
                [str(reply.rtt) for reply in self.replies]))
        else:
            method, args, slot = commandChain[self.chainIndex]
            boundSlot = slot.__get__(self, type(self))
            reply = self.rpc.request(method, *args)
            reply.finished.connect(boundSlot)
            reply.error.connect(self.netError)
            # Reply object must be kept alive until slot is finished
            self.replies.append(reply)
            self.chainIndex += 1

    @chainRequest('getinfo')
    def updateInfo(self, info):
        self.ui.lConns.setText(str(info['connections']))
        blocks = info['blocks']
        self.ui.lBlocks.setText(str(blocks))
        if self.lastBlockCount is None:
            self.lastBlockCount = blocks
        else:
            if blocks > self.lastBlockCount:
                #pylint: disable=attribute-defined-outside-init
                # ^ false positive?
                self.lastBlockCount = blocks
                self.blockRecvTimes.update(time.time())

    @chainRequest('getmininginfo')
    def updateMiningInfo(self, info):
        self.ui.lDifficulty.setText(u'%.3g' % info['difficulty'])
        self.ui.lPooledTx.setText(str(info['pooledtx']))

    @chainRequest('getnettotals')
    def updateNetTotals(self, totals):
        def format_speed(byte_count, seconds):
            if byte_count is None:
                return '-'
            else:
                return self.byteFormatter(byte_count/float(seconds)) + '/s'

        # Update in-memory RRAs for high-resolution traffic data and averages
        recv = totals['totalbytesrecv']
        self.ui.lRecvTotal.setText(self.byteFormatter(recv))
        self.trafRecv.update(recv)
        self.ui.lRecv10s.setText(
                format_speed(self.trafRecv.difference(-1, -6), 10))
        self.ui.lRecv1m.setText(
                format_speed(self.trafRecv.difference(-1, -31), 60))
        self.ui.lRecv10m.setText(
                format_speed(self.trafRecv.difference(-1, -300), 598))

        sent = totals['totalbytessent']
        self.ui.lSentTotal.setText(self.byteFormatter(sent))
        self.trafSent.update(sent)
        self.ui.lSent10s.setText(
                format_speed(self.trafSent.difference(-1, -6), 10))
        self.ui.lSent1m.setText(
                format_speed(self.trafSent.difference(-1, -31), 60))
        self.ui.lSent10m.setText(
                format_speed(self.trafSent.difference(-1, -300), 598))

        # Update RRDtool database for long-term traffic data
        sampleTime = totals['timemillis']
        self.trafRRD.update(sampleTime, (recv, sent))
        # Postpone updating the plot until updateMemPool so they can redraw at
        # the same time

    @chainRequest('getrawmempool', True)
    def updateMemPool(self, pool):
        self.plotNetTotals()
        now = time.time()
        transactions = pool.values()
        minFreePriority = bitcoinconf.COIN * 144 // 250
        redPen = pyqtgraph.mkPen((255, 0, 0, 100))
        pens = [None]*len(transactions)
        positions = numpy.empty((len(transactions), 2))
        idx_iter = iter(xrange(len(transactions)))
        for tx in transactions:
            fee = float(tx['fee']) / math.ceil(float(tx['size'])/1000.)
            i = next(idx_iter)
            positions[i] = (ageOfTime(now, float(tx['time'])), fee)
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
                self.memPoolPlot.addLine(x=ageOfTime(now, blockTime))

    @QtCore.Slot(QtNetwork.QNetworkReply.NetworkError, str)
    def netError(self, _, err_str):
        self.busy = False
        err_str = 'Network error: {}'.format(err_str)
        if DEBUG:
            sys.stderr.write(err_str + '\n')
        self.statusNetwork.setText(err_str)
        self.plotNetTotals()

    @QtCore.Slot()
    def updateStatusMissedSamples(self):
        self.statusMissedSamples.setText('Missed samples: %d' %
            self.missedSamples)

    @QtCore.Slot()
    def updateStatusRSS(self):
        self.statusRSS.setText('RSS: %s' %
            self.byteFormatter(self.perfProbe.rss))

def load_config(argv):

    "Parse arguments, do global setup, and return a bitcoinconf."

    # Parse arguments
    datadir = None
    conffile = 'bitcoin.conf'
    testnet = False
    for arg in argv[1:]:
        parts = arg.split('=', 1)
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
            global DEBUG
            DEBUG = True
        else:
            sys.stderr.write('Warning: unknown argument ' + arg + '\n')

    # Load Bitcoin configuration
    conf = bitcoinconf.Conf()
    conf.load(datadir, conffile)
    if testnet:
        # CLI overrides config file
        conf['testnet'] = '1'

    # Initialize QSettings identity
    QtGui.qApp.setOrganizationName('Welsh Computing')
    QtGui.qApp.setOrganizationDomain('welshcomputing.com')
    QtGui.qApp.setApplicationName('Bitnomon')

    # QDesktopServices.DataLocation doesn't give the desired result.
    # QStandardPaths.DataLocation in Qt5 does, so mimic that for now.
    # TODO: support other platforms
    global DATA_DIR
    DATA_DIR = os.path.expanduser('~/.local/share/Bitnomon')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    return conf

def main(argv):

    "Main entry point of the program"

    global qApp #pylint: disable=global-statement
    qApp = QtGui.QApplication(argv)
    signal.signal(signal.SIGINT, lambda *args: qApp.closeAllWindows())

    # pyqtgraph's exit crash workaround seems to do more harm than good.
    pyqtgraph.setConfigOption('exitCleanup', False)

    conf = load_config(argv)

    try:
        #pylint: disable=bare-except
        mainWin = MainWindow(conf)
        mainWin.show()
        return QtGui.qApp.exec_()
    except:
        # PyQt4 segfaults if there's an uncaught exception after
        # Ui_MainWindow.setupUi.
        traceback.print_exc()
        return 1
