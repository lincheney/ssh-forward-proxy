#!/bin/sh
__HOST__="$1" ssh -o SendEnv=__HOST__ -o StrictHostKeyChecking=no -o PubkeyAuthentication=no localhost -p4000 "$2"