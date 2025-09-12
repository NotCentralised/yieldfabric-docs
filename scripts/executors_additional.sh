#!/bin/bash

# YieldFabric Additional Command Executors Module
# Contains additional executor functions that were too large for the main executors.sh

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
