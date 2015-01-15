# qbitcoinrpc.py
# Jacob Welsh, 2014
# Based loosely on python-bitcoinlib/bitcoin/rpc.py: Copyright 2011 Jeff Garzik

#pylint: disable=invalid-name

"""Asynchronous Bitcoin Core RPC support for Qt"""

import decimal
import json

from bitnomon.qtwrapper import QtCore, QtNetwork

class JSONRPCException(Exception):
    "Error returned in JSON-RPC response"
    def __init__(self, error):
        super(JSONRPCException, self).__init__('msg: %r  code: %r' %
                (error['message'], error['code']))
        self.error = error

class RPCReply(QtCore.QObject):
    #pylint: disable=too-few-public-methods

    """QtNetwork.QNetworkReply wrapper for handling JSON-RPC results

    Do not instantiate this directly; it is returned by an RPCProxy call.
    Connect the "finished" signal of this object to a slot that receives
    the JSON result, deserialized into a Python object. Also connect the
    "error" signal to be informed of errors (unlike QNetworkReply.finished,
    RPCReply.finished will not be emitted in case of error).

    Floating point numbers in the JSON text will be parsed as Decimal.

    As with other Qt objects in PySide, do not allow it to go out of scope
    prior to its signal being emmitted, or bad things will happen.
    """

    finished = QtCore.Signal(object)
    error = QtCore.Signal(QtNetwork.QNetworkReply.NetworkError, str)

    def __init__(self, networkReply):
        super(RPCReply, self).__init__()
        self.networkReply = networkReply
        self.networkReply.setParent(None)
        self.networkReply.finished.connect(self._read_reply)
        self.networkReply.error.connect(self._error)
        self._starttime = QtCore.QDateTime.currentMSecsSinceEpoch()
        self.rtt = 0

    def _error(self, err):
        'Internal slot for handling network error'
        self.networkReply.finished.disconnect()
        self.error.emit(err, self.networkReply.errorString())

    def _read_reply(self):
        'Internal slot for handling network reply; emits "finished"'
        self.rtt = QtCore.QDateTime.currentMSecsSinceEpoch() - self._starttime
        reply_text = bytes(self.networkReply.readAll()).decode('utf8')
        reply_obj = json.loads(reply_text, parse_float=decimal.Decimal)
        if reply_obj['error'] is not None:
            raise JSONRPCException(reply_obj['error'])
        self.finished.emit(reply_obj['result'])

class RPCManager(QtCore.QObject):

    """Bitcoin JSON-RPC request manager, based on Qt's asynchronous
    networking"""

    host = 'localhost'
    port = 8332
    useragent = 'bitnomon/0.1'

    def __init__(self, conf=None, parent=None):
        super(RPCManager, self).__init__(parent)
        if conf is None:
            conf = {}
        if conf.get('testnet', '0') == '1':
            self.port = 18332
        if 'rpcport' in conf:
            self.port = int(conf['rpcport'])
        if 'rpcconnect' in conf:
            self.host = conf['rpcconnect']

        # Don't try to format the URL ourselves; QUrl knows how to
        # handle literal IPv6 addresses and whatnot.
        self.url = QtCore.QUrl()
        self.url.setScheme('http')
        self.url.setHost(self.host)
        self.url.setPort(self.port)
        self.url.setPath('/')
        if 'rpcuser' in conf:
            self.url.setUserName(conf['rpcuser'])
        if 'rpcpassword' in conf:
            self.url.setPassword(conf['rpcpassword'])
        self.manager = QtNetwork.QNetworkAccessManager()
        self.rpc_id = 0

    def request(self, method, *args):
        """Invoke a method over the network, optionally with keyword arguments.
        Returns immediately with an RPCReply."""
        self.rpc_id += 1
        request = QtNetwork.QNetworkRequest(self.url)
        request.setRawHeader('User-Agent', self.useragent)
        request.setRawHeader('Content-Type', 'application/json')
        request.setAttribute(
                QtNetwork.QNetworkRequest.HttpPipeliningAllowedAttribute, True)
        postdata = json.dumps({
            'version': '1.1',
            'method': method,
            'params': args,
            'id': self.rpc_id
            })
        return RPCReply(self.manager.post(request, postdata))
