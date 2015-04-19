import logging
import argparse

logging.basicConfig(level=logging.INFO)

import ssh_forward_proxy

if __name__ == '__main__':
    SSH_PORT = 22
    parser = argparse.ArgumentParser(description='Forward all SSH requests to remote but authenticating as the proxy')
    parser.add_argument('remote', help='Remote host ([USER@]HOST:[PORT]). Default port is same as port argument.')
    parser.add_argument('port', nargs='?', default=SSH_PORT, type=int, help='Port (default {})'.format(SSH_PORT))
    parser.add_argument('host', nargs='?', default='', help='Bind host')
    parser.add_argument('-i', dest='identity_file', help='Path to identity file (same as ssh -i)')

    args = parser.parse_args()
    args.username, args.remote, args.remote_port = ssh_forward_proxy.parse_host_string(args.remote)
    args.remote_port = (args.remote_port or args.port)

    ssh_forward_proxy.run_server(args.host, args.port, args)
