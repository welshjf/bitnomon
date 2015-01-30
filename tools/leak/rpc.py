import decimal
import json
import sys

from qtwrapper import QtCore, QtNetwork

class RPCManager(QtNetwork.QNetworkAccessManager):

    def __init__(self, parent=None):
        super(RPCManager, self).__init__(parent)
        self.rpc_id = 0

    def call(self, method, *args):
        self.rpc_id += 1
        print(self.rpc_id)
        request = QtNetwork.QNetworkRequest(QtCore.QUrl('http://localhost:5000/'))
        reply = self.get(request)
        reply.setParent(None)
        return reply
