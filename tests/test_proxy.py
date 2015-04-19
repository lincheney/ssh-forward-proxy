import unittest
from unittest import mock
from unittest.mock import patch, sentinel

try:
    import queue
except ImportError:
    import Queue as queue

from bin.ssh_forward_proxy import Proxy

class WithSimpleProxy:
    """
    mocks out the __init__() method of Proxy
    """

    def setUp(self):
        self.proxy_patch = patch('bin.ssh_forward_proxy.Proxy.__init__', return_value=None)
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
