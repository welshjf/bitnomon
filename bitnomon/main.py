# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

#pylint: disable=bare-except

"""Main window and program entry point"""

import sys
import os
import time
import math
import traceback
import signal

# This must come before pyqtgraph so it doesn't try to guess the binding
from .qtwrapper import (
    QtCore,
    QtGui,
    QtNetwork,
)
QMessageBox = QtGui.QMessageBox
QIcon = QtGui.QIcon
import numpy
import pyqtgraph
import appdirs

from . import (
    ui_main,
    about,
    bitcoinconf,
    perfprobe,
    qbitcoinrpc,
    rrdmodel,
    formatting,
)
from .age import ageOfTime, AgeAxisItem
from .qsettings import QSettingsGroup, qSettingsProperty

if sys.version_info[0] > 2:
    #pylint: disable=redefined-builtin,invalid-name
    unicode = str
    xrange = range

# Must be global to avoid crash at exit
qApp = None

# Bitnomon global settings
DEBUG = False
TESTNET = False
DATA_DIR = ''
BITCOIN_DATA_DIR = None
BITCOIN_CONF = 'bitcoin.conf'

def printException():
    "Print a stack trace, or just the exception, depending on debug setting"
    if DEBUG:
        traceback.print_exc()
    else:
        sys.stderr.write(str(sys.exc_info()[1]) + '\n')

def pgAxisData(viewBox):
    """Get axis ranges and auto-scale status from a ViewBox, using pyqtgraph
    internals.

    Returns: (xAuto, xMin, xMax, yAuto, yMin, yMax)
    """
    state = viewBox.state
    xAuto, yAuto = state['autoRange']
    (xMin, xMax), (yMin, yMax) = state['targetRange']
    return (bool(xAuto), float(xMin), float(xMax),
            bool(yAuto), float(yMin), float(yMax))

class MainWindowSettings(QSettingsGroup):
    #pylint: disable=too-few-public-methods

    """QSettings model for MainWindow"""

    def __init__(self):
        super(MainWindowSettings, self).__init__('MainWindow')

    size = qSettingsProperty('size')
    pos = qSettingsProperty('pos')
    fullScreen = qSettingsProperty('fullScreen', False, valueType=bool)
    statusBar = qSettingsProperty('statusBar', False, valueType=bool)
    formatBits = qSettingsProperty('formatBits', False, valueType=bool)
    formatSI = qSettingsProperty('formatSI', True, valueType=bool)

    netPlotXAuto = qSettingsProperty('netPlotXAuto', False, valueType=bool)
    netPlotYAuto = qSettingsProperty('netPlotYAuto', True, valueType=bool)
    netPlotXMin = qSettingsProperty('netPlotXMin', valueType=float)
    netPlotXMax = qSettingsProperty('netPlotXMax', valueType=float)
    netPlotYMin = qSettingsProperty('netPlotYMin', valueType=float)
    netPlotYMax = qSettingsProperty('netPlotYMax', valueType=float)

    memPlotXAuto = qSettingsProperty('memPlotXAuto', False, valueType=bool)
    memPlotYAuto = qSettingsProperty('memPlotYAuto', True, valueType=bool)
    # Don't need memPoolPlot X range because it's linked to networkPlot
    memPlotYMin = qSettingsProperty('memPlotYMin', valueType=float)
    memPlotYMax = qSettingsProperty('memPlotYMax', valueType=float)

# API requests are chained sequentially (doesn't seem to work reliably if
# QNetworkAccessManager parallelizes them).
commandChain = []
def chainRequest(method, *args):
    """Decorator to register an API request in the chain. Parameters are the
    API method name and optional arguments. The decorated function is the slot
    that handles the reply."""
    #pylint: disable=missing-docstring
    def decorator(responseHandler):
        def handlerWrapper(self, data):
            try:
                responseHandler(self, data)
            except:
                printException()
            self.nextChainedRequest()
        commandChain.append((method, args, handlerWrapper))
        return handlerWrapper
    return decorator

class MainWindow(QtGui.QMainWindow):
    #pylint: disable=missing-docstring, too-many-instance-attributes
    #pylint: disable=too-many-public-methods

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.ui = ui_main.Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.label_logo.hide()

        self.origWindowTitle = self.windowTitle()

        self.byteFormatter = formatting.ByteCountFormatter()
        self.isFullScreen = False
        self.missedSamples = 0
        self._setupMenus()
        self._setupStatusBar()
        self._setupPlots()
        self.resetZoom()
        try:
            self.readSettings()
        except:
            # Failing to restore UI state is not important enough to bother the
            # user.
            printException()

        self.rpc = None
        self.busy = False
        self.chainIndex = 0
        self.replies = []
        self.tempReply = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.setInterval(2000)
        QtCore.QTimer.singleShot(0, self.loadBitcoinConf)

        if DEBUG:
            self.perfProbe = perfprobe.PerfProbe(self)
            self.perfProbe.updated.connect(self.updateStatusRSS)

    def _setupMenus(self):
        #pylint: disable=attribute-defined-outside-init
        ui = self.ui

        icon = QIcon(QIcon.fromTheme('view-refresh'))
        ui.action_ReloadConf.setIcon(icon)
        ui.action_ReloadConf.triggered.connect(self.loadBitcoinConf)

        ui.action_ClearTraffic.triggered.connect(self.clearTraffic)

        ui.action_ShutDownQuit.triggered.connect(self.shutdown)

        icon = QIcon(QIcon.fromTheme('application-exit'))
        ui.action_Quit.setIcon(icon)

        icon = QIcon(QIcon.fromTheme('view-fullscreen'))
        ui.action_FullScreen.setIcon(icon)
        ui.action_FullScreen.toggled.connect(self.toggleFullScreen)

        icon = QIcon(QIcon.fromTheme('zoom-original'))
        ui.action_ResetZoom.setIcon(icon)
        ui.action_ResetZoom.triggered.connect(self.resetZoom)

        icon = QIcon(QIcon.fromTheme('help-about'))
        ui.action_About.setIcon(icon)
        ui.action_About.triggered.connect(self.about)

        icon = QIcon(':/trolltech/qmessagebox/images/qtlogo-64.png')
        ui.action_AboutQt.setIcon(icon)
        ui.action_AboutQt.triggered.connect(QtGui.qApp.aboutQt)

        ui.action_NetUnits.setSeparator(True)
        ui.netUnitGroup = QtGui.QActionGroup(self)
        ui.netUnitGroup.addAction(ui.action_NetUnitBitSI)
        ui.netUnitGroup.addAction(ui.action_NetUnitByteSI)
        ui.netUnitGroup.addAction(ui.action_NetUnitByteBinary)
        ui.action_NetUnitByteSI.setChecked(True)
        ui.action_NetUnitBitSI.triggered.connect(self.netUnitBitSI)
        ui.action_NetUnitByteSI.triggered.connect(self.netUnitByteSI)
        ui.action_NetUnitByteBinary.triggered.connect(
                self.netUnitByteBinary)

        # Any actions with keyboard shortcuts need to be added to the main
        # window to keep working when the menu bar is hidden :(
        self.addAction(ui.action_Quit)
        self.addAction(ui.action_FullScreen)
        self.addAction(ui.action_ResetZoom)

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
        self.trafSentPlot = pyqtgraph.PlotDataItem(numpy.zeros(traf_intervals),
                pen=(255, 0, 0), fillLevel=0, brush=(255, 0, 0, 100))
        self.trafRecvPlot = pyqtgraph.PlotDataItem(numpy.zeros(traf_intervals),
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
        ui = self.ui
        with MainWindowSettings() as s:
            if s.size:
                self.resize(s.size)
            if s.pos:
                self.move(s.pos)
            ui.action_FullScreen.setChecked(s.fullScreen)
            ui.action_StatusBar.setChecked(s.statusBar)

            if s.formatBits:
                ui.action_NetUnitBitSI.trigger()
            elif s.formatSI:
                ui.action_NetUnitByteSI.trigger()
            else:
                ui.action_NetUnitByteBinary.trigger()

            if s.netPlotXAuto:
                self.networkPlot.enableAutoRange(x=True)
            elif s.memPlotXAuto:
                # FIXME: this doesn't work. Something to do with axis linkage;
                # autoRange gets reset to False when the window is first shown.
                self.memPoolPlot.enableAutoRange(x=True)
            elif None not in (s.netPlotXMin, s.netPlotXMax):
                self.networkPlot.setXRange(
                        s.netPlotXMin,
                        s.netPlotXMax,
                        padding=0)

            if (not s.netPlotYAuto) and (
                    None not in (s.netPlotYMin, s.netPlotYMax)):
                self.networkPlot.setYRange(
                        s.netPlotYMin,
                        s.netPlotYMax,
                        padding=0)

            if (not s.memPlotYAuto) and (
                    None not in (s.memPlotYMin, s.memPlotYMax)):
                self.memPoolPlot.setYRange(
                        s.memPlotYMin,
                        s.memPlotYMax,
                        padding=0)

    def writeSettings(self):
        with MainWindowSettings() as s:
            s.size = self.size()
            s.pos = self.pos()
            s.fullScreen = self.isFullScreen
            s.statusBar = self.ui.action_StatusBar.isChecked()
            s.formatBits = self.byteFormatter.unit_bits
            s.formatSI = self.byteFormatter.prefix_si
            (s.netPlotXAuto,
             s.netPlotXMin,
             s.netPlotXMax,
             s.netPlotYAuto,
             s.netPlotYMin,
             s.netPlotYMax) = pgAxisData(self.networkPlot.getViewBox())
            (s.memPlotXAuto, _, _,
             s.memPlotYAuto,
             s.memPlotYMin,
             s.memPlotYMax) = pgAxisData(self.memPoolPlot.getViewBox())

    def loadBitcoinConf(self):
        conf = bitcoinconf.Conf()
        try:
            conf.load(BITCOIN_DATA_DIR, BITCOIN_CONF)
        except bitcoinconf.FileNotFoundError:
            mb = QMessageBox()
            mb.setWindowTitle(self.tr('Bitcoin Config Not Found'))
            mb.setText(self.tr(
                'Bitcoin configuration file not found. Create one?'
            ))
            mb.setInformativeText(self.tr("""\
Bitcoin Core does not accept API connections from external applications by \
default; a configuration file is required to allow this. Bitnomon can create \
one to allow connections from the local system, restricted to your user \
account by a stored random password. You will need to restart your node for \
this to take effect. As always, if you store funds on this system, it is \
recommended to set a wallet encryption passphrase and keep backups."""
            ))
            mb.setIcon(QMessageBox.Question)
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            mb.setDefaultButton(QMessageBox.Yes)
            ret = mb.exec_()
            if ret == QMessageBox.Yes:
                try:
                    conf.generate(BITCOIN_DATA_DIR, BITCOIN_CONF)
                except EnvironmentError as e:
                    mb = QMessageBox()
                    mb.setWindowTitle(self.tr('Error Writing Bitcoin Config'))
                    mb.setText(self.tr(
                        'Error writing Bitcoin configuration file.'
                    ))
                    mb.setInformativeText(str(e))
                    mb.setIcon(QMessageBox.Critical)
                    mb.exec_()
                except:
                    printException()
        except EnvironmentError as e:
            mb = QMessageBox()
            mb.setWindowTitle(self.tr('Error Loading Bitcoin Config'))
            mb.setText(self.tr('Error loading Bitcoin configuration file.'))
            mb.setInformativeText(str(e))
            mb.setIcon(QMessageBox.Critical)
            mb.exec_()
            return
        except:
            printException()

        if TESTNET:
            # Command line overrides config file
            conf['testnet'] = '1'
        if conf.get('testnet', '0') == '1':
            self.setWindowTitle(self.origWindowTitle + ' [testnet]')
        else:
            self.setWindowTitle(self.origWindowTitle)
        self.rpc = qbitcoinrpc.RPCManager(conf)
        if not self.timer.isActive():
            self.timer.start()
            QtCore.QTimer.singleShot(0, self.update)

    def closeEvent(self, _):
        self.writeSettings()

    def about(self):
        about.AboutDialog(self).show()

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
        self.networkPlot.enableAutoRange(y=True)
        self.memPoolPlot.enableAutoRange(y=True)

    @QtCore.Slot()
    def clearTraffic(self):
        ret = QMessageBox.question(self, self.tr('Clear Traffic Data'),
                self.tr('Clear the long-term network traffic history?'),
                buttons=(QMessageBox.Yes | QMessageBox.No))
        if ret == QMessageBox.Yes:
            self.trafRRD.create()
            self.trafRecv.clear()
            self.trafSent.clear()
            self.plotNetTotals()

    @QtCore.Slot()
    def shutdown(self):
        ret = QMessageBox.question(self,
                self.tr('Shut Down Node and Quit'),
                self.tr('Stop the monitored Bitcoin node as well as Bitnomon?'),
                buttons=(QMessageBox.Yes | QMessageBox.No))
        if ret == QMessageBox.Yes:
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
        ui = self.ui

        def format_speed(byte_count, seconds):
            if byte_count is None:
                return '-'
            else:
                return self.byteFormatter(byte_count/float(seconds)) + '/s'

        # Update in-memory RRAs for high-resolution traffic data and averages
        recv = totals['totalbytesrecv']
        ui.lRecvTotal.setText(self.byteFormatter(recv))
        self.trafRecv.update(recv)
        ui.lRecv10s.setText(
                format_speed(self.trafRecv.difference(-1, -6), 10))
        ui.lRecv1m.setText(
                format_speed(self.trafRecv.difference(-1, -31), 60))
        ui.lRecv10m.setText(
                format_speed(self.trafRecv.difference(-1, -300), 598))

        sent = totals['totalbytessent']
        ui.lSentTotal.setText(self.byteFormatter(sent))
        self.trafSent.update(sent)
        ui.lSent10s.setText(
                format_speed(self.trafSent.difference(-1, -6), 10))
        ui.lSent1m.setText(
                format_speed(self.trafSent.difference(-1, -31), 60))
        ui.lSent10m.setText(
                format_speed(self.trafSent.difference(-1, -300), 598))

        # Update RRDtool database for long-term traffic data
        sampleTime = totals['timemillis']
        self.trafRRD.update(sampleTime, (recv, sent))
        # Postpone updating the plot until updateMemPool so they can redraw at
        # the same time

    @chainRequest('getrawmempool', True)
    def updateMemPool(self, pool):
        try:
            self.plotNetTotals()
        except:
            printException()
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
        try:
            self.plotNetTotals()
        except:
            printException()

    @QtCore.Slot()
    def updateStatusMissedSamples(self):
        self.statusMissedSamples.setText('Missed samples: %d' %
            self.missedSamples)

    @QtCore.Slot()
    def updateStatusRSS(self):
        self.statusRSS.setText('RSS: %s' %
            self.byteFormatter(self.perfProbe.rss))

def main(argv=sys.argv[:]):

    """Main entry point: parse arguments, do global setup, show the main
    window, and start the Qt event loop."""

    global qApp
    argv[0] = 'bitnomon' # Set WM_CLASS on X11
    qApp = QtGui.QApplication(argv)
    signal.signal(signal.SIGINT, lambda *args: qApp.closeAllWindows())

    # Parse arguments
    # TODO: use a proper arg parser; provide help
    global DEBUG, TESTNET, BITCOIN_DATA_DIR, BITCOIN_CONF
    for arg in argv[1:]:
        parts = arg.split('=', 1)
        if parts[0] == '-datadir':
            if len(parts) == 2:
                BITCOIN_DATA_DIR = parts[1]
            else:
                sys.stderr.write('Warning: empty -datadir, needs "="\n')
        elif parts[0] == '-conf':
            if len(parts) == 2:
                BITCOIN_CONF = parts[1]
            else:
                sys.stderr.write('Warning: empty -conf, needs "="\n')
        elif arg == '-testnet':
            TESTNET = True
        elif arg == '-d' or arg == '-debug':
            DEBUG = True
        else:
            sys.stderr.write('Warning: unknown argument ' + arg + '\n')

    # Set up standard directories...
    dirs = appdirs.AppDirs('Bitnomon', 'Welsh Computing')
    # for QSettings
    qApp.setApplicationName(dirs.appname)
    qApp.setOrganizationName(dirs.appauthor)
    qApp.setOrganizationDomain('welshcomputing.com')
    # for RRD
    global DATA_DIR
    DATA_DIR = dirs.user_data_dir
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    try:
        mainWin = MainWindow()
        mainWin.show()
        return QtGui.qApp.exec_()
    except:
        # PyQt4 segfaults if there's an uncaught exception after
        # Ui_MainWindow.setupUi.
        printException()
        return 1
