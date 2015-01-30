#!/usr/bin/python3

import sys, signal
#from PySide import QtCore, QtNetwork
from PyQt4 import QtCore, QtGui, QtNetwork
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot

import rpc

class Poller(QtCore.QObject):

    url = QtCore.QUrl("http://localhost:5000/")

    def __init__(self, parent=None):
        super(Poller,self).__init__(parent)
        self.manager = rpc.RPCManager()

    def start(self):
        self.reply = self.manager.call('getinfo')
        self.reply.finished.connect(self.readReply)
        self.reply.error.connect(self.error)

    def readReply(self):
        text = self.reply.readAll()
        self.reply.deleteLater()
        #self.reply = None # culprit??
        QtCore.QTimer.singleShot(10, self.start)

    @QtCore.Slot(QtNetwork.QNetworkReply.NetworkError)
    def error(self, err):
        sys.stderr.write('Error: {}\n'.format(self.sender().errorString()))
        self.reply.finished.disconnect()
        self.reply.deleteLater()
        QtCore.QTimer.singleShot(10, self.start)

signal.signal(signal.SIGINT, signal.SIG_DFL)
app = QtGui.QApplication(sys.argv)
p = Poller()
p.start()
app.exec_()
