#!/bin/bash

# Simple alias for the main authentication manager
# This makes it even easier for users to access authentication

exec "$(dirname "$0")/yieldfabric-auth.sh" "$@"
