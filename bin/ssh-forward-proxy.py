import logging
import argparse

logging.basicConfig(level=logging.INFO)

import ssh_forward_proxy

if __name__ == '__main__':
    SSH_PORT = 22
    parser = argparse.ArgumentParser(description='Forward all SSH requests to remote but authenticating as the proxy')
    parser.add_argument('host', help='Remote host')
    parser.add_argument('port', type=int, help='Remote port')
    parser.add_argument('user', help='Username')
    parser.add_argument('-i', dest='identity_file', help='Path to identity file (same as ssh -i)')

    args = parser.parse_args()

    ssh_forward_proxy.Proxy(
        remote_host=args.host,
        remote_port=args.port,
        username=args.user,
        key_filename=args.identity_file,
    )
