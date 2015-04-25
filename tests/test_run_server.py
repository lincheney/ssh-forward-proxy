import unittest
try:
    from unittest import mock
except ImportError:
    import mock
patch = mock.patch
sentinel = mock.sentinel

import os
import signal

from ssh_forward_proxy import run_server

class RunServerTest(unittest.TestCase):

    class Error(Exception):
        pass

    @patch('socket.socket.bind')
    def test_bind(self, bind):
        """
        the server should bind to the correct host and port
        """

        # raise an error to stop the server going into the accept loop
        with patch('socket.socket.accept', side_effect=self.Error):
            try:
                run_server('host', 1234)
            except self.Error:
                pass
            bind.assert_called_once_with(('host', 1234))

    @patch('socket.socket.bind')
    @patch('socket.socket.accept', return_value=(sentinel.socket, sentinel.address))
    @patch('threading.Thread')
    def test_server_thread(self, Thread, accept, bind):
        """
        the server should start a thread for the proxy on accept()
        """

        # raise an error to stop the server going into the accept loop
        thread = Thread.return_value
        thread.start = mock.Mock(side_effect=self.Error)

        try:
            run_server('host', 1234, key='value', worker=sentinel.worker)
        except self.Error:
            pass
        Thread.assert_called_once_with(target=sentinel.worker, args=(sentinel.socket,), kwargs={'key': 'value'})
        thread.start.assert_called_once_with()

    @patch('socket.socket.close')
    @patch('socket.socket.bind')
    def test_keyboard_interrupt(self, bind, close):
        """
        the server should start a thread for the proxy on accept()
        """

        with patch('socket.socket.accept', side_effect=self.send_sig_int):
            run_server('host', 1234, key='value', worker=sentinel.worker)
            close.assert_called_once_with()

    def send_sig_int(self):
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

    @patch('socket.socket.close')
    @patch('socket.socket.bind')
    def test_error(self, bind, close):
        """
        the server should start a thread for the proxy on accept()
        """

        with patch('socket.socket.accept', side_effect=self.Error):
            with self.assertRaises(self.Error):
                run_server('host', 1234, key='value', worker=sentinel.worker)
            close.assert_called_once_with()
