#!/bin/sh
exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o ProxyCommand="ssh -o StrictHostKeyChecking=no -p4000 localhost $PROXY_CMD" "$@"