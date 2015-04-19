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
    username, remote_host, remote_port = ssh_forward_proxy.parse_host_string(args.remote)

    ssh_forward_proxy.run_server(
        args.host, args.port,
        remote_host=remote_host,
        remote_port=(remote_port or args.port),
        username=username,
        key_filename=args.identity_file,
    )
