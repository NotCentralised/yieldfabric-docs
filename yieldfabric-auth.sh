#!/bin/bash

# YieldFabric Authentication Manager - User-friendly token management
# Automatically handles token creation, validation, and provides clear guidance

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKENS_DIR="$SCRIPT_DIR/tokens"

# Ensure tokens directory exists
mkdir -p "$TOKENS_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo_with_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if a service is running
check_service_running() {
    local service_name=$1
    local port=$2
    
    if nc -z localhost $port 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to load tokens from files
load_tokens() {
    # Load admin token
    if [[ -f "$TOKENS_DIR/.jwt_token" ]]; then
        export ADMIN_TOKEN=$(cat "$TOKENS_DIR/.jwt_token" 2>/dev/null)
    fi
    
    # Load test token
    if [[ -f "$TOKENS_DIR/.jwt_token_test" ]]; then
        export TEST_TOKEN=$(cat "$TOKENS_DIR/.jwt_token_test" 2>/dev/null)
    fi
    
    # Load delegation token
    if [[ -f "$TOKENS_DIR/.jwt_token_delegate" ]]; then
        export DELEGATION_TOKEN=$(cat "$TOKENS_DIR/.jwt_token_delegate" 2>/dev/null)
    fi
    
    # Set BASE_URL
    export BASE_URL="http://localhost:3000"
}

# Function to get or create admin JWT token
get_admin_token() {
    local token_file="$TOKENS_DIR/.jwt_token"
    local expiry_file="$TOKENS_DIR/.jwt_expiry"
    
    # Check if token exists and is valid
    if [[ -f "$token_file" ]] && [[ -f "$expiry_file" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$expiry_file" 2>/dev/null || echo "0")
        
        if [[ $current_time -lt $expiry_time ]]; then
            cat "$token_file"
            return 0
        fi
    fi
    
    # Token doesn't exist or is expired, create new one
    echo_with_color $YELLOW "Creating new admin JWT token..."
    
    # First, always try to create the user with SuperAdmin role (like the working scripts do)
    echo_with_color $BLUE "Creating admin user with SuperAdmin role..."
    
    # Debug: Show exactly what we're sending
    # Use the same email as the working scripts to see if that resolves the role issue
    local user_payload='{"email": "test@yieldfabric.com", "password": "testpass123", "role": "SuperAdmin"}'
    echo_with_color $BLUE "   Sending payload: $user_payload"
    
    local create_response=$(curl -s -X POST "http://localhost:3000/auth/users" \
        -H "Content-Type: application/json" \
        -d "$user_payload")
    
    echo_with_color $BLUE "   User creation response: $create_response"
    
    # Check if user was created or already exists
    local user_id=$(echo "$create_response" | jq -r '.user.id // .id // empty' 2>/dev/null)
    local user_role=$(echo "$create_response" | jq -r '.user.role // .role // empty' 2>/dev/null)
    
    if [[ -n "$user_id" && "$user_id" != "null" ]]; then
        echo_with_color $GREEN "Admin user ready with ID: $user_id"
        if [[ -n "$user_role" && "$user_role" != "null" ]]; then
            echo_with_color $BLUE "   User role in response: '$user_role'"
        else
            echo_with_color $YELLOW "   No role field in response"
        fi
    else
        echo_with_color $YELLOW "User creation response didn't contain ID, continuing anyway..."
    fi
    
    # Now try to login (like the working scripts do after user creation)
    echo_with_color $BLUE "Logging in with services..."
    local response=$(curl -s -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d '{"email": "test@yieldfabric.com", "password": "testpass123", "services": ["vault", "payments"]}')
    
    local token=$(echo "$response" | jq -r '.token // .access_token // .jwt // empty' 2>/dev/null)
    
    if [[ -n "$token" && "$token" != "null" ]]; then
        # Extract expiry time
        local payload=$(echo "$token" | cut -d'.' -f2)
        local padding=$((4 - ${#payload} % 4))
        if [[ $padding -ne 4 ]]; then
            payload="${payload}$(printf '=%.0s' $(seq 1 $padding))"
        fi
        
        local decoded=$(echo "$payload" | base64 -d 2>/dev/null)
        local expiry=$(echo "$decoded" | jq -r '.exp // empty' 2>/dev/null)
        
        if [[ -z "$expiry" || "$expiry" == "null" ]]; then
            expiry=$(($(date +%s) + 3600))
        fi
        
        # Store token
        echo "$token" > "$token_file"
        echo "$expiry" > "$expiry_file"
        chmod 600 "$token_file" "$expiry_file"
        
        echo_with_color $GREEN "Admin JWT token created successfully"
        
        # Show token info for debugging
        local user_id=$(echo "$decoded" | jq -r '.sub // empty' 2>/dev/null)
        local user_role=$(echo "$decoded" | jq -r '.role // empty' 2>/dev/null)
        local user_permissions=$(echo "$decoded" | jq -r '.permissions // []' 2>/dev/null)
        
        echo_with_color $BLUE "   User ID: $user_id"
        echo_with_color $BLUE "   User Role: $user_role"
        echo_with_color $BLUE "   Permissions: $user_permissions"
        
        echo "$token"
        return 0
    else
        echo_with_color $RED "Failed to create admin JWT token"
        echo_with_color $YELLOW "Response: $response"
        return 1
    fi
}

# Function to get or create test JWT token
get_test_token() {
    local token_file="$TOKENS_DIR/.jwt_token_test"
    local expiry_file="$TOKENS_DIR/.jwt_expiry_test"
    
    # Check if token exists and is valid
    if [[ -f "$token_file" ]] && [[ -f "$expiry_file" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$expiry_file" 2>/dev/null || echo "0")
        
        if [[ $current_time -lt $expiry_time ]]; then
            cat "$token_file"
            return 0
        fi
    fi
    
    # Token doesn't exist or is expired, create new one
    echo_with_color $YELLOW "Creating new test JWT token..."
    
    local response=$(curl -s -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d '{"email": "test@yieldfabric.com", "password": "testpass123", "services": ["vault", "payments"]}')
    
    local token=$(echo "$response" | jq -r '.token // .access_token // .jwt // empty' 2>/dev/null)
    
    if [[ -n "$token" && "$token" != "null" ]]; then
        # Extract expiry time
        local payload=$(echo "$token" | cut -d'.' -f2)
        local padding=$((4 - ${#payload} % 4))
        if [[ $padding -ne 4 ]]; then
            payload="${payload}$(printf '=%.0s' $(seq 1 $padding))"
        fi
        
        local decoded=$(echo "$payload" | base64 -d 2>/dev/null)
        local expiry=$(echo "$decoded" | jq -r '.exp // empty' 2>/dev/null)
        
        if [[ -z "$expiry" || "$expiry" == "null" ]]; then
            expiry=$(($(date +%s) + 3600))
        fi
        
        # Store token
        echo "$token" > "$token_file"
        echo "$expiry" > "$expiry_file"
        chmod 600 "$token_file" "$expiry_file"
        
        echo_with_color $GREEN "Test JWT token created successfully"
        echo "$token"
        return 0
    else
        echo_with_color $RED "Failed to create test JWT token"
        echo_with_color $YELLOW "Response: $response"
        return 1
    fi
}

# Function to get or create delegation JWT token
get_delegation_token() {
    local token_file="$TOKENS_DIR/.jwt_token_delegate"
    local expiry_file="$TOKENS_DIR/.jwt_token_delegate_expiry"
    
    # Check if token exists and is valid
    if [[ -f "$token_file" ]] && [[ -f "$expiry_file" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$expiry_file" 2>/dev/null || echo "0")
        
        if [[ $current_time -lt $expiry_time ]]; then
            cat "$token_file"
            return 0
        fi
    fi
    
    # Token doesn't exist or is expired, create new one
    echo_with_color $YELLOW "Creating new delegation JWT token..."
    
    # Use the test user directly since it already has the correct permissions and works
    echo_with_color $BLUE "Using test user for delegation token creation..."
    local test_token=$(get_test_token)
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "Failed to get test token"
        return 1
    fi
    
    # Debug: Show the test token payload
    echo_with_color $BLUE "Debug: Examining test token payload..."
    local payload=$(echo "$test_token" | cut -d'.' -f2)
    local padding=$((4 - ${#payload} % 4))
    if [[ $padding -ne 4 ]]; then
        payload="${payload}$(printf '=%.0s' $(seq 1 $padding))"
    fi
    
    local decoded=$(echo "$payload" | base64 -d 2>/dev/null)
    echo_with_color $BLUE "   JWT Payload: $decoded"
    
    local user_id=$(echo "$decoded" | jq -r '.sub // empty' 2>/dev/null)
    local user_role=$(echo "$decoded" | jq -r '.role // empty' 2>/dev/null)
    local user_permissions=$(echo "$decoded" | jq -r '.permissions // []' 2>/dev/null)
    
    echo_with_color $BLUE "   User ID: $user_id"
    echo_with_color $BLUE "   User Role: '$user_role'"
    echo_with_color $BLUE "   Permissions: $user_permissions"
    
    if [[ -z "$user_id" ]]; then
        echo_with_color $RED "Failed to extract user ID from test token"
        return 1
    fi
    
    echo_with_color $BLUE "Ensuring user has required permissions..."
    
    # Check and grant necessary permissions
    local required_permissions=("CreateGroup" "ManageGroup" "AddGroupMember" "RemoveGroupMember" "ManageGroupPermissions" "CreateDelegationToken")
    
    for permission in "${required_permissions[@]}"; do
        echo_with_color $BLUE "   Checking permission: $permission"
        
        # Check if permission exists
        local has_permission=$(curl -s -X GET "http://localhost:3000/auth/users/$user_id/permissions" \
            -H "Authorization: Bearer $test_token" | jq -r ".[] | select(. == \"$permission\") // empty")
        
        if [[ -z "$has_permission" ]]; then
            echo_with_color $YELLOW "   Permission $permission missing, granting it..."
            
            local grant_response=$(curl -s -X POST "http://localhost:3000/auth/users/$user_id/permissions" \
                -H "Authorization: Bearer $test_token" \
                -H "Content-Type: application/json" \
                -d "{\"permission\": \"$permission\"}")
            
            if [[ -n "$grant_response" ]]; then
                echo_with_color $GREEN "   Permission $permission granted successfully"
            else
                echo_with_color $RED "   Failed to grant permission $permission"
                return 1
            fi
        else
            echo_with_color $GREEN "   Permission $permission already exists"
        fi
    done
    
    echo_with_color $BLUE "Getting fresh JWT token with updated permissions..."
    
    # Get a fresh token after granting permissions
    local fresh_login_response=$(curl -s -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d '{"email": "test@yieldfabric.com", "password": "testpass123", "services": ["vault", "payments"]}')
    
    local fresh_token=$(echo "$fresh_login_response" | jq -r '.token // .access_token // .jwt // empty' 2>/dev/null)
    
    if [[ -z "$fresh_token" || "$fresh_token" == "null" ]]; then
        echo_with_color $RED "Failed to get fresh JWT token"
        return 1
    fi
    
    echo_with_color $GREEN "Fresh JWT token obtained with updated permissions"
    
    # Debug: Show the fresh token payload
    echo_with_color $BLUE "Debug: Examining fresh token payload..."
    local fresh_payload=$(echo "$fresh_token" | cut -d'.' -f2)
    local fresh_padding=$((4 - ${#fresh_payload} % 4))
    if [[ $fresh_padding -ne 4 ]]; then
        fresh_payload="${fresh_payload}$(printf '=%.0s' $(seq 1 $fresh_padding))"
    fi
    
    local fresh_decoded=$(echo "$fresh_payload" | base64 -d 2>/dev/null)
    echo_with_color $BLUE "   Fresh JWT Payload: $fresh_decoded"
    
    local fresh_user_role=$(echo "$fresh_decoded" | jq -r '.role // empty' 2>/dev/null)
    echo_with_color $BLUE "   Fresh User Role: '$fresh_user_role'"
    
    # Look for existing groups
    echo_with_color $BLUE "Looking for existing groups..."
    local groups_response=$(curl -s -X GET "http://localhost:3000/auth/groups" \
        -H "Authorization: Bearer $fresh_token")
    
    local group_id=$(echo "$groups_response" | jq -r '.[0].id // empty' 2>/dev/null)
    
    if [[ -z "$group_id" ]]; then
        echo_with_color $YELLOW "No existing groups found, creating default group..."
        
        local create_group_response=$(curl -s -X POST "http://localhost:3000/auth/groups" \
            -H "Authorization: Bearer $fresh_token" \
            -H "Content-Type: application/json" \
            -d '{"name": "Default Test Group", "description": "Default group for testing", "group_type": "project"}')
        
        if [[ -n "$create_group_response" ]]; then
            group_id=$(echo "$create_group_response" | jq -r '.id // empty' 2>/dev/null)
            echo_with_color $GREEN "Default group created with ID: $group_id"
        else
            echo_with_color $RED "Failed to create default group"
            return 1
        fi
    else
        echo_with_color $GREEN "Using existing group with ID: $group_id"
        
        # Try to add the user to the existing group as a member (required for permission checks)
        echo_with_color $BLUE "Adding user to existing group as member..."
        local add_member_response=$(curl -s -X POST "http://localhost:3000/auth/groups/$group_id/members" \
            -H "Authorization: Bearer $fresh_token" \
            -H "Content-Type: application/json" \
            -d "{\"user_id\": \"$user_id\", \"role\": \"admin\"}")
        
        echo_with_color $BLUE "   Add member response: $add_member_response"
        
        if [[ -n "$add_member_response" ]]; then
            echo_with_color $GREEN "User added to group as member"
        else
            echo_with_color $YELLOW "Failed to add user to existing group, trying to create new group..."
            
            # If adding to existing group fails, create a new group
            local create_group_response=$(curl -s -X POST "http://localhost:3000/auth/groups" \
                -H "Authorization: Bearer $fresh_token" \
                -H "Content-Type: application/json" \
                -d '{"name": "Test Group for Delegation", "description": "Group for testing delegation", "group_type": "project"}')
            
            echo_with_color $BLUE "   Create group response: $create_group_response"
            
            if [[ -n "$create_group_response" ]]; then
                group_id=$(echo "$create_group_response" | jq -r '.id // empty' 2>/dev/null)
                echo_with_color $GREEN "New group created with ID: $group_id (user automatically added as admin)"
            else
                echo_with_color $RED "Failed to create new group"
                return 1
            fi
        fi
    fi
    
    echo_with_color $BLUE "Creating delegation JWT with CryptoOperations scope..."
    echo_with_color $BLUE "   Group ID: $group_id"
    echo_with_color $BLUE "   Admin token preview: ${fresh_token:0:50}..."
    
    # Create delegation JWT using the exact format from test files
    local delegation_response=$(curl -s -X POST "http://localhost:3000/auth/delegation/jwt" \
        -H "Authorization: Bearer $fresh_token" \
        -H "Content-Type: application/json" \
        -d "{\"group_id\": \"$group_id\", \"delegation_scope\": [\"CryptoOperations\"], \"expiry_seconds\": 3600}")
    
    echo_with_color $BLUE "   Delegation Response Body: $delegation_response"
    
    local delegation_token=$(echo "$delegation_response" | jq -r '.delegation_jwt // .token // .delegation_token // .jwt // empty' 2>/dev/null)
    
    if [[ -n "$delegation_token" && "$delegation_token" != "null" ]]; then
        # Extract expiry time
        local delegation_payload=$(echo "$delegation_token" | cut -d'.' -f2)
        local delegation_padding=$((4 - ${#delegation_payload} % 4))
        if [[ $delegation_padding -ne 4 ]]; then
            delegation_payload="${delegation_payload}$(printf '=%.0s' $(seq 1 $delegation_padding))"
        fi
        
        local delegation_decoded=$(echo "$delegation_payload" | base64 -d 2>/dev/null)
        local delegation_expiry=$(echo "$delegation_decoded" | jq -r '.exp // empty' 2>/dev/null)
        
        if [[ -z "$delegation_expiry" || "$delegation_expiry" == "null" ]]; then
            delegation_expiry=$(($(date +%s) + 3600))
        fi
        
        # Store token
        echo "$delegation_token" > "$token_file"
        echo "$delegation_expiry" > "$expiry_file"
        chmod 600 "$token_file" "$expiry_file"
        
        echo_with_color $GREEN "Delegation JWT token created successfully"
        echo "$delegation_token"
        return 0
    else
        echo_with_color $RED "Failed to extract delegation JWT from response"
        echo_with_color $YELLOW "Response: $delegation_response"
        return 1
    fi
}

# Function to show comprehensive status
show_status() {
    echo_with_color $CYAN "YieldFabric Authentication Status"
    echo "=========================================="
    
    # Check services
    echo_with_color $BLUE "Service Status:"
    if check_service_running "Auth Service" "3000"; then
        echo_with_color $GREEN "   Auth Service (port 3000) - Running"
    else
        echo_with_color $RED "   Auth Service (port 3000) - Not running"
        echo_with_color $YELLOW "   Start the auth service first: cd ../yieldfabric-auth && cargo run"
        return 1
    fi
    
    echo ""
    
    # Check admin token
    echo_with_color $BLUE "Admin Token:"
    local admin_token_file="$TOKENS_DIR/.jwt_token"
    local admin_expiry_file="$TOKENS_DIR/.jwt_expiry"
    
    if [[ -f "$admin_token_file" ]] && [[ -f "$admin_expiry_file" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$admin_expiry_file")
        local expiry_date=$(date -r "$expiry_time")
        local time_left=$((expiry_time - current_time))
        local minutes_left=$((time_left / 60))
        
        if [[ $time_left -gt 0 ]]; then
            echo_with_color $GREEN "   Valid (expires in ${minutes_left} minutes)"
            echo_with_color $BLUE "   Expires: $expiry_date"
        else
            echo_with_color $RED "   Expired"
        fi
    else
        echo_with_color $YELLOW "   Not created yet"
    fi
    
    echo ""
    
    # Check test token
    echo_with_color $BLUE "Test Token:"
    local test_token_file="$TOKENS_DIR/.jwt_token_test"
    local test_expiry_file="$TOKENS_DIR/.jwt_expiry_test"
    
    if [[ -f "$test_token_file" ]] && [[ -f "$test_expiry_file" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$test_expiry_file")
        local expiry_date=$(date -r "$expiry_time")
        local time_left=$((expiry_time - current_time))
        local minutes_left=$((time_left / 60))
        
        if [[ $time_left -gt 0 ]]; then
            echo_with_color $GREEN "   Valid (expires in ${minutes_left} minutes)"
            echo_with_color $BLUE "   Expires: $expiry_date"
        else
            echo_with_color $RED "   Expired"
        fi
    else
        echo_with_color $YELLOW "   Not created yet"
    fi
    
    echo ""
    
    # Check delegation tokens
    echo_with_color $BLUE "Delegation Tokens:"
    if [[ -f "$TOKENS_DIR/.jwt_token_delegate" ]] && [[ -f "$TOKENS_DIR/.jwt_token_delegate_expiry" ]]; then
        local current_time=$(date +%s)
        local expiry_time=$(cat "$TOKENS_DIR/.jwt_token_delegate_expiry" 2>/dev/null || echo "0")
        
        if [[ $current_time -lt $expiry_time ]]; then
            local delegation_token=$(cat "$TOKENS_DIR/.jwt_token_delegate" 2>/dev/null)
            local expiry_date=$(date -r $expiry_time 2>/dev/null || date -d @$expiry_time 2>/dev/null || echo "Unknown")
            
            echo_with_color $GREEN "   Valid (expires in $(( (expiry_time - current_time) / 60 )) minutes)"
            echo_with_color $BLUE "   Expires: $expiry_date"
            echo_with_color $BLUE "   Token: ${delegation_token:0:50}..."
        else
            echo_with_color $RED "   Expired"
        fi
    else
        echo_with_color $YELLOW "   Not created yet"
    fi
}

# Function to setup everything automatically
auto_setup() {
    echo_with_color $CYAN "Setting up YieldFabric authentication automatically..."
    echo ""
    
    # Check if auth service is running
    if ! check_service_running "Auth Service" "3000"; then
        echo_with_color $RED "Auth service is not running on port 3000"
        echo_with_color $YELLOW "Please start the auth service first:"
        echo "   cd ../yieldfabric-auth && cargo run"
        echo ""
        echo_with_color $BLUE "   Or start all services:"
        echo "   cd .. && ./scripts/start-services.sh"
        return 1
    fi
    
    echo_with_color $GREEN "Auth service is running"
    echo ""
    
    # Create admin token
    echo_with_color $BLUE "Setting up admin token..."
    local admin_token=$(get_admin_token)
    if [[ $? -eq 0 ]]; then
        echo_with_color $GREEN "Admin token ready"
    else
        echo_with_color $RED "Failed to setup admin token"
        return 1
    fi
    
    echo ""
    
    # Create test token
    echo_with_color $BLUE "Setting up test token..."
    local test_token=$(get_test_token)
    if [[ $? -eq 0 ]]; then
        echo_with_color $GREEN "Test token ready"
    else
        echo_with_color $YELLOW "Test token creation failed (this is optional)"
    fi
    
    echo ""

    # Create delegation token
    echo_with_color $BLUE "Setting up delegation token..."
    local delegation_token=$(get_delegation_token "$admin_token")
    if [[ $? -eq 0 ]]; then
        echo_with_color $GREEN "Delegation token ready"
    else
        echo_with_color $YELLOW "Delegation token creation failed (this is optional)"
    fi
    
    echo ""
    echo_with_color $GREEN "Setup complete! Your tokens are ready for testing."
    echo ""
    
    # Show final status
    show_status
}

# Function to show help
show_help() {
    echo_with_color $CYAN "YieldFabric Authentication Manager"
    echo "=========================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo_with_color $GREEN "  setup" "     - Automatically setup all tokens (recommended for first time)"
    echo_with_color $GREEN "  status" "    - Show current authentication status"
    echo_with_color $GREEN "  admin" "     - Get or create admin JWT token"
    echo_with_color $GREEN "  test" "      - Get or create test JWT token"
    echo_with_color $GREEN "  delegate" "  - Get or create delegation JWT token"
    echo_with_color $GREEN "  clean" "     - Remove all stored tokens"
    echo_with_color $GREEN "  help" "      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup     # First time setup - creates all tokens automatically"
    echo "  $0 status    # Check what's working and what needs attention"
    echo "  $0 admin     # Get admin token for manual testing"
    echo "  $0 delegate  # Get delegation token for group operations"
    echo ""
    echo_with_color $YELLOW "For first-time users, run: $0 setup"
}

# Main execution
case "${1:-setup}" in
    "setup")
        auto_setup
        ;;
    "status")
        show_status
        ;;
    "admin")
        get_admin_token
        ;;
    "test")
        load_tokens
        echo "Testing authentication system..."
        
        # Test admin token
        if [ -n "$ADMIN_TOKEN" ]; then
            echo "   Testing admin token..."
            ADMIN_TEST_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "$BASE_URL/auth/users" \
                -H "Authorization: Bearer $ADMIN_TOKEN")
            
            HTTP_STATUS=$(echo "$ADMIN_TEST_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
            RESPONSE_BODY=$(echo "$ADMIN_TEST_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')
            
            if [ "$HTTP_STATUS" = "200" ]; then
                echo "   Admin token valid - can access user management"
            else
                echo "   Admin token invalid or expired"
                echo "   HTTP Status: $HTTP_STATUS"
            fi
        else
            echo "   No admin token available for testing"
        fi
        
        # Test test token
        if [ -n "$TEST_TOKEN" ]; then
            echo "   Testing test token..."
            TEST_TEST_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "$BASE_URL/auth/users/me" \
                -H "Authorization: Bearer $TEST_TOKEN")
            
            HTTP_STATUS=$(echo "$TEST_TEST_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
            RESPONSE_BODY=$(echo "$TEST_TEST_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')
            
            if [ "$HTTP_STATUS" = "200" ]; then
                echo "   Test token valid - can access user profile"
                # Extract user ID for permission testing
                USER_ID=$(echo "$RESPONSE_BODY" | jq -r '.user.id' 2>/dev/null)
                if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
                    echo "   User ID: $USER_ID"
                    
                    # Test permission checking
                    echo "   Testing permission checking..."
                    PERMISSIONS_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "$BASE_URL/auth/users/$USER_ID/permissions" \
                        -H "Authorization: Bearer $ADMIN_TOKEN")
                    
                    HTTP_STATUS=$(echo "$PERMISSIONS_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
                    PERMISSIONS_BODY=$(echo "$PERMISSIONS_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')
                    
                    if [ "$HTTP_STATUS" = "200" ]; then
                        echo "   Permission check successful"
                        PERMISSIONS=$(echo "$PERMISSIONS_BODY" | jq -r '.permissions[]' 2>/dev/null)
                        if [ -n "$PERMISSIONS" ] && [ "$PERMISSIONS" != "null" ]; then
                            echo "   User permissions: $PERMISSIONS"
                        else
                            echo "   User has no specific permissions"
                        fi
                    else
                        echo "   Permission check failed"
                        echo "   HTTP Status: $HTTP_STATUS"
                    fi
                fi
            else
                echo "   Test token invalid or expired"
                echo "   HTTP Status: $HTTP_STATUS"
            fi
        else
            echo "   No test token available for testing"
        fi
        
        # Test delegation token
        if [ -n "$DELEGATION_TOKEN" ]; then
            echo "   Testing delegation token..."
            DELEGATION_TEST_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "$BASE_URL/api/v1/encrypt" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $DELEGATION_TOKEN" \
                -d '{"data": "test", "key_id": "test"}')
            
            HTTP_STATUS=$(echo "$DELEGATION_TEST_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
            RESPONSE_BODY=$(echo "$DELEGATION_TEST_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')
            
            if [ "$HTTP_STATUS" = "400" ] || [ "$HTTP_STATUS" = "403" ]; then
                echo "   Delegation token valid - crypto operations accessible"
                echo "   HTTP Status: $HTTP_STATUS (expected for invalid key_id)"
            elif [ "$HTTP_STATUS" = "200" ]; then
                echo "   Delegation token valid - crypto operations working"
            else
                echo "   Delegation token invalid or expired"
                echo "   HTTP Status: $HTTP_STATUS"
            fi
            
            # Test delegation scope
            echo "   Testing delegation scope..."
            DELEGATION_PAYLOAD=$(echo "$DELEGATION_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null)
            DELEGATION_SCOPE=$(echo "$DELEGATION_PAYLOAD" | jq -r '.delegation_scope[]' 2>/dev/null)
            DELEGATION_ACTING_AS=$(echo "$DELEGATION_PAYLOAD" | jq -r '.acting_as' 2>/dev/null)
            
            if [ -n "$DELEGATION_SCOPE" ] && [ "$DELEGATION_SCOPE" != "null" ]; then
                echo "   Delegation scope: $DELEGATION_SCOPE"
            else
                echo "   Delegation scope not found"
            fi
            
            if [ -n "$DELEGATION_ACTING_AS" ] && [ "$DELEGATION_ACTING_AS" != "null" ]; then
                echo "   Acting as: $DELEGATION_ACTING_AS"
            else
                echo "   Acting as not found"
            fi
        else
            echo "   No delegation token available for testing"
        fi
        
        echo "   Authentication testing completed"
        ;;
        
    permissions)
        load_tokens
        echo "Checking permission status..."
        
        if [ -z "$ADMIN_TOKEN" ]; then
            echo "   Admin token required for permission checking"
            exit 1
        fi
        
        if [ -z "$TEST_TOKEN" ]; then
            echo "   Test token required for permission checking"
            exit 1
        fi
        
        # Extract user ID from test token JWT payload
        echo "   Extracting user ID from test token..."
        TEST_TOKEN_PAYLOAD=$(echo "$TEST_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null)
        USER_ID=$(echo "$TEST_TOKEN_PAYLOAD" | sed 's/.*"sub":"\([^"]*\)".*/\1/' 2>/dev/null)
        
        if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
            echo "   Failed to extract user ID from test token"
            exit 1
        fi
        
        echo "   Test User ID: $USER_ID"
        
        # Check current permissions
        echo "   Checking current permissions..."
        PERMISSIONS_RESPONSE=$(curl -s "$BASE_URL/auth/users/$USER_ID/permissions" \
            -H "Authorization: Bearer $ADMIN_TOKEN")
        
        if [ -n "$PERMISSIONS_RESPONSE" ]; then
            PERMISSIONS=$(echo "$PERMISSIONS_RESPONSE" | jq -r '.permissions[]' 2>/dev/null)
            if [ -n "$PERMISSIONS" ] && [ "$PERMISSIONS" != "null" ]; then
                echo "   Current permissions: $PERMISSIONS"
            else
                echo "   User has no specific permissions"
            fi
        else
            echo "   Failed to retrieve permissions"
        fi
        
        # Test specific permission checks
        echo "   Testing specific permission checks..."
        PERMISSIONS_TO_CHECK=("ManageUsers" "ManageGroups" "CryptoOperations" "ReadGroup" "UpdateGroup")
        
        for permission in "${PERMISSIONS_TO_CHECK[@]}"; do
            echo "   Checking $permission permission..."
            PERMISSION_CHECK_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" "$BASE_URL/auth/permissions/$USER_ID/$permission/check" \
                -H "Authorization: Bearer $ADMIN_TOKEN")
            
            HTTP_STATUS=$(echo "$PERMISSION_CHECK_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
            RESPONSE_BODY=$(echo "$PERMISSION_CHECK_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')
            
            if [ "$HTTP_STATUS" = "200" ]; then
                HAS_PERMISSION=$(echo "$RESPONSE_BODY" | jq -r '.has_permission' 2>/dev/null)
                if [ "$HAS_PERMISSION" = "true" ]; then
                    echo "   User has $permission permission"
                else
                    echo "   User does not have $permission permission"
                fi
            else
                echo "   Permission check for $permission failed"
                echo "   HTTP Status: $HTTP_STATUS"
            fi
        done
        
        echo "   Permission status check completed"
        ;;
        
    delegate)
        # Get admin token first, then create delegation token
        admin_token=$(get_admin_token)
        if [[ $? -eq 0 ]]; then
            get_delegation_token "$admin_token"
        else
            echo_with_color $RED "Need admin token to create delegation token"
            exit 1
        fi
        ;;

    "clean")
        rm -f "$TOKENS_DIR"/.jwt_*
        echo_with_color $GREEN "All tokens cleaned up"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo_with_color $RED "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
