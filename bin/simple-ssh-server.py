import logging
import argparse

logging.basicConfig(level=logging.INFO)

import ssh_forward_proxy as ssh

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch a really simple SSH server')
    parser.add_argument('port', nargs='?', default=ssh.SSH_PORT, type=int, help='Port (default {})'.format(ssh.SSH_PORT))
    parser.add_argument('host', nargs='?', default='', help='Host')
    parser.add_argument('--server-key', help='Host key for the server')

    args = parser.parse_args()

    ssh.run_server(args.host, args.port, worker=ssh.Server, server_key=args.server_key)
