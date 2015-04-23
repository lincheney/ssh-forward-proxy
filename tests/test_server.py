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

from . import fake_io
from ssh_forward_proxy import run_server, ServerWorker

class ServerTest(unittest.TestCase):

    ROOT_DIR = os.path.abspath(os.path.join(__file__, '..', '..'))

    def test_server(self):
        return
        """
        test that we can SSH into server
        """

        PORT = '4000'
        server = None
        try:
            server_cmd = os.path.join(self.ROOT_DIR, 'bin', 'simple-ssh-server.py')
            server = subprocess.Popen([sys.executable, server_cmd, PORT])
            # wait a second
            time.sleep(1)
            subprocess.check_call(['ssh', '-p', PORT, 'localhost', 'true'])

        finally:
            if server:
                server.kill()

class ServerWorkerTest(unittest.TestCase):
    class Error(Exception):
        pass

    def setUp(self):
        self.client = fake_io.FakeSocket('stdin.txt')
        self.process = fake_io.FakeProcessSocket()

        self.patches = []
        self.patches.append( patch('subprocess.Popen', return_value=self.process) )
        self.patches.append( patch.object(queue, 'Queue', return_value=queue.Queue()) )
        self.patches.append( patch('paramiko.Transport') )

        self.patched = [p.start() for p in self.patches]
        self.queue = self.patched[1]

        self.queue().put((self.client, sentinel.command))

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.client.input.close()
        self.process.input.close()
        self.process.input2.close()

    def test_stdin_copied_to_remote(self):
        """
        client stdin should be copied to process stdin
        """

        server = ServerWorker(sentinel.socket)
        result = self.process.stdin.getvalue()
        expected = fake_io.read_file('stdin.txt')
        self.assertEqual(result, expected)

    def test_stdout_copied_to_client(self):
        """
        remote stdout should be copied to client stdout
        """

        server = ServerWorker(sentinel.socket)
        result = self.client.stdout.getvalue()
        expected = fake_io.read_file('stdout.txt')
        self.assertEqual(result, expected)

    def test_stderr_copied_to_client(self):
        """
        remote stderr should be copied to client stderr
        """

        server = ServerWorker(sentinel.socket)
        result = self.client.stderr.getvalue()
        expected = fake_io.read_file('stderr.txt')
        self.assertEqual(result, expected)

