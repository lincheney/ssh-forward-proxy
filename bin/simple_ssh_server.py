import sys
import os
import select
import socket
import paramiko
import threading

try:
    import queue
except ImportError:
    import Queue as queue

import logging
import argparse

logging.basicConfig(level=logging.DEBUG)

class Server(paramiko.ServerInterface):
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, client):
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(client)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        channel, command = self.queue.get()
        channel.send('Command: %s\n' % command)
        channel.close()

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none'

    def check_channel_exec_request(self, channel, command):
        self.queue.put((channel, command))
        return True

def make_server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.debug('bind()')
    sock.bind((host, port))

    logging.debug('listen()')
    sock.listen(100)

    try:
        while True:
            logging.info('Waiting for connection...')
            r, w, x = select.select([sock], [], [], 1)
            if sock in r:
                logging.debug('accept()')
                client, address = sock.accept()
                logging.info('Got a connection!')
                Server(client)
    except KeyboardInterrupt:
        sock.close()
        sys.exit(0)

if __name__ == '__main__':
    make_server('', 22)

