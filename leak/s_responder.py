#!/usr/bin/python

import SocketServer
import socket
import sys
import logging
import json

class HttpError(Exception):
    pass

class HttpHandler(SocketServer.BaseRequestHandler):

    max_header_len = 64
    methods = {
        'GET',
        'POST',
    }
    response = 'Hello world\n'

    def handle(self):
        self.rfile = self.request.makefile('rb',-1)
        self.wfile = self.request.makefile('wb',0)

        try:
            self.begin()
            while True:
                self.state_func()
        except EOFError:
            logging.debug('EOF, closing connection')
        except KeyboardInterrupt:
            logging.debug('KeyboardInterrupt, closing connection')
        except HttpError,e:
            logging.warn('HttpError(%s), closing connection' % str(e))

        self.request.shutdown(socket.SHUT_RDWR)
        self.request.close()

    def begin(self):
        self.state_func = self.read_method
        self.headers = {}

    def read_method(self):
        line = self.rfile.readline()
        if len(line) == 0:
            raise EOFError

        parts = line.split()
        if len(parts) == 0:
            return
        elif parts[0] in self.methods:
            self.method = parts[0]
            logging.debug('Method: %s' % ' '.join(parts))
            self.state_func = self.read_header
        else:
            raise HttpError('Unsupported method %s' %
                parts[0][:self.max_header_len])

    def read_header(self):
        line = self.rfile.readline()
        if len(line) == 0:
            raise EOFError

        line = line.rstrip('\r\n')
        if len(line) == 0:
            self.state_func = self.read_content
            return

        if len(line) > 0:
            parts = line.split(': ', 1)
            header = parts[0]
            if len(header) > self.max_header_len:
                logging.warn('ignoring %d byte header name: %s...' %
                    (len(header), header[:self.max_header_len])
                )
            elif len(parts) != 2:
                logging.warn('ignoring malformed header: %s' % header)
            else:
                self.headers[header] = parts[1]

    def read_content(self):
        logging.debug('Headers: %s' % str(self.headers))
        if self.method == 'POST':
            try:
                content_length = int(self.headers['Content-Length'])
                if content_length < 0:
                    raise ValueError
            except KeyError:
                raise HttpError('Missing Content-Length header in POST')
            except ValueError:
                raise HttpError('Invalid Content-Length in POST: %s' %
                    self.headers['Content-Length'][:self.max_header_len])
            content = self.rfile.read(content_length)
            if len(content) < content_length:
                raise HttpError('Read less content than expected')
            self.handle_post(content)
        self.state_func = self.send_response

    def handle_post(self, content):
        logging.debug('Stub POST handler')

    def send_response(self):
        msg = '\r\n'.join((
            'HTTP/1.0 200 OK',
            'Connection: Keep-Alive',
            'Content-Length: %d' % len(self.response),
            '',
            self.response))
        self.wfile.write(msg)
        self.begin()

class JsonRpcHandler(HttpHandler):

    def handle_post(self, data):
        result = {}
        data = json.loads(data)
        id = data['id']
        method = data['method']
        if method == 'getinfo':
            result['blocks'] = 317247
            result['connections'] = 0
        elif method == 'getmininginfo':
            result['difficulty'] = 23844670038.80329895
            result['pooledtx'] = 2512
        elif method == 'getnettotals':
            result['totalbytesrecv'] = 2473056304
            result['totalbytessent'] = 13355852932
        elif method == 'getrawmempool':
            result['003156476fcc8d8a620ef2efa227865088b38697d55e1a6c1b5d1b2e3637fa3b'] = {
                "size" : 191,
                "fee" : 0.00000000,
                "time" : 1407220106,
                "height" : 314036,
                "startingpriority" : 5498181.81818182,
                "currentpriority" : 5666454.06949072,
                "depends" : []
            }
        else:
            logging.warn('Unknown method: %s' % method)
        self.response = json.dumps({'result': result, 'error': None, 'id': id})

class TCPServer(SocketServer.TCPServer):
    allow_reuse_address = True

logging.basicConfig(level=logging.WARN)
server = TCPServer(('localhost', 5000), JsonRpcHandler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
