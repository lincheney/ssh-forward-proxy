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

def FakeInputChannel(file='stdin.txt'):
    m = mock.Mock()
    m.inputs = [open_file(file)]
    m.stdout = BytesIO()
    m.stderr = BytesIO()
    m.fileno = m.inputs[0].fileno
    m.recv = m.inputs[0].read
    m.sendall = m.stdout.write
    m.sendall_stderr = m.stderr.write
    return m

def FakeOutputChannel():
    m = FakeInputChannel('stdout.txt')
    m.inputs.append( open_file('stderr.txt') )
    m.recv_stderr = m.inputs[-1].read
    return m

def FakeProcess():
    m = mock.Mock()

    m.stdout = open_file('stdout.txt')
    m.stderr = open_file('stderr.txt')

    stdin = os.pipe()
    stdin = [os.fdopen(stdin[0], 'rb'), os.fdopen(stdin[1], 'wb')]
    m.stdin = stdin[1]
    m.readable_stdin = stdin[0]

    m.inputs = [m.stdout, m.stderr] + stdin

    return m

def close_fake_io(io):
    for i in io.inputs:
        i.close()
