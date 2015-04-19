"""
Tests for ssh_forward_proxy.parse_host_string

No user or port
    >>> parse_host_string('host')
    (None, 'host', None)

With a user
    >>> parse_host_string('user@host')
    ('user', 'host', None)
    >>> parse_host_string('@host')
    (None, 'host', None)

With a port
    >>> parse_host_string('host:1234')
    (None, 'host', 1234)

With an invalid port
    >>> parse_host_string('host:')
    (None, 'host:', None)
    >>> parse_host_string('host:abcd')
    (None, 'host:abcd', None)

With both user and port
    >>> parse_host_string('user@host:1234')
    ('user', 'host', 1234)
"""

from ssh_forward_proxy import parse_host_string