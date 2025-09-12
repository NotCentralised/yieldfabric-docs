#!/bin/bash

# YieldFabric Authentication Module
# Contains functions for user authentication and group delegation

# Helper function to get group ID by name from auth service
get_group_id_by_name() {
    local token="$1"
    local group_name="$2"
    
    echo_with_color $BLUE "  🔍 Looking up group ID for: $group_name" >&2
    
    local groups_json=$(curl -s -X GET "http://localhost:3000/auth/groups" \
        -H "Authorization: Bearer $token")
    
    if [[ -n "$groups_json" ]]; then
        local group_id=$(echo "$groups_json" | jq -r ".[] | select(.name == \"$group_name\") | .id" 2>/dev/null)
        if [[ -n "$group_id" && "$group_id" != "null" ]]; then
            echo_with_color $GREEN "    ✅ Found group ID: ${group_id:0:8}..." >&2
            echo "$group_id"
            return 0
        else
            echo_with_color $RED "    ❌ Group not found: $group_name" >&2
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Failed to retrieve groups list" >&2
        return 1
    fi
}

# Helper function to create delegation JWT token for a specific group
create_delegation_token() {
    local user_token="$1"
    local group_id="$2"
    local group_name="$3"
    
    echo_with_color $BLUE "  🎫 Creating delegation JWT for group: $group_name" >&2
    echo_with_color $BLUE "    Group ID: ${group_id:0:8}..." >&2
    
    # Create delegation JWT with comprehensive scope for payments operations
    local delegation_response=$(curl -s -X POST "http://localhost:3000/auth/delegation/jwt" \
        -H "Authorization: Bearer $user_token" \
        -H "Content-Type: application/json" \
        -d "{\"group_id\": \"$group_id\", \"delegation_scope\": [\"CryptoOperations\", \"ReadGroup\", \"UpdateGroup\", \"ManageGroupMembers\"], \"expiry_seconds\": 3600}")
    
    echo_with_color $BLUE "    Delegation response: $delegation_response" >&2
    
    local delegation_token=$(echo "$delegation_response" | jq -r '.delegation_jwt // .token // .delegation_token // .jwt // empty' 2>/dev/null)
    
    if [[ -n "$delegation_token" && "$delegation_token" != "null" ]]; then
        echo_with_color $GREEN "    ✅ Delegation JWT created successfully" >&2
        echo "$delegation_token"
        return 0
    else
        echo_with_color $RED "    ❌ Failed to create delegation JWT" >&2
        echo_with_color $YELLOW "    Response: $delegation_response" >&2
        return 1
    fi
}

# Function to login user and get JWT token (with optional group delegation)
login_user() {
    local email="$1"
    local password="$2"
    local group_name="$3"  # Optional group name for delegation
    local services_json='["vault", "payments"]'

    echo_with_color $BLUE "  🔐 Logging in user: $email" >&2
    
    local http_response=$(curl -s -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\", \"password\": \"$password\", \"services\": $services_json}")

    echo_with_color $BLUE "    📡 Login response: $http_response" >&2
    
    if [[ -n "$http_response" ]]; then
        local token=$(echo "$http_response" | jq -r '.token // .access_token // .jwt // empty')
        if [[ -n "$token" && "$token" != "null" ]]; then
            echo_with_color $GREEN "    ✅ Login successful" >&2
            
            # If group name is specified, create delegation token
            if [[ -n "$group_name" && "$group_name" != "null" ]]; then
                echo_with_color $CYAN "  🏢 Group delegation requested for: $group_name" >&2
                
                # Get group ID by name
                local group_id=$(get_group_id_by_name "$token" "$group_name")
                if [[ $? -eq 0 && -n "$group_id" ]]; then
                    # Create delegation token
                    local delegation_token=$(create_delegation_token "$token" "$group_id" "$group_name")
                    if [[ $? -eq 0 && -n "$delegation_token" ]]; then
                        echo_with_color $GREEN "    ✅ Group delegation successful" >&2
                        echo "$delegation_token"
                        return 0
                    else
                        echo_with_color $YELLOW "    ⚠️  Delegation failed, using regular token" >&2
                        echo "$token"
                        return 0
                    fi
                else
                    echo_with_color $YELLOW "    ⚠️  Group not found, using regular token" >&2
                    echo "$token"
                    return 0
                fi
            else
                echo "$token"
                return 0
            fi
        else
            echo_with_color $RED "    ❌ No token in response" >&2
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Login failed: no response" >&2
        return 1
    fi
}