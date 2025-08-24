#!/bin/bash

# YieldFabric Commands Execution Script
# Reads commands.yaml and executes each command sequentially
# Gets JWT tokens for users and makes REST API calls based on command type

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMANDS_FILE="$SCRIPT_DIR/commands.yaml"
AUTH_SCRIPT="$SCRIPT_DIR/yieldfabric-auth.sh"
TOKENS_DIR="$SCRIPT_DIR/tokens"

# Ensure tokens directory exists
mkdir -p "$TOKENS_DIR"

# Global arrays to store command outputs for variable substitution
# Using regular arrays instead of associative arrays for compatibility
COMMAND_OUTPUT_KEYS=()
COMMAND_OUTPUT_VALUES=()

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

# Function to store a command output value
store_command_output() {
    local command_name="$1"
    local field_name="$2"
    local value="$3"
    
    local key="${command_name}_${field_name}"
    
    # Check if key already exists
    for idx in "${!COMMAND_OUTPUT_KEYS[@]}"; do
        if [[ "${COMMAND_OUTPUT_KEYS[$idx]}" == "$key" ]]; then
            # Update existing value
            COMMAND_OUTPUT_VALUES[$idx]="$value"
            return 0
        fi
    done
    
    # Add new key-value pair
    COMMAND_OUTPUT_KEYS+=("$key")
    COMMAND_OUTPUT_VALUES+=("$value")
}

# Function to retrieve a stored command output value
get_command_output() {
    local command_name="$1"
    local field_name="$2"
    
    local key="${command_name}_${field_name}"
    
    # Look up the value in our stored outputs
    for idx in "${!COMMAND_OUTPUT_KEYS[@]}"; do
        if [[ "${COMMAND_OUTPUT_KEYS[$idx]}" == "$key" ]]; then
            echo "${COMMAND_OUTPUT_VALUES[$idx]}"
            return 0
        fi
    done
    
    # Not found
    echo ""
    return 1
}

# Function to substitute variables in command parameters
# Supports format: $command_name.field_name
substitute_variables() {
    local value="$1"
    
    # Check if the value contains variable references
    if [[ "$value" =~ \$[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]* ]]; then
        # Extract command name and field name
        local command_name=$(echo "$value" | sed -n 's/.*\$\([a-zA-Z_][a-zA-Z0-9_]*\)\.[a-zA-Z0-9_]*.*/\1/p')
        local field_name=$(echo "$value" | sed -n 's/.*\$[a-zA-Z_][a-zA-Z0-9_]*\.\([a-zA-Z0-9_]*\).*/\1/p')
        
        if [[ -n "$command_name" && -n "$field_name" ]]; then
            # Look up the value in our stored outputs
            local stored_value=$(get_command_output "$command_name" "$field_name")
            if [[ -n "$stored_value" ]]; then
                echo_with_color $CYAN "    🔄 Substituting $value -> $stored_value" >&2
                echo "$stored_value"
                return 0
            else
                echo_with_color $YELLOW "    ⚠️  Variable $value not found in stored outputs" >&2
                echo "$value"
                return 1
            fi
        fi
    fi
    
    # No substitution needed
    echo "$value"
}

# Debug function to show all stored variables
debug_show_variables() {
    echo_with_color $PURPLE "🔍 Debug: All stored variables:"
    for idx in "${!COMMAND_OUTPUT_KEYS[@]}"; do
        local key="${COMMAND_OUTPUT_KEYS[$idx]}"
        local value="${COMMAND_OUTPUT_VALUES[$idx]}"
        echo_with_color $BLUE "  $key = $value"
    done
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

# Function to login user and get JWT token
login_user() {
    local email="$1"
    local password="$2"
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
            echo "$token"
            return 0
        else
            echo_with_color $RED "    ❌ No token in response" >&2
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Login failed: no response" >&2
        return 1
    fi
}

# Function to execute deposit command
execute_deposit() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local token_id="$4"
    local amount="$5"
    local idempotency_key="$6"
    
    echo_with_color $CYAN "🏦 Executing deposit command: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    echo_with_color $BLUE "  📤 Sending deposit request..."
    
    # Prepare deposit request payload
    local deposit_payload="{\"token_id\": \"$token_id\", \"amount\": \"$amount\"}"
    if [[ -n "$idempotency_key" ]]; then
        deposit_payload="{\"token_id\": \"$token_id\", \"amount\": \"$amount\", \"idempotency_key\": \"$idempotency_key\"}"
    fi
    
    echo_with_color $BLUE "  📋 Request payload: $deposit_payload"
    
    # Send deposit request to payments service
    echo_with_color $BLUE "  🌐 Making curl request to: http://localhost:3002/deposit"
    local http_response=$(curl -s -X POST "http://localhost:3002/deposit" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$deposit_payload")
    
    echo_with_color $BLUE "  📡 Raw curl response: '$http_response'"
    
    local http_status="200"  # Since curl -s doesn't show status, assume success if we get response
    local response_body="$http_response"
    
    if [[ "$http_status" == "200" ]]; then
        echo_with_color $BLUE "  📥 Response received: $response_body"
        local success=$(echo "$response_body" | jq -r '.success // empty')
        if [[ "$success" == "true" ]]; then
            local account_address=$(echo "$response_body" | jq -r '.account_address // empty')
            local message=$(echo "$response_body" | jq -r '.message // empty')
            local message_id=$(echo "$response_body" | jq -r '.message_id // empty')
            
            # Store outputs for variable substitution in future commands
            store_command_output "$command_name" "account_address" "$account_address"
            store_command_output "$command_name" "message" "$message"
            store_command_output "$command_name" "message_id" "$message_id"
            
            echo_with_color $GREEN "    ✅ Deposit successful!"
            echo_with_color $BLUE "      Account: $account_address"
            echo_with_color $BLUE "      Message: $message"
            echo_with_color $BLUE "      Message ID: $message_id"
            echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
            echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_message_id"
            return 0
        else
            echo_with_color $RED "    ❌ Deposit failed: success=false"
            echo_with_color $BLUE "      Full response: $response_body"
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Deposit request failed (HTTP $http_status)"
        echo_with_color $BLUE "      Response: $response_body"
        return 1
    fi
}

# Function to execute instant command
execute_instant() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local token_id="$4"
    local amount="$5"
    local destination_id="$6"
    local idempotency_key="$7"
    
    echo_with_color $CYAN "⚡ Executing instant command: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending instant payment request..."
    
    # Prepare instant payment request payload
    local instant_payload="{\"token_id\": \"$token_id\", \"amount\": \"$amount\", \"destination_id\": \"$destination_id\"}"
    if [[ -n "$idempotency_key" ]]; then
        instant_payload="{\"token_id\": \"$token_id\", \"amount\": \"$amount\", \"destination_id\": \"$destination_id\", \"idempotency_key\": \"$idempotency_key\"}"
    fi
    
    echo_with_color $BLUE "  📋 Request payload: $instant_payload"
    
    # Send instant payment request to payments service
    echo_with_color $BLUE "  🌐 Making curl request to: http://localhost:3002/instant"
    local http_response=$(curl -s -X POST "http://localhost:3002/instant" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$instant_payload")
    
    echo_with_color $BLUE "  📡 Raw curl response: '$http_response'"
    
    local http_status="200"  # Since curl -s doesn't show status, assume success if we get response
    local response_body="$http_response"
    
    if [[ "$http_status" == "200" ]]; then
        echo_with_color $BLUE "  📥 Response received: $response_body"
        local success=$(echo "$response_body" | jq -r '.success // empty')
        if [[ "$success" == "true" ]]; then
            local account_address=$(echo "$response_body" | jq -r '.account_address // empty')
            local destination_address=$(echo "$response_body" | jq -r '.destination_id // empty')
            local message=$(echo "$response_body" | jq -r '.message // empty')
            local id_hash=$(echo "$response_body" | jq -r '.id_hash // empty')
            local message_id=$(echo "$response_body" | jq -r '.message_id // empty')
            
            # Store outputs for variable substitution in future commands
            store_command_output "$command_name" "account_address" "$account_address"
            store_command_output "$command_name" "destination_id" "$destination_address"
            store_command_output "$command_name" "message" "$message"
            store_command_output "$command_name" "id_hash" "$id_hash"
            store_command_output "$command_name" "message_id" "$message_id"
            
            echo_with_color $GREEN "    ✅ Instant payment successful!"
            echo_with_color $BLUE "      From Account: $account_address"
            echo_with_color $BLUE "      To Address: $destination_address"
            echo_with_color $BLUE "      Message: $message"
            echo_with_color $BLUE "      Message ID: $message_id"
            if [[ -n "$id_hash" ]]; then
                echo_with_color $CYAN "      ID Hash: $id_hash"
            fi
            echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
            echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_destination_id, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id"
            return 0
        else
            echo_with_color $RED "    ❌ Instant payment failed: success=false"
            echo_with_color $BLUE "      Full response: $response_body"
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Instant payment request failed (HTTP $http_status)"
        echo_with_color $BLUE "      Response: $response_body"
        return 1
    fi
}

# Function to execute accept command
execute_accept() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local id_hash="$4"
    local idempotency_key="$5"
    
    echo_with_color $CYAN "✅ Executing accept command: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending accept request..."
    
    # Prepare accept request payload
    local accept_payload="{\"id_hash\": \"$id_hash\"}"
    if [[ -n "$idempotency_key" ]]; then
        accept_payload="{\"id_hash\": \"$id_hash\", \"idempotency_key\": \"$idempotency_key\"}"
    fi
    
    echo_with_color $BLUE "  📋 Request payload: $accept_payload"
    
    # Send accept request to payments service
    echo_with_color $BLUE "  🌐 Making curl request to: http://localhost:3002/accept"
    local http_response=$(curl -s -X POST "http://localhost:3002/accept" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$accept_payload")
    
    echo_with_color $BLUE "  📡 Raw curl response: '$http_response'"
    
    local http_status="200"  # Since curl -s doesn't show status, assume success if we get response
    local response_body="$http_response"
    
    if [[ "$http_status" == "200" ]]; then
        echo_with_color $BLUE "  📥 Response received: $response_body"
        local success=$(echo "$response_body" | jq -r '.success // empty')
        if [[ "$success" == "true" ]]; then
            local account_address=$(echo "$response_body" | jq -r '.account_address // empty')
            local message=$(echo "$response_body" | jq -r '.message // empty')
            local id_hash=$(echo "$response_body" | jq -r '.id_hash // empty')
            local message_id=$(echo "$response_body" | jq -r '.message_id // empty')
            
            # Store outputs for variable substitution in future commands
            store_command_output "$command_name" "account_address" "$account_address"
            store_command_output "$command_name" "message" "$message"
            store_command_output "$command_name" "id_hash" "$id_hash"
            store_command_output "$command_name" "message_id" "$message_id"
            
            echo_with_color $GREEN "    ✅ Accept successful!"
            echo_with_color $BLUE "      Account: $account_address"
            echo_with_color $BLUE "      ID Hash: $id_hash"
            echo_with_color $BLUE "      Message: $message"
            echo_with_color $BLUE "      Message ID: $message_id"
            echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
            echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id"
            return 0
        else
            echo_with_color $RED "    ❌ Accept failed: success=false"
            echo_with_color $BLUE "      Full response: $response_body"
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Accept request failed (HTTP $http_status)"
        echo_with_color $BLUE "      Response: $response_body"
        return 1
    fi
}

# Function to execute hello world command (example for future use)
execute_hello_world() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local message="$4"
    
    echo_with_color $CYAN "🌍 Executing hello world command: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending hello world request..."
    
    # Prepare hello world request payload
    local hello_payload="{\"message\": \"$message\"}"
    
    echo_with_color $BLUE "  📋 Request payload: $hello_payload"
    
    # Send hello world request (assuming there's a /hello endpoint that accepts POST)
    local http_response=$(curl -s -X POST "http://localhost:3002/hello" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$hello_payload")
    
    local http_status="200"  # Since curl -s doesn't show status, assume success if we get response
    local response_body="$http_response"
    
    if [[ "$http_status" == "200" ]]; then
        echo_with_color $GREEN "    ✅ Hello world successful!"
        echo_with_color $BLUE "      Response: $response_body"
        return 0
    else
        echo_with_color $RED "    ❌ Hello world request failed (HTTP $http_status)"
        echo_with_color $BLUE "      Response: $response_body"
        return 1
    fi
}

# Function to execute command based on type
execute_command() {
    local command_index="$1"
    
            echo_with_color $PURPLE "🔍 DEBUG: execute_command called with index $command_index"
        echo_with_color $PURPLE "🔍 DEBUG: Starting to parse command at index $command_index"
        
        # Parse command details
    local command_name=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].name")
    local command_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].type")
    local user_email=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].user.id")
    local user_password=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].user.password")
    
    # Parse command parameters
    local token_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.token_id")
    local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.amount")
    local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.destination_id")
    local id_hash=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.id_hash")
    local idempotency_key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.idempotency_key")
    
    # Apply variable substitution to parameters
    echo_with_color $CYAN "  🔄 Applying variable substitution to parameters..."
    token_id=$(substitute_variables "$token_id")
    amount=$(substitute_variables "$amount")
    destination_id=$(substitute_variables "$destination_id")
    id_hash=$(substitute_variables "$id_hash")
    idempotency_key=$(substitute_variables "$idempotency_key")
    
    echo_with_color $PURPLE "🚀 Executing command $((command_index + 1)): $command_name"
    echo_with_color $BLUE "  Type: $command_type"
    echo_with_color $BLUE "  User: $user_email"
    echo_with_color $BLUE "  Parameters after substitution:"
    if [[ -n "$token_id" ]]; then echo_with_color $BLUE "    token_id: $token_id"; fi
    if [[ -n "$amount" ]]; then echo_with_color $BLUE "    amount: $amount"; fi
    if [[ -n "$destination_id" ]]; then echo_with_color $BLUE "    destination_id: $destination_id"; fi
    if [[ -n "$id_hash" ]]; then echo_with_color $BLUE "    id_hash: $id_hash"; fi
    if [[ -n "$idempotency_key" ]]; then echo_with_color $BLUE "    idempotency_key: $idempotency_key"; fi
    
    # Execute command based on type
    case "$command_type" in
        "deposit")
            execute_deposit "$command_name" "$user_email" "$user_password" "$token_id" "$amount" "$idempotency_key"
            ;;
        "instant")
            execute_instant "$command_name" "$user_email" "$user_password" "$token_id" "$amount" "$destination_id" "$idempotency_key"
            ;;
        "accept")
            execute_accept "$command_name" "$user_email" "$user_password" "$id_hash" "$idempotency_key"
            ;;
        "hello_world")
            local message=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.message")
            message=$(substitute_variables "$message")
            execute_hello_world "$command_name" "$user_email" "$user_password" "$message"
            ;;
        *)
            echo_with_color $RED "❌ Unknown command type: $command_type"
            return 1
            ;;
    esac
}

# Function to validate commands.yaml file
validate_commands_file() {
    echo_with_color $CYAN "Validating commands.yaml..."
    
    if [[ ! -f "$COMMANDS_FILE" ]]; then
        echo_with_color $RED "Commands file not found: $COMMANDS_FILE"
        return 1
    fi
    
    if ! check_yq_available; then
        echo_with_color $RED "yq is required for YAML validation"
        return 1
    fi
    
    # Basic structure validation
    local has_commands=$(parse_yaml "$COMMANDS_FILE" '.commands | length > 0')
    
    if [[ "$has_commands" != "true" ]]; then
        echo_with_color $RED "No commands defined in commands.yaml"
        return 1
    fi
    
    # Validate each command structure
    local command_count=$(parse_yaml "$COMMANDS_FILE" '.commands | length')
    for ((i=0; i<$command_count; i++)); do
        local command_name=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].name")
        local command_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].type")
        local user_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].user.id")
        local user_password=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].user.password")
        
        if [[ -z "$command_name" ]]; then
            echo_with_color $RED "Error: Command $i missing 'name' field"
            return 1
        fi
        
        if [[ -z "$command_type" ]]; then
            echo_with_color $RED "Error: Command '$command_name' missing 'type' field"
            return 1
        fi
        
        if [[ -z "$user_id" ]]; then
            echo_with_color $RED "Error: Command '$command_name' missing 'user.id' field"
            return 1
        fi
        
        if [[ -z "$user_password" ]]; then
            echo_with_color $RED "Error: Command '$command_name' missing 'user.password' field"
            return 1
        fi
        
        # Validate command type
        case "$command_type" in
            "deposit")
                local token_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.token_id")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                
                if [[ -z "$token_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.token_id' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                ;;
            "instant")
                local token_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.token_id")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.destination_id")
                
                if [[ -z "$token_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.token_id' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                
                if [[ -z "$destination_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.destination_id' field"
                    return 1
                fi
                ;;
            "accept")
                local id_hash=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.id_hash")
                
                if [[ -z "$id_hash" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.id_hash' field"
                    return 1
                fi
                ;;
            "hello_world")
                local message=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.message")
                
                if [[ -z "$message" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.message' field"
                    return 1
                fi
                ;;
            *)
                echo_with_color $RED "Error: Command '$command_name' has unsupported type: '$command_type'"
                echo_with_color $YELLOW "Supported types: deposit, instant, accept, hello_world"
                return 1
                ;;
        esac
    done
    
    echo_with_color $GREEN "Commands file validation passed"
    return 0
}

# Function to show commands status
show_commands_status() {
    echo_with_color $CYAN "YieldFabric Commands Execution Status"
    echo "============================================="
    
    # Check services
    echo_with_color $BLUE "Service Status:"
    if check_service_running "Auth Service" "3000"; then
        echo_with_color $GREEN "   Auth Service (port 3000) - Running"
    else
        echo_with_color $RED "   Auth Service (port 3000) - Not running"
        echo_with_color $YELLOW "   Start the auth service first: cd ../yieldfabric-auth && cargo run"
        return 1
    fi
    
    if check_service_running "Payments Service" "3002"; then
        echo_with_color $GREEN "   Payments Service (port 3002) - Running"
    else
        echo_with_color $RED "   Payments Service (port 3002) - Not running"
        echo_with_color $YELLOW "   Start the payments service first: cd ../yieldfabric-payments && cargo run"
        return 1
    fi
    
    # Check commands file
    echo_with_color $BLUE "Commands File:"
    if [[ -f "$COMMANDS_FILE" ]]; then
        echo_with_color $GREEN "   commands.yaml - Found"
        
        if check_yq_available; then
            local command_count=$(parse_yaml "$COMMANDS_FILE" '.commands | length')
            echo_with_color $BLUE "   Commands defined: $command_count"
            
            # Show command details
            for ((i=0; i<$command_count; i++)); do
                local command_name=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].name")
                local command_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].type")
                local user_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].user.id")
                echo_with_color $BLUE "   Command $((i+1)): '$command_name' ($command_type) - User: $user_id"
            done
        else
            echo_with_color $YELLOW "   yq not available - cannot parse YAML"
        fi
    else
        echo_with_color $RED "   commands.yaml - Not found"
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

# Function to execute all commands
execute_all_commands() {
    echo_with_color $CYAN "🚀 Executing all commands from commands.yaml..."
    echo ""
    
    # Validate commands file
    if ! validate_commands_file; then
        echo_with_color $RED "❌ Commands file validation failed"
        return 1
    fi
    
    # Check service status
    if ! check_service_running "Auth Service" "3000"; then
        echo_with_color $RED "❌ Auth service is not running on port 3000"
        echo_with_color $YELLOW "Please start the auth service first:"
        echo "   cd ../yieldfabric-auth && cargo run"
        return 1
    fi
    
    if ! check_service_running "Payments Service" "3002"; then
        echo_with_color $RED "❌ Payments service is not running on port 3002"
        echo_with_color $YELLOW "Please start the payments service first:"
        echo "   cd ../yieldfabric-payments && cargo run"
        return 1
    fi
    
    # Get command count
    local command_count=$(parse_yaml "$COMMANDS_FILE" '.commands | length')
    local success_count=0
    local total_count=$command_count
    
    echo_with_color $GREEN "✅ Found $command_count commands to execute"
    echo ""
    
    # Execute each command sequentially
    echo_with_color $PURPLE "🔍 DEBUG: Starting loop with command_count=$command_count"
    for ((i=0; i<$command_count; i++)); do
        echo_with_color $PURPLE "================================================" | tr '=' '=' | head -c 80
        echo ""
        echo_with_color $CYAN "🔍 DEBUG: About to execute command $((i+1)) (index $i)"
        echo_with_color $PURPLE "🔍 DEBUG: Loop iteration $i, command_count=$command_count"
        echo_with_color $PURPLE "🔍 DEBUG: Loop condition: i=$i < command_count=$command_count = $((i < command_count))"
        echo_with_color $PURPLE "🔍 DEBUG: About to call execute_command with index $i"
        if execute_command "$i"; then
            echo_with_color $PURPLE "🔍 DEBUG: execute_command $i returned SUCCESS"
            success_count=$((success_count + 1))
            echo_with_color $GREEN "✅ Command $((i+1)) completed successfully"
        else
            echo_with_color $PURPLE "🔍 DEBUG: execute_command $i returned FAILURE"
            echo_with_color $RED "❌ Command $((i+1)) failed"
            echo_with_color $YELLOW "Continuing with next command..."
        fi
        
        echo_with_color $PURPLE "🔍 DEBUG: After execute_command $i, success_count=$success_count"
        echo_with_color $PURPLE "🔍 DEBUG: Next iteration will be i=$((i+1))"
        echo ""
        
        # Add delay between commands
        if [[ $i -lt $((command_count - 1)) ]]; then
            echo_with_color $BLUE "⏳ Waiting 2 seconds before next command..."
            sleep 2
        fi
    done
    
    echo_with_color $PURPLE "=" | tr '=' '=' | head -c 80
    echo ""
    echo_with_color $GREEN "🎉 Commands execution completed!"
    echo_with_color $BLUE "   Successful: $success_count/$total_count"
    
    if [[ $success_count -eq $total_count ]]; then
        echo_with_color $GREEN "   ✅ All commands executed successfully!"
        return 0
    else
        echo_with_color $YELLOW "   ⚠️  Some commands failed"
        return 1
    fi
}

# Function to show current stored variables
show_stored_variables() {
    echo_with_color $CYAN "Currently Stored Variables for Command Chaining"
    echo "========================================================"
    
    if [[ ${#COMMAND_OUTPUT_KEYS[@]} -eq 0 ]]; then
        echo_with_color $YELLOW "No variables stored yet. Run some commands first to see stored outputs."
        return 0
    fi
    
    echo_with_color $BLUE "Available variables for substitution:"
    for idx in "${!COMMAND_OUTPUT_KEYS[@]}"; do
        local key="${COMMAND_OUTPUT_KEYS[$idx]}"
        local value="${COMMAND_OUTPUT_VALUES[$idx]}"
        echo_with_color $GREEN "  $key = $value"
    done
    
    echo ""
    echo_with_color $CYAN "Usage in commands.yaml:"
    echo "  parameters:"
    echo "    id_hash: \$issuer_send_1.id_hash    # Use id_hash from 'issuer_send_1' command"
    echo "    amount: \$previous_deposit.amount   # Use amount from 'previous_deposit' command"
    echo ""
}

# Function to show help
show_help() {
    echo_with_color $CYAN "YieldFabric Commands Execution Script"
    echo "============================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo_with_color $GREEN "  execute" "  - Execute all commands from commands.yaml"
    echo_with_color $GREEN "  status" "   - Show current status and requirements"
    echo_with_color $GREEN "  validate" " - Validate commands.yaml file structure"
    echo_with_color $GREEN "  variables" " - Show currently stored variables for command chaining"
    echo_with_color $GREEN "  help" "     - Show this help message"
    echo ""
    echo "Requirements:"
    echo "  • yieldfabric-auth service running on port 3000"
    echo "  • yieldfabric-payments service running on port 3002"
    echo "  • yq YAML parser installed"
    echo "  • commands.yaml file with commands configuration"
    echo ""
    echo "Commands.yaml Structure:"
    echo "  • commands: array of commands with type, user, and parameters"
    echo "  • Supported command types: deposit, instant, accept, hello_world"
    echo "  • Each command must have user.id, user.password, and parameters"
    echo "  • Variables can be referenced using: \$command_name.field_name"
    echo ""
    echo "Variable Substitution Examples:"
    echo "  • id_hash: \$issuer_send_1.id_hash    # Use id_hash from 'issuer_send_1' command"
    echo "  • amount: \$previous_deposit.amount   # Use amount from 'previous_deposit' command"
    echo "  • message_id: \$instant_pay.message_id # Use message_id from 'instant_pay' command"
    echo ""
    echo "Examples:"
    echo "  $0 execute    # Execute all commands"
    echo "  $0 status     # Check requirements"
    echo "  $0 validate   # Validate commands.yaml structure"
    echo "  $0 variables  # Show stored variables"
    echo ""
    echo_with_color $YELLOW "For first-time users, run: $0 execute"
}

# Main execution
case "${1:-execute}" in
    "execute")
        execute_all_commands
        ;;
    "status")
        show_commands_status
        ;;
    "validate")
        validate_commands_file
        ;;
    "variables")
        show_stored_variables
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
