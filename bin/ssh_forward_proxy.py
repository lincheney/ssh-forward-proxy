import sys
import os
import socket
import select
import paramiko
import threading

try:
    import queue
except ImportError:
    import Queue as queue

import logging
import argparse

logging.basicConfig(level=logging.INFO)

def parse_host_string(host):
    user, _, host = host.partition('@')
    host, _, port = host.partition(':')
    port = (port and int(port))
    return user, host, port

class Proxy(paramiko.ServerInterface):
    timeout = 10
    host_key = paramiko.RSAKey(filename='server-key')

    def __init__(self, socket, args):
        self.username = None
        self.queue = queue.Queue()

        self.transport = paramiko.Transport(socket)
        self.transport.add_server_key(self.host_key)
        self.transport.start_server(server=self)

        try:
            client, command = self.queue.get(self.timeout)
        except queue.Empty:
            logging.error('Client passed no commands')
            self.transport.close()
            return
        except Exception as e:
            self.transport.close()
            raise e

        self.remote = None
        try:
            self.remote = self.connect_to_remote(
                args.remote,
                args.remote_port,
                args.username or self.username,
                key_filename=args.identity_file,
            )
            remote = self.remote.get_transport().open_session()
            remote.exec_command(command)

            size = 1024
            while True:
                r, w, x = select.select([client, remote], [], [])

                if remote in r:
                    stdout = (remote.recv_ready() and remote.recv(size))
                    if stdout:
                        client.sendall(stdout)
                    stderr = (remote.recv_stderr_ready() and remote.recv_stderr(size))
                    if stderr:
                        client.sendall_stderr(stderr)
                    if not stdout and not stderr:
                        logging.debug('Output streams closed')
                        break

                if client in r:
                    content = client.recv(size)
                    if not content:
                        logging.debug('Input stream closed')
                        break
                    remote.sendall(content)

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

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_none(self, username):
        self.username = username
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'none'

    def check_channel_exec_request(self, channel, command):
        self.queue.put((channel, command))
        return True

def run_server(host, port, args):
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
            client, address = sock.accept()
            logging.info('Got a connection!')

            thread = threading.Thread(target=Proxy, args=(client, args))
            thread.daemon = True
            threads.append(thread)
            thread.start()
    except KeyboardInterrupt:
        # stop server on ctrl+c
        sock.close()
        sys.exit(0)

if __name__ == '__main__':
    SSH_PORT = 22
    parser = argparse.ArgumentParser(description='Forward all SSH requests to remote but authenticating as the proxy')
    parser.add_argument('remote', help='Remote host ([USER@]HOST:[PORT]). Default port is same as port argument.')
    parser.add_argument('port', nargs='?', default=SSH_PORT, type=int, help='Port (default {})'.format(SSH_PORT))
    parser.add_argument('host', nargs='?', default='', help='Host')
    parser.add_argument('-i', dest='identity_file', help='Path to identity file (same as ssh -i)')

    args = parser.parse_args()
    args.username, args.remote, args.remote_port = parse_host_string(args.remote)
    args.remote_port = (args.remote_port or args.port)

    run_server(args.host, args.port, args)
