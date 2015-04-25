import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

import os
import sys
try:
    import queue
except ImportError:
    import Queue as queue

import paramiko
from . import fake_io
from ssh_forward_proxy import Proxy, StdSocket

class WithSimpleProxy:
    """
    mocks out the __init__() method of Proxy
    """

    def setUp(self):
        self.proxy_patch = patch.object(Proxy, '__init__', return_value=None)
        self.proxy_patch.start()
    def tearDown(self):
        self.proxy_patch.stop()

class TransportTest(unittest.TestCase):
    @patch('ssh_forward_proxy.StdSocket', return_value=sentinel.std_socket)
    @patch('paramiko.Transport.start_server')
    def test_std_socket_used(self, transport, std_socket):
        """
        proxy should connect SSH to stdin, stdout, stderr
        """

        with patch.object(Proxy, 'get_command', return_value=(None, None)):
            proxy = Proxy('host', 1234)
            self.assertIs(proxy.transport.sock, sentinel.std_socket)

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
    def test_connects_to_remote(self, client):
        """
        it should connect to the remote
        """

        host = 'abcdef'
        port = 12345
        kwargs = {'username': 'user', 'key': 'value'}
        Proxy.connect_to_remote(host=host, port=port, **kwargs)

        client.assert_called_once_with()
        client.return_value.connect.assert_called_once_with(host, port, **kwargs)

    @patch('paramiko.SSHClient')
    def test_client_is_returned(self, client):
        result = Proxy.connect_to_remote('abcdef', 12345, 'user')
        self.assertIs(result, client.return_value)

class TransportTest(unittest.TestCase):
    """
    tests for the paramiko.Transport
    """

    @patch.object(Proxy, 'get_command', return_value=(None, None))
    @patch('paramiko.Transport')
    def test_transport_opened_to_std_streams(self, transport, get_command):
        """
        proxy should open SSH transport to stdin, stdout and stderrr
        """

        with patch('ssh_forward_proxy.StdSocket') as sock:
            Proxy()
            transport.assert_called_once_with(sock())

    @patch.object(Proxy, 'get_command', return_value=(None, None))
    @patch('paramiko.Transport')
    def test_transport_opened_to_st(self, transport, get_command):
        """
        proxy should open SSH transport to given socket
        """

        Proxy(sentinel.socket)
        transport.assert_called_once_with(sentinel.socket)


class IOTest(unittest.TestCase):
    """
    tests that the proxy connects the remote to stdin,stdout,stderr
    """

    def add_patch(self, patch):
        patch.start()
        self.patches.append(patch)

    def setUp(self):
        self.client = fake_io.FakeSocket('stdin.txt')
        self.remote_channel = fake_io.FakeOutputSocket()

        self.patches = []
        self.add_patch( patch.object(queue, 'Queue', return_value=queue.Queue()) )
        self.add_patch( patch.object(Proxy, 'connect_to_remote') )
        self.add_patch( patch('paramiko.Transport') )

        self.queue = queue.Queue()
        self.remote = Proxy.connect_to_remote()

        self.remote.get_transport().open_session.return_value = self.remote_channel
        self.queue.put((self.client, sentinel.command))

    def tearDown(self):
        for p in self.patches:
            p.stop()
        fake_io.close_fake_socket(self.remote_channel)
        fake_io.close_fake_socket(self.client)

    def make_proxy(self):
        return Proxy(host='host', port=1234)

    def test_exec_command_on_remote(self):
        """
        command should be executed on remote
        """

        self.make_proxy()
        self.remote_channel.exec_command.assert_called_once_with(sentinel.command)

    def test_stdin_copied_to_remote(self):
        """
        client stdin should be copied to remote's stdin
        """

        self.make_proxy()
        result = self.remote_channel.stdout.getvalue()
        expected = fake_io.read_file('stdin.txt')
        self.assertEqual(result, expected)

    def test_stdout_copied_to_client(self):
        """
        remote stdout should be copied to client stdout
        """

        self.make_proxy()
        result = self.client.stdout.getvalue()
        expected = fake_io.read_file('stdout.txt')
        self.assertEqual(result, expected)

    def test_stderr_copied_to_client(self):
        """
        remote stderr should be copied to client stderr
        """

        self.make_proxy()
        result = self.client.stderr.getvalue()
        expected = fake_io.read_file('stderr.txt')
        self.assertEqual(result, expected)

    def test_channels_closed(self):
        """
        all channels are closed after the session is over
        """

        self.make_proxy()
        self.client.close.assert_called_once_with()
        self.remote.close.assert_called_once_with()
