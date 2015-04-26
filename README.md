# ssh-forward-proxy

[![Build Status](https://travis-ci.org/lincheney/ssh-forward-proxy.svg?branch=master)](https://travis-ci.org/lincheney/ssh-forward-proxy)
[![Code Climate](https://codeclimate.com/github/lincheney/ssh-forward-proxy/badges/gpa.svg)](https://codeclimate.com/github/lincheney/ssh-forward-proxy)
[![Coverage Status](https://coveralls.io/repos/lincheney/ssh-forward-proxy/badge.svg?branch=master)](https://coveralls.io/r/lincheney/ssh-forward-proxy?branch=master)

SSH proxy server to allow clients access to a SSH remote by authenticating as the proxy, instead of the client.

## Usage

The proxy is provided in the script in `bin/ssh-forward-proxy.py`. Note that this package must be installed on an intermediate/proxy machine (rather than your local machine). You can use the proxy in two ways: as a standalone SSH server; or as a `netcat` alternative in the `ProxyCommand` option (relay).

### Relay

```
python ssh-forward-proxy.py [-i IDENTITY_FILE] [--no-host-key-check] [--server-key KEY] relay PORT HOST USER
```

If you use the proxy as a relay, you must also have an SSH server. A very basic (and insecure) SSH server is provided in `bin/simply-ssh-server.py` but it is recommended you provide your own (e.g. OpenSSH).

Using the relay is easy. Instead of doing:

`ssh -p1234 user@remote.host command ...`

do:

```
PROXY_CMD="ssh proxy.host python /path/to/ssh-forward-proxy.py relay %p %h %r"
ssh -o StrictHostKeyChecking=no -o ProxyCommand="$PROXY_CMD" -p1234 user@remote.host command ...
```

assuming that the proxy server is `proxy.host`. 

### Standalone server

```
python ssh-forward-proxy.py [-i IDENTITY_FILE] [--no-host-key-check] [--server-key KEY] server [PORT|22 [HOST]]
```

The standalone proxy server has *no* security. It allows *all* connections without authentication. Make sure you set up your firewall appropriately.

First, run the proxy on the intermediate/proxy server (say, on port 4000):

`python /path/to/ssh-forward-proxy.py server 4000`

The proxy figures out which host to forward to through the `__HOST__` environment variable:

```
export __HOST__=user@remote.host:1234
ssh -o StrictHostKeyChecking=no -o SendEnv=__HOST__ -p4000 proxy.host command ...
```

### Additional notes

In both methods above, the given `ssh` command will authenticate to `user@remote.host:1234` using SSH keys or forwarded SSH agents on the intermediate/proxy server.

The `StrictHostKeyChecking=no` is necessary since the host key you receive will actually be provided by the proxy server and not `remote.host`. (An alternative is to set up a secondary `known_hosts` file for proxied SSH connections).

#### Host key

The proxy server will use a default host key provided in this python package. You can specify an alternative with the `--server-key` option.

#### Identity file

The `-i` option can be used to specify a public SSH key that the proxy will use to authenticate with the remote. It is *not* used to authenticate clients.


## Using with Docker

`ssh-forward-proxy` was made with the sole purpose of facilitating `git clone`-ing of private git repositories during `docker build` *without* pre-cloning the repositories or adding SSH keys into docker images.

You can pull a pre-built docker image with `docker pull lincheney/ssh-forward-proxy`.

### Procedure

We will assume that for a typical build process, we do:

1. `ssh` from your local machine to a server (with the `-A` option for agent forwarding).
2. Run `docker build`, including:
  1. `COPY` a private SSH key into the image.
  2. Install software, possibly from private git repositories.

Copying a private SSH key into the image is less than ideal since that key is now permanently embedded in the image. Even if you later `rm` the key, it will still exist in the lower layers. An ideal situtation would be to use the the forwarded SSH agent from step 1.

With `ssh-forward-proxy`, we can instead do this:

1. `ssh` from your local machine to a server (with the `-A` option for agent forwarding).
2. Launch the proxy:
  
  ```bash
  docker run -d -v "$SSH_AUTH_SOCK:/tmp/ssh.sock" -e SSH_AUTH_SOCK=/tmp/ssh.sock --name ssh-proxy -p 127.0.0.1:4000:4000 lincheney/ssh-forward-proxy server 4000
  ```
  
3. Run `docker build`, which now does:
  1. `COPY git-ssh.sh /` The `git_ssh.sh` file is a script containing:
    
    ```bash
    #!/bin/sh
    export __HOST__="$1"
    ssh -o SendEnv=__HOST__ -o StrictHostKeyChecking=no -p4000 proxy.host "$2"
    ```
    
  2. `ENV GIT_SSH /git_ssh.sh`
  3. Install software.
4. Remove the proxy container, `docker rm -f ssh-proxy`

No private SSH key will appear in the resulting image.

In this case, the standalone server was used and the `-p 127.0.0.1:4000:4000` option ensures that the proxy is only accessible on the server (and not externally, since it has no security). We can use the `relay` instead; the process is largely the same but the `git_ssh.sh` will be different.

You should replace `proxy.host` (in the `git_ssh.sh` script) with an appropriate hostname/IP address. You *cannot* use `127.0.0.1` because that will refer to the building container rather than the proxy.
