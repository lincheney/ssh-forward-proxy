SSH_PORT = 22

#   splits the string @host into into its components
#   given it's in the format user@host:port (where user and port components are optional)
#   port is converted to an integer or None
def parse_host_string(host):
    user, _, host = host.rpartition('@')
    host2, _, port = host.partition(':')
    if port.isdigit():
        port = int(port)
        host = host2
    else:
        port = SSH_PORT
    return (user or None), host, port
