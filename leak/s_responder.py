#!/usr/bin/python

import SocketServer
import sys

class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        while True:
            line = self.request.recv(1024)
            if len(line) == 0:
                break
            content = 'Hello world'
            response = '\r\n'.join((
                'HTTP/1.0 200 OK',
                'Connection: Keep-Alive',
                'Content-Length: %d' % len(content),
                '',
                content))
            self.request.sendall(response)
            #sys.stderr.write('.')
        #sys.stderr.write('\n')

server = SocketServer.TCPServer(('localhost', 5000), Handler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
