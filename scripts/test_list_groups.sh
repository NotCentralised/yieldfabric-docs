#!/bin/bash

# Test script for the new list_groups command
# This script tests the list_groups functionality

echo "🧪 Testing list_groups command implementation"
echo "============================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the execute_commands script
source "$SCRIPT_DIR/execute_commands.sh"

echo "📋 Testing with user_functions.yaml..."
echo ""

# Run the execute_commands script with user_functions.yaml
cd "$SCRIPT_DIR"
./execute_commands.sh user_functions.yaml execute

echo ""
echo "✅ Test completed!"
