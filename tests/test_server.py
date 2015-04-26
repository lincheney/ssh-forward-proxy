import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

from . import fake_io, helper

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

import paramiko
from ssh_forward_proxy import run_server, Server, ServerInterface

ROOT_DIR = os.path.abspath(os.path.join(__file__, '..', '..'))

class ServerScriptTest(unittest.TestCase):
    def test_server(self):
        """
        test that we can SSH into server
        """

        PORT = '4002'
        server = None

        self.env = {}
        self.env['PYTHONPATH'] = ROOT_DIR

        try:
            server_cmd = os.path.join(ROOT_DIR, 'bin', 'simple-ssh-server.py')
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
        self.add_patch( patch('paramiko.Transport.start_server') )


        self.queue = queue.Queue()

class TransportTest(PatchedServer):
    SERVER = Server

    def patch_get_command(self):
        self.add_patch( patch.object(ServerInterface, 'get_command', return_value=(None, None)) )

    @patch('paramiko.Transport')
    def test_transport_opened_to_socket(self, transport):
        """
        proxy should open SSH transport to given socket
        """

        self.patch_get_command()
        self.SERVER(sentinel.socket)
        transport.assert_called_once_with(sentinel.socket)

    @patch('paramiko.Transport')
    def test_no_ssh_command(self, transport):
        """
        server should close transport and exit if no commands within the timeout
        """

        # reduce the timeout to 1 second
        with patch.object(ServerInterface, 'timeout', new_callable=mock.PropertyMock(return_value=1)):
            server = self.SERVER(sentinel.socket)
            server.transport.close.assert_called_with()

    def test_default_host_key(self):
        """
        server should load the default key provided in the package
        """

        self.patch_get_command()
        server = self.SERVER(sentinel.socket)
        server.transport.host_key_type = 'ssh-rsa'

        server_key = server.transport.get_server_key()
        expected_key = paramiko.RSAKey(filename=os.path.join(self.ROOT_DIR, 'tests', 'default-server-key'))
        self.assertEqual( server_key, expected_key )

    def test_host_key(self):
        """
        server should load the default key provided in the package
        """

        self.patch_get_command()
        key_path = os.path.join(self.ROOT_DIR, 'tests', 'test-server-key')
        server = self.SERVER(sentinel.socket, server_key=key_path)
        server.transport.host_key_type = 'ssh-rsa'

        server_key = server.transport.get_server_key()
        expected_key = paramiko.RSAKey(filename=key_path)
        self.assertEqual( server_key, expected_key )

class ServerIOTest(PatchedServer):

    def setUp(self):
        super(ServerIOTest, self).setUp()

        self.client = fake_io.FakeInputChannel()
        self.queue.put((self.client, sentinel.command))

        self.process = fake_io.FakeProcess()
        self.add_patch( patch('subprocess.Popen', return_value=self.process) )

    def tearDown(self):
        super(ServerIOTest, self).tearDown()
        fake_io.close_fake_io(self.client)
        fake_io.close_fake_io(self.process)

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

    client = None

    def tearDown(self):
        super(ServerProcessTest, self).tearDown()
        if self.client:
            fake_io.close_fake_io(self.client)

    def test_returncode(self):
        """
        server should give the appropriate return code
        """

        self.client = fake_io.FakeInputChannel()
        self.queue.put((self.client, 'exit 5'))
        self.client.closed = False
        server = Server(sentinel.socket)
        self.client.send_exit_status.assert_called_with(5)

    def test_ssh_channel_closed(self):
        """
        server should exit if ssh channel closed even if process is still running
        """

        self.client = fake_io.FakeInputChannel()
        self.queue.put((self.client, 'yes'))
        self.client.closed = True
        server = Server(sentinel.socket)

    def test_process_closed(self):
        """
        server should exit if process closed even if client is still connected
        """

        self.client = fake_io.FakeInputChannel(cmd=['yes'])
        self.queue.put((self.client, 'true'))
        server = Server(sentinel.socket)
        self.assertIsNone( self.client.inputs[0].poll() )
