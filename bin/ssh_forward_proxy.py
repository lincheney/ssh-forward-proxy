import sys
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

SSH_PORT = 22

class Proxy(threading.Thread):
    daemon = True

    def __init__(self, queue, transport):
        threading.Thread.__init__(self)
        self.transport = transport
        self.queue = queue

    def run(self):
        try:
            server_channel = self.transport.accept(20)
            assert(server_channel is not None)
        except Exception as e:
            logging.exception()
            return

        server_channel.send('Hello!')

        server_channel.close()

class ConnectionServer(paramiko.ServerInterface):
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, conn, addr):
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(conn)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        self.thread = Proxy(self.queue, self.transport)
        self.thread.start()

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED
    def check_auth_password(self, username, password):
        self.queue.put(('username', username))
        return paramiko.AUTH_SUCCESSFUL
    def check_auth_publickey(self, username, key):
        self.queue.put(('username', username))
        return paramiko.AUTH_SUCCESSFUL
    
    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        return True
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return False
    def check_channel_exec_request(self, channel, command):
        self.queue.put(('exec', command))
        return True
    def check_channel_env_request(self, channel, name, value):
        return False

def run_server(host, port=SSH_PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.info('bind()')
    sock.bind((host, port))

    logging.info('listen()')
    sock.listen(10)

    try:
        while True:
            r, w, x = select.select([sock], [], [], 1)
            if sock in r:
                conn, addr = sock.accept()
                logging.info('Got a connection!')
                ConnectionServer(conn, addr)
    except KeyboardInterrupt:
        sock.close()
        sys.exit(0)

if __name__ == '__main__':
    run_server('', SSH_PORT)

