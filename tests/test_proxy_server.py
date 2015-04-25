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

from .test_proxy import IOTest, SimpleProxyTestCase
from ssh_forward_proxy import run_server, ProxyServer, Proxy

class RemoteConnectionTest(SimpleProxyTestCase):
    """
    tests that ProxyServer connects to remote given in HOST environment variable
    """

    def test_connects_to_remote(self):
        """
        it should connect to the remote
        """

        host = 'abcdef'
        port = 12345
        user = 'user'
        host_string = '{}@{}:{}'.format(user, host, port).encode('utf-8')

        server = ProxyServer(sentinel.socket)
        server.check_channel_env_request(sentinel.channel, ProxyServer.HOST, host_string)

        kwargs = {'username': 'string', 'key': 'value'}
        with patch.object(Proxy, 'relay_to_remote') as relay_to_remote:
            server.relay_to_remote(sentinel.client, sentinel.command, host='string', port='string', **kwargs)

            relay_to_remote.assert_called_once_with(
                sentinel.client,
                sentinel.command,
                host=host,
                port=port,
                username=user,
                key='value',
            )

class IOTest(IOTest):
    """
    tests that the proxy connects the remote to the client SSH channel
    """

    def make_proxy(self):
        return ProxyServer(sentinel.socket)

    def setUp(self):
        super(IOTest, self).setUp()
        self.old_proxy_init = Proxy.__init__
        self.add_patch( patch.object(Proxy, '__init__', side_effect=self.proxy_init) )

    def proxy_init(self, proxy, *args, **kwargs):
        proxy.env[ProxyServer.HOST] = b'user@host:1234'
        self.old_proxy_init(proxy, *args, **kwargs)
