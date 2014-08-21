#!/usr/bin/python

import sys, signal
from PySide import QtCore, QtNetwork
#from PyQt4 import QtCore, QtNetwork
#QtCore.Signal = QtCore.pyqtSignal
#QtCore.Slot = QtCore.pyqtSlot

class Poller(QtCore.QObject):
    url = QtCore.QUrl("http://localhost:5000/")

    def __init__(self, parent=None):
        super(Poller,self).__init__(parent)
        self.manager = QtNetwork.QNetworkAccessManager()

    def start(self):
        request = QtNetwork.QNetworkRequest(self.url)
        self.reply = self.manager.get(request)
        self.reply.finished.connect(self.readReply)
        self.reply.error.connect(self.error)

    def readReply(self):
        text = self.reply.readAll()
        #self.reply.close() # doesn't help
        #self.reply.deleteLater() # doesn't help
        self.reply.setParent(None)
        #QtCore.QTimer.singleShot(10, self.start)
        QtCore.QTimer.singleShot(0, self.start)

    @QtCore.Slot(QtNetwork.QNetworkReply.NetworkError)
    def error(self, err):
        sys.stderr.write('Error: ' + str(err) + '\n')
        QtCore.QCoreApplication.instance().quit()

signal.signal(signal.SIGINT, signal.SIG_DFL)
app = QtCore.QCoreApplication(sys.argv)
p = Poller()
p.start()
app.exec_()
