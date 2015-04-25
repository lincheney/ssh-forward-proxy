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
import subprocess
PIPE = subprocess.PIPE

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

        StdSocket().send(b'hello')
        self.stdout[1].close()
        self.assertEqual( self.stdout[0].read(), b'hello' )

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

        bytes = b'abcdefgh'
        self.stdin[1].write(bytes)
        self.stdin[1].close()
        result = StdSocket().recv(4)
        self.assertEqual( result, bytes[:4] )
        self.assertEqual( self.stdin[0].read(), bytes[4:] )

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

class ProcessStreamTest(unittest.TestCase):

    def make_process(self, cmd):
        self.process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
        return self.process

    def make_stream(self, cmd):
        self.stream = ProcessStream(self.make_process(cmd))
        return self.stream

    def tearDown(self):
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        if self.process.poll() is None:
            self.process.kill()

    def test_streams(self):
        """
        streams should have the readable streams
        """

        self.make_stream('true')
        self.assertEqual( self.stream.streams, [self.process.stdout, self.process.stderr] )

    def test_write(self):
        """
        writes to stdin
        """

        self.make_stream('tr l m').write(b'hello') # swap l with m
        self.process.stdin.close()
        self.assertEqual( self.process.stdout.read(), b'hemmo' )

    def test_read(self):
        """
        reads from stdout
        """

        bytes = b'abcdefgh'
        self.make_stream( 'echo {}'.format(bytes.decode('utf-8')) )
        result = self.stream.read(4)
        self.assertEqual( result, bytes[:4] )
        self.assertEqual( self.process.stdout.read(), bytes[4:] + b'\n' )

    def test_read_more(self):
        """
        does not block when reading more than is available
        """

        bytes = b'abcdefgh'
        self.make_stream( 'echo {} && sleep infinity'.format(bytes.decode('utf-8')) )
        result = self.stream.read(100)
        self.assertEqual( result, bytes + b'\n' )

    def test_read_stderr(self):
        """
        reads from stderr
        """

        bytes = b'abcdefgh'
        self.make_stream( 'echo {} >&2'.format(bytes.decode('utf-8')) )
        result = self.stream.read_stderr(4)
        self.assertEqual( result, bytes[:4] )
        self.assertEqual( self.process.stderr.read(), bytes[4:] + b'\n' )

    def test_read_stderr_more(self):
        """
        does not block when reading more than is available
        """

        bytes = b'abcdefgh'
        self.make_stream( 'echo {} >&2 && sleep infinity'.format(bytes.decode('utf-8')) )
        result = self.stream.read_stderr(100)
        self.assertEqual( result, bytes + b'\n' )

    def test_stdout_ready(self):
        """
        basically just tests if the stream is correct
        """

        self.make_stream('true')
        self.assertTrue( self.stream.stdout_ready(self.process.stdout) )
        self.assertFalse( self.stream.stdout_ready(self.process.stdin) )
        self.assertFalse( self.stream.stdout_ready(self.process.stderr) )

    def test_stderr_ready(self):
        """
        basically just tests if the stream is correct
        """

        self.make_stream('true')
        self.assertTrue( self.stream.stderr_ready(self.process.stderr) )
        self.assertFalse( self.stream.stderr_ready(self.process.stdin) )
        self.assertFalse( self.stream.stderr_ready(self.process.stdout) )
