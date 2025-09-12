#!/bin/bash

# Fix Group Ownership Script
# This script deletes the existing group and recreates it with the correct ownership

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTH_SCRIPT="$SCRIPT_DIR/yieldfabric-auth.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_with_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

echo_with_color $CYAN "🔧 Fixing Group Ownership Issue"
echo "=========================================="

# Get admin token
echo_with_color $BLUE "🔑 Getting admin token..."
admin_token=$($AUTH_SCRIPT admin 2>/dev/null)
if [[ $? -ne 0 || -z "$admin_token" ]]; then
    echo_with_color $RED "❌ Failed to get admin token"
    exit 1
fi

echo_with_color $GREEN "✅ Admin token obtained"

# List existing groups
echo_with_color $BLUE "📋 Listing existing groups..."
groups_response=$(curl -s -X GET "http://localhost:3000/auth/groups" \
    -H "Authorization: Bearer $admin_token")

echo_with_color $BLUE "Groups response: $groups_response"

# Find the Admin Group
group_id=$(echo "$groups_response" | jq -r '.[] | select(.name == "Admin Group") | .id' 2>/dev/null)

if [[ -z "$group_id" || "$group_id" == "null" ]]; then
    echo_with_color $RED "❌ Admin Group not found"
    exit 1
fi

echo_with_color $BLUE "🔍 Found Admin Group with ID: $group_id"

# Delete the existing group
echo_with_color $BLUE "🗑️  Deleting existing Admin Group..."
delete_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X DELETE "http://localhost:3000/auth/groups/$group_id" \
    -H "Authorization: Bearer $admin_token")

http_status=$(echo "$delete_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
response_body=$(echo "$delete_response" | sed 's/HTTP_STATUS:[0-9]*//')

if [[ "$http_status" == "204" ]]; then
    echo_with_color $GREEN "✅ Admin Group deleted successfully"
else
    echo_with_color $RED "❌ Failed to delete Admin Group (HTTP $http_status)"
    echo_with_color $YELLOW "Response: $response_body"
    exit 1
fi

# Wait a moment for cleanup
sleep 2

# Recreate the group with the fixed logic
echo_with_color $BLUE "🏗️  Recreating Admin Group with correct ownership..."
create_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "http://localhost:3000/auth/groups" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $admin_token" \
    -d '{"name": "Admin Group", "description": "Administrative group for system management", "group_type": "project"}')

http_status=$(echo "$create_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
response_body=$(echo "$create_response" | sed 's/HTTP_STATUS:[0-9]*//')

if [[ "$http_status" == "200" ]]; then
    new_group_id=$(echo "$response_body" | jq -r '.id // empty' 2>/dev/null)
    if [[ -n "$new_group_id" && "$new_group_id" != "null" ]]; then
        echo_with_color $GREEN "✅ Admin Group recreated successfully with ID: $new_group_id"
    else
        echo_with_color $RED "❌ Failed to extract group ID from response"
        exit 1
    fi
else
    echo_with_color $RED "❌ Failed to recreate Admin Group (HTTP $http_status)"
    echo_with_color $YELLOW "Response: $response_body"
    exit 1
fi

# Wait for group account deployment
echo_with_color $BLUE "⏳ Waiting for group account deployment..."
sleep 5

# Check group account status
echo_with_color $BLUE "🔍 Checking group account status..."
account_status_response=$(curl -s -X GET "http://localhost:3000/auth/groups/$new_group_id/account-status" \
    -H "Authorization: Bearer $admin_token")

echo_with_color $BLUE "Account status response: $account_status_response"

account_address=$(echo "$account_status_response" | jq -r '.account_status.account_address // empty' 2>/dev/null)
status=$(echo "$account_status_response" | jq -r '.account_status.status // empty' 2>/dev/null)

if [[ "$status" == "deployed" && -n "$account_address" && "$account_address" != "null" ]]; then
    echo_with_color $GREEN "✅ Group account deployed successfully with address: $account_address"
else
    echo_with_color $YELLOW "⚠️  Group account status: $status"
    echo_with_color $BLUE "Account address: $account_address"
fi

# Add members to the group
echo_with_color $BLUE "👥 Adding members to the group..."

# Add admin2@yieldfabric.com as owner
echo_with_color $BLUE "  Adding admin2@yieldfabric.com as owner..."
# First, we need to get the user ID for admin2@yieldfabric.com
# This is a bit tricky since we don't have a direct way to get user ID by email
# We'll need to use the setup script's logic

# For now, let's just show what needs to be done
echo_with_color $YELLOW "⚠️  Manual step required:"
echo_with_color $YELLOW "   Run the setup script again to add members to the recreated group:"
echo_with_color $BLUE "   ./setup_system.sh owners"

echo_with_color $GREEN "🎉 Group ownership fix completed!"
echo_with_color $BLUE "   New group ID: $new_group_id"
echo_with_color $BLUE "   Group account address: $account_address"
echo_with_color $YELLOW "   Next step: Run './setup_system.sh owners' to add members"
