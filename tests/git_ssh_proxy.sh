#!/bin/sh
exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no git@localhost -p4000 "$2"