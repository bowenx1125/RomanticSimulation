#!/bin/sh
set -eu

docker compose -p love-simulator down "$@"

