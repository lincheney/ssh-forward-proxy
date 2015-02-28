import sys
import os
import select
import select
import paramiko
import threading

try:
    import queue
except ImportError:
    import Queue as queue

import logging
import argparse

SSH_PORT = 22

class FakeSocket:
    """
    Fake socket to read from stdin and write to stdout
    conforming to the interface specified at
    http://docs.paramiko.org/en/1.15/api/transport.html
    """

    timeout = None
    def settimeout(self, timeout):
        self.timeout = timeout

    def send(self, string):
        if sys.stdout.closed:
            return 0
        return os.write(sys.stdout.fileno(), string)

    def recv(self, count):
        if sys.stdin.closed:
            return ''
        r, w, x = select.select([sys.stdin], [], [], self.timeout)
        if sys.stdin in r:
            return os.read(sys.stdin.fileno(), count)
        raise socket.timeout()

    def close(self):
        sys.stdin.close()
        sys.stdout.close()

class Proxy(threading.Thread):
    daemon = True

    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server
        self.transport = self.server.transport

    def _run(self, client_channel):
        username = self.server.user_queue.get()
        client_channel.send('Hello %s!' % username)

        command = self.server.exec_queue.get()
        client_channel.send('Command: %s' % command)

    def run(self):
        try:
            client_channel = self.transport.accept(20)
            assert(client_channel is not None)
        except Exception as e:
            logging.exception('Failed to open channel to client')
            return

        try:
            self._run(client_channel)
        except Exception as e:
            logging.exception('Error serving')
        finally:
            client_channel.close()

class ConnectionServer(paramiko.ServerInterface):
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, conn, addr):
        self.exec_queue = queue.Queue()
        self.user_queue = queue.Queue()

        self.transport = paramiko.Transport(conn)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        self.thread = Proxy(self)
        self.thread.start()

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED
    def check_auth_password(self, username, password):
        self.user_queue.put(username)
        return paramiko.AUTH_SUCCESSFUL
    def check_auth_publickey(self, username, key):
        self.user_queue.put(username)
        return paramiko.AUTH_SUCCESSFUL
    def check_auth_none(self, username):
        self.user_queue.put(username)
        return paramiko.AUTH_SUCCESSFUL
    
    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        return True
    def check_channel_exec_request(self, channel, command):
        self.exec_queue.put(command)
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
