#!/bin/bash

# YieldFabric System Setup Script
# Reads setup.yaml and creates users, groups, and relationships
# Integrates with yieldfabric-auth.sh for authentication management

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_FILE="$SCRIPT_DIR/setup.yaml"
AUTH_SCRIPT="$SCRIPT_DIR/yieldfabric-auth.sh"
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

# Function to check if yq is available for YAML parsing
check_yq_available() {
    if command -v yq &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to parse YAML using yq
parse_yaml() {
    local yaml_file="$1"
    local query="$2"
    
    if ! check_yq_available; then
        echo_with_color $RED "yq is required for YAML parsing but not installed"
        echo_with_color $YELLOW "Install yq: brew install yq (macOS) or see https://github.com/mikefarah/yq"
        return 1
    fi
    
    yq eval "$query" "$yaml_file" 2>/dev/null
}

# Function to login with services and return JWT token
login_with_services() {
    local email="$1"
    local password="$2"
    local services_json='["vault", "payments"]'

    local http_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\", \"password\": \"$password\", \"services\": $services_json}")

    local http_status=$(echo "$http_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    local response_body=$(echo "$http_response" | sed 's/HTTP_STATUS:[0-9]*//')

    if [[ "$http_status" == "200" ]]; then
        echo "$response_body" | jq -r '.token // .access_token // .jwt // empty'
        return 0
    else
        echo "" # no token
        return 1
    fi
}

# Helper to fetch first user's credentials from setup.yaml
get_first_user_credentials() {
    local email=$(parse_yaml "$SETUP_FILE" '.users[0].id')
    local password=$(parse_yaml "$SETUP_FILE" '.users[0].password')
    if [[ -n "$email" && -n "$password" ]]; then
        echo "$email $password"
        return 0
    fi
    return 1
}

# Helper to find a group's DB id by its name
get_group_id_by_name() {
    local token="$1"
    local name="$2"
    local groups_json=$(curl -s -X GET "http://localhost:3000/auth/groups" -H "Authorization: Bearer $token")
    echo "$groups_json" | jq -r ".[] | select(.name == \"$name\") | .id" 2>/dev/null
}

# Helper to get user ID by email from stored user IDs
get_user_id_by_email() {
    local email="$1"
    local user_count=$(parse_yaml "$SETUP_FILE" '.users | length')
    
    for ((i=0; i<$user_count; i++)); do
        local stored_email=$(parse_yaml "$SETUP_FILE" ".users[$i].id")
        if [[ "$stored_email" == "$email" ]]; then
            # Get the stored user ID
            local user_id_var="USER_ID_${i}"
            local user_id="${!user_id_var}"
            if [[ -n "$user_id" ]]; then
                echo "$user_id"
                return 0
            fi
        fi
    done
    
    return 1
}

# Ensure we have a working auth token for group operations
ensure_auth_token() {
    # 1) Try logging in with the first user from setup.yaml
    local creds
    creds=$(get_first_user_credentials)
    if [[ -n "$creds" ]]; then
        local email password
        email=$(echo "$creds" | awk '{print $1}')
        password=$(echo "$creds" | awk '{print $2}')
        local token
        token=$(login_with_services "$email" "$password")
        if [[ -n "$token" && "$token" != "null" ]]; then
            echo "$token"
            return 0
        fi
    fi

    # 2) Try test token via helper script
    if [[ -x "$AUTH_SCRIPT" ]]; then
        local test_token
        test_token=$($AUTH_SCRIPT test 2>/dev/null)
        if [[ -n "$test_token" && "$test_token" != "null" ]]; then
            echo "$test_token"
            return 0
        fi
        # 3) Fallback to admin helper
        local admin_token
        admin_token=$($AUTH_SCRIPT admin 2>/dev/null)
        if [[ -n "$admin_token" && "$admin_token" != "null" ]]; then
            echo "$admin_token"
            return 0
        fi
    fi

    echo ""
    return 1
}

# Function to create user (requires admin token)
create_user() {
    local email="$1"
    local password="$2"
    local role="$3"
    local admin_token="$4"
    
    echo_with_color $BLUE "Creating user: $email with role: $role"
    
    local user_payload="{\"email\": \"$email\", \"password\": \"$password\", \"role\": \"$role\"}"
    
    # Get HTTP status code along with response
    local http_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "http://localhost:3000/auth/users" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -d "$user_payload")
    
    local http_status=$(echo "$http_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    local response_body=$(echo "$http_response" | sed 's/HTTP_STATUS:[0-9]*//')
    
    if [[ "$http_status" == "200" ]]; then
        local user_id=$(echo "$response_body" | jq -r '.user.id // .id // empty' 2>/dev/null)
        if [[ -n "$user_id" && "$user_id" != "null" ]]; then
            echo_with_color $GREEN "User created successfully: $email (ID: $user_id)"
            return 0
        else
            echo_with_color $RED "User creation failed: invalid response format"
            echo_with_color $YELLOW "Response: $response_body"
            return 1
        fi
    elif [[ "$http_status" == "409" ]]; then
        echo_with_color $YELLOW "User already exists: $email"
        return 0
    else
        echo_with_color $RED "Failed to create user: $email (HTTP $http_status)"
        echo_with_color $YELLOW "Response: $response_body"
        return 1
    fi
}

# Function to check if user exists and return user ID
check_user_exists() {
    local email="$1"
    
    # Since there's no GET /auth/users endpoint, we need to try to get user info
    # by attempting to login and extract user ID from the response
    local login_response=$(curl -s -X POST "http://localhost:3000/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\", \"password\": \"$(parse_yaml "$SETUP_FILE" ".users[] | select(.id == \"$email\") | .password")\", \"services\": [\"vault\", \"payments\"]}")
    
    if [[ -n "$login_response" ]]; then
        local user_id=$(echo "$login_response" | jq -r '.user.id // empty' 2>/dev/null)
        if [[ -n "$user_id" && "$user_id" != "null" ]]; then
            echo "$user_id"
            return 0
        fi
    fi
    
    return 1
}

# Function to create initial users (without admin token)
create_initial_users() {
    echo_with_color $CYAN "Creating initial users from setup.yaml..."
    
    local success_count=0
    local total_count=0
    
    # Get user count
    local user_count=$(parse_yaml "$SETUP_FILE" '.users | length')
    
    for ((i=0; i<$user_count; i++)); do
        local email=$(parse_yaml "$SETUP_FILE" ".users[$i].id")
        local password=$(parse_yaml "$SETUP_FILE" ".users[$i].password")
        local role=$(parse_yaml "$SETUP_FILE" ".users[$i].role")
        
        if [[ -n "$email" && -n "$password" && -n "$role" ]]; then
            total_count=$((total_count + 1))
            
            # Check if user already exists
            local existing_user_id=$(check_user_exists "$email")
            if [[ -n "$existing_user_id" ]]; then
                echo_with_color $YELLOW "User already exists: $email (ID: $existing_user_id) - skipping creation"
                # Store user ID for later use
                eval "USER_ID_${i}=\"$existing_user_id\""
                success_count=$((success_count + 1))
                continue
            fi
            
            echo_with_color $BLUE "Creating user: $email with role: $role"
            
            # Create user without admin token (direct API call)
            local user_payload="{\"email\": \"$email\", \"password\": \"$password\", \"role\": \"$role\"}"
            
            # Add a small delay to prevent race conditions
            sleep 1
            
            # Get HTTP status code along with response
            local http_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "http://localhost:3000/auth/users" \
                -H "Content-Type: application/json" \
                -d "$user_payload")
            
            local http_status=$(echo "$http_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
            local response_body=$(echo "$http_response" | sed 's/HTTP_STATUS:[0-9]*//')
            
            if [[ "$http_status" == "200" ]]; then
                local user_id=$(echo "$response_body" | jq -r '.user.id // .id // empty' 2>/dev/null)
                if [[ -n "$user_id" && "$user_id" != "null" ]]; then
                    echo_with_color $GREEN "User created successfully: $email (ID: $user_id)"
                    # Store user ID for later use
                    eval "USER_ID_${i}=\"$user_id\""
                    success_count=$((success_count + 1))
                    # Wait a moment for the user to be fully registered
                    sleep 2
                else
                    echo_with_color $RED "User creation failed: invalid response format"
                    echo_with_color $YELLOW "Response: $response_body"
                fi
            elif [[ "$http_status" == "409" ]]; then
                echo_with_color $YELLOW "User already exists: $email"
                success_count=$((success_count + 1))
            else
                echo_with_color $RED "Failed to create user: $email (HTTP $http_status)"
                echo_with_color $YELLOW "Response: $response_body"
            fi
        else
            echo_with_color $RED "Invalid user data at index $i"
        fi
    done
    
    echo_with_color $GREEN "Initial users setup completed: $success_count/$total_count successful"
    return $((success_count == total_count ? 0 : 1))
}

# Function to create group
create_group() {
    local group_id="$1"
    local name="$2"
    local description="$3"
    local group_type="$4"
    local admin_token="$5"
    
    echo_with_color $BLUE "Creating group: $name ($group_type)"
    
    local group_payload="{\"name\": \"$name\", \"description\": \"$description\", \"group_type\": \"$group_type\"}"
    
    # Get HTTP status code along with response
    local http_response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "http://localhost:3000/auth/groups" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -d "$group_payload")
    
    local http_status=$(echo "$http_response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    local response_body=$(echo "$http_response" | sed 's/HTTP_STATUS:[0-9]*//')
    
    if [[ "$http_status" == "200" ]]; then
        local created_group_id=$(echo "$response_body" | jq -r '.id // empty' 2>/dev/null)
        if [[ -n "$created_group_id" && "$created_group_id" != "null" ]]; then
            echo_with_color $GREEN "Group created successfully: $name (ID: $created_group_id)"
            return 0
        else
            echo_with_color $RED "Group creation failed: invalid response format"
            echo_with_color $YELLOW "Response: $response_body"
            return 1
        fi
    elif [[ "$http_status" == "409" ]]; then
        echo_with_color $YELLOW "Group already exists: $name"
        return 0
    else
        echo_with_color $RED "Failed to create group: $name (HTTP $http_status)"
        echo_with_color $YELLOW "Response: $response_body"
        return 1
    fi
}

# Function to add user to group as member
add_user_to_group() {
    local group_id="$1"
    local user_email="$2"
    local role="$3"
    local admin_token="$4"
    
    echo_with_color $BLUE "Adding user $user_email to group as $role"
    
    # Get the user ID from stored user IDs (since there's no GET /auth/users endpoint)
    local user_id
    user_id=$(get_user_id_by_email "$user_email")
    
    if [[ -z "$user_id" ]]; then
        echo_with_color $RED "User not found in stored user IDs: $user_email"
        echo_with_color $BLUE "Available stored users:"
        local user_count=$(parse_yaml "$SETUP_FILE" '.users | length')
        for ((i=0; i<$user_count; i++)); do
            local stored_email=$(parse_yaml "$SETUP_FILE" ".users[$i].id")
            local user_id_var="USER_ID_${i}"
            local stored_user_id="${!user_id_var}"
            if [[ -n "$stored_user_id" ]]; then
                echo_with_color $BLUE "   $stored_email (ID: $stored_user_id)"
            fi
        done
        return 1
    fi
    
    echo_with_color $BLUE "Found user: $user_email (ID: $user_id)"
    
    # Add user to group
    local member_payload="{\"user_id\": \"$user_id\", \"role\": \"$role\"}"
    
    local response=$(curl -s -X POST "http://localhost:3000/auth/groups/$group_id/members" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $admin_token" \
        -d "$member_payload")
    
    if [[ -n "$response" ]]; then
        echo_with_color $GREEN "User $user_email added to group as $role"
        return 0
    else
        echo_with_color $RED "Failed to add user $user_email to group"
        return 1
    fi
}

# Function to set group owner (if API supports it)
set_group_owner() {
    local group_id="$1"
    local owner_email="$2"
    local admin_token="$3"
    
    echo_with_color $BLUE "Setting group owner: $owner_email"
    
    # This is a placeholder - need to verify if the API supports setting owners
    # For now, we'll add the owner as an admin member
    echo_with_color $YELLOW "Note: Setting group owner - adding as admin member instead"
    add_user_to_group "$group_id" "$owner_email" "admin" "$admin_token"
}

# Function to setup users (requires admin token)
setup_users() {
    echo_with_color $CYAN "Setting up users from setup.yaml..."
    
    local admin_token="$1"
    local success_count=0
    local total_count=0
    
    # Get user count
    local user_count=$(parse_yaml "$SETUP_FILE" '.users | length')
    
    for ((i=0; i<$user_count; i++)); do
        local email=$(parse_yaml "$SETUP_FILE" ".users[$i].id")
        local password=$(parse_yaml "$SETUP_FILE" ".users[$i].password")
        local role=$(parse_yaml "$SETUP_FILE" ".users[$i].role")
        
        if [[ -n "$email" && -n "$password" && -n "$role" ]]; then
            total_count=$((total_count + 1))
            if create_user "$email" "$password" "$role" "$admin_token"; then
                success_count=$((success_count + 1))
            fi
        else
            echo_with_color $RED "Invalid user data at index $i"
        fi
    done
    
    echo_with_color $GREEN "Users setup completed: $success_count/$total_count successful"
    return $((success_count == total_count ? 0 : 1))
}

# Function to setup groups
setup_groups() {
    echo_with_color $CYAN "Setting up groups from setup.yaml..."
    
    # Always use a fresh token from the first user (which has SuperAdmin role)
    echo_with_color $BLUE "Getting fresh token from first user for group operations..."
    local effective_token
    effective_token=$(ensure_auth_token)
    if [[ -z "$effective_token" ]]; then
        echo_with_color $RED "Failed to obtain a valid token for group operations"
        return 1
    fi
    
    echo_with_color $GREEN "Using fresh token for group operations"
    
    local success_count=0
    local total_count=0
    
    # Get group count
    local group_count=$(parse_yaml "$SETUP_FILE" '.groups | length')
    
    for ((i=0; i<$group_count; i++)); do
        local group_id=$(parse_yaml "$SETUP_FILE" ".groups[$i].id")
        local name=$(parse_yaml "$SETUP_FILE" ".groups[$i].name")
        local description=$(parse_yaml "$SETUP_FILE" ".groups[$i].description")
        local group_type=$(parse_yaml "$SETUP_FILE" ".groups[$i].group_type")
        
        if [[ -n "$group_id" && -n "$name" && -n "$description" && -n "$group_type" ]]; then
            total_count=$((total_count + 1))
            if create_group "$group_id" "$name" "$description" "$group_type" "$effective_token"; then
                success_count=$((success_count + 1))
            fi
        else
            echo_with_color $RED "Invalid group data at index $i"
        fi
    done
    
    echo_with_color $GREEN "Groups setup completed: $success_count/$total_count successful"
    return $((success_count == total_count ? 0 : 1))
}

# Function to setup group relationships
setup_group_relationships() {
    echo_with_color $CYAN "Setting up group relationships from setup.yaml..."
    
    # Always use a fresh token from the first user (which has SuperAdmin role)
    echo_with_color $BLUE "Getting fresh token from first user for group operations..."
    local effective_token
    effective_token=$(ensure_auth_token)
    if [[ -z "$effective_token" ]]; then
        echo_with_color $RED "Failed to obtain a valid token for group operations"
        return 1
    fi
    
    echo_with_color $GREEN "Using fresh token for group operations"
    
    local success_count=0
    local total_count=0
    
    # Get group count
    local group_count=$(parse_yaml "$SETUP_FILE" '.groups | length')
    
    for ((i=0; i<$group_count; i++)); do
        local group_id=$(parse_yaml "$SETUP_FILE" ".groups[$i].id")
        local group_name=$(parse_yaml "$SETUP_FILE" ".groups[$i].name")
        
        echo_with_color $BLUE "Setting up relationships for group: $group_name"
        # Resolve group id by name if provided id does not work
        local resolved_group_id="$group_id"
        if [[ -z "$resolved_group_id" || "$resolved_group_id" == "null" ]]; then
            resolved_group_id=$(get_group_id_by_name "$effective_token" "$group_name")
        fi
        if [[ -z "$resolved_group_id" || "$resolved_group_id" == "null" ]]; then
            # Attempt to create the group quickly if it doesn't exist
            local description=$(parse_yaml "$SETUP_FILE" ".groups[$i].description")
            local group_type=$(parse_yaml "$SETUP_FILE" ".groups[$i].group_type")
            if create_group "$group_id" "$group_name" "$description" "$group_type" "$effective_token"; then
                resolved_group_id=$(get_group_id_by_name "$effective_token" "$group_name")
            fi
        fi
        if [[ -z "$resolved_group_id" || "$resolved_group_id" == "null" ]]; then
            echo_with_color $RED "Could not resolve group id for: $group_name"
            continue
        fi
        
        # Handle owners
        local owners=$(parse_yaml "$SETUP_FILE" ".groups[$i].owners[]" 2>/dev/null)
        if [[ -n "$owners" ]]; then
            for owner in $owners; do
                total_count=$((total_count + 1))
                if set_group_owner "$resolved_group_id" "$owner" "$effective_token"; then
                    success_count=$((success_count + 1))
                fi
            done
        fi
        
        # Handle members
        local members=$(parse_yaml "$SETUP_FILE" ".groups[$i].members[]" 2>/dev/null)
        if [[ -n "$members" ]]; then
            for member in $members; do
                total_count=$((total_count + 1))
                if add_user_to_group "$resolved_group_id" "$member" "member" "$effective_token"; then
                    success_count=$((success_count + 1))
                fi
            done
        fi
    done
    
    echo_with_color $GREEN "Group relationships setup completed: $success_count/$total_count successful"
    return $((success_count == total_count ? 0 : 1))
}

# Function to validate setup.yaml
validate_setup_file() {
    echo_with_color $CYAN "Validating setup.yaml..."
    
    if [[ ! -f "$SETUP_FILE" ]]; then
        echo_with_color $RED "Setup file not found: $SETUP_FILE"
        return 1
    fi
    
    if ! check_yq_available; then
        echo_with_color $RED "yq is required for YAML validation"
        return 1
    fi
    
    # Basic structure validation
    local has_users=$(parse_yaml "$SETUP_FILE" '.users | length > 0')
    local has_groups=$(parse_yaml "$SETUP_FILE" '.groups | length > 0')
    
    if [[ "$has_users" != "true" ]]; then
        echo_with_color $RED "No users defined in setup.yaml"
        return 1
    fi
    
    if [[ "$has_groups" != "true" ]]; then
        echo_with_color $RED "No groups defined in setup.yaml"
        return 1
    fi
    
    echo_with_color $GREEN "Setup file validation passed"
    return 0
}

# Function to show setup status
show_setup_status() {
    echo_with_color $CYAN "YieldFabric System Setup Status"
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
    
    # Check setup file
    echo_with_color $BLUE "Setup File:"
    if [[ -f "$SETUP_FILE" ]]; then
        echo_with_color $GREEN "   setup.yaml - Found"
        
        if check_yq_available; then
            local user_count=$(parse_yaml "$SETUP_FILE" '.users | length')
            local group_count=$(parse_yaml "$SETUP_FILE" '.groups | length')
            echo_with_color $BLUE "   Users defined: $user_count"
            echo_with_color $BLUE "   Groups defined: $group_count"
        else
            echo_with_color $YELLOW "   yq not available - cannot parse YAML"
        fi
    else
        echo_with_color $RED "   setup.yaml - Not found"
        return 1
    fi
    
    # Check yq availability
    echo_with_color $BLUE "YAML Parser:"
    if check_yq_available; then
        echo_with_color $GREEN "   yq - Available"
    else
        echo_with_color $RED "   yq - Not available"
        echo_with_color $YELLOW "   Install yq: brew install yq (macOS) or see https://github.com/mikefarah/yq"
        return 1
    fi
}

# Function to run complete setup
run_setup() {
    echo_with_color $CYAN "Running YieldFabric System Setup..."
    echo ""
    
    # Validate setup file
    if ! validate_setup_file; then
        echo_with_color $RED "Setup file validation failed"
        return 1
    fi
    
    # Check service status
    if ! check_service_running "Auth Service" "3000"; then
        echo_with_color $RED "Auth service is not running on port 3000"
        echo_with_color $YELLOW "Please start the auth service first:"
        echo "   cd ../yieldfabric.sh"
        return 1
    fi
    
    # Create initial users first (without admin token)
    echo_with_color $BLUE "Creating initial users..."
    if ! create_initial_users; then
        echo_with_color $RED "Failed to create initial users"
        return 1
    fi
    
    echo_with_color $GREEN "Initial users created successfully"
    echo ""
    
    # Now setup authentication using yieldfabric-auth.sh
    echo_with_color $BLUE "Setting up authentication..."
    local admin_token=$($AUTH_SCRIPT admin 2>/dev/null)
    if [[ $? -ne 0 || -z "$admin_token" ]]; then
        echo_with_color $RED "Failed to get admin token"
        return 1
    fi
    
    echo_with_color $GREEN "Authentication setup completed"
    echo ""
    
    # Setup groups
    if ! setup_groups "$admin_token"; then
        echo_with_color $YELLOW "Group setup had some issues, continuing with relationships..."
    fi
    
    echo ""
    
    # Setup group relationships
    if ! setup_group_relationships "$admin_token"; then
        echo_with_color $YELLOW "Group relationship setup had some issues"
    fi
    
    echo ""
    echo_with_color $GREEN "System setup completed!"
    echo ""
    
    # Show final status
    show_setup_status
}

# Function to show help
show_help() {
    echo_with_color $CYAN "YieldFabric System Setup Script"
    echo "=========================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo_with_color $GREEN "  setup" "     - Run complete system setup from setup.yaml"
    echo_with_color $GREEN "  status" "    - Show current setup status and requirements"
    echo_with_color $GREEN "  validate" "  - Validate setup.yaml file structure"
    echo_with_color $GREEN "  users" "     - Setup only users from setup.yaml"
    echo_with_color $GREEN "  groups" "    - Setup only groups from setup.yaml"
    echo_with_color $GREEN "  help" "      - Show this help message"
    echo ""
    echo "Requirements:"
    echo "  • yieldfabric-auth service running on port 3000"
    echo "  • yieldfabric-auth.sh script available"
    echo "  • yq YAML parser installed"
    echo "  • setup.yaml file with users and groups configuration"
    echo ""
    echo "Examples:"
    echo "  $0 setup     # Complete system setup"
    echo "  $0 status    # Check setup requirements"
    echo "  $0 validate  # Validate setup.yaml structure"
    echo ""
    echo_with_color $YELLOW "For first-time users, run: $0 setup"
}

# Main execution
case "${1:-setup}" in
    "setup")
        run_setup
        ;;
    "status")
        show_setup_status
        ;;
    "validate")
        validate_setup_file
        ;;
    "users")
        if check_service_running "Auth Service" "3000"; then
            # Get admin token first, then create users
            echo_with_color $BLUE "Getting admin token first..."
            admin_token=$($AUTH_SCRIPT admin 2>/dev/null)
            if [[ $? -eq 0 && -n "$admin_token" ]]; then
                echo_with_color $GREEN "Admin token obtained, creating users..."
                if setup_users "$admin_token"; then
                    echo_with_color $GREEN "Users created successfully"
                else
                    echo_with_color $RED "Failed to create users"
                    exit 1
                fi
            else
                echo_with_color $RED "Failed to get admin token"
                exit 1
            fi
        else
            echo_with_color $RED "Auth service not running"
            exit 1
        fi
        ;;
    "groups")
        if check_service_running "Auth Service" "3000"; then
            # Create users first if they don't exist
            if ! create_initial_users; then
                echo_with_color $RED "Failed to create users"
                exit 1
            fi
            
            # Now get admin token
            admin_token=$($AUTH_SCRIPT admin 2>/dev/null)
            if [[ $? -eq 0 && -n "$admin_token" ]]; then
                setup_groups "$admin_token"
            else
                echo_with_color $RED "Failed to get admin token"
                exit 1
            fi
        else
            echo_with_color $RED "Auth service not running"
            exit 1
        fi
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
