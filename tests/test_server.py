import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

import os
import shlex
import subprocess
import shutil
import time
import sys

try:
    import queue
except ImportError:
    import Queue as queue

from . import fake_io, helper
from ssh_forward_proxy import run_server, Server

class ServerScriptTest(unittest.TestCase):

    ROOT_DIR = os.path.abspath(os.path.join(__file__, '..', '..'))

    def test_server(self):
        """
        test that we can SSH into server
        """

        PORT = '4000'
        server = None

        self.env = {}
        self.env['PYTHONPATH'] = self.ROOT_DIR

        try:
            server_cmd = os.path.join(self.ROOT_DIR, 'bin', 'simple-ssh-server.py')
            server = subprocess.Popen([sys.executable, server_cmd, PORT], env=self.env)
            # wait a second
            time.sleep(1)
            subprocess.check_call(['ssh', '-o', 'StrictHostKeyChecking=no', '-p', PORT, 'localhost', 'true'])

        finally:
            if server:
                server.kill()


class PatchedServer(helper.TestCase):
    def setUp(self):
        super(PatchedServer, self).setUp()
        self.add_patch( patch.object(queue, 'Queue', return_value=queue.Queue()) )
        self.add_patch( patch('paramiko.Transport') )

        self.queue = queue.Queue()

class ServerIOTest(PatchedServer):

    def setUp(self):
        super(ServerIOTest, self).setUp()

        self.client = fake_io.FakeSocket('stdin.txt')
        self.queue.put((self.client, sentinel.command))

        self.process = fake_io.FakeProcessSocket()
        self.add_patch( patch('subprocess.Popen', return_value=self.process) )

    def tearDown(self):
        super(ServerIOTest, self).tearDown()
        fake_io.close_fake_socket(self.client)
        fake_io.close_fake_socket(self.process)

    def test_stdin_copied_to_remote(self):
        """
        client stdin should be copied to process stdin
        """

        server = Server(sentinel.socket)
        self.process.stdin.close()
        result = self.process.readable_stdin.read()
        expected = fake_io.read_file('stdin.txt')
        self.assertEqual(result, expected)

    def test_stdout_copied_to_client(self):
        """
        remote stdout should be copied to client stdout
        """

        server = Server(sentinel.socket)
        result = self.client.stdout.getvalue()
        expected = fake_io.read_file('stdout.txt')
        self.assertEqual(result, expected)

    def test_stderr_copied_to_client(self):
        """
        remote stderr should be copied to client stderr
        """

        server = Server(sentinel.socket)
        result = self.client.stderr.getvalue()
        expected = fake_io.read_file('stderr.txt')
        self.assertEqual(result, expected)

class ServerProcessTest(PatchedServer):

    def setUp(self):
        super(ServerProcessTest, self).setUp()
        self.client = fake_io.FakeSocket('stdin.txt')

    def tearDown(self):
        super(ServerProcessTest, self).tearDown()
        fake_io.close_fake_socket(self.client)

    def test_returncode(self):
        """
        server should give the appropriate return code
        """

        self.queue.put((self.client, 'exit 5'))
        self.client.closed = False
        server = Server(sentinel.socket)
        self.client.send_exit_status.assert_called_with(5)

    def test_ssh_channel_closed(self):
        """
        server should exit if ssh channel closed even if process is still running
        """

        self.queue.put((self.client, 'sleep infinity'))
        self.client.closed = True
        server = Server(sentinel.socket)
