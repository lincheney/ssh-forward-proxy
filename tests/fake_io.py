try:
    from unittest import mock
except ImportError:
    import mock

import os
from io import BytesIO

def open_file(file):
    return open(os.path.join(os.path.dirname(__file__), file), 'rb')

def read_file(file):
    with open_file(file) as f:
        return f.read()

def FakeSocket(file):
    m = mock.Mock()
    m.input = open_file(file)
    m.stdout = BytesIO()
    m.stderr = BytesIO()
    m.fileno = m.input.fileno
    m.recv = m.input.read
    m.sendall = m.stdout.write
    m.sendall_stderr = m.stderr.write
    return m

def FakeOutputSocket():
    m = FakeSocket('stdout.txt')
    m.input2 = open_file('stderr.txt')
    m.recv_stderr = m.input2.read
    return m

def FakeProcessSocket():
    m = mock.Mock()

    m.input = open_file('stdout.txt')
    m.stdout = mock.Mock(wraps=m.input, raw=m.input)

    m.input2 = open_file('stderr.txt')
    m.stderr = mock.Mock(wraps=m.input2, raw=m.input2)

    m.stdin = mock.Mock(raw=BytesIO())

    return m
