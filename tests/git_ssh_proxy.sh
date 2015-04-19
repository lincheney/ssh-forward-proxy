#!/bin/sh
exec ssh -o PubkeyAuthentication=no git@localhost -p4000 "$2"
exec ssh -o PubkeyAuthentication=no "$@"