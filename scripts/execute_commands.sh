#!/bin/bash

# YieldFabric GraphQL Commands Execution Script
# Reads commands.yaml and executes each command sequentially using GraphQL mutations
# Gets JWT tokens for users and makes GraphQL API calls based on command type

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
    local asset_id="$4"
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
        graphql_mutation="mutation { deposit(input: { assetId: \\\"$asset_id\\\", amount: \\\"$amount\\\", idempotencyKey: \\\"$idempotency_key\\\" }) { success message accountAddress depositResult messageId timestamp } }"
    else
        graphql_mutation="mutation { deposit(input: { assetId: \\\"$asset_id\\\", amount: \\\"$amount\\\" }) { success message accountAddress depositResult messageId timestamp } }"
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
    local asset_id="$4"
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
        graphql_mutation="mutation { instant(input: { assetId: \\\"$asset_id\\\", amount: \\\"$amount\\\", destinationId: \\\"$destination_id\\\", idempotencyKey: \\\"$idempotency_key\\\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    else
        graphql_mutation="mutation { instant(input: { assetId: \\\"$asset_id\\\", amount: \\\"$amount\\\", destinationId: \\\"$destination_id\\\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
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
            echo_with_color $CYAN "      This represents the total notional value from deals where you are the owner"
            
            # Show beneficial transaction IDs if available
            local beneficial_ids_count=$(echo "$beneficial_transaction_ids" | jq 'length')
            if [[ "$beneficial_ids_count" -gt 0 ]]; then
                echo_with_color $YELLOW "      Beneficial Transaction ID Hashes:"
                echo "$beneficial_transaction_ids" | jq -r '.[]' | while read -r id_hash; do
                    echo_with_color $YELLOW "        ID Hash: $id_hash"
                done
            else
                echo_with_color $CYAN "      💡 Note: No locked transactions found in deal cashflows"
                echo_with_color $CYAN "         The beneficial balance shows deal notional values as fallback"
                echo_with_color $CYAN "         When locked transactions exist, they will show ID hashes"
                echo_with_color $CYAN "         and the beneficial balance will be calculated from those transactions"
            fi
            
            # Show beneficial transaction details if available
            if echo "$http_response" | jq -e '.balance.locked_out' >/dev/null 2>&1; then
                local beneficial_out_count=$(echo "$http_response" | jq '[.balance.locked_out[] | select(.deal_id != "0")] | length')
                local beneficial_in_count=$(echo "$http_response" | jq '[.balance.locked_in[] | select(.deal_id != "0")] | length')
                
                if [[ "$beneficial_out_count" -gt 0 || "$beneficial_in_count" -gt 0 ]]; then
                    echo_with_color $CYAN "      Beneficial Transactions:"
                    echo_with_color $CYAN "        Locked Out (from deals): $beneficial_out_count"
                    echo_with_color $CYAN "        Locked In (from deals): $beneficial_in_count"
                    
                    # Show beneficial transaction IDs with deal information
                    if [[ "$beneficial_out_count" -gt 0 ]]; then
                        echo_with_color $YELLOW "        Beneficial Locked Out Transaction Details:"
                        echo "$http_response" | jq -r '.balance.locked_out[] | select(.deal_id != "0") | "          ID Hash: " + .id_hash + " (Deal ID: " + .deal_id + ", Amount: " + .amount + ")"' 2>/dev/null | sed 's/^/        /'
                    fi
                    
                    if [[ "$beneficial_in_count" -gt 0 ]]; then
                        echo_with_color $YELLOW "        Beneficial Locked In Transaction Details:"
                        echo "$http_response" | jq -r '.balance.locked_in[] | select(.deal_id != "0") | "          ID Hash: " + .id_hash + " (Deal ID: " + .deal_id + ", Amount: " + .amount + ")"' 2>/dev/null | sed 's/^/        /'
                    fi
                fi
            fi
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_private_balance, ${command_name}_public_balance, ${command_name}_decimals, ${command_name}_beneficial_balance, ${command_name}_locked_out_count, ${command_name}_locked_in_count, ${command_name}_locked_out, ${command_name}_locked_in, ${command_name}_denomination, ${command_name}_obligor, ${command_name}_group_id, ${command_name}_timestamp"
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

# Function to execute create deal command using GraphQL (with ergonomic input)
execute_create_deal_ergonomic() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local counterpart="$4"
    local deal_address="$5"
    local deal_group_id="$6"
    local denomination="$7"
    local obligor="$8"
    local notional="$9"
    local expiry="${10}"
    local data="${11}"
    local initial_payments_amount="${12}"
    local initial_payments_json="${13}"
    local idempotency_key="${14}"
    local group_name="${15}"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing create deal command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create deal mutation..."
    
    # Prepare GraphQL mutation with required fields
    local graphql_mutation
    local graphql_variables=""
    local input_params="counterpart: \\\"$counterpart\\\", denomination: \\\"$denomination\\\""
    
    # Add optional deal_address if provided (and not "null")
    if [[ -n "$deal_address" && "$deal_address" != "null" ]]; then
        input_params="$input_params, dealAddress: \\\"$deal_address\\\""
    fi
    
    # Add optional deal_group_id if provided (and not "null")
    if [[ -n "$deal_group_id" && "$deal_group_id" != "null" ]]; then
        input_params="$input_params, dealGroupId: \\\"$deal_group_id\\\""
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
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput, \$data: JSON) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "initialPayments"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$data: JSON) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        else
            graphql_mutation="mutation { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        fi
        local graphql_payload="{\"query\": \"$graphql_mutation\", \"variables\": {$graphql_variables}}"
    else
        graphql_mutation="mutation { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
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
    local success=$(echo "$http_response" | jq -r '.data.createDeal.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.createDeal.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.createDeal.message // empty')
        local deal_result=$(echo "$http_response" | jq -r '.data.createDeal.dealResult // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.createDeal.messageId // empty')
        local contract_id=$(echo "$http_response" | jq -r '.data.createDeal.contractId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.createDeal.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.createDeal.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.createDeal.timestamp // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.createDeal.idHash // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "deal_result" "$deal_result"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "contract_id" "$contract_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "id_hash" "$id_hash"
        
        echo_with_color $GREEN "    ✅ Create deal successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Contract ID: $contract_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Deal Result: $deal_result"
        if [[ -n "$id_hash" ]]; then
            echo_with_color $CYAN "      ID Hash: $id_hash"
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_deal_result, ${command_name}_message_id, ${command_name}_contract_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_id_hash"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Create deal failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute accept deal command using GraphQL
execute_accept_deal() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local contract_id="$4"
    local idempotency_key="$5"
    local group_name="$6"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing accept deal command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL accept deal mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="contractId: \\\"$contract_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { acceptDeal(input: { $input_params }) { success message accountAddress dealId acceptResult messageId transactionId signature timestamp } }"
    
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
    local success=$(echo "$http_response" | jq -r '.data.acceptDeal.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.acceptDeal.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.acceptDeal.message // empty')
        local deal_id=$(echo "$http_response" | jq -r '.data.acceptDeal.dealId // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.acceptDeal.messageId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.acceptDeal.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.acceptDeal.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.acceptDeal.timestamp // empty')
        local accept_result=$(echo "$http_response" | jq -r '.data.acceptDeal.acceptResult // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "deal_id" "$deal_id"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "accept_result" "$accept_result"
        
        echo_with_color $GREEN "    ✅ Accept deal successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Deal ID: $deal_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Accept Result: $accept_result"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_deal_id, ${command_name}_message_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_accept_result"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Accept deal failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute deals command using REST API
execute_deals() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local group_name="$4"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing deals command via REST API: $command_name"
    
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
    echo_with_color $BLUE "  📤 Sending REST API deals request..."
    
    # Send REST API request to payments service
    echo_with_color $BLUE "  🌐 Making REST API request to: http://localhost:3002/deals"
    local http_response=$(curl -s -X GET "http://localhost:3002/deals" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Raw REST API response: '$http_response'"
    
    # Parse REST API response
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        local deals_count=$(echo "$http_response" | jq -r '.deals | length // 0')
        local timestamp=$(echo "$http_response" | jq -r '.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "deals_count" "$deals_count"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "deals_json" "$(echo "$http_response" | jq -c '.deals // []')"
        
        echo_with_color $GREEN "    ✅ Deals retrieved successfully!"
        
        echo_with_color $BLUE "  📋 Deals Information:"
        echo_with_color $BLUE "      Total Deals: $deals_count"
        echo_with_color $BLUE "      Timestamp: $timestamp"
        
        # Display deals if they exist
        if [[ "$deals_count" -gt 0 ]]; then
            echo_with_color $YELLOW "  🤝 Deals Details:"
            echo "$http_response" | jq '.deals[]' 2>/dev/null | sed 's/^/      /'
        else
            echo_with_color $YELLOW "  📭 No deals found for this user"
        fi
        
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_deals_count, ${command_name}_timestamp, ${command_name}_deals_json"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.error // "Unknown error"')
        echo_with_color $RED "    ❌ Deals retrieval failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute create deal command using GraphQL
execute_create_deal() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local counterpart="$4"
    local deal_address="$5"
    local deal_group_id="$6"
    local denomination="$7"
    local obligor="$8"
    local notional="$9"
    local expiry="${10}"
    local data="${11}"
    local initial_payments_amount="${12}"
    local initial_payments_json="${13}"
    local idempotency_key="${14}"
    local group_name="${15}"  # Optional group name for delegation
    
    echo_with_color $CYAN "🤝 Executing create deal command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create deal mutation..."
    
    # Prepare GraphQL mutation with required fields
    local graphql_mutation
    local graphql_variables=""
    local input_params="counterpart: \\\"$counterpart\\\", denomination: \\\"$denomination\\\""
    
    # Add optional deal_address if provided (and not "null")
    if [[ -n "$deal_address" && "$deal_address" != "null" ]]; then
        input_params="$input_params, dealAddress: \\\"$deal_address\\\""
    fi
    
    # Add optional deal_group_id if provided (and not "null")
    if [[ -n "$deal_group_id" && "$deal_group_id" != "null" ]]; then
        input_params="$input_params, dealGroupId: \\\"$deal_group_id\\\""
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
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput, \$data: JSON) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "initialPayments"; then
            graphql_mutation="mutation(\$initialPayments: InitialPaymentsInput) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        elif echo "$graphql_variables" | grep -q "data"; then
            graphql_mutation="mutation(\$data: JSON) { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        else
            graphql_mutation="mutation { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
        fi
        local graphql_payload="{\"query\": \"$graphql_mutation\", \"variables\": {$graphql_variables}}"
    else
        graphql_mutation="mutation { createDeal(input: { $input_params }) { success message accountAddress dealResult messageId contractId transactionId signature timestamp idHash } }"
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
    local success=$(echo "$http_response" | jq -r '.data.createDeal.success // empty')
    if [[ "$success" == "true" ]]; then
        local account_address=$(echo "$http_response" | jq -r '.data.createDeal.accountAddress // empty')
        local message=$(echo "$http_response" | jq -r '.data.createDeal.message // empty')
        local deal_result=$(echo "$http_response" | jq -r '.data.createDeal.dealResult // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.createDeal.messageId // empty')
        local contract_id=$(echo "$http_response" | jq -r '.data.createDeal.contractId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.createDeal.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.createDeal.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.createDeal.timestamp // empty')
        local id_hash=$(echo "$http_response" | jq -r '.data.createDeal.idHash // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "deal_result" "$deal_result"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "contract_id" "$contract_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        store_command_output "$command_name" "id_hash" "$id_hash"
        
        echo_with_color $GREEN "    ✅ Create deal successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      Contract ID: $contract_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Deal Result: $deal_result"
        if [[ -n "$id_hash" ]]; then
            echo_with_color $CYAN "      ID Hash: $id_hash"
        fi
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_deal_result, ${command_name}_message_id, ${command_name}_contract_id, ${command_name}_transaction_id, ${command_name}_signature, ${command_name}_timestamp, ${command_name}_id_hash"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Create deal failed: $error_message"
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
    local asset_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.asset_id")
    local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.amount")
    local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.destination_id")
    local payment_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.payment_id")
    local idempotency_key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.idempotency_key")
    local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.denomination")
    local obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligor")
    local group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.group_id")
    
    # Parse create_deal specific parameters
    local counterpart=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterpart")
    local deal_address=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.deal_address")
    local deal_group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.deal_group_id")
    local notional=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.notional")
    local expiry=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expiry")
    local data=$(yq eval -o json -I 0 ".commands[$command_index].parameters.data" "$COMMANDS_FILE" 2>/dev/null || echo "null")
    local initial_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initial_payments.amount")
    local initial_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.initial_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    
    # Parse accept_deal specific parameters
    local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.contract_id")
    
    # Apply variable substitution to parameters
    echo_with_color $CYAN "  🔄 Applying variable substitution to parameters..."
    asset_id=$(substitute_variables "$asset_id")
    amount=$(substitute_variables "$amount")
    destination_id=$(substitute_variables "$destination_id")
    payment_id=$(substitute_variables "$payment_id")
    idempotency_key=$(substitute_variables "$idempotency_key")
    denomination=$(substitute_variables "$denomination")
    obligor=$(substitute_variables "$obligor")
    group_id=$(substitute_variables "$group_id")
    group_name=$(substitute_variables "$group_name")
    
    # Apply variable substitution to create_deal specific parameters
    counterpart=$(substitute_variables "$counterpart")
    deal_address=$(substitute_variables "$deal_address")
    deal_group_id=$(substitute_variables "$deal_group_id")
    notional=$(substitute_variables "$notional")
    expiry=$(substitute_variables "$expiry")
    data=$(substitute_variables "$data")
    initial_payments_amount=$(substitute_variables "$initial_payments_amount")
    
    # Apply variable substitution to accept_deal specific parameters
    contract_id=$(substitute_variables "$contract_id")
    
    echo_with_color $PURPLE "🚀 Executing command $((command_index + 1)): $command_name"
    echo_with_color $BLUE "  Type: $command_type"
    echo_with_color $BLUE "  User: $user_email"
    if [[ -n "$group_name" ]]; then echo_with_color $CYAN "  Group: $group_name (delegation)"; fi
    echo_with_color $BLUE "  Parameters after substitution:"
    if [[ -n "$asset_id" ]]; then echo_with_color $BLUE "    asset_id: $asset_id"; fi
    if [[ -n "$amount" ]]; then echo_with_color $BLUE "    amount: $amount"; fi
    if [[ -n "$destination_id" ]]; then echo_with_color $BLUE "    destination_id: $destination_id"; fi
    if [[ -n "$payment_id" ]]; then echo_with_color $BLUE "    payment_id: $payment_id"; fi
    if [[ -n "$idempotency_key" ]]; then echo_with_color $BLUE "    idempotency_key: $idempotency_key"; fi
    if [[ -n "$denomination" ]]; then echo_with_color $BLUE "    denomination: $denomination"; fi
    if [[ -n "$obligor" ]]; then echo_with_color $BLUE "    obligor: $obligor"; fi
    if [[ -n "$group_id" ]]; then echo_with_color $BLUE "    group_id: $group_id"; fi
    
    # Display create_deal specific parameters
    if [[ -n "$counterpart" ]]; then echo_with_color $BLUE "    counterpart: $counterpart"; fi
    if [[ -n "$deal_address" && "$deal_address" != "null" ]]; then echo_with_color $BLUE "    deal_address: $deal_address"; fi
    if [[ -n "$deal_group_id" && "$deal_group_id" != "null" ]]; then echo_with_color $BLUE "    deal_group_id: $deal_group_id"; fi
    if [[ -n "$notional" && "$notional" != "null" ]]; then echo_with_color $BLUE "    notional: $notional"; fi
    if [[ -n "$expiry" && "$expiry" != "null" ]]; then echo_with_color $BLUE "    expiry: $expiry"; fi
    if [[ -n "$data" && "$data" != "null" ]]; then echo_with_color $BLUE "    data: $data"; fi
    if [[ -n "$initial_payments_amount" ]]; then echo_with_color $BLUE "    initial_payments_amount: $initial_payments_amount"; fi
    
    # Display accept_deal specific parameters
    if [[ -n "$contract_id" ]]; then echo_with_color $BLUE "    contract_id: $contract_id"; fi
    
    # Execute command based on type
    case "$command_type" in
        "deposit")
            execute_deposit "$command_name" "$user_email" "$user_password" "$asset_id" "$amount" "$idempotency_key" "$group_name"
            ;;
        "instant")
            execute_instant "$command_name" "$user_email" "$user_password" "$asset_id" "$amount" "$destination_id" "$idempotency_key" "$group_name"
            ;;
        "accept")
            execute_accept "$command_name" "$user_email" "$user_password" "$payment_id" "$idempotency_key" "$group_name"
            ;;
        "balance")
            execute_balance "$command_name" "$user_email" "$user_password" "$denomination" "$obligor" "$group_id" "$group_name"
            ;;
        "create_deal")
            execute_create_deal_ergonomic "$command_name" "$user_email" "$user_password" "$counterpart" "$deal_address" "$deal_group_id" "$denomination" "$obligor" "$notional" "$expiry" "$data" "$initial_payments_amount" "$initial_payments_json" "$idempotency_key" "$group_name"
            ;;
        "accept_deal")
            execute_accept_deal "$command_name" "$user_email" "$user_password" "$contract_id" "$idempotency_key" "$group_name"
            ;;
        "deals")
            execute_deals "$command_name" "$user_email" "$user_password" "$group_name"
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
                local asset_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.asset_id")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                
                if [[ -z "$asset_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.asset_id' field"
                    return 1
                fi
                
                if [[ -z "$amount" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.amount' field"
                    return 1
                fi
                ;;
            "instant")
                local asset_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.asset_id")
                local amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.amount")
                local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.destination_id")
                
                if [[ -z "$asset_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.asset_id' field"
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
            "create_deal")
                local counterpart=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterpart")
                local deal_address=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.deal_address")
                local deal_group_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.deal_group_id")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                
                if [[ -z "$counterpart" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterpart' field"
                    return 1
                fi
                
                # deal_address and deal_group_id are now optional - no validation needed
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
                    return 1
                fi
                ;;
            "accept_deal")
                local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.contract_id")
                
                if [[ -z "$contract_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.contract_id' field"
                    return 1
                fi
                ;;
            "deals")
                # Deals command doesn't require any specific parameters
                # It will list all deals for the authenticated user
                ;;
            *)
                echo_with_color $RED "Error: Command '$command_name' has unsupported type: '$command_type'"
                echo_with_color $YELLOW "Supported types: deposit, instant, accept, balance, create_deal, accept_deal, deals"
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
    echo_with_color $CYAN "YieldFabric GraphQL Commands Execution Script"
    echo "====================================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo_with_color $GREEN "  execute" "  - Execute all commands from commands.yaml using GraphQL mutations"
    echo_with_color $GREEN "  status" "   - Show current status and requirements"
    echo_with_color $GREEN "  validate" " - Validate commands.yaml file structure"
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
    echo "  • createDeal: Creates deals via GraphQL"
    echo "  • acceptDeal: Accepts deals using contract_id via GraphQL"
    echo "  • deals: Lists all deals for a user via REST API"
    echo ""
    echo "Commands.yaml Structure:"
    echo "  • commands: array of commands with type, user, and parameters"
    echo "  • Supported command types: deposit, instant, accept, balance, create_deal, accept_deal, deals"
    echo "  • Each command must have user.id, user.password, and parameters"
    echo "  • Variables can be referenced using: \$command_name.field_name"
    echo ""
    echo "Variable Substitution Examples:"
    echo "  • id_hash: \$issuer_send_1.id_hash    # Use id_hash from 'issuer_send_1' command"
    echo "  • amount: \$previous_deposit.amount   # Use amount from 'previous_deposit' command"
    echo "  • message_id: \$instant_pay.message_id # Use message_id from 'instant_pay' command"
    echo "  • private_balance: \$issuer_balance.private_balance # Use private_balance from 'issuer_balance' command"
    echo "  • beneficial_balance: \$issuer_balance.beneficial_balance # Use beneficial_balance from 'issuer_balance' command"
    echo "  • denomination: \$issuer_balance.denomination # Use denomination from 'issuer_balance' command"
    echo "  • locked_out: \$issuer_balance.locked_out # Use locked_out transactions from 'issuer_balance' command"
    echo "  • locked_in: \$issuer_balance.locked_in # Use locked_in transactions from 'issuer_balance' command"
    echo "  • deals_count: \$admin2_balance_2.deals_count # Use deals count from 'admin2_balance_2' command"
    echo "  • deals_json: \$admin2_balance_2.deals_json # Use deals JSON from 'admin2_balance_2' command"
    echo ""
    echo "Examples:"
    echo "  $0 execute    # Execute all commands via GraphQL"
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
