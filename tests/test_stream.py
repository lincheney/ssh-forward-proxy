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
import paramiko
import subprocess
PIPE = subprocess.PIPE

from ssh_forward_proxy import StdSocket, ChannelStream, ProcessStream

DATA = b'abcdefgh'

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

        StdSocket().send(DATA)
        self.stdout[1].close()
        self.assertEqual( self.stdout[0].read(), DATA )

    def test_send_closed(self):
        """
        send() should return 0 when closed
        """

        self.stdout[1].close()
        self.assertEqual( StdSocket().send(DATA), 0 )

    def test_recv(self):
        """
        recv() should read from stdin
        """

        self.stdin[1].write(DATA)
        self.stdin[1].close()
        result = StdSocket().recv(4)
        self.assertEqual( result, DATA[:4] )
        self.assertEqual( self.stdin[0].read(), DATA[4:] )

    def test_recv_closed(self):
        """
        recv() should return an empty string when closed
        """

        self.stdin[0].close()
        self.assertEqual( StdSocket().recv(4), b'' )

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

        self.make_stream('tr l m').write(0, b'hello') # swap l with m
        self.process.stdin.close()
        self.assertEqual( self.process.stdout.read(), b'hemmo' )

    def test_read_stdout(self):
        """
        reads from stdout
        """

        self.make_stream( 'echo {}'.format(DATA.decode('utf-8')) )
        result = self.stream.read(self.stream.STDOUT, 4)
        self.assertEqual( result, DATA[:4] )
        self.assertEqual( self.process.stdout.read(), DATA[4:] + b'\n' )

    def test_read_more_stdout(self):
        """
        does not block when reading more than is available
        """

        self.make_stream( 'echo {} && sleep infinity'.format(DATA.decode('utf-8')) )
        result = self.stream.read(self.stream.STDOUT, 100)
        self.assertEqual( result, DATA + b'\n' )

    def test_read_stderr(self):
        """
        reads from stderr
        """

        self.make_stream( 'echo {} >&2'.format(DATA.decode('utf-8')) )
        result = self.stream.read(self.stream.STDERR, 4)
        self.assertEqual( result, DATA[:4] )
        self.assertEqual( self.process.stderr.read(), DATA[4:] + b'\n' )

    def test_read_more_stderr(self):
        """
        does not block when reading more than is available
        """

        self.make_stream( 'echo {} >&2 && sleep infinity'.format(DATA.decode('utf-8')) )
        result = self.stream.read(self.stream.STDERR, 100)
        self.assertEqual( result, DATA + b'\n' )

    def test_stdout_ready(self):
        """
        basically just tests if the stream is correct
        """

        self.make_stream('true')
        self.assertTrue( self.stream.ready(self.stream.STDOUT, self.process.stdout) )
        self.assertFalse( self.stream.ready(self.stream.STDOUT, self.process.stdin) )
        self.assertFalse( self.stream.ready(self.stream.STDOUT, self.process.stderr) )

    def test_stderr_ready(self):
        """
        basically just tests if the stream is correct
        """

        self.make_stream('true')
        self.assertTrue( self.stream.ready(self.stream.STDERR, self.process.stderr) )
        self.assertFalse( self.stream.ready(self.stream.STDERR, self.process.stdin) )
        self.assertFalse( self.stream.ready(self.stream.STDERR, self.process.stdout) )

    def test_pipe_stdout(self):
        """
        pipes stdout to another stream
        """

        self.make_stream( 'echo {}'.format(DATA.decode('utf-8')) )
        other = mock.Mock()
        result = self.stream.pipe(self.stream.STDOUT, self.stream.stdout, other, 4)
        self.assertEqual( result, DATA[:4] )
        other.write.assert_called_once_with(self.stream.STDOUT, DATA[:4])

    def test_pipe_stderr(self):
        """
        pipes stderr to another stream
        """

        self.make_stream( 'echo {} >&2'.format(DATA.decode('utf-8')) )
        other = mock.Mock()
        result = self.stream.pipe(self.stream.STDERR, self.stream.stderr, other, 4)
        self.assertEqual( result, DATA[:4] )
        other.write.assert_called_once_with(self.stream.STDERR, DATA[:4])

class ChannelStreamTest(unittest.TestCase):
    """
    basic API test for ChannelStream
    """

    def make_channel(self):
        self.channel = mock.Mock(spec=paramiko.Channel)
        return self.channel

    def test_api(self):
        stream = ChannelStream(self.make_channel())

        self.assertEqual( stream.streams, [self.channel] )
        self.assertTrue( hasattr(stream, 'read') )
        self.assertTrue( hasattr(stream, 'write') )
        self.assertTrue( hasattr(stream, 'ready') )
        self.assertTrue( hasattr(stream, 'pipe') )

    def test_read(self):
        stream = ChannelStream(self.make_channel())
        self.assertEqual( stream.read(stream.STDOUT, 10), self.channel.recv(10) )
        self.assertEqual( stream.read(stream.STDERR, 10), self.channel.recv_stderr(10) )

    def test_write(self):
        stream = ChannelStream(self.make_channel())
        self.assertEqual( stream.write(stream.STDOUT, DATA), self.channel.sendall(DATA) )
        self.assertEqual( stream.write(stream.STDERR, DATA), self.channel.sendall_stderr(DATA) )

    def test_ready(self):
        stream = ChannelStream(self.make_channel())
        self.assertEqual( stream.ready(stream.STDOUT, sentinel.stream), self.channel.recv_ready() )
        self.assertEqual( stream.ready(stream.STDERR, sentinel.stream), self.channel.recv_stderr_ready() )
