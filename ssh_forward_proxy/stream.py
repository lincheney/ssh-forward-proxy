import sys
import os
import select
import socket

import logging

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
            return ''
        r, w, x = select.select([sys.stdin], [], [], self.timeout)
        if sys.stdin in r:
            return os.read(sys.stdin.fileno(), count)
        raise socket.timeout()

    def close(self):
        sys.stdin.close()
        sys.stdout.close()


class ProcessStream:
    def __init__(self, process):
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr

        self.streams = [self.stdout, self.stderr]

    def write(self, string):
        return os.write(self.stdin.fileno(), string)

    def read(self, n):
        return os.read(self.stdout.fileno(), n)

    def read_stderr(self, n):
        return os.read(self.stderr.fileno(), n)

    def stdout_ready(self, stream):
        return stream is self.stdout

    def stderr_ready(self, stream):
        return stream is self.stderr


class ChannelStream:
    def __init__(self, channel):
        self.channel = channel

        self.streams = [channel]

        self.read = self.channel.recv
        self.read_stderr = self.channel.recv_stderr

        self.write = self.channel.sendall
        self.write_stderr = self.channel.sendall_stderr

    def stdout_ready(self, stream):
        return self.channel.recv_ready()

    def stderr_ready(self, size):
        return self.channel.recv_stderr_ready()


def pipe_streams(input, output, size=1024):
    done = False
    while not done:
        r, w, x = select.select(input.streams + output.streams, [], [])

        for stream in r:
            if stream in output.streams:
                stdout = (output.stdout_ready(stream) and output.read(size))
                if stdout:
                    input.write(stdout)
                stderr = (output.stderr_ready(stream) and output.read_stderr(size))
                if stderr:
                    input.write_stderr(stderr)
                if not stdout and not stderr:
                    logging.debug('Output streams closed')
                    done = True

            if stream in input.streams:
                stdin = input.read(size)
                if stdin:
                    output.write(stdin)
                else:
                    logging.debug('Input streams closed')
                    done = True
