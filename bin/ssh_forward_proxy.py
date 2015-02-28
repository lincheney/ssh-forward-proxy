import sys
import os
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

def make_client(host, port, username):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logging.info('Connecting to ssh host %s@%s:%d ...', username, host, port)
    client.connect(host, port, username=username)
    return client

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

class Pipe:
    def run_command(self, client_channel, command):
        client_channel.send('Hello %s!\n' % self.username)
        client_channel.send('Command: %s\n' % command)

    def run(self, username, client_channel, command):
        self.username = username
        self.run_command(client_channel, command)
        client_channel.close()

class Proxy(paramiko.ServerInterface):
    timeout = 10
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, remote):
        self.username = None
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(FakeSocket())
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        try:
            channel, command = self.queue.get(self.timeout)
        except queue.Empty:
            logging.error('Client passed no commands')
            sys.exit(1)
        Pipe().run(self.username, channel, command)

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_none(self, username):
        self.username = username
        return paramiko.AUTH_SUCCESSFUL
    
    def get_allowed_auths(self, username):
        return 'none'

    def check_channel_exec_request(self, channel, command):
        self.queue.put((channel, command))
        return True

if __name__ == '__main__':
    host = sys.argv[1]
    port = int(sys.argv[2])
    user = sys.argv[3]
    remote = make_client(host, port, user)

    Proxy(remote)

