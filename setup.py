from setuptools import setup

tests_require = []
try:
    import unittest.mock
except ImportError:
    tests_require = ['mock']

setup(
    name = 'ssh-forward-proxy',
    version = '0.1',
    description = 'SSH proxy server to allow clients access to a SSH remote using the credentials of the proxy, instead of the client.',
    url = 'https://github.com/lincheney/ssh-forward-proxy',
    author = 'Cheney Lin',
    author_email = 'lincheney@gmail.com',
    #packages = ['ssh_forward_proxy'],
    scripts = ['bin/ssh_forward_proxy.py'],
    install_requires = ['paramiko'],

    tests_require = tests_require,
    test_suite="tests",
)
