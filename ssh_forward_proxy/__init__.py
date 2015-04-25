import sys
import socket
import paramiko
import threading
import subprocess
import errno

try:
    import queue
except ImportError:
    import Queue as queue

try:
    ProcessLookupError
except NameError:
    ProcessLookupError = None

import logging

from .util import *
from .stream import *

class ServerInterface(paramiko.ServerInterface):
    timeout = 10
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, socket):
        paramiko.ServerInterface.__init__(self)
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(socket)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

    def get_command(self):
        try:
            return self.queue.get(self.timeout)
        except queue.Empty:
            logging.error('Client passed no commands')
            self.transport.close()
            return None, None
        except Exception as e:
            self.transport.close()
            raise e

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        self.queue.put((channel, command))
        return True

class Proxy(ServerInterface):
    def __init__(self, socket=None, username=None, **kwargs):
        self.username = username
        ServerInterface.__init__(self, socket or StdSocket())

        client, command = self.get_command()
        if client:
            self.relay_to_remote(client, command, username=self.username, **kwargs)

    def relay_to_remote(self, client, command, *args, **kwargs):
        self.remote = None
        try:
            self.remote = self.connect_to_remote(*args, **kwargs)
            remote = self.remote.get_transport().open_session()
            remote.exec_command(command)

            pipe_streams(ChannelStream(client), ChannelStream(remote))
            if remote.exit_status_ready():
                status = remote.recv_exit_status()
                client.send_exit_status(status)
        finally:
            client.close()
            if self.remote:
                self.remote.close()
            self.transport.close()

    @staticmethod
    def connect_to_remote(host, port, username, host_key_check=True, **kwargs):
        client = paramiko.SSHClient()
        if host_key_check:
            client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logging.info('Connecting to ssh host %s@%s:%s ...', username, host, port)
        client.connect(host, port, username=username, **kwargs)
        return client

    def check_auth_none(self, username):
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none'

class ProxyServer(Proxy):
    HOST = b'__HOST__'

    def __init__(self, *args, **kwargs):
        self.env = {}
        Proxy.__init__(self, *args, **kwargs)

    def check_channel_env_request(self, channel, key, value):
        self.env[key] = value
        return True

    def relay_to_remote(self, *args, **kwargs):
        username, host, port = parse_host_string(self.env[self.HOST].decode('utf-8'))
        kwargs.update(username=username, host=host, port=port)
        return super(ProxyServer, self).relay_to_remote(*args, **kwargs)

class Server(ServerInterface):
    def __init__(self, socket):
        ServerInterface.__init__(self, socket)

        client, command = self.get_command()
        if not client:
            return

        logging.info('Executing %r', command)
        process = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )

            pipe_streams(ChannelStream(client), ProcessStream(process))
            if not client.closed:
                client.send_exit_status(process.wait())
        finally:
            self.kill_process(process)
            client.close()
            self.transport.close()

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none'

    def kill_process(self, process):
        if not process:
            return
        try:
            process.stdout.close()
            process.stdin.close()
            process.stderr.close()
            process.kill()
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise
        except ProcessLookupError:
            pass

def run_server(host, port, worker=Server, **kwargs):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.debug('bind()')
    sock.bind((host, port))

    logging.debug('listen()')
    sock.listen(100)

    threads = []
    try:
        while True:
            # clean up closed connections
            threads = [t for t in threads if not t.isAlive()]

            logging.debug('accept()')
            logging.info('Server started')
            client, address = sock.accept()
            logging.info('Got a connection!')

            thread = threading.Thread(target=worker, args=(client,), kwargs=kwargs)
            thread.daemon = True
            threads.append(thread)
            thread.start()
    except KeyboardInterrupt:
        # stop server on ctrl+c
        pass
    finally:
        sock.close()
