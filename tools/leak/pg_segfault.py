#!/usr/bin/python3

import sys
from PyQt4 import QtCore, QtGui
import pyqtgraph

class PlotWindow(QtGui.QWidget):

    def __init__(self, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.plot = pyqtgraph.PlotWidget(self)
        QtCore.QTimer.singleShot(0, self.close)

app = QtGui.QApplication(sys.argv)
window = PlotWindow()
window.show()
app.exec_()
#pyqtgraph.exit()
