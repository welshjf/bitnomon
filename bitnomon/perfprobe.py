# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

import os
import sys
from .qtwrapper import QtCore

class PerfProbe(QtCore.QObject):

    "Performance probe of Bitnomon resource usage"

    pageSize = os.sysconf(os.sysconf_names['SC_PAGESIZE'])
    clockTickInterval = 1. / os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    updated = QtCore.Signal()

    def __init__(self, parent=None):

        super(PerfProbe, self).__init__(parent)

        self.probeTimer = QtCore.QTimer(self)
        self.probeTimer.timeout.connect(self.run)
        self.probeTimer.start(1000)
        QtCore.QTimer.singleShot(0, self.run)

        from .main import DEBUG
        if DEBUG:
            self.logTimer = QtCore.QTimer(self)
            self.logTimer.timeout.connect(self.logCSV)
            self.logTimer.start(1000*60)
            QtCore.QTimer.singleShot(0, self.logCSV)
            sys.stdout.write('"User time (sec)","RSS (KiB)"\n')

    @QtCore.Slot()
    def run(self):
        with open('/proc/self/stat', 'rb') as f:
            stat = f.read().split()
        self.rss = int(stat[23]) * self.pageSize
        self.utime = int(float(stat[13]) * self.clockTickInterval)
        self.updated.emit()

    @QtCore.Slot()
    def logCSV(self):
        sys.stdout.write('%d,%d\n' % (self.utime, self.rss // 1024))
        sys.stdout.flush()
