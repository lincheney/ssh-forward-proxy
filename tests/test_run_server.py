import unittest
from unittest import mock
from unittest.mock import patch, sentinel

from bin.ssh_forward_proxy import run_server, Proxy

class RunServerTest(unittest.TestCase):

    class Error(Exception):
        pass

    def setUp(self):
        self.sys_exit_patch = patch('sys.exit')
        self.sys_exit_patch.start()
    def tearDown(self):
        self.sys_exit_patch.stop()

    @patch('socket.socket.bind')
    def test_bind(self, bind):
        """
        the server should bind to the correct host and port
        """

        # raise an error to stop the server going into the accept loop
        with patch('socket.socket.accept', side_effect=self.Error() ):
            try:
                run_server('host', 1234, None)
            except self.Error:
                pass
            bind.assert_called_once_with(('host', 1234))

    @patch('socket.socket.bind')
    @patch('socket.socket.accept', return_value=(sentinel.socket, sentinel.address))
    def test_proxy_thread(self, accept, bind):
        """
        the server should start a thread for the proxy on accept()
        """

        thread = mock.Mock()
        # raise an error to stop the server going into the accept loop
        with patch('threading.Thread', return_value=thread) as Thread:
            thread.start = mock.Mock(side_effect=self.Error() )
            try:
                run_server('host', 1234, sentinel.args)
            except self.Error:
                pass
            Thread.assert_called_once_with(target=Proxy, args=(sentinel.socket, sentinel.args))
            thread.start.assert_called_once()
