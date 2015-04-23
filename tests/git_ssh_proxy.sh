#!/bin/sh
# exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no git@localhost -p4000 "$2"
# exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o ProxyCommand="ssh -p4000 localhost \"python bin/ssh-forward-proxy.py %h %p %r $PROXY_ARGS \"" "$@"
exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o "ProxyCommand=$PROXY_CMD" "$@"