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
    IS_PYSIDE,
)
QMessageBox = QtGui.QMessageBox
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
        if IS_PYSIDE:
            sys.stderr.write('Warning: restoring state from QSettings not ' +
                    'supported with PySide\n')
        else:
            try:
                self.readSettings()
            except:
                # Failing to restore UI state is not important enough to bother
                # the user.
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

        # FIXME: not very pythonic

        settings = QtCore.QSettings()
        settings.beginGroup('MainWindow')

        if settings.contains('size'):
            self.resize(settings.value('size', type=QtCore.QSize))
        if settings.contains('pos'):
            self.move(settings.value('pos', type=QtCore.QPoint))
        if settings.value('fullScreen', type=bool):
            self.ui.action_FullScreen.trigger()
        self.ui.action_StatusBar.setChecked(
                settings.value('statusBar', type=bool))

        if settings.value('formatBits', type=bool):
            self.ui.action_NetUnitBitSI.trigger()
        elif settings.contains('formatSI'):
            if settings.value('formatSI', type=bool):
                self.ui.action_NetUnitByteSI.trigger()
            else:
                self.ui.action_NetUnitByteBinary.trigger()

        if settings.value('netPlotXAuto', False, type=bool):
            self.networkPlot.enableAutoRange(x=True)
        elif settings.value('memPlotXAuto', False, type=bool):
            # FIXME: this doesn't work. Something to do with axis linkage;
            # autoRange gets reset to False when the window is first shown.
            self.memPoolPlot.enableAutoRange(x=True)
        elif (settings.contains('netPlotXMin') and
                settings.contains('netPlotXMax')):
            self.networkPlot.setXRange(
                    settings.value('netPlotXMin', type=float),
                    settings.value('netPlotXMax', type=float),
                    padding=0)
        if not settings.value('netPlotYAuto', True, type=bool):
            self.networkPlot.setYRange(
                    settings.value('netPlotYMin', type=float),
                    settings.value('netPlotYMax', type=float),
                    padding=0)
        if not settings.value('memPlotYAuto', True, type=bool):
            self.memPoolPlot.setYRange(
                    settings.value('memPlotYMin', type=float),
                    settings.value('memPlotYMax', type=float),
                    padding=0)

        settings.endGroup()

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup('MainWindow')

        settings.setValue('size', self.size())
        settings.setValue('pos', self.pos())
        settings.setValue('fullScreen', self.isFullScreen)
        settings.setValue('statusBar', self.ui.action_StatusBar.isChecked())

        settings.setValue('formatBits', self.byteFormatter.unit_bits)
        settings.setValue('formatSI', self.byteFormatter.prefix_si)

        netXAuto, netXMin, netXMax, netYAuto, netYMin, netYMax = pgAxisData(
                self.networkPlot.getViewBox())
        memXAuto, _, _, memYAuto, memYMin, memYMax = pgAxisData(
                self.memPoolPlot.getViewBox())
        settings.setValue('netPlotXAuto', netXAuto)
        settings.setValue('memPlotXAuto', memXAuto)
        if not netXAuto and not memXAuto:
            settings.setValue('netPlotXMin', netXMin)
            settings.setValue('netPlotXMax', netXMax)
        # Don't need memPoolPlot X range because it's linked to networkPlot
        settings.setValue('netPlotYAuto', netYAuto)
        if not netYAuto:
            settings.setValue('netPlotYMin', netYMin)
            settings.setValue('netPlotYMax', netYMax)
        settings.setValue('memPlotYAuto', memYAuto)
        if not memYAuto:
            settings.setValue('memPlotYMin', memYMin)
            settings.setValue('memPlotYMax', memYMax)

        settings.endGroup()

    def loadBitcoinConf(self):
        conf = bitcoinconf.Conf()
        try:
            conf.load(BITCOIN_DATA_DIR, BITCOIN_CONF)
        except bitcoinconf.FileNotFoundError:
            mb = QMessageBox()
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

def load_config(argv):

    "Parse arguments, do global setup, and return a bitcoinconf."
    # FIXME: Lies. Refactoring.

    # Parse arguments
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

    # Get standard directories...
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

def main(argv=sys.argv[:]):

    "Main entry point of the program"

    global qApp
    qApp = QtGui.QApplication(argv)
    signal.signal(signal.SIGINT, lambda *args: qApp.closeAllWindows())

    load_config(argv)

    try:
        mainWin = MainWindow()
        mainWin.show()
        return QtGui.qApp.exec_()
    except:
        # PyQt4 segfaults if there's an uncaught exception after
        # Ui_MainWindow.setupUi.
        printException()
        return 1
