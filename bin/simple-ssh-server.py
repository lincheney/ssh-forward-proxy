import logging
import argparse

logging.basicConfig(level=logging.INFO)

import ssh_forward_proxy

if __name__ == '__main__':
    SSH_PORT = 22
    parser = argparse.ArgumentParser(description='Launch a really simple SSH server')
    parser.add_argument('port', nargs='?', default=SSH_PORT, type=int, help='Port (default {})'.format(SSH_PORT))
    parser.add_argument('host', nargs='?', default='', help='Host')
    args = parser.parse_args()

    ssh_forward_proxy.run_server(args.host, args.port)
