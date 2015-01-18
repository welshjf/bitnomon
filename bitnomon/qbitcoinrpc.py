# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.
#
# Based loosely on python-bitcoinlib/bitcoin/rpc.py:
#  Copyright 2011 Jeff Garzik
#
# Previous copyright, from python-jsonrpc/jsonrpc/proxy.py:
#
# Copyright (c) 2007 Jan-Klaas Kollhof
#
# This file is part of jsonrpc.
#
# jsonrpc is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""Asynchronous Bitcoin Core RPC support for Qt"""

import decimal
import base64
import json

from .qtwrapper import QtCore, QtNetwork
from . import __version__

class JSONRPCError(Exception):
    "Error returned in JSON-RPC response"

    def __init__(self, error):
        super(JSONRPCError, self).__init__(error['code'], error['message'])

    def __str__(self):
        return 'code: {}, message: {}'.format(*self.args)

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
            raise JSONRPCError(reply_obj['error'])
        self.finished.emit(reply_obj['result'])

class RPCManager(QtCore.QObject):

    """Bitcoin JSON-RPC request manager, based on Qt's asynchronous
    networking"""

    useragent = 'bitnomon/' + __version__

    def __init__(self, conf=None, parent=None):
        super(RPCManager, self).__init__(parent)

        if conf is None:
            conf = {}

        if conf.get('testnet', '0') == '1':
            rpcport = 18332
        else:
            rpcport = 8332

        # Don't try to format the URL ourselves; QUrl knows how to
        # handle literal IPv6 addresses and whatnot.
        self.url = QtCore.QUrl()
        self.url.setScheme('http')
        self.url.setHost(conf.get('rpcconnect', 'localhost'))
        self.url.setPort(int(conf.get('rpcport', rpcport)))
        self.url.setPath('/')

        authpair = conf.get('rpcuser', '') + ':' + conf.get('rpcpassword', '')
        self.auth = b'Basic ' + base64.b64encode(authpair.encode('utf8'))

        self.manager = QtNetwork.QNetworkAccessManager()
        self.rpc_id = 0

    def request(self, method, *args):
        """Invoke a method over the network, optionally with keyword arguments.
        Returns immediately with an RPCReply."""
        self.rpc_id += 1
        request = QtNetwork.QNetworkRequest(self.url)
        request.setRawHeader('User-Agent', self.useragent)
        request.setRawHeader('Authorization', self.auth)
        request.setRawHeader('Content-Type', 'application/json')
        request.setAttribute(
                QtNetwork.QNetworkRequest.HttpPipeliningAllowedAttribute, True)
        data = json.dumps({
            'version': '1.1',
            'method': method,
            'params': args,
            'id': self.rpc_id
            })
        return RPCReply(self.manager.post(request, data))
