try:
    from unittest import mock
except ImportError:
    import mock

import os
import subprocess
from io import BytesIO

def open_file(file):
    return open(os.path.join(os.path.dirname(__file__), file), 'rb')

def read_file(file):
    with open_file(file) as f:
        return f.read()

def FakeInputChannel(file='stdin.txt', cmd=None):
    m = mock.Mock()

    if cmd:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.close = lambda: (proc.poll() is None and proc.kill())
        m.inputs = [proc]
        stdin = proc.stdout
    else:
        m.inputs = [open_file(file)]
        stdin = m.inputs[0]

    m.stdout = BytesIO()
    m.stderr = BytesIO()
    m.fileno = stdin.fileno
    m.recv = stdin.read
    m.sendall = m.stdout.write
    m.sendall_stderr = m.stderr.write
    return m

def FakeOutputChannel():
    m = FakeInputChannel(file='stdout.txt')
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
