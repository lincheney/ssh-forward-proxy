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
    STDOUT = 0
    STDERR = 1

    def pipe(self, key, stream, other, size):
        output = (self.ready(key, stream) and self.read(key, size))
        if output:
            other.write(key, output)
        return output

class ProcessStream(Stream):
    def __init__(self, process):
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr

        self.streams = [self.stdout, self.stderr]

    def read(self, key, n):
        return os.read(self.streams[key].fileno(), n)

    def write(self, key, buf):
        return ignore_broken_pipe(os.write, self.stdin.fileno(), buf)

    def ready(self, key, stream):
        return stream is self.streams[key]


class ChannelStream(Stream):
    def __init__(self, channel):
        self.channel = channel
        self.streams = [channel]
        self.func_map = [
            [self.channel.recv, self.channel.sendall, self.channel.recv_ready],
            [self.channel.recv_stderr, self.channel.sendall_stderr, self.channel.recv_stderr_ready],
        ]

    def read(self, key, n):
        return self.func_map[key][0](n)

    def write(self, key, buf):
        return self.func_map[key][1](buf)

    def ready(self, key, stream):
        return self.func_map[key][2]()


def pipe_streams(input, output, size=1024):
    done = False
    while not done:
        r, w, x = select.select(input.streams + output.streams, [], [])

        for stream in r:
            if stream in output.streams:
                stdout = output.pipe(Stream.STDOUT, stream, input, size)
                stderr = output.pipe(Stream.STDERR, stream, input, size)
                if not (stdout or stderr):
                    logging.debug('Output streams closed')
                    done = True

            if stream in input.streams:
                stdin = input.pipe(Stream.STDOUT, stream, output, size)
                if not stdin:
                    logging.debug('Input streams closed')
                    done = True
