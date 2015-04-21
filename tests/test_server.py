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

from ssh_forward_proxy import run_server, ServerWorker

class ServerTest(unittest.TestCase):

    ROOT_DIR = os.path.abspath(os.path.join(__file__, '..', '..'))

    def test_server(self):
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
