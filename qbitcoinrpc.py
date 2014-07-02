# qbitcoinrpc.py
# Jacob Welsh, April 2014
# Based loosely on python-bitcoinlib/bitcoin/rpc.py: Copyright 2011 Jeff Garzik
# Based in turn on python-jsonrpc/jsonrpc/proxy.py. Original copyright:
##
## Copyright (c) 2007 Jan-Klaas Kollhof
##
## This file is part of jsonrpc.
##
## jsonrpc is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2.1 of the License, or
## (at your option) any later version.
##
## This software is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this software; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# The above license applies only to the parts of this file that may be
# considered derived from the originals. Any parts not subject to the above
# copyrights may be reused under either the above terms OR the same terms as
# the rest of Bitnomon.

"""Asynchronous Bitcoin Core RPC support for Qt"""

import decimal
import json

from PySide import QtCore, QtNetwork

import bitcoinconf

class JSONRPCException(Exception):
	def __init__(self, error):
		super(JSONRPCException, self).__init__('msg: %r  code: %r' %
				(error['message'], error['code']))
		self.error = error

class QNetworkReplyError(Exception):
	def __init__(self, error):
		super(QNetworkReplyError, self).__init__(error.name)

class RPCReply(QtCore.QObject):

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
	error = QtCore.Signal(QtNetwork.QNetworkReply.NetworkError)

	def __init__(self, networkReply):
		super(RPCReply, self).__init__()
		self.networkReply = networkReply
		self.networkReply.setParent(None)
		self.networkReply.finished.connect(self._read_reply)
		self.networkReply.error.connect(self._error)
		self._starttime = QtCore.QDateTime.currentMSecsSinceEpoch()

	def _error(self, err):
		self.networkReply.finished.disconnect()
		self.error.emit(err)

	def _read_reply(self):
		self.rtt = QtCore.QDateTime.currentMSecsSinceEpoch() - self._starttime
		reply_text = bytes(self.networkReply.readAll()).decode('utf8')
		reply_obj = json.loads(reply_text, parse_float=decimal.Decimal)
		if reply_obj['error'] is not None:
			raise JSONRPCException(reply['error'])
		self.finished.emit(reply_obj['result'])

class RPCProxy(QtCore.QObject):

	"""Bitcoin JSON-RPC proxy based on Qt's asynchronous networking

	To use this, create a proxy object, which will manage connections to
	the Bitcoin Core node as defined in bitcoin.conf. Invoke any desired
	method on this object, optionally with keyword arguments. It will send
	the request over the network and return immediately. See RPCReply for
	what to do with the return value.
	"""

	host = 'localhost'
	port = 8332
	useragent = 'bitnomon/0.1'

	def __init__(self, conf={}, parent=None):
		super(RPCProxy, self).__init__(parent)
		if conf.get('testnet','0') == '1':
			self.port = 18332
		if 'rpcport' in conf:
			self.port = conf['rpcport']
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

	def _call(self, method, *args):
		self.rpc_id += 1
		request = QtNetwork.QNetworkRequest(self.url)
		request.setRawHeader('User-Agent', self.useragent)
		request.setRawHeader('Content-Type', 'application/json')
		request.setAttribute(QtNetwork.QNetworkRequest.HttpPipeliningAllowedAttribute, True)
		postdata = json.dumps({
			'version': '1.1',
			'method': method,
			'params': args,
			'id': self.rpc_id
			})
		return RPCReply(self.manager.post(request, postdata))

	def __getattr__(self, method):
		if method.startswith('__') and method.endswith('__'):
			# Python internal stuff
			raise AttributeError

		# Create a callable to do the actual call
		f = lambda *args: self._call(method, *args)

		# Make debuggers show <function qbitcoinrpc.name> rather than <function
		# qbitcoinrpc.<lambda>>
		f.__name__ = method
		return f
