#!/bin/sh
exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o ProxyCommand="ssh -o StrictHostKeyChecking=no -p $PORT localhost $PROXY_CMD" "$@"