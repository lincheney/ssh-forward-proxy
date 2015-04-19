#!/bin/sh
exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no "$@"