#!/bin/sh
exec ssh -o PreferredAuthentications=keyboard-interactive,password -o PubkeyAuthentication=no "$@"