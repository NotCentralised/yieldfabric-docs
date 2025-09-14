#!/bin/bash

# YieldFabric Additional Command Executors Module
# Contains additional executor functions that were too large for the main executors.sh

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

# Function to execute create obligation swap command using GraphQL
execute_create_obligation_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local counterparty="$5"
    local obligation_id="$6"
    local deadline="$7"
    local expected_payments_amount="$8"
    local expected_payments_denomination="$9"
    local expected_payments_obligor="${10}"
    local expected_payments_json="${11}"
    local idempotency_key="${12}"
    local group_name="${13}"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing create obligation swap command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create obligation swap mutation..."
    
    # Debug: Show parsed values
    echo_with_color $PURPLE "  🔍 DEBUG: Parsed values:"
    echo_with_color $PURPLE "    expected_payments_amount: '$expected_payments_amount'"
    echo_with_color $PURPLE "    expected_payments_denomination: '$expected_payments_denomination'"
    echo_with_color $PURPLE "    expected_payments_obligor: '$expected_payments_obligor'"
    echo_with_color $PURPLE "    expected_payments_json: '$expected_payments_json'"
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\", counterparty: \\\"$counterparty\\\", obligationId: \\\"$obligation_id\\\", deadline: \\\"$deadline\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Add expected_payments if provided (check for null values from YAML parsing)
    if [[ -n "$expected_payments_amount" && "$expected_payments_amount" != "null" && -n "$expected_payments_json" && "$expected_payments_json" != "[]" && "$expected_payments_json" != "null" ]]; then
        local expected_payments_input="expectedPayments: { amount: \\\"$expected_payments_amount\\\""
        
        if [[ -n "$expected_payments_denomination" && "$expected_payments_denomination" != "null" ]]; then
            expected_payments_input="$expected_payments_input, denomination: \\\"$expected_payments_denomination\\\""
        fi
        
        if [[ -n "$expected_payments_obligor" && "$expected_payments_obligor" != "null" ]]; then
            expected_payments_input="$expected_payments_input, obligor: \\\"$expected_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local payments_array=$(echo "$expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "1") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "1") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "1") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "2") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\" }"' | tr '\n' ',' | sed 's/,$//')
        expected_payments_input="$expected_payments_input, payments: [$payments_array] }"
        
        input_params="$input_params, $expected_payments_input"
    fi
    
    graphql_mutation="mutation { createObligationSwap(input: { $input_params }) { success message accountAddress swapId counterparty obligationId swapResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Debug: Show the final input_params
    echo_with_color $PURPLE "  🔍 DEBUG: Final input_params:"
    echo_with_color $PURPLE "    $input_params"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    # Check if request was successful
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "❌ Failed to send GraphQL request"
        return 1
    fi
    
    # Parse and display response
    local success=$(echo "$http_response" | jq -r '.data.createObligationSwap.success // false')
    local message=$(echo "$http_response" | jq -r '.data.createObligationSwap.message // "No message"')
    local swap_id_result=$(echo "$http_response" | jq -r '.data.createObligationSwap.swapId // "No swap ID"')
    local message_id=$(echo "$http_response" | jq -r '.data.createObligationSwap.messageId // "No message ID"')
    
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Create obligation swap completed successfully"
        echo_with_color $BLUE "  📊 Swap ID: $swap_id_result"
        echo_with_color $BLUE "  📊 Message ID: $message_id"
        echo_with_color $BLUE "  📊 Message: $message"
    else
        echo_with_color $RED "❌ Create obligation swap failed"
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "  📊 Error: $error_message"
        echo_with_color $BLUE "  📊 Full response: $http_response"
        return 1
    fi
    
    # Store command output for variable substitution
    store_command_output "$command_name" "$http_response"
    
    return 0
}

# Function to execute complete swap command using GraphQL
execute_complete_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local expected_payments_amount="$5"
    local expected_payments_denomination="$6"
    local expected_payments_obligor="$7"
    local expected_payments_json="$8"
    local idempotency_key="$9"
    local group_name="${10}"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing complete swap command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL complete swap mutation..."
    
    # Debug: Show parsed values
    echo_with_color $PURPLE "  🔍 DEBUG: Parsed values:"
    echo_with_color $PURPLE "    expected_payments_amount: '$expected_payments_amount'"
    echo_with_color $PURPLE "    expected_payments_denomination: '$expected_payments_denomination'"
    echo_with_color $PURPLE "    expected_payments_obligor: '$expected_payments_obligor'"
    echo_with_color $PURPLE "    expected_payments_json: '$expected_payments_json'"
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Add expected_payments if provided (check for null values from YAML parsing)
    if [[ -n "$expected_payments_amount" && "$expected_payments_amount" != "null" && -n "$expected_payments_json" && "$expected_payments_json" != "[]" && "$expected_payments_json" != "null" ]]; then
        local expected_payments_input="expectedPayments: { amount: \\\"$expected_payments_amount\\\""
        
        if [[ -n "$expected_payments_denomination" && "$expected_payments_denomination" != "null" ]]; then
            expected_payments_input="$expected_payments_input, denomination: \\\"$expected_payments_denomination\\\""
        fi
        
        if [[ -n "$expected_payments_obligor" && "$expected_payments_obligor" != "null" ]]; then
            expected_payments_input="$expected_payments_input, obligor: \\\"$expected_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local payments_array=$(echo "$expected_payments_json" | jq -r '.[] | "{ oracleAddress: null, oracleOwner: null, oracleKeySender: \\\"" + (.payer.key // "1") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "1") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "1") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "2") + "\\\", unlockSender: " + (if .payer.unlock then "\\\"" + .payer.unlock + "\\\"" else "null" end) + ", unlockReceiver: " + (if .payee.unlock then "\\\"" + .payee.unlock + "\\\"" else "null" end) + " }"' | tr '\n' ',' | sed 's/,$//')
        expected_payments_input="$expected_payments_input, payments: [$payments_array] }"
        
        input_params="$input_params, $expected_payments_input"
    fi
    
    graphql_mutation="mutation { completeSwap(input: { $input_params }) { success message accountAddress swapId completeResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    # Check if request was successful
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "❌ Failed to send GraphQL request"
        return 1
    fi
    
    # Parse and display response
    local success=$(echo "$http_response" | jq -r '.data.completeSwap.success // false')
    local message=$(echo "$http_response" | jq -r '.data.completeSwap.message // "No message"')
    local swap_id_result=$(echo "$http_response" | jq -r '.data.completeSwap.swapId // "No swap ID"')
    local message_id=$(echo "$http_response" | jq -r '.data.completeSwap.messageId // "No message ID"')
    
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Complete swap completed successfully"
        echo_with_color $BLUE "  📊 Swap ID: $swap_id_result"
        echo_with_color $BLUE "  📊 Message ID: $message_id"
        echo_with_color $BLUE "  📊 Message: $message"
    else
        echo_with_color $RED "❌ Complete swap failed"
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "  📊 Error: $error_message"
        echo_with_color $BLUE "  📊 Full response: $http_response"
        return 1
    fi
    
    # Store command output for variable substitution
    store_command_output "$command_name" "$http_response"
    
    return 0
}

# Function to execute cancel swap command using GraphQL
execute_cancel_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local key="$5"
    local value="$6"
    local idempotency_key="$7"
    local group_name="$8"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing cancel swap command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL cancel swap mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\", key: \\\"$key\\\", value: \\\"$value\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { cancelSwap(input: { $input_params }) { success message accountAddress swapId cancelResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    # Check if request was successful
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "❌ Failed to send GraphQL request"
        return 1
    fi
    
    # Parse and display response
    local success=$(echo "$http_response" | jq -r '.data.cancelSwap.success // false')
    local message=$(echo "$http_response" | jq -r '.data.cancelSwap.message // "No message"')
    local swap_id_result=$(echo "$http_response" | jq -r '.data.cancelSwap.swapId // "No swap ID"')
    local message_id=$(echo "$http_response" | jq -r '.data.cancelSwap.messageId // "No message ID"')
    
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Cancel swap completed successfully"
        echo_with_color $BLUE "  📊 Swap ID: $swap_id_result"
        echo_with_color $BLUE "  📊 Message ID: $message_id"
        echo_with_color $BLUE "  📊 Message: $message"
    else
        echo_with_color $RED "❌ Cancel swap failed"
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "  📊 Error: $error_message"
        echo_with_color $BLUE "  📊 Full response: $http_response"
        return 1
    fi
    
    # Store command output for variable substitution
    store_command_output "$command_name" "$http_response"
    
    return 0
}


# Function to execute create obligation swap command using GraphQL (simplified approach)
execute_create_obligation_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local counterparty="$5"
    local obligation_id="$6"
    local deadline="$7"
    local expected_payments_amount="$8"
    local expected_payments_denomination="$9"
    local expected_payments_obligor="${10}"
    local expected_payments_json="${11}"
    local idempotency_key="${12}"
    local group_name="${13}"
    
    echo "✅ Executing create obligation swap ergonomic command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    if [[ -n "$group_name" && "$group_name" != "null" ]]; then
        echo "  🏢 Using delegation JWT for group: $group_name"
    fi
    
    # Build expected payments input for ergonomic version using GraphQL variables
    local expected_payments_variable=""
    if [[ -n "$expected_payments_amount" && "$expected_payments_amount" != "null" ]]; then
        # Convert user-friendly payments to VaultPaymentInput format using the same approach as create_obligation
        local vault_payments="[]"
        if [[ -n "$expected_payments_json" && "$expected_payments_json" != "null" && "$expected_payments_json" != "{}" ]]; then
            echo "  🔍 DEBUG: expected_payments_json = $expected_payments_json"
            vault_payments=$(echo "$expected_payments_json" | jq '. // [] | map({
                oracleAddress: null,
                oracleOwner: .owner,
                oracleKeySender: (.payer.key // "1"),
                oracleValueSenderSecret: (.payer.valueSecret // "1"),
                oracleKeyRecipient: (.payee.key // "1"),
                oracleValueRecipientSecret: (.payee.valueSecret // "2"),
                unlockSender: .payer.unlock,
                unlockReceiver: .payee.unlock
            })')
            echo "  🔍 DEBUG: vault_payments = $vault_payments"
        fi
        
        # Debug: Show the values being passed to jq
        echo "  🔍 DEBUG: Values for jq:"
        echo "    expected_payments_amount: '$expected_payments_amount'"
        echo "    expected_payments_denomination: '$expected_payments_denomination'"
        echo "    expected_payments_obligor: '$expected_payments_obligor'"
        
           # Create the expected payments variable (InitialPaymentsInput has amount, denomination, obligor, and payments)
           expected_payments_variable=$(echo "$vault_payments" | jq --arg amount "$expected_payments_amount" --arg denomination "$expected_payments_denomination" --arg obligor "$expected_payments_obligor" '{
               amount: $amount,
               denomination: (if $denomination != "" and $denomination != "null" then $denomination else null end),
               obligor: (if $obligor != "" and $obligor != "null" then $obligor else null end),
               payments: .
           }')
        echo "  🔍 DEBUG: expected_payments_variable = $expected_payments_variable"
    fi
    
    # Build GraphQL mutation with variables
    local mutation="mutation"
    local variables=""
    if [[ -n "$expected_payments_variable" && "$expected_payments_variable" != "null" && "$expected_payments_variable" != "{}" ]]; then
    mutation="$mutation(\$expectedPayments: InitialPaymentsInput)"
    variables="\"expectedPayments\": $expected_payments_variable"
fi

mutation="$mutation { createObligationSwap(input: { swapId: \"$swap_id\", counterparty: \"$counterparty\", obligationId: \"$obligation_id\", deadline: \"$deadline\", idempotencyKey: \"$idempotency_key\""
    if [[ -n "$expected_payments_variable" && "$expected_payments_variable" != "null" && "$expected_payments_variable" != "{}" ]]; then
        mutation="$mutation, expectedPayments: \$expectedPayments"
    fi
    mutation="$mutation }) { success message accountAddress swapId counterparty obligationId swapResult messageId transactionId signature timestamp } }"
    
    echo "  📤 Sending GraphQL create obligation swap ergonomic mutation..."
    echo "  📋 GraphQL mutation:"
    echo "    $mutation"
    
    # Make GraphQL request using proper JSON construction
    local request_body
    if [[ -n "$variables" ]]; then
        request_body=$(jq -n --arg query "$mutation" --argjson variables "$expected_payments_variable" '{
            query: $query,
            variables: {
                expectedPayments: $variables
            }
        }')
    else
        request_body=$(jq -n --arg query "$mutation" '{
            query: $query
        }')
    fi
    
    echo "  🔍 DEBUG: request_body = $request_body"
    
    local response=$(curl -s -X POST http://localhost:3002/graphql \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$request_body")
    
    echo "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    
    # Check for errors in response
    local error_message=$(echo "$response" | jq -r ".errors[0].message // empty")
    if [[ -n "$error_message" && "$error_message" != "null" ]]; then
        echo "❌ Create obligation swap failed"
        echo "  📊 Error: $error_message"
        echo "  📊 Full response: $response"
        return 1
    fi
    
    # Extract success status
    local success=$(echo "$response" | jq -r ".data.createObligationSwap.success // false")
    if [[ "$success" == "true" ]]; then
        echo "✅ Create obligation swap successful"
        local message=$(echo "$response" | jq -r ".data.createObligationSwap.message // \"No message\"")
        local swap_id=$(echo "$response" | jq -r ".data.createObligationSwap.swapId // \"No swap ID\"")
        local message_id=$(echo "$response" | jq -r ".data.createObligationSwap.messageId // \"No message ID\"")
        echo "  📊 Message: $message"
        echo "  📊 Swap ID: $swap_id"
        echo "  📊 Message ID: $message_id"
    else
        echo "❌ Create obligation swap failed"
        echo "  📊 Full response: $response"
        return 1
    fi
}

# Function to execute create payment swap command using GraphQL
execute_create_payment_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local counterparty="$5"
    local deadline="$6"
    local initial_payments_amount="$7"
    local initial_payments_denomination="$8"
    local initial_payments_obligor="$9"
    local initial_payments_json="${10}"
    local expected_payments_amount="${11}"
    local expected_payments_denomination="${12}"
    local expected_payments_obligor="${13}"
    local expected_payments_json="${14}"
    local idempotency_key="${15}"
    local group_name="${16}"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing create payment swap command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL create payment swap mutation..."
    
    # Debug: Show parsed values
    echo_with_color $PURPLE "  🔍 DEBUG: Parsed values:"
    echo_with_color $PURPLE "    initial_payments_amount: '$initial_payments_amount'"
    echo_with_color $PURPLE "    initial_payments_denomination: '$initial_payments_denomination'"
    echo_with_color $PURPLE "    initial_payments_obligor: '$initial_payments_obligor'"
    echo_with_color $PURPLE "    initial_payments_json: '$initial_payments_json'"
    echo_with_color $PURPLE "    expected_payments_amount: '$expected_payments_amount'"
    echo_with_color $PURPLE "    expected_payments_denomination: '$expected_payments_denomination'"
    echo_with_color $PURPLE "    expected_payments_obligor: '$expected_payments_obligor'"
    echo_with_color $PURPLE "    expected_payments_json: '$expected_payments_json'"
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\", counterparty: \\\"$counterparty\\\", deadline: \\\"$deadline\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Add initial_payments if provided (check for null values from YAML parsing)
    if [[ -n "$initial_payments_amount" && "$initial_payments_amount" != "null" && -n "$initial_payments_json" && "$initial_payments_json" != "[]" && "$initial_payments_json" != "null" ]]; then
        local initial_payments_input="initialPayments: { amount: \\\"$initial_payments_amount\\\""
        
        if [[ -n "$initial_payments_denomination" && "$initial_payments_denomination" != "null" ]]; then
            initial_payments_input="$initial_payments_input, denomination: \\\"$initial_payments_denomination\\\""
        fi
        
        if [[ -n "$initial_payments_obligor" && "$initial_payments_obligor" != "null" ]]; then
            initial_payments_input="$initial_payments_input, obligor: \\\"$initial_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local payments_array=$(echo "$initial_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "1") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "1") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "1") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "2") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\" }"' | tr '\n' ',' | sed 's/,$//')
        initial_payments_input="$initial_payments_input, payments: [$payments_array] }"
        
        input_params="$input_params, $initial_payments_input"
    fi
    
    # Add expected_payments if provided (check for null values from YAML parsing)
    if [[ -n "$expected_payments_amount" && "$expected_payments_amount" != "null" && -n "$expected_payments_json" && "$expected_payments_json" != "[]" && "$expected_payments_json" != "null" ]]; then
        local expected_payments_input="expectedPayments: { amount: \\\"$expected_payments_amount\\\""
        
        if [[ -n "$expected_payments_denomination" && "$expected_payments_denomination" != "null" ]]; then
            expected_payments_input="$expected_payments_input, denomination: \\\"$expected_payments_denomination\\\""
        fi
        
        if [[ -n "$expected_payments_obligor" && "$expected_payments_obligor" != "null" ]]; then
            expected_payments_input="$expected_payments_input, obligor: \\\"$expected_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local payments_array=$(echo "$expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "1") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "1") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "1") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "2") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\" }"' | tr '\n' ',' | sed 's/,$//')
        expected_payments_input="$expected_payments_input, payments: [$payments_array] }"
        
        input_params="$input_params, $expected_payments_input"
    fi
    
    graphql_mutation="mutation { createPaymentSwap(input: { $input_params }) { success message accountAddress swapId counterparty paymentSwapResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Debug: Show the final input_params
    echo_with_color $PURPLE "  🔍 DEBUG: Final input_params:"
    echo_with_color $PURPLE "    $input_params"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: http://localhost:3002/graphql"
    local http_response=$(curl -s -X POST "http://localhost:3002/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    # Check if request was successful
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "❌ Failed to send GraphQL request"
        return 1
    fi
    
    # Parse and display response
    local success=$(echo "$http_response" | jq -r '.data.createPaymentSwap.success // false')
    local message=$(echo "$http_response" | jq -r '.data.createPaymentSwap.message // "No message"')
    local swap_id_result=$(echo "$http_response" | jq -r '.data.createPaymentSwap.swapId // "No swap ID"')
    local message_id=$(echo "$http_response" | jq -r '.data.createPaymentSwap.messageId // "No message ID"')
    
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Create payment swap completed successfully"
        echo_with_color $BLUE "  📊 Swap ID: $swap_id_result"
        echo_with_color $BLUE "  📊 Message ID: $message_id"
        echo_with_color $BLUE "  📊 Message: $message"
        
        # Store command output for variable substitution
        store_command_output "$command_name" "swap_id" "$swap_id_result"
        store_command_output "$command_name" "message_id" "$message_id"
        
        return 0
    else
        echo_with_color $RED "❌ Create payment swap failed"
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "  📊 Error: $error_message"
        echo_with_color $RED "  📊 Full response: $http_response"
        return 1
    fi
}
