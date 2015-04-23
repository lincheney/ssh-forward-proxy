import sys
import os
import socket
import select
import paramiko
import threading
import subprocess

try:
    import queue
except ImportError:
    import Queue as queue

import logging

class ProcessStream:
    def __init__(self, process):
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr
        self.streams = [self.stdout, self.stderr]
        self.write = self.stdin.raw.write
        self.read = self.stdout.raw.read
        self.read_stderr = self.stderr.raw.read
    def stdout_ready(self, stream):
        return stream is self.stdout
    def stderr_ready(self, stream):
        return stream is self.stderr

class ChannelStream:
    def __init__(self, channel):
        self.channel = channel
        self.streams = [channel]
        self.write = self.channel.sendall
        self.write_stderr = self.channel.sendall_stderr
        self.read = self.channel.recv
        self.read_stderr = self.channel.recv_stderr
    def stdout_ready(self, stream):
        return self.channel.recv_ready()
    def stderr_ready(self, size):
        return self.channel.recv_stderr_ready()

class StdSocket:
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


def pipe_streams(input, output, size=1024):
    done = False
    while not done:
        r, w, x = select.select(input.streams + output.streams, [], [])

        for stream in r:
            if stream in output.streams:
                stdout = (output.stdout_ready(stream) and output.read(size))
                if stdout:
                    input.write(stdout)
                stderr = (output.stderr_ready(stream) and output.read_stderr(size))
                if stderr:
                    input.write_stderr(stderr)
                if not stdout and not stderr:
                    logging.debug('Output streams closed')
                    done = True

            if stream in input.streams:
                stdin = input.read(size)
                if stdin:
                    output.write(stdin)
                else:
                    logging.debug('Input streams closed')
                    done = True

class Server(paramiko.ServerInterface):
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

class Proxy(Server):
    def __init__(self, remote_host, remote_port, username=None, **kwargs):
        self.username = username
        Server.__init__(self, StdSocket())

        client, command = self.get_command()
        if not client:
            return

        self.remote = None
        try:
            self.remote = self.connect_to_remote(
                remote_host,
                remote_port,
                username or self.username,
                **kwargs
            )
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
    def connect_to_remote(host, port, username, **kwargs):
        client = paramiko.SSHClient()
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

class ServerWorker(Server):
    def __init__(self, socket):
        Server.__init__(self, socket)

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
            client.send_exit_status(process.wait())
        finally:
            if process:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            client.close()
            self.transport.close()

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none'


def run_server(host, port):
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

            thread = threading.Thread(target=ServerWorker, args=(client,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
    except KeyboardInterrupt:
        # stop server on ctrl+c
        pass
    finally:
        sock.close()
        sys.exit(0)
