import sys
import os
import select
import socket
import errno

import logging

try:
    BrokenPipeError
except NameError:
    BrokenPipeError = None

def ignore_broken_pipe(fn, *args):
    try:
        return fn(*args)
    except OSError as e:
        if e.errno == errno.EPIPE:
            return None
        raise
    except BrokenPipeError:
        return None

class StdSocket:
    """
    Fake socket to read from stdin and write to stdout
    conforming to the interface specified at
    http://docs.paramiko.org/en/1.15/api/transport.html
    """

    timeout = None
    def settimeout(self, timeout):
        self.timeout = timeout

    def send(self, string):
        if sys.stdout.closed:
            return 0
        return os.write(sys.stdout.fileno(), string)

    def recv(self, count):
        if sys.stdin.closed:
            return b''
        r, w, x = select.select([sys.stdin], [], [], self.timeout)
        if sys.stdin in r:
            return os.read(sys.stdin.fileno(), count)
        raise socket.timeout()

    def close(self):
        sys.stdin.close()
        sys.stdout.close()

class Stream:
    def pipe_stdout(self, stream, other, size):
        stdout = (self.stdout_ready(stream) and self.read(size))
        if stdout:
            other.write(stdout)
        return stdout

    def pipe_stderr(self, stream, other, size):
        stderr = (self.stderr_ready(stream) and self.read_stderr(size))
        if stderr:
            other.write_stderr(stderr)
        return stderr

class ProcessStream(Stream):
    def __init__(self, process):
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr

        self.streams = [self.stdout, self.stderr]

    def write(self, string):
        return ignore_broken_pipe(os.write, self.stdin.fileno(), string)

    def read(self, n):
        return os.read(self.stdout.fileno(), n)

    def read_stderr(self, n):
        return os.read(self.stderr.fileno(), n)

    def stdout_ready(self, stream):
        return stream is self.stdout

    def stderr_ready(self, stream):
        return stream is self.stderr


class ChannelStream(Stream):
    def __init__(self, channel):
        self.channel = channel

        self.streams = [channel]

        self.read = self.channel.recv
        self.read_stderr = self.channel.recv_stderr

        self.write = self.channel.sendall
        self.write_stderr = self.channel.sendall_stderr

    def stdout_ready(self, stream):
        return self.channel.recv_ready()

    def stderr_ready(self, stream):
        return self.channel.recv_stderr_ready()


def pipe_streams(input, output, size=1024):
    done = False
    while not done:
        r, w, x = select.select(input.streams + output.streams, [], [])

        for stream in r:
            if stream in output.streams:
                stdout = output.pipe_stdout(stream, input, size)
                stderr = output.pipe_stderr(stream, input, size)
                if not (stdout or stderr):
                    logging.debug('Output streams closed')
                    done = True

            if stream in input.streams:
                stdin = input.pipe_stdout(stream, output, size)
                if not stdin:
                    logging.debug('Input streams closed')
                    done = True
