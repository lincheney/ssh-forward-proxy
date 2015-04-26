import logging
import argparse

logging.basicConfig(level=logging.INFO)

import ssh_forward_proxy as ssh

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Forward all SSH requests to remote but authenticating as the proxy')
    parser.add_argument('-i', dest='identity_file',
                        help='Path to identity file (same as ssh -i)')
    parser.add_argument('--no-host-key-check', action='store_true', default=False,
                        help="Same as StrictHostKeyCheck=no option for SSH")
    parser.add_argument('--server-key',
                        help='Host key for the server')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    sub = subparsers.add_parser('relay', help='Proxy SSH traffic on STDIN to the remote')
    sub.add_argument('port', type=int, help='Remote port')
    sub.add_argument('host', help='Remote host')
    sub.add_argument('user', help='Username')

    sub = subparsers.add_parser('server', help='Run a standalone SSH server that forwards traffic to the remote')
    sub.add_argument('port', nargs='?', default=ssh.SSH_PORT, type=int,
                     help='Port to run server on (default: {})'.format(ssh.SSH_PORT))
    sub.add_argument('host', nargs='?', default='',
                     help='Host to bind server to')

    args = parser.parse_args()

    kwargs = dict(
        key_filename = args.identity_file,
        host_key_check = not args.no_host_key_check,
        server_key = args.server_key,
    )
    if args.command == 'relay':
        # no logging in relay since stderr is piped to SSH client
        logging.disable(level=logging.CRITICAL)
        ssh.Proxy(username=args.user, host=args.host, port=args.port, **kwargs)
    elif args.command == 'server':
        ssh.run_server(args.host, args.port, worker=ssh.ProxyServer, **kwargs)
