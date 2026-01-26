#!/bin/bash

# YieldFabric Command Executors Module
# Contains functions for executing different types of commands

# Service URLs - can be overridden by environment variables
# PAY_SERVICE_URL="${PAY_SERVICE_URL:-http://localhost:3002}"
# AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:3000}"
PAY_SERVICE_URL="${PAY_SERVICE_URL:-https://pay.yieldfabric.io}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth.yieldfabric.io}"

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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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

# Function to execute withdraw command using GraphQL
execute_withdraw() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local amount="$5"
    local idempotency_key="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "💸 Executing withdraw command via GraphQL: $command_name"
    
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
    echo_with_color $BLUE "  📤 Sending GraphQL withdraw mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    if [[ -n "$idempotency_key" ]]; then
        graphql_mutation="mutation { withdraw(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\", idempotencyKey: \\\"$idempotency_key\\\" }) { success message accountAddress withdrawResult messageId timestamp } }"
    else
        graphql_mutation="mutation { withdraw(input: { assetId: \\\"$denomination\\\", amount: \\\"$amount\\\" }) { success message accountAddress withdrawResult messageId timestamp } }"
    fi
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📥 Response received:"
    echo_with_color $BLUE "    $http_response"
    
    # Check if the response contains success
    if echo "$http_response" | jq -e '.data.withdraw.success' > /dev/null 2>&1; then
        local message_id=$(echo "$http_response" | jq -r '.data.withdraw.messageId // "N/A"')
        local account_address=$(echo "$http_response" | jq -r '.data.withdraw.accountAddress // "N/A"')
        local withdraw_result=$(echo "$http_response" | jq -r '.data.withdraw.withdrawResult // "N/A"')
        local timestamp=$(echo "$http_response" | jq -r '.data.withdraw.timestamp // "N/A"')
        
        echo_with_color $GREEN "    ✅ Withdraw successful!"
        echo_with_color $GREEN "      Message ID: $message_id"
        echo_with_color $GREEN "      Account Address: $account_address"
        echo_with_color $GREEN "      Withdraw Result: $withdraw_result"
        echo_with_color $GREEN "      Timestamp: $timestamp"
        
        # Store command output for variable substitution
        store_command_output "$command_name" "$http_response"
        
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Withdraw failed: $error_message"
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
    local obligor="$8"  # Optional obligor
    local group_name="$9"  # Optional group name for delegation
    
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
    
    # Prepare GraphQL mutation with optional obligor
    local graphql_mutation
    local mutation_input="assetId: \\\"$denomination\\\", amount: \\\"$amount\\\", destinationId: \\\"$destination_id\\\""
    
    # Add obligor if provided
    if [[ -n "$obligor" && "$obligor" != "null" ]]; then
        mutation_input="$mutation_input, obligor: \\\"$obligor\\\""
    fi
    
    # Add idempotency key if provided
    if [[ -n "$idempotency_key" ]]; then
        mutation_input="$mutation_input, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { instant(input: { $mutation_input }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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
    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/balance?$query_params"
    local http_response=$(curl -s -X GET "${PAY_SERVICE_URL}/balance?$query_params" \
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
    local amount="$5"
    local idempotency_key="$6"
    local group_name="$7"  # Optional group name for delegation
    
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
    
    # Add amount if provided (for partial retrieval)
    if [[ -n "$amount" && "$amount" != "null" ]]; then
        input_params="$input_params, amount: $amount"
        echo_with_color $CYAN "  💰 Partial acceptance: amount = $amount"
    else
        echo_with_color $CYAN "  💰 Full acceptance (no amount specified)"
    fi
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { accept(input: { $input_params }) { success message accountAddress idHash acceptResult messageId timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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
        if [[ -n "$amount" && "$amount" != "null" ]]; then
            store_command_output "$command_name" "amount" "$amount"
        fi
        
        echo_with_color $GREEN "    ✅ Accept successful!"
        echo_with_color $BLUE "      Account: $account_address"
        echo_with_color $BLUE "      ID Hash: $id_hash"
        if [[ -n "$amount" && "$amount" != "null" ]]; then
            echo_with_color $CYAN "      Amount (Partial): $amount"
        fi
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Accept Result: $accept_result"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        if [[ -n "$amount" && "$amount" != "null" ]]; then
            echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id, ${command_name}_accept_result, ${command_name}_amount"
        else
            echo_with_color $CYAN "        ${command_name}_account_address, ${command_name}_message, ${command_name}_id_hash, ${command_name}_message_id, ${command_name}_accept_result"
        fi
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Accept failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}

# Function to execute accept_all command using GraphQL
# NOTE: This only processes PAYABLES (where the user is the RECEIVER/PAYEE)
# It will NOT process PAYOUTS (where the user is the PAYER)
execute_accept_all() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local denomination="$4"
    local obligor="$5"
    local idempotency_key="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing accept_all command via GraphQL: $command_name"
    echo_with_color $YELLOW "   ⚠️  Note: Only accepting PAYABLES (where user is the RECEIVER)"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL accept_all mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="denomination: \\\"$denomination\\\""
    
    # Add obligor if provided (optional parameter)
    if [[ -n "$obligor" && "$obligor" != "null" ]]; then
        input_params="$input_params, obligor: \\\"$obligor\\\""
    fi
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { acceptAll(input: { $input_params }) { success message totalPayments acceptedCount failedCount acceptedPayments { paymentId amount messageId transactionId } failedPayments { paymentId amount error } timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.acceptAll.success // empty')
    if [[ "$success" == "true" ]]; then
        local message=$(echo "$http_response" | jq -r '.data.acceptAll.message // empty')
        local total_payments=$(echo "$http_response" | jq -r '.data.acceptAll.totalPayments // 0')
        local accepted_count=$(echo "$http_response" | jq -r '.data.acceptAll.acceptedCount // 0')
        local failed_count=$(echo "$http_response" | jq -r '.data.acceptAll.failedCount // 0')
        local timestamp=$(echo "$http_response" | jq -r '.data.acceptAll.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "total_payments" "$total_payments"
        store_command_output "$command_name" "accepted_count" "$accepted_count"
        store_command_output "$command_name" "failed_count" "$failed_count"
        store_command_output "$command_name" "denomination" "$denomination"
        store_command_output "$command_name" "obligor" "$obligor"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        echo_with_color $GREEN "    ✅ Accept All PAYABLES successful!"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Total PAYABLE Payments Found: $total_payments"
        echo_with_color $GREEN "      Accepted (as PAYEE/RECEIVER): $accepted_count"
        echo_with_color $BLUE "      Denomination: $denomination"
        if [[ -n "$obligor" && "$obligor" != "null" ]]; then
            echo_with_color $BLUE "      Obligor (Payer) Filter: $obligor"
        else
            echo_with_color $BLUE "      Obligor (Payer) Filter: Any"
        fi
        
        if [[ "$failed_count" -gt 0 ]]; then
            echo_with_color $YELLOW "      Failed: $failed_count"
        fi
        
        # Display accepted payments details
        if [[ "$accepted_count" -gt 0 ]]; then
            echo_with_color $GREEN "  ✅ Accepted Payments:"
            echo "$http_response" | jq -r '.data.acceptAll.acceptedPayments[]? | "      • Payment ID: \(.paymentId), Amount: \(.amount), Message ID: \(.messageId)"' 2>/dev/null
        fi
        
        # Display failed payments details
        if [[ "$failed_count" -gt 0 ]]; then
            echo_with_color $YELLOW "  ⚠️  Failed Payments:"
            echo "$http_response" | jq -r '.data.acceptAll.failedPayments[]? | "      • Payment ID: \(.paymentId), Amount: \(.amount), Error: \(.error)"' 2>/dev/null
        fi
        
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_message, ${command_name}_total_payments, ${command_name}_accepted_count, ${command_name}_failed_count, ${command_name}_denomination, ${command_name}_obligor, ${command_name}_timestamp"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Accept All failed: $error_message"
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
    local contract_id="${16}"  # Optional contract ID - if not provided, one will be auto-generated
    
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
    local input_params="counterpart: \\\"$counterpart\\\""
    
    # Add denomination if provided (optional - only required with payments)
    if [[ -n "$denomination" && "$denomination" != "null" ]]; then
        input_params="$input_params, denomination: \\\"$denomination\\\""
    fi
    
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
    if [[ -n "$initial_payments_amount" && "$initial_payments_amount" != "null" && -n "$initial_payments_json" && "$initial_payments_json" != "null" ]]; then
        # Convert user-friendly payments to VaultPaymentInput format
        local vault_payments=$(echo "$initial_payments_json" | jq 'map({
            oracleAddress: null,
            oracleOwner: .owner,
            oracleKeySender: (.payer.key // "0"),
            oracleValueSenderSecret: (.payer.valueSecret // "0"),
            oracleKeyRecipient: (.payee.key // "0"),
            oracleValueRecipientSecret: (.payee.valueSecret // "0"),
            unlockSender: .payer.unlock,
            unlockReceiver: .payee.unlock,
            linearVesting: (.linear_vesting // false)
        })')
        
        local initial_payments_variable=$(echo "$vault_payments" | jq --arg amount "$initial_payments_amount" '{
            amount: $amount,
            payments: .
        }')
        
        if [[ -n "$graphql_variables" ]]; then
            graphql_variables="$graphql_variables, "
        fi
        graphql_variables="$graphql_variables\"initialPayments\": $initial_payments_variable"
        input_params="$input_params, initialPayments: \$initialPayments"
    fi
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Add optional contract_id if provided (and not "null")
    if [[ -n "$contract_id" && "$contract_id" != "null" ]]; then
        input_params="$input_params, contractId: \\\"$contract_id\\\""
    fi
    
    # Build GraphQL mutation with variables if needed
    if [[ -n "$graphql_variables" ]]; then
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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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

# Function to execute list_groups command using Auth Service
execute_list_groups() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local group_name="$4"  # Optional group name for delegation
    
    echo_with_color $CYAN "👥 Executing list_groups command via Auth Service: $command_name"
    
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
    echo_with_color $BLUE "  📤 Sending request to Auth Service..."
    
    # Make request to auth service to get user's groups
    echo_with_color $BLUE "  🌐 Making request to: ${AUTH_SERVICE_URL}/auth/groups/user"
    local http_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Response received:"
    echo_with_color $BLUE "    $http_response"
    
    # Check if request was successful
    if echo "$http_response" | jq -e '. | type == "array"' >/dev/null 2>&1; then
        local group_count=$(echo "$http_response" | jq '. | length')
        echo_with_color $GREEN "    ✅ List groups successful!"
        echo_with_color $GREEN "    📊 Found $group_count groups for user"
        
        # Display groups in a formatted way
        if [[ $group_count -gt 0 ]]; then
            echo_with_color $CYAN "    📋 Groups:"
            echo "$http_response" | jq -r '.[] | "      • \(.name) (ID: \(.id), Type: \(.group_type), Active: \(.is_active))"'
        else
            echo_with_color $YELLOW "    📋 No groups found for this user"
        fi
        
        # Store command outputs for variable substitution
        store_command_output "${command_name}_groups" "$http_response"
        store_command_output "${command_name}_group_count" "$group_count"
        
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_groups, ${command_name}_group_count"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ List groups failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        return 1
    fi
}
