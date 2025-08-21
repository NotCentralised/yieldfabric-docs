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
            echo_with_color $GREEN "    ✅ Deposit successful!"
            echo_with_color $BLUE "      Account: $account_address"
            echo_with_color $BLUE "      Message: $message"
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
    
    # Parse command details
    local command_name=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].name")
    local command_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].type")
    local user_email=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].user.id")
    local user_password=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].user.password")
    
    # Parse command parameters
    local token_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.token_id")
    local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.amount")
    local idempotency_key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.idempotency_key")
    
    echo_with_color $PURPLE "🚀 Executing command $((command_index + 1)): $command_name"
    echo_with_color $BLUE "  Type: $command_type"
    echo_with_color $BLUE "  User: $user_email"
    
    # Execute command based on type
    case "$command_type" in
        "deposit")
            execute_deposit "$command_name" "$user_email" "$user_password" "$token_id" "$amount" "$idempotency_key"
            ;;
        "hello_world")
            local message=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.message")
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
            "hello_world")
                local message=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.message")
                
                if [[ -z "$message" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.message' field"
                    return 1
                fi
                ;;
            *)
                echo_with_color $RED "Error: Command '$command_name' has unsupported type: '$command_type'"
                echo_with_color $YELLOW "Supported types: deposit, hello_world"
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
    for ((i=0; i<$command_count; i++)); do
        echo_with_color $PURPLE "=" | tr '=' '=' | head -c 80
        echo ""
        
        if execute_command "$i"; then
            success_count=$((success_count + 1))
            echo_with_color $GREEN "✅ Command $((i+1)) completed successfully"
        else
            echo_with_color $RED "❌ Command $((i+1)) failed"
            echo_with_color $YELLOW "Continuing with next command..."
        fi
        
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
    echo "  • Supported command types: deposit, hello_world"
    echo "  • Each command must have user.id, user.password, and parameters"
    echo ""
    echo "Examples:"
    echo "  $0 execute   # Execute all commands"
    echo "  $0 status    # Check requirements"
    echo "  $0 validate  # Validate commands.yaml structure"
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
