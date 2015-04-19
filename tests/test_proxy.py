import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

import os
import sys
from io import BytesIO
try:
    import queue
except ImportError:
    import Queue as queue

from ssh_forward_proxy import Proxy

class WithSimpleProxy:
    """
    mocks out the __init__() method of Proxy
    """

    def setUp(self):
        self.proxy_patch = patch.object(Proxy, '__init__', return_value=None)
        self.proxy_patch.start()
    def tearDown(self):
        self.proxy_patch.stop()

class UsernameTest(WithSimpleProxy, unittest.TestCase):
    """
    tests for Proxy.check_auth_none
    """

    def test_username_is_stored(self):
        """
        proxy should store username after auth
        """

        proxy = Proxy()
        proxy.username = None
        proxy.check_auth_none('abcdef')
        self.assertEqual(proxy.username, 'abcdef')

class ExecTest(WithSimpleProxy, unittest.TestCase):
    """
    tests for Proxy.check_channel_exec_request
    """

    def test_command_is_queued(self):
        """
        proxy should queue socket and command on ssh exec
        """

        proxy = Proxy()
        proxy.queue = queue.Queue()
        proxy.check_channel_exec_request(sentinel.channel, sentinel.command)
        queued_items = proxy.queue.get(0)
        self.assertEqual(queued_items, (sentinel.channel, sentinel.command))

class RemoteConnectionTest(unittest.TestCase):
    """
    tests for Proxy.connect_to_remote
    """

    @patch('paramiko.SSHClient')
    def test_connection_is_made(self, client):
        """
        it should connect to the remote
        """

        host = 'abcdef'
        port = 12345
        user = 'user'
        kwargs = {'key': 'value'}
        Proxy.connect_to_remote(host, port, user, **kwargs)

        client.assert_called_once_with()
        client.return_value.connect.assert_called_once_with(host, port, username=user, **kwargs)

    @patch('paramiko.SSHClient')
    def test_client_is_returned(self, client):
        result = Proxy.connect_to_remote('abcdef', 12345, 'user')
        self.assertIs(result, client.return_value)

class IOTest(unittest.TestCase):

    class Error(Exception):
        pass

    @staticmethod
    def open_file(file):
        return open(os.path.join(os.path.dirname(__file__), file), 'rb')
    @staticmethod
    def read_file(file):
        with IOTest.open_file(file) as f:
            return f.read()

    @staticmethod
    def FakeSocket(file):
        m = mock.Mock()
        m.input = IOTest.open_file(file)
        m.stdout = BytesIO()
        m.stderr = BytesIO()
        m.fileno = m.input.fileno
        m.recv = m.input.read
        m.sendall = m.stdout.write
        m.sendall_stderr = m.stderr.write
        return m

    @staticmethod
    def FakeOutputSocket():
        m = IOTest.FakeSocket('stdout.txt')
        m.input2 = IOTest.open_file('stderr.txt')
        m.recv_stderr = m.input2.read
        return m

    def setUp(self):
        self.remote_channel = self.FakeOutputSocket()
        self.client = self.FakeSocket('stdin.txt')

        self.patches = []
        self.patches.append( patch.object(Proxy, 'connect_to_remote') )
        self.patches.append( patch.object(queue, 'Queue', return_value=queue.Queue()) )
        self.patches.append( patch('paramiko.Transport') )

        self.patched = [p.start() for p in self.patches]
        self.remote = self.patched[0]
        self.queue = self.patched[1]

        self.remote().get_transport().open_session.return_value = self.remote_channel
        self.queue().put((self.client, sentinel.command))

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.remote_channel.input.close()
        self.remote_channel.input2.close()
        self.client.input.close()

    def make_proxy(self):
        return Proxy(sentinel.socket, 'host', 1234)

    def test_exec_command_on_remote(self):
        """
        command should be executed on remote
        """

        try:
            self.make_proxy()
        except self.Error:
            pass
        self.remote_channel.exec_command.assert_called_once_with(sentinel.command)

    def test_stdin_copied_to_remote(self):
        """
        client stdin should be copied to remote's stdin
        """

        self.make_proxy()
        result = self.remote_channel.stdout.getvalue()
        expected = self.read_file('stdin.txt')
        self.assertEqual(result, expected)

    def test_stdout_copied_to_client(self):
        """
        remote stdout should be copied to client stdout
        """

        self.make_proxy()
        result = self.client.stdout.getvalue()
        expected = self.read_file('stdout.txt')
        self.assertEqual(result, expected)

    def test_stderr_copied_to_client(self):
        """
        remote stderr should be copied to client stderr
        """

        self.make_proxy()
        result = self.client.stderr.getvalue()
        expected = self.read_file('stderr.txt')
        self.assertEqual(result, expected)

    def test_channels_closed(self):
        """
        all channels are closed after the session is over
        """

        self.make_proxy()
        self.client.close.assert_called_once_with()
        self.remote().close.assert_called_once_with()
