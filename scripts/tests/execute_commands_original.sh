#!/bin/bash

# YieldFabric GraphQL Commands Execution Script
# Reads a YAML file (default: commands.yaml) and executes each command sequentially using GraphQL mutations
# Gets JWT tokens for users and makes GraphQL API calls based on command type

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments to get the YAML file
YAML_FILE="${1:-commands.yaml}"
COMMANDS_FILE="$SCRIPT_DIR/$YAML_FILE"
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

# Function to execute deposit command using GraphQL
execute_deposit() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local amount="$5"
    local idempotency_key="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "🏦 Executing deposit command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL deposit mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    if [[ -n "$idempotency_key" ]]; then
        graphql_mutation="mutation { deposit(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\", idempotencyKey: \\\"$idempotency_key\\\" }) { success message accountAddress depositResult messageId timestamp } }"
    else
        graphql_mutation="mutation { deposit(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\" }) { success message accountAddress depositResult messageId timestamp } }"
    fi
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.deposit.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.deposit.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.deposit.message // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.deposit.messageId // empty')
        local deposit_result=$(echo "$http_response" | jq -r '.data.deposit.depositResult // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "deposit_result" "$deposit_result"
        
        echo_with_color $GREEN "    ✅ Deposit successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Deposit Result: $deposit_result"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_message_id, ${command_name}_deposit_result"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Deposit failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute instant command using GraphQL
execute_instant() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local amount="$5"
    local destination_id="$6"
    local idempotency_key="$7"
    local group_name="$8"  # Optional group name for delegation
    
    echo_with_color $CYAN "⚡ Executing instant command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL instant send mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    if [[ -n "$idempotency_key" ]]; then
        graphql_mutation="mutation { instant(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\", destinationId: \\\"$destination_id\\\", idempotencyKey: \\\"$idempotency_key\\\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    else
        graphql_mutation="mutation { instant(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\", destinationId: \\\"$destination_id\\\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    fi
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.instant.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.instant.accountAddress // empty')
        local destination_address=$(echo "$http_response" | jq -r '.data.instant.destinationId // empty')
        local message=$(echo "$http_response" | jq -r '.data.instant.message // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.instant.idHash // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.instant.messageId // empty')
        local payment_id=$(echo "$http_response" | jq -r '.data.instant.paymentId // empty')
        local send_result=$(echo "$http_response" | jq -r '.data.instant.sendResult // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "destination_id" "$destination_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "id_hash" "$id_hash"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "payment_id" "$payment_id"
        store_command_output "$command_name" "send_result" "$send_result"
        
        echo_with_color $GREEN "    ✅ Instant payment successful!"
        echo_with_color $BLUE "      From Account: $account_address"
        echo_with_color $BLUE "      To Address: $destination_address"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Payment ID: $payment_id"
        echo_with_color $BLUE "      Send Result: $send_result"
        if [[ -n "$id_hash" ]]; then
            echo_with_color $CYAN "      ID Hash: $id_hash"
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_destination_id, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id, ${command_name}_payment_id, ${command_name}_send_result"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Instant payment failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute balance command using REST API
execute_balance() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local obligor="$5"
    local group_id="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "💰 Executing balance command via REST API: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending REST API balance request..."
    
    # Prepare query parameters
    local query_params="denomination=${denomination}&obligor=${obligor}&group_id=${group_id}"
    
    echo_with_color $BLUE "  📋 Query parameters:"
    echo_with_color $BLUE "    denomination: $denomination"
    echo_with_color $BLUE "    obligor: $obligor"
    echo_with_color $BLUE "    group_id: $group_id"
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/balance?$query_params"
    local http_response=$(curl -s -X GET "http://localhost:3002/balance?$query_params" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local private_balance=$(echo "$http_response" | jq -r '.balance.private_balance // empty')
        local public_balance=$(echo "$http_response" | jq -r '.balance.public_balance // empty')
        local decimals=$(echo "$http_response" | jq -r '.balance.decimals // empty')
        local beneficial_balance=$(echo "$http_response" | jq -r '.balance.beneficial_balance // empty')
        local beneficial_transaction_ids=$(echo "$http_response" | jq -r '.balance.beneficial_transaction_ids // []')
        local outstanding=$(echo "$http_response" | jq -r '.balance.outstanding // empty')
        # Handle both old format (counts) and new format (arrays)
        local locked_out_count
        local locked_in_count
        
        if echo "$http_response" | jq -e '.balance.locked_out' >/dev/null 2>&1; then
            # New format with arrays
            locked_out_count=$(echo "$http_response" | jq -r '.balance.locked_out | length')
            locked_in_count=$(echo "$http_response" | jq -r '.balance.locked_in | length')
        else
            # Old format with counts
            locked_out_count=$(echo "$http_response" | jq -r '.balance.locked_out_count // 0')
            locked_in_count=$(echo "$http_response" | jq -r '.balance.locked_in_count // 0')
        fi
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "private_balance" "$private_balance"
        store_command_output "$command_name" "public_balance" "$public_balance"
        store_command_output "$command_name" "decimals" "$decimals"
        store_command_output "$command_name" "beneficial_balance" "$beneficial_balance"
        store_command_output "$command_name" "outstanding" "$outstanding"
        store_command_output "$command_name" "locked_out_count" "$locked_out_count"
        store_command_output "$command_name" "locked_in_count" "$locked_in_count"
        store_command_output "$command_name" "denomination" "$denomination"
        store_command_output "$command_name" "obligor" "$obligor"
        store_command_output "$command_name" "group_id" "$group_id"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        # Store locked transactions as JSON strings for variable substitution
        if echo "$http_response" | jq -e '.balance.locked_out' >/dev/null 2>&1; then
            # New format with arrays
            local locked_out_json=$(echo "$http_response" | jq -c '.balance.locked_out')
            local locked_in_json=$(echo "$http_response" | jq -c '.balance.locked_in')
            store_command_output "$command_name" "locked_out" "$locked_out_json"
            store_command_output "$command_name" "locked_in" "$locked_in_json"
        else
            # Old format - store empty arrays
            store_command_output "$command_name" "locked_out" "[]"
            store_command_output "$command_name" "locked_in" "[]"
        fi
        
        echo_with_color $GREEN "    ✅ Balance retrieved successfully!"
        
        echo_with_color $BLUE "  📋 Balance Information:"
        echo_with_color $BLUE "      Private Balance: $private_balance"
        echo_with_color $BLUE "      Public Balance: $public_balance"
        echo_with_color $BLUE "      Decimals: $decimals"
        echo_with_color $GREEN "      Beneficial Balance: $beneficial_balance"
        echo_with_color $YELLOW "      Outstanding: $outstanding"
        echo_with_color $BLUE "      Locked Out Count: $locked_out_count"
        echo_with_color $BLUE "      Locked In Count: $locked_in_count"
        echo_with_color $BLUE "      Denomination: $denomination"
        echo_with_color $BLUE "      Obligor: $obligor"
        echo_with_color $BLUE "      Group ID: $group_id"
        echo_with_color $BLUE "      Timestamp: $timestamp"
        
        # Display locked transactions if they exist
        if [[ "$locked_out_count" -gt 0 ]]; then
            echo_with_color $YELLOW "  🔒 Locked Out Transactions:"
            if echo "$http_response" | jq -e '.balance.locked_out' >/dev/null 2>&1; then
                # New format with arrays - display each transaction as properly formatted JSON
                echo "$http_response" | jq '.balance.locked_out[]' 2>/dev/null | sed 's/^/      /'
            else
                # Old format - just show count
                echo_with_color $BLUE "      Count: $locked_out_count (detailed transactions not available in old format)"
            fi
        fi
        
        if [[ "$locked_in_count" -gt 0 ]]; then
            echo_with_color $YELLOW "  🔒 Locked In Transactions:"
            if echo "$http_response" | jq -e '.balance.locked_in' >/dev/null 2>&1; then
                # New format with arrays - display each transaction as properly formatted JSON
                echo "$http_response" | jq '.balance.locked_in[]' 2>/dev/null | sed 's/^/      /'
            else
                # Old format - just show count
                echo_with_color $BLUE "      Count: $locked_in_count (detailed transactions not available in old format)"
            fi
        fi
        
        # Display beneficial balance information
        if [[ "$beneficial_balance" != "0" && "$beneficial_balance" != "" ]]; then
            echo_with_color $GREEN "  💎 Beneficial Balance Details:"
            echo_with_color $GREEN "      Total Beneficial Value: $beneficial_balance"
            echo_with_color $CYAN "      This represents the total notional value from obligations where you are the owner"
            
            # Show beneficial transaction IDs if available
            local beneficial_ids_count=$(echo "$beneficial_transaction_ids" | jq 'length')
            if [[ "$beneficial_ids_count" -gt 0 ]]; then
                echo_with_color $YELLOW "      Beneficial Transaction ID Hashes:"
                echo "$beneficial_transaction_ids" | jq -r '.[]' | while read -r id_hash; do
                    echo_with_color $YELLOW "        ID Hash: $id_hash"
                done
            else
                echo_with_color $CYAN "      💡 Note: No locked transactions found in obligation cashflows"
                echo_with_color $CYAN "         The beneficial balance shows obligation notional values as fallback"
                echo_with_color $CYAN "         When locked transactions exist, they will show ID hashes"
                echo_with_color $CYAN "         and the beneficial balance will be calculated from those transactions"
            fi
            
            # Show beneficial transaction details if available
            if echo "$http_response" | jq -e '.balance.locked_out' >/dev/null 2>&1; then
                local beneficial_out_count=$(echo "$http_response" | jq '[.balance.locked_out[] | select(.obligation_id != "0")] | length')
                local beneficial_in_count=$(echo "$http_response" | jq '[.balance.locked_in[] | select(.obligation_id != "0")] | length')
                
                if [[ "$beneficial_out_count" -gt 0 || "$beneficial_in_count" -gt 0 ]]; then
                    echo_with_color $CYAN "      Beneficial Transactions:"
                    echo_with_color $CYAN "        Locked Out (from obligations): $beneficial_out_count"
                    echo_with_color $CYAN "        Locked In (from obligations): $beneficial_in_count"
                    
                    # Show beneficial transaction IDs with obligation information
                    if [[ "$beneficial_out_count" -gt 0 ]]; then
                        echo_with_color $YELLOW "        Beneficial Locked Out Transaction Details:"
                        echo "$http_response" | jq -r '.balance.locked_out[] | select(.obligation_id != "0") | "          ID Hash: " + .id_hash + " (Obligation ID: " + .obligation_id + ", Amount: " + .amount + ")"' 2>/dev/null | sed 's/^/        /'
                    fi
                    
                    if [[ "$beneficial_in_count" -gt 0 ]]; then
                        echo_with_color $YELLOW "        Beneficial Locked In Transaction Details:"
                        echo "$http_response" | jq -r '.balance.locked_in[] | select(.obligation_id != "0") | "          ID Hash: " + .id_hash + " (Obligation ID: " + .obligation_id + ", Amount: " + .amount + ")"' 2>/dev/null | sed 's/^/        /'
                    fi
                fi
            fi
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_private_balance, ${command_name}_public_balance, ${command_name}_decimals, ${command_name}_beneficial_balance, ${command_name}_outstanding, ${command_name}_locked_out_count, ${command_name}_locked_in_count, ${command_name}_locked_out, ${command_name}_locked_in, ${command_name}_denomination, ${command_name}_obligor, ${command_name}_group_id, ${command_name}_timestamp"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Balance retrieval failed: $error_message"
        
        return 1
    fi
}

# Function to execute accept command using GraphQL
execute_accept() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local payment_id="$4"
    local idempotency_key="$5"
    local group_name="$6"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing accept command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL accept mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="paymentId: \\\"$payment_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { accept(input: { $input_params }) { success message accountAddress idHash acceptResult messageId timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.accept.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.accept.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.accept.message // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.accept.idHash // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.accept.messageId // empty')
        local accept_result=$(echo "$http_response" | jq -r '.data.accept.acceptResult // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "id_hash" "$id_hash"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "accept_result" "$accept_result"
        
        echo_with_color $GREEN "    ✅ Accept successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      ID Hash: $id_hash"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Accept Result: $accept_result"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id, ${command_name}_accept_result"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Accept failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute create obligation command using GraphQL (with ergonomic input)
execute_create_obligation_ergonomic() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local counterpart="$4"
    local obligation_address="$5"
    local obligation_group_id="$6"
    local denomination="$7"
    local obligor="$8"
    local notional="$9"
    local expiry="${10}"
    local data="${11}"
    local initial_payments_amount="${12}"
    local initial_payments_json="${13}"
    local idempotency_key="${14}"
    local group_name="${15}"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing create obligation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create obligation mutation..."
    
    # Prepare GraphQL mutation with required fields
    local graphql_mutation
    local graphql_variables=""
    local input_params="counterpart: \\\"$counterpart\\\", denomination: \\\"$denomination\\\""
    
    # Add optional obligation_address if provided (and not "null")
    if [[ -n "$obligation_address" && "$obligation_address" != "null" ]]; then
        input_params="$input_params, obligationAddress: \\\"$obligation_address\\\""
    fi
    
    # Add optional obligation_group_id if provided (and not "null")
    if [[ -n "$obligation_group_id" && "$obligation_group_id" != "null" ]]; then
        input_params="$input_params, obligationGroupId: \\\"$obligation_group_id\\\""
    fi
    
    # Add optional fields if provided (and not "null")
    if [[ -n "$obligor" && "$obligor" != "null" ]]; then
        input_params="$input_params, obligor: \\\"$obligor\\\""
    fi
    if [[ -n "$notional" && "$notional" != "null" ]]; then
        input_params="$input_params, notional: \\\"$notional\\\""
    fi
    if [[ -n "$expiry" && "$expiry" != "null" ]]; then
        input_params="$input_params, expiry: \\\"$expiry\\\""
    fi
    if [[ -n "$data" && "$data" != "{}" && "$data" != "null" ]]; then
        # Add data as a GraphQL variable
        if [[ -n "$graphql_variables" ]]; then
            graphql_variables="$graphql_variables, "
        fi
        graphql_variables="$graphql_variables\"data\": $data"
        input_params="$input_params, data: \$data"
    fi
    if [[ -n "$initial_payments_amount" && -n "$initial_payments_json" ]]; then
        # Convert user-friendly payments to VaultPaymentInput format
        # The user-friendly format uses nested structure with payer/payee
        # We need to convert this to the flat VaultPaymentInput structure
        # Note: GraphQL converts snake_case to camelCase, so we use camelCase field names
        local vault_payments=$(echo "$initial_payments_json" | jq 'map({
            oracleAddress: null,  # Will be set by the backend
            oracleOwner: .owner,
            oracleKeySender: (.payer.key // "0"),
            oracleValueSenderSecret: (.payer.valueSecret // "0"),
            oracleKeyRecipient: (.payee.key // "0"),
            oracleValueRecipientSecret: (.payee.valueSecret // "0"),
            unlockSender: .payer.unlock,
            unlockReceiver: .payee.unlock
        })')
        
        # Create a JSON variable for initial payments
        local initial_payments_variable=$(echo "$vault_payments" | jq --arg amount "$initial_payments_amount" '{
            amount: $amount,
            payments: .
        }')
        
        # Add the variable to the GraphQL variables
        if [[ -n "$graphql_variables" ]]; then
            graphql_variables="$graphql_variables, "
        fi
        graphql_variables="$graphql_variables\"initialPayments\": $initial_payments_variable"
        
        # Add the parameter to the input
        input_params="$input_params, initialPayments: \$initialPayments"
    fi
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Build GraphQL mutation with variables if needed
    if [[ -n "$graphql_variables" ]]; then
        # Check if we have both data and initialPayments variables
        if echo "$graphql_variables" | grep -q "initialPayments" && echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput, \$data: JSON) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "initialPayments"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$data: JSON) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        else
            graphql_mutation="mutation { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        fi
        local graphql_payload="{\"query\": \"$graphql_mutation\", \"variables\": {$graphql_variables}}"
    else
        graphql_mutation="mutation { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    fi
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.createObligation.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.createObligation.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.createObligation.message // empty')
        local obligation_result=$(echo "$http_response" | jq -r '.data.createObligation.obligationResult // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.createObligation.messageId // empty')
        local contract_id=$(echo "$http_response" | jq -r '.data.createObligation.contractId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.createObligation.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.createObligation.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.createObligation.timestamp // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.createObligation.idHash // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "obligation_result" "$obligation_result"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "contract_id" "$contract_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "id_hash" "$id_hash"
        
        echo_with_color $GREEN "    ✅ Create obligation successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Contract ID: $contract_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Obligation Result: $obligation_result"
        if [[ -n "$id_hash" ]]; then
            echo_with_color $CYAN "      ID Hash: $id_hash"
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_obligation_result, ${command_name}_message_id, ${command_name}_contract_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_id_hash"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Create obligation failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute accept obligation command using GraphQL
execute_accept_obligation() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local contract_id="$4"
    local idempotency_key="$5"
    local group_name="$6"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing accept obligation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL accept obligation mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="contractId: \\\"$contract_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { acceptObligation(input: { $input_params }) { success message accountAddress obligationId acceptResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.acceptObligation.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.acceptObligation.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.acceptObligation.message // empty')
        local obligation_id=$(echo "$http_response" | jq -r '.data.acceptObligation.obligationId // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.acceptObligation.messageId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.acceptObligation.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.acceptObligation.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.acceptObligation.timestamp // empty')
        local accept_result=$(echo "$http_response" | jq -r '.data.acceptObligation.acceptResult // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "obligation_id" "$obligation_id"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "accept_result" "$accept_result"
        
        echo_with_color $GREEN "    ✅ Accept obligation successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Obligation ID: $obligation_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Accept Result: $accept_result"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_obligation_id, ${command_name}_message_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_accept_result"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Accept obligation failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute total_supply command using REST API
execute_total_supply() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local group_name="$5"  # Optional group name for delegation
    
    echo_with_color $CYAN "💰 Executing total_supply command via REST API: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending REST API total_supply request..."
    
    # Prepare query parameters
    local query_params="asset_id=${denomination}"
    
    echo_with_color $BLUE "  📋 Query parameters:"
    echo_with_color $BLUE "    asset_id: $denomination"
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/total_supply?$query_params"
    local http_response=$(curl -s -X GET "http://localhost:3002/total_supply?$query_params" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local total_supply=$(echo "$http_response" | jq -r '.total_supply // empty')
        local treasury_address=$(echo "$http_response" | jq -r '.treasury_address // empty')
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "total_supply" "$total_supply"
        store_command_output "$command_name" "treasury_address" "$treasury_address"
        store_command_output "$command_name" "denomination" "$denomination"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        echo_with_color $GREEN "    ✅ Total supply retrieved successfully!"
        
        echo_with_color $BLUE "  📋 Total Supply Information:"
        echo_with_color $BLUE "      Total Supply: $total_supply"
        echo_with_color $BLUE "      Treasury Address: $treasury_address"
        echo_with_color $BLUE "      Asset ID: $denomination"
        echo_with_color $BLUE "      Timestamp: $timestamp"
        
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_total_supply, ${command_name}_treasury_address, ${command_name}_denomination, ${command_name}_timestamp"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Total supply retrieval failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute mint command using REST API
execute_mint() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local amount="$5"
    local policy_secret="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "🪙 Executing mint command via REST API: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending REST API mint request..."
    
    # Prepare query parameters
    local query_params="asset_id=${denomination}&amount=${amount}&policy_secret=${policy_secret}"
    
    echo_with_color $BLUE "  📋 Query parameters:"
    echo_with_color $BLUE "    asset_id: $denomination"
    echo_with_color $BLUE "    amount: $amount"
    echo_with_color $BLUE "    policy_secret: ${policy_secret:0:8}..."
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/mint?$query_params"
    local http_response=$(curl -s -X POST "http://localhost:3002/mint?$query_params" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local mint_result=$(echo "$http_response" | jq -r '.mint_result // empty')
        local message_id=$(echo "$mint_result" | jq -r '.message_id // empty')
        local execution_id=$(echo "$mint_result" | jq -r '.execution_id // empty')
        local transaction_id=$(echo "$mint_result" | jq -r '.transaction_id // empty')
        local account_address=$(echo "$mint_result" | jq -r '.account_address // empty')
        local confidential_treasury=$(echo "$mint_result" | jq -r '.confidential_treasury // empty')
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "execution_id" "$execution_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "confidential_treasury" "$confidential_treasury"
        store_command_output "$command_name" "amount" "$amount"
        store_command_output "$command_name" "denomination" "$denomination"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        echo_with_color $GREEN "    ✅ Mint successful!"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Execution ID: $execution_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Account Address: $account_address"
        echo_with_color $BLUE "      Confidential Treasury: $confidential_treasury"
        echo_with_color $BLUE "      Amount: $amount"
        echo_with_color $BLUE "      Asset ID: $denomination"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_message_id, ${command_name}_execution_id, ${command_name}_transaction_id, ${command_name}_account_address, ${command_name}_confidential_treasury, ${command_name}_amount, ${command_name}_denomination, ${command_name}_timestamp"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Mint failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute burn command using REST API
execute_burn() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local amount="$5"
    local policy_secret="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "🔥 Executing burn command via REST API: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending REST API burn request..."
    
    # Prepare query parameters
    local query_params="asset_id=${denomination}&amount=${amount}&policy_secret=${policy_secret}"
    
    echo_with_color $BLUE "  📋 Query parameters:"
    echo_with_color $BLUE "    asset_id: $denomination"
    echo_with_color $BLUE "    amount: $amount"
    echo_with_color $BLUE "    policy_secret: ${policy_secret:0:8}..."
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/burn?$query_params"
    local http_response=$(curl -s -X POST "http://localhost:3002/burn?$query_params" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local burn_result=$(echo "$http_response" | jq -r '.burn_result // empty')
        local message_id=$(echo "$burn_result" | jq -r '.message_id // empty')
        local execution_id=$(echo "$burn_result" | jq -r '.execution_id // empty')
        local transaction_id=$(echo "$burn_result" | jq -r '.transaction_id // empty')
        local account_address=$(echo "$burn_result" | jq -r '.account_address // empty')
        local confidential_treasury=$(echo "$burn_result" | jq -r '.confidential_treasury // empty')
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "execution_id" "$execution_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "confidential_treasury" "$confidential_treasury"
        store_command_output "$command_name" "amount" "$amount"
        store_command_output "$command_name" "denomination" "$denomination"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        echo_with_color $GREEN "    ✅ Burn successful!"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Execution ID: $execution_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Account Address: $account_address"
        echo_with_color $BLUE "      Confidential Treasury: $confidential_treasury"
        echo_with_color $BLUE "      Amount: $amount"
        echo_with_color $BLUE "      Asset ID: $denomination"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_message_id, ${command_name}_execution_id, ${command_name}_transaction_id, ${command_name}_account_address, ${command_name}_confidential_treasury, ${command_name}_amount, ${command_name}_denomination, ${command_name}_timestamp"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Burn failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute obligations command using REST API
execute_obligations() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local group_name="$4"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing obligations command via REST API: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending REST API obligations request..."
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/obligations"
    local http_response=$(curl -s -X GET "http://localhost:3002/obligations" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local obligations_count=$(echo "$http_response" | jq -r '.obligations | length // 0')
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "obligations_count" "$obligations_count"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "obligations_json" "$(echo "$http_response" | jq -c '.obligations // []')"
        
        echo_with_color $GREEN "    ✅ Obligations retrieved successfully!"
        
        echo_with_color $BLUE "  📋 Obligations Information:"
        echo_with_color $BLUE "      Total Obligations: $obligations_count"
        echo_with_color $BLUE "      Timestamp: $timestamp"
        
        # Display obligations if they exist
        if [[ "$obligations_count" -gt 0 ]]; then
            echo_with_color $YELLOW "  🤝 Obligations Details:"
            echo "$http_response" | jq '.obligations[]' 2>/dev/null | sed 's/^/      /'
        else
            echo_with_color $YELLOW "  📭 No obligations found for this user"
        fi
        
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_obligations_count, ${command_name}_timestamp, ${command_name}_obligations_json"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Obligations retrieval failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute create obligation command using GraphQL
execute_create_obligation() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local counterpart="$4"
    local obligation_address="$5"
    local obligation_group_id="$6"
    local denomination="$7"
    local obligor="$8"
    local notional="$9"
    local expiry="${10}"
    local data="${11}"
    local initial_payments_amount="${12}"
    local initial_payments_json="${13}"
    local idempotency_key="${14}"
    local group_name="${15}"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing create obligation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create obligation mutation..."
    
    # Prepare GraphQL mutation with required fields
    local graphql_mutation
    local graphql_variables=""
    local input_params="counterpart: \\\"$counterpart\\\", denomination: \\\"$denomination\\\""
    
    # Add optional obligation_address if provided (and not "null")
    if [[ -n "$obligation_address" && "$obligation_address" != "null" ]]; then
        input_params="$input_params, obligationAddress: \\\"$obligation_address\\\""
    fi
    
    # Add optional obligation_group_id if provided (and not "null")
    if [[ -n "$obligation_group_id" && "$obligation_group_id" != "null" ]]; then
        input_params="$input_params, obligationGroupId: \\\"$obligation_group_id\\\""
    fi
    
    # Add optional fields if provided (and not "null")
    if [[ -n "$obligor" && "$obligor" != "null" ]]; then
        input_params="$input_params, obligor: \\\"$obligor\\\""
    fi
    if [[ -n "$notional" && "$notional" != "null" ]]; then
        input_params="$input_params, notional: \\\"$notional\\\""
    fi
    if [[ -n "$expiry" && "$expiry" != "null" ]]; then
        input_params="$input_params, expiry: \\\"$expiry\\\""
    fi
    if [[ -n "$data" && "$data" != "{}" && "$data" != "null" ]]; then
        # Add data as a GraphQL variable
        if [[ -n "$graphql_variables" ]]; then
            graphql_variables="$graphql_variables, "
        fi
        graphql_variables="$graphql_variables\"data\": $data"
        input_params="$input_params, data: \$data"
    fi
    if [[ -n "$initial_payments_amount" && -n "$initial_payments_json" ]]; then
        # Convert field names to match GraphQL schema (snake_case)
        # Convert numeric oracle fields to strings as required by GraphQL schema
        # Handle missing fields by providing defaults
        local converted_payments=$(echo "$initial_payments_json" | jq 'map({
            oracleAddress: (.oracle_address // "0x0000000000000000000000000000000000000000"),
            oracleOwner: (.oracle_owner // "0x0000000000000000000000000000000000000000"),
            oracleKeySender: ((.oracle_key_sender // 0) | tostring),
            oracleValueSenderSecret: ((.oracle_value_sender_secret // 0) | tostring),
            oracleKeyRecipient: ((.oracle_key_recipient // 0) | tostring),
            oracleValueRecipientSecret: ((.oracle_value_recipient_secret // 0) | tostring),
            unlockSender: .unlock_sender,
            unlockReceiver: .unlock_receiver
        })')
        
        # Create a JSON variable for initial payments
        local initial_payments_variable=$(echo "$converted_payments" | jq --arg amount "$initial_payments_amount" '{
            amount: $amount,
            payments: .
        }')
        
        # Add the variable to the GraphQL variables
        if [[ -n "$graphql_variables" ]]; then
            graphql_variables="$graphql_variables, "
        fi
        graphql_variables="$graphql_variables\"initialPayments\": $initial_payments_variable"
        
        # Add the parameter to the input
        input_params="$input_params, initialPayments: \$initialPayments"
    fi
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Build GraphQL mutation with variables if needed
    if [[ -n "$graphql_variables" ]]; then
        # Check if we have both data and initialPayments variables
        if echo "$graphql_variables" | grep -q "initialPayments" && echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput, \$data: JSON) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "initialPayments"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$data: JSON) { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        else
            graphql_mutation="mutation { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        fi
        local graphql_payload="{\"query\": \"$graphql_mutation\", \"variables\": {$graphql_variables}}"
    else
        graphql_mutation="mutation { createObligation(input: { $input_params }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
        local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    fi
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.createObligation.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.createObligation.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.createObligation.message // empty')
        local obligation_result=$(echo "$http_response" | jq -r '.data.createObligation.obligationResult // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.createObligation.messageId // empty')
        local contract_id=$(echo "$http_response" | jq -r '.data.createObligation.contractId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.createObligation.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.createObligation.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.createObligation.timestamp // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.createObligation.idHash // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "obligation_result" "$obligation_result"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "contract_id" "$contract_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "id_hash" "$id_hash"
        
        echo_with_color $GREEN "    ✅ Create obligation successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Contract ID: $contract_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Obligation Result: $obligation_result"
        if [[ -n "$id_hash" ]]; then
            echo_with_color $CYAN "      ID Hash: $id_hash"
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_obligation_result, ${command_name}_message_id, ${command_name}_contract_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_id_hash"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Create obligation failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
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
    local group_name=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].user.group")
    
    # Parse command parameters
    local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.denomination")
    local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.amount")
    local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.destination_id")
    local payment_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.payment_id")
    local idempotency_key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.idempotency_key")
    local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.denomination")
    local obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligor")
    local group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.group_id")
    
    # Parse create_obligation specific parameters
    local counterpart=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterpart")
    local obligation_address=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligation_address")
    local obligation_group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligation_group_id")
    local notional=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.notional")
    local expiry=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expiry")
    local data=$(yq eval -o json -I 0 ".commands[$command_index].parameters.data" "$COMMANDS_FILE" 2>/dev/null || echo "null")
    local initial_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initial_payments.amount")
    local initial_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.initial_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    
    # Parse accept_obligation specific parameters
    local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.contract_id")
    
    # Parse treasury specific parameters
    local policy_secret=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.policy_secret")
    
    # Apply variable substitution to parameters
    echo_with_color $CYAN "  🔄 Applying variable substitution to parameters..."
    denomination=$(substitute_variables "$denomination")
    amount=$(substitute_variables "$amount")
    destination_id=$(substitute_variables "$destination_id")
    payment_id=$(substitute_variables "$payment_id")
    idempotency_key=$(substitute_variables "$idempotency_key")
    obligor=$(substitute_variables "$obligor")
    group_id=$(substitute_variables "$group_id")
    group_name=$(substitute_variables "$group_name")
    
    # Apply variable substitution to create_obligation specific parameters
    counterpart=$(substitute_variables "$counterpart")
    obligation_address=$(substitute_variables "$obligation_address")
    obligation_group_id=$(substitute_variables "$obligation_group_id")
    notional=$(substitute_variables "$notional")
    expiry=$(substitute_variables "$expiry")
    data=$(substitute_variables "$data")
    initial_payments_amount=$(substitute_variables "$initial_payments_amount")
    
    # Apply variable substitution to accept_obligation specific parameters
    contract_id=$(substitute_variables "$contract_id")
    
    # Apply variable substitution to treasury specific parameters
    policy_secret=$(substitute_variables "$policy_secret")
    
    echo_with_color $PURPLE "🚀 Executing command $((command_index + 1)): $command_name"
    echo_with_color $BLUE "  Type: $command_type"
    echo_with_color $BLUE "  User: $user_email"
    if [[ -n "$group_name" ]]; then echo_with_color $CYAN "  Group: $group_name (delegation)"; fi
    echo_with_color $BLUE "  Parameters after substitution:"
    if [[ -n "$denomination" ]]; then echo_with_color $BLUE "    denomination: $denomination"; fi
    if [[ -n "$amount" ]]; then echo_with_color $BLUE "    amount: $amount"; fi
    if [[ -n "$destination_id" ]]; then echo_with_color $BLUE "    destination_id: $destination_id"; fi
    if [[ -n "$payment_id" ]]; then echo_with_color $BLUE "    payment_id: $payment_id"; fi
    if [[ -n "$idempotency_key" ]]; then echo_with_color $BLUE "    idempotency_key: $idempotency_key"; fi
    if [[ -n "$denomination" ]]; then echo_with_color $BLUE "    denomination: $denomination"; fi
    if [[ -n "$obligor" ]]; then echo_with_color $BLUE "    obligor: $obligor"; fi
    if [[ -n "$group_id" ]]; then echo_with_color $BLUE "    group_id: $group_id"; fi
    
    # Display create_obligation specific parameters
    if [[ -n "$counterpart" ]]; then echo_with_color $BLUE "    counterpart: $counterpart"; fi
    if [[ -n "$obligation_address" && "$obligation_address" != "null" ]]; then echo_with_color $BLUE "    obligation_address: $obligation_address"; fi
    if [[ -n "$obligation_group_id" && "$obligation_group_id" != "null" ]]; then echo_with_color $BLUE "    obligation_group_id: $obligation_group_id"; fi
    if [[ -n "$notional" && "$notional" != "null" ]]; then echo_with_color $BLUE "    notional: $notional"; fi
    if [[ -n "$expiry" && "$expiry" != "null" ]]; then echo_with_color $BLUE "    expiry: $expiry"; fi
    if [[ -n "$data" && "$data" != "null" ]]; then echo_with_color $BLUE "    data: $data"; fi
    if [[ -n "$initial_payments_amount" ]]; then echo_with_color $BLUE "    initial_payments_amount: $initial_payments_amount"; fi
    
    # Display accept_obligation specific parameters
    if [[ -n "$contract_id" ]]; then echo_with_color $BLUE "    contract_id: $contract_id"; fi
    
    # Display treasury specific parameters
    if [[ -n "$policy_secret" ]]; then echo_with_color $BLUE "    policy_secret: ${policy_secret:0:8}..."; fi
    
    # Execute command based on type
    case "$command_type" in
        "deposit")
            execute_deposit "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$idempotency_key" "$group_name"
            ;;
        "instant")
            execute_instant "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$destination_id" "$idempotency_key" "$group_name"
            ;;
        "accept")
            execute_accept "$command_name" "$user_email" "$user_password" "$payment_id" "$idempotency_key" "$group_name"
            ;;
        "balance")
            execute_balance "$command_name" "$user_email" "$user_password" "$denomination" "$obligor" "$group_id" "$group_name"
            ;;
        "create_obligation")
            execute_create_obligation_ergonomic "$command_name" "$user_email" "$user_password" "$counterpart" "$obligation_address" "$obligation_group_id" "$denomination" "$obligor" "$notional" "$expiry" "$data" "$initial_payments_amount" "$initial_payments_json" "$idempotency_key" "$group_name"
            ;;
        "accept_obligation")
            execute_accept_obligation "$command_name" "$user_email" "$user_password" "$contract_id" "$idempotency_key" "$group_name"
            ;;
        "obligations")
            execute_obligations "$command_name" "$user_email" "$user_password" "$group_name"
            ;;
        "total_supply")
            execute_total_supply "$command_name" "$user_email" "$user_password" "$denomination" "$group_name"
            ;;
        "mint")
            execute_mint "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$policy_secret" "$group_name"
            ;;
        "burn")
            execute_burn "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$policy_secret" "$group_name"
            ;;
        *)
            echo_with_color $RED "❌ Unknown command type: $command_type"
            return 1
            ;;
    esac
}

# Function to validate commands.yaml file
validate_commands_file() {
    echo_with_color $CYAN "Validating $YAML_FILE..."
    
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
        echo_with_color $RED "No commands defined in $YAML_FILE"
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
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                ;;
            "instant")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.destination_id")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
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
                local payment_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.payment_id")
                
                if [[ -z "$payment_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.payment_id' field"
                    return 1
                fi
                ;;
            "balance")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                local obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligor")
                local group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.group_id")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                
                if [[ -z "$obligor" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.obligor' field"
                    return 1
                fi
                
                if [[ -z "$group_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.group_id' field"
                    return 1
                fi
                ;;
            "create_obligation")
                local counterpart=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterpart")
                local obligation_address=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligation_address")
                local obligation_group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligation_group_id")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                
                if [[ -z "$counterpart" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterpart' field"
                    return 1
                fi
                
                # obligation_address and obligation_group_id are now optional - no validation needed
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                ;;
            "accept_obligation")
                local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.contract_id")
                
                if [[ -z "$contract_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.contract_id' field"
                    return 1
                fi
                ;;
            "obligations")
                # Obligations command doesn't require any specific parameters
                # It will list all obligations for the authenticated user
                ;;
            "total_supply")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                ;;
            "mint")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                local policy_secret=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.policy_secret")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                
                if [[ -z "$policy_secret" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.policy_secret' field"
                    return 1
                fi
                ;;
            "burn")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                local policy_secret=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.policy_secret")
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                
                if [[ -z "$policy_secret" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.policy_secret' field"
                    return 1
                fi
                ;;
            *)
                echo_with_color $RED "Error: Command '$command_name' has unsupported type: '$command_type'"
                echo_with_color $YELLOW "Supported types: deposit, instant, accept, balance, create_obligation, accept_obligation, obligations, total_supply, mint, burn"
                return 1
                ;;
        esac
    done
    
    echo_with_color $GREEN "Commands file validation passed"
    return 0
}

# Function to show commands status
show_commands_status() {
    echo_with_color $CYAN "YieldFabric GraphQL Commands Execution Status"
    echo "====================================================="
    
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
        echo_with_color $BLUE "   GraphQL endpoint available at: http://localhost:3002/graphql"
    else
        echo_with_color $RED "   Payments Service (port 3002) - Not running"
        echo_with_color $YELLOW "   Start the payments service first: cd ../yieldfabric-payments && cargo run"
        return 1
    fi
    
    # Check commands file
    echo_with_color $BLUE "Commands File:"
    if [[ -f "$COMMANDS_FILE" ]]; then
        echo_with_color $GREEN "   $YAML_FILE - Found"
        
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
        echo_with_color $RED "   $YAML_FILE - Not found"
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
    echo_with_color $CYAN "🚀 Executing all commands from commands.yaml using GraphQL mutations..."
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
        echo_with_color $BLUE "   GraphQL endpoint will be available at: http://localhost:3002/graphql"
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
    echo_with_color $CYAN "YieldFabric GraphQL Commands Execution Script"
    echo "====================================================="
    echo ""
    echo "Usage: $0 [yaml_file] [command]"
    echo ""
    echo "Arguments:"
    echo_with_color $GREEN "  yaml_file" " - YAML file containing commands (default: commands.yaml)"
    echo_with_color $GREEN "  command" "   - Command to execute (default: execute)"
    echo ""
    echo "Commands:"
    echo_with_color $GREEN "  execute" "  - Execute all commands from the specified YAML file using GraphQL mutations"
    echo_with_color $GREEN "  status" "   - Show current status and requirements"
    echo_with_color $GREEN "  validate" " - Validate YAML file structure"
    echo_with_color $GREEN "  variables" " - Show currently stored variables for command chaining"
    echo_with_color $GREEN "  help" "     - Show this help message"
    echo ""
    echo "Requirements:"
    echo "  • yieldfabric-auth service running on port 3000"
    echo "  • yieldfabric-payments service running on port 3002 with GraphQL endpoint"
    echo "  • yq YAML parser installed"
    echo "  • commands.yaml file with commands configuration"
    echo ""
    echo "API Endpoints Used:"
    echo "  • deposit: Creates token deposits via GraphQL"
    echo "  • instantSend: Sends instant payments via GraphQL"
    echo "  • accept: Accepts payments using id_hash via GraphQL"
    echo "  • balance: Retrieves balance information via REST API"
    echo "  • createObligation: Creates obligations via GraphQL"
    echo "  • acceptObligation: Accepts obligations using contract_id via GraphQL"
    echo "  • obligations: Lists all obligations for a user via REST API"
    echo "  • total_supply: Gets total supply of a treasury token via REST API"
    echo "  • mint: Mints new treasury tokens via REST API"
    echo "  • burn: Burns treasury tokens via REST API"
    echo ""
    echo "Commands.yaml Structure:"
    echo "  • commands: array of commands with type, user, and parameters"
    echo "  • Supported command types: deposit, instant, accept, balance, create_obligation, accept_obligation, obligations, total_supply, mint, burn"
    echo "  • Each command must have user.id, user.password, and parameters"
    echo "  • Variables can be referenced using: \$command_name.field_name"
    echo ""
    echo "Variable Substitution Examples:"
    echo "  • id_hash: \$issuer_send_1.id_hash    # Use id_hash from 'issuer_send_1' command"
    echo "  • amount: \$previous_deposit.amount   # Use amount from 'previous_deposit' command"
    echo "  • message_id: \$instant_pay.message_id # Use message_id from 'instant_pay' command"
    echo "  • private_balance: \$issuer_balance.private_balance # Use private_balance from 'issuer_balance' command"
    echo "  • beneficial_balance: \$issuer_balance.beneficial_balance # Use beneficial_balance from 'issuer_balance' command"
    echo "  • outstanding: \$issuer_balance.outstanding # Use outstanding amount from 'issuer_balance' command"
    echo "  • denomination: \$issuer_balance.denomination # Use denomination from 'issuer_balance' command"
    echo "  • locked_out: \$issuer_balance.locked_out # Use locked_out transactions from 'issuer_balance' command"
    echo "  • locked_in: \$issuer_balance.locked_in # Use locked_in transactions from 'issuer_balance' command"
    echo "  • obligations_count: \$admin2_balance_2.obligations_count # Use obligations count from 'admin2_balance_2' command"
    echo "  • obligations_json: \$admin2_balance_2.obligations_json # Use obligations JSON from 'admin2_balance_2' command"
    echo "  • total_supply: \$total_supply_1.total_supply # Use total supply from 'total_supply_1' command"
    echo "  • treasury_address: \$total_supply_1.treasury_address # Use treasury address from 'total_supply_1' command"
    echo "  • mint_amount: \$mint_1.amount # Use amount from 'mint_1' command"
    echo "  • burn_transaction_id: \$burn_1.transaction_id # Use transaction ID from 'burn_1' command"
    echo ""
    echo "Examples:"
    echo "  $0                    # Execute commands from commands.yaml"
    echo "  $0 treasury.yaml      # Execute commands from treasury.yaml"
    echo "  $0 commands.yaml status     # Check requirements for commands.yaml"
    echo "  $0 treasury.yaml validate   # Validate treasury.yaml structure"
    echo "  $0 commands.yaml variables  # Show stored variables"
    echo ""
    echo_with_color $YELLOW "For first-time users, run: $0"
}

# Main execution
# Parse arguments: first argument is YAML file, second is command
# Handle special case where first argument is a command (help, status, etc.)
if [[ "$1" == "help" || "$1" == "-h" || "$1" == "--help" || "$1" == "status" || "$1" == "variables" ]]; then
    YAML_FILE="commands.yaml"
    COMMAND="$1"
else
    YAML_FILE="${1:-commands.yaml}"
    COMMAND="${2:-execute}"
fi

# Update COMMANDS_FILE with the parsed YAML file
COMMANDS_FILE="$SCRIPT_DIR/$YAML_FILE"

case "$COMMAND" in
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
        echo_with_color $RED "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
