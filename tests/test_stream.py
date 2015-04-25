import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

import sys
import os
import socket

from ssh_forward_proxy import StdSocket, ChannelStream, ProcessStream

class StdSocketTest(unittest.TestCase):

    def make_pipe(self):
        pipe = os.pipe()
        return list(map(os.fdopen, pipe, ['rb', 'wb']))

    def setUp(self):
        self.stdin = self.make_pipe()
        self.stdout = self.make_pipe()

        sys.stdin = self.stdin[0]
        sys.stdout = self.stdout[1]

    def tearDown(self):
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__

        for i in (self.stdin + self.stdout):
            if not i.closed:
                i.close()

    def test_settimeout(self):
        """
        settimeout() should not fail
        """

        StdSocket().settimeout(10)

    def test_send(self):
        """
        send() should write to stdout
        """

        StdSocket().send('hello')
        self.stdout[1].close()
        self.assertEqual( self.stdout[0].read(), 'hello' )

    def test_send_closed(self):
        """
        send() should return 0 when closed
        """

        self.stdout[1].close()
        self.assertEqual( StdSocket().send('hello'), 0 )

    def test_recv(self):
        """
        recv() should read from stdin
        """

        string = 'abcdefgh'
        self.stdin[1].write(string)
        self.stdin[1].close()
        result = StdSocket().recv(4)
        self.assertEqual( result, string[:4] )
        self.assertEqual( self.stdin[0].read(), string[4:] )

    def test_recv_closed(self):
        """
        recv() should return an empty string when closed
        """

        self.stdin[0].close()
        self.assertEqual( StdSocket().recv(4), '' )

    def test_recv_timeout(self):
        """
        recv() should raise a timeout error if no input after timeout
        """

        sock = StdSocket()
        sock.settimeout(1)
        with self.assertRaises(socket.timeout):
            sock.recv(4)

    def test_close(self):
        """
        close() should close both stdin and stdout
        """

        sys.stdin = mock.Mock()
        sys.stdout = mock.Mock()
        StdSocket().close()
        sys.stdin.close.assert_called_once_with()
        sys.stdout.close.assert_called_once_with()

