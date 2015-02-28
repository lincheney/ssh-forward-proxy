import sys
import os
import select
import socket
import paramiko
import shlex
import subprocess
import threading

try:
    import queue
except ImportError:
    import Queue as queue

import logging
import argparse

logging.basicConfig(level=logging.DEBUG)

class Worker(threading.Thread):
    timeout = 10
    daemon = True
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        try:
            channel, command = self.queue.get(self.timeout)
        except queue.Empty:
            logging.error('Client passed no commands')
            return

        logging.info('Executing %r', command)
        process = subprocess.Popen(
            ['sh', '-c', command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        size = 1024
        endpoint = {process.stdout: channel.sendall, process.stderr: channel.sendall_stderr, channel: process.stdin.raw.write}
        data = True
        while data:
            r, w, x = select.select(list(endpoint.keys()), [], [])
            for stream in r:
                if stream is channel:
                    data = stream.recv(size)
                else:
                    data = stream.raw.read(size)
                endpoint[stream](data)
                if not data:
                    logging.info('No more data on %r', stream)
                    break

        channel.close()

class Server(paramiko.ServerInterface):
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, client):
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(client)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        self.worker = Worker(self.queue)
        self.worker.start()

    def join(self, timeout):
        return self.worker.join(timeout)

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

    servers = []

    try:
        while True:
            #logging.debug('Waiting for connection...')
            r, w, x = select.select([sock], [], [], 1)
            if sock in r:
                logging.debug('accept()')
                client, address = sock.accept()
                logging.info('Got a connection!')
                servers.append(Server(client))
    except KeyboardInterrupt:
        for s in servers:
            s.join(1)
        sock.close()
        sys.exit(0)

if __name__ == '__main__':
    SSH_PORT = 22
    parser = argparse.ArgumentParser(description='Launch a really simple SSH server')
    parser.add_argument('port', nargs='?', default=SSH_PORT, type=int, help='Port (default {})'.format(SSH_PORT))
    parser.add_argument('host', nargs='?', default='', help='Host')
    args = parser.parse_args()

    make_server(args.host, args.port)

