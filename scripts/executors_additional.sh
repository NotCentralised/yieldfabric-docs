#!/bin/bash

# YieldFabric Additional Command Executors Module
# Contains additional executor functions that were too large for the main executors.sh

# Service URLs - can be overridden by environment variables
PAY_SERVICE_URL="${PAY_SERVICE_URL:-https://pay.yieldfabric.io}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth.yieldfabric.io}"

# Function to execute composed operation command using GraphQL
execute_composed_operation() {
    local command_index="$1"
    local command_name="$2"
    local user_email="$3"
    local user_password="$4"
    local group_name="$5"  # Optional group name for delegation
    
    echo_with_color $CYAN "🔄 Executing composed operation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    
    # Parse composed operation specific parameters
    local idempotency_key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.idempotency_key")
    idempotency_key=$(substitute_variables "$idempotency_key")
    
    # Get the number of operations
    local operations_count=$(yq eval ".commands[$command_index].parameters.operations | length" "$COMMANDS_FILE")
    
    echo_with_color $BLUE "  📋 Composed Operation Details:"
    echo_with_color $BLUE "    Operation Count: $operations_count"
    echo_with_color $BLUE "    Idempotency Key: $idempotency_key"
    echo_with_color $CYAN "    ℹ️  Account address will be extracted from JWT token"
    
    # Build operations array for GraphQL
    local operations_graphql="["
    
    for ((op_index=0; op_index<$operations_count; op_index++)); do
        echo_with_color $CYAN "  🔍 Processing operation $((op_index + 1))/$operations_count"
        
        # Parse operation type and data
        local op_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.operations[$op_index].operation_type")
        local op_data_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.operations[$op_index].operation_data" "$COMMANDS_FILE")
        
        # Apply variable substitution to operation data
        op_data_json=$(substitute_variables "$op_data_json")
        
        echo_with_color $BLUE "    Operation Type: $op_type"
        echo_with_color $PURPLE "    Operation Data: $op_data_json"
        
        # Convert operation_type to GraphQL OperationType enum (capitalize first letter of each word)
        local op_type_graphql
        case "$op_type" in
            "complete_swap") op_type_graphql="CompleteSwap" ;;
            "transfer_obligation") op_type_graphql="TransferObligation" ;;
            "accept_obligation") op_type_graphql="AcceptObligation" ;;
            "cancel_obligation") op_type_graphql="CancelObligation" ;;
            "create_obligation") op_type_graphql="CreateObligation" ;;
            "deposit") op_type_graphql="Deposit" ;;
            "instant"|"instant_send") op_type_graphql="InstantSend" ;;
            "withdraw") op_type_graphql="Withdraw" ;;
            "create_swap") op_type_graphql="CreateSwap" ;;
            "cancel_swap") op_type_graphql="CancelSwap" ;;
            *) 
                echo_with_color $RED "    ❌ Unknown operation type: $op_type"
                return 1
                ;;
        esac
        
        # Build operation item (escape the JSON properly for GraphQL)
        local op_data_escaped=$(echo "$op_data_json" | jq -c . | sed 's/"/\\"/g')
        
        if [[ $op_index -gt 0 ]]; then
            operations_graphql="$operations_graphql, "
        fi
        
        # Add operation to array with proper JSON escaping
        operations_graphql="$operations_graphql{ operationType: $op_type_graphql, operationData: \"$op_data_escaped\" }"
    done
    
    operations_graphql="$operations_graphql]"
    
    echo_with_color $BLUE "  📤 Sending GraphQL composed operation mutation..."
    
    # Build the GraphQL mutation using variables to avoid escaping issues
    local graphql_mutation='mutation($input: ComposedOperationInput!) { 
        executeComposedOperations(input: $input) { 
            success 
            message 
            messageId 
            composedId 
            accountAddress 
            operationCount 
            operationResults {
                operationType
                success
                message
                paymentId
                contractId
                amount
                idHash
                destinationId
                obligationId
                swapId
            }
        } 
    }'
    
    # Build the variables JSON (no account_address - extracted from JWT)
    local variables_json=$(jq -n \
        --arg idempotency "$idempotency_key" \
        --argjson operations_count "$operations_count" \
        '{
            input: {
                idempotencyKey: $idempotency,
                operations: []
            }
        }')
    
    # Build operations array properly
    local operations_array="["
    for ((op_index=0; op_index<$operations_count; op_index++)); do
        local op_type=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.operations[$op_index].operation_type")
        local op_data_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.operations[$op_index].operation_data" "$COMMANDS_FILE")
        op_data_json=$(substitute_variables "$op_data_json")
        
        # Transform payment data for composed operations (convert nested payer/payee to flat VaultPayment structure)
        # This matches what the single operation does, but for composed operations that go through MQ/serde
        if [[ "$op_type" == "create_obligation" ]]; then
            # Check if initial_payments.payments exists and has payer/payee structure
            if echo "$op_data_json" | jq -e '.initial_payments.payments[0].payer' >/dev/null 2>&1; then
                echo_with_color $CYAN "    🔄 Transforming initial_payments for create_obligation operation"
                # Transform the payments array from nested structure to flat VaultPayment structure
                op_data_json=$(echo "$op_data_json" | jq '.initial_payments.payments |= map({
                    oracle_address: .oracle_address,
                    oracle_owner: .owner,
                    oracle_key_sender: (.payer.key // "0"),
                    oracle_value_sender_secret: (.payer.valueSecret // "0"),
                    oracle_key_recipient: (.payee.key // "0"),
                    oracle_value_recipient_secret: (.payee.valueSecret // "0"),
                    unlock_sender: .payer.unlock,
                    unlock_receiver: .payee.unlock,
                    linear_vesting: .linear_vesting
                })')
            fi
        elif [[ "$op_type" == "create_swap" ]]; then
            # First, transform nested initiator/counterparty structure to flat structure if needed
            if echo "$op_data_json" | jq -e '.initiator' >/dev/null 2>&1; then
                echo_with_color $CYAN "    🔄 Flattening nested initiator/counterparty structure for create_swap operation"
                # Build object with only non-null fields using jq's del function to remove nulls
                # Handle both initial_payments and expected_payments for initiator (initial_payments is an alias)
                op_data_json=$(echo "$op_data_json" | jq '{
                    swap_id: .swap_id,
                    counterparty: (.counterparty.id // .counterparty),
                    initiator_obligation_ids: (.initiator.obligation_ids // []),
                    initiator_expected_payments: (.initiator.expected_payments // .initiator.initial_payments),
                    counterparty_obligation_ids: (.counterparty.obligation_ids // []),
                    counterparty_expected_payments: (.counterparty.expected_payments // .counterparty.initial_payments),
                    deadline: .deadline
                } | with_entries(select(.value != null))')
            fi
            
            # Transform initiator expected payments if they have payer/payee structure
            if echo "$op_data_json" | jq -e '.initiator_expected_payments.payments[0].payer' >/dev/null 2>&1; then
                echo_with_color $CYAN "    🔄 Transforming initiator_expected_payments for create_swap operation"
                op_data_json=$(echo "$op_data_json" | jq '.initiator_expected_payments.payments |= map({
                    oracle_address: .oracle_address,
                    oracle_owner: .owner,
                    oracle_key_sender: (.payer.key // "0"),
                    oracle_value_sender_secret: (.payer.valueSecret // "0"),
                    oracle_key_recipient: (.payee.key // "0"),
                    oracle_value_recipient_secret: (.payee.valueSecret // "0"),
                    unlock_sender: .payer.unlock,
                    unlock_receiver: .payee.unlock,
                    linear_vesting: .linear_vesting
                })')
            fi
            # Transform counterparty expected payments if they have payer/payee structure
            if echo "$op_data_json" | jq -e '.counterparty_expected_payments.payments[0].payer' >/dev/null 2>&1; then
                echo_with_color $CYAN "    🔄 Transforming counterparty_expected_payments for create_swap operation"
                op_data_json=$(echo "$op_data_json" | jq '.counterparty_expected_payments.payments |= map({
                    oracle_address: .oracle_address,
                    oracle_owner: .owner,
                    oracle_key_sender: (.payer.key // "0"),
                    oracle_value_sender_secret: (.payer.valueSecret // "0"),
                    oracle_key_recipient: (.payee.key // "0"),
                    oracle_value_recipient_secret: (.payee.valueSecret // "0"),
                    unlock_sender: .payer.unlock,
                    unlock_receiver: .payee.unlock,
                    linear_vesting: .linear_vesting
                })')
            fi
        fi
        
        # Convert to GraphQL enum
        local op_type_graphql
        case "$op_type" in
            "complete_swap") op_type_graphql="CompleteSwap" ;;
            "transfer_obligation") op_type_graphql="TransferObligation" ;;
            "accept_obligation") op_type_graphql="AcceptObligation" ;;
            "cancel_obligation") op_type_graphql="CancelObligation" ;;
            "create_obligation") op_type_graphql="CreateObligation" ;;
            "deposit") op_type_graphql="Deposit" ;;
            "instant"|"instant_send") op_type_graphql="InstantSend" ;;
            "withdraw") op_type_graphql="Withdraw" ;;
            "create_swap") op_type_graphql="CreateSwap" ;;
            "cancel_swap") op_type_graphql="CancelSwap" ;;
        esac
        
        if [[ $op_index -gt 0 ]]; then
            operations_array="$operations_array, "
        fi
        
        # Build operation JSON with proper structure
        operations_array="$operations_array{\"operationType\": \"$op_type_graphql\", \"operationData\": $op_data_json}"
    done
    operations_array="$operations_array]"
    
    # Update variables with operations array
    variables_json=$(echo "$variables_json" | jq --argjson ops "$operations_array" '.input.operations = $ops')
    
    # Build final GraphQL payload
    local graphql_payload=$(jq -n \
        --arg query "$graphql_mutation" \
        --argjson variables "$variables_json" \
        '{
            query: $query,
            variables: $variables
        }')
    
    echo_with_color $PURPLE "  🔍 DEBUG: GraphQL Payload:"
    echo_with_color $PURPLE "    $(echo "$graphql_payload" | jq -c .)"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    echo_with_color $BLUE "  📡 Raw GraphQL response: '$http_response'"
    
    # Parse GraphQL response
    local success=$(echo "$http_response" | jq -r '.data.executeComposedOperations.success // empty')
    if [[ "$success" == "true" ]]; then
        local message=$(echo "$http_response" | jq -r '.data.executeComposedOperations.message // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.executeComposedOperations.messageId // empty')
        local composed_id=$(echo "$http_response" | jq -r '.data.executeComposedOperations.composedId // empty')
        local account_address=$(echo "$http_response" | jq -r '.data.executeComposedOperations.accountAddress // empty')
        local operation_count=$(echo "$http_response" | jq -r '.data.executeComposedOperations.operationCount // empty')
        
        # Store top-level outputs for variable substitution in future commands
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "composed_id" "$composed_id"
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "operation_count" "$operation_count"
        
        # Extract and store individual operation results for composed operation variable access
        # This enables syntax like: $composed_command_name-0.payment_id, $composed_command_name-1.contract_id
        echo_with_color $CYAN "      🔍 Extracting individual operation results..."
        
        # Check if operationResults array exists in response
        local has_operation_results=$(echo "$http_response" | jq -e '.data.executeComposedOperations.operationResults' >/dev/null 2>&1 && echo "true" || echo "false")
        
        if [[ "$has_operation_results" == "true" ]]; then
            local operation_results=$(echo "$http_response" | jq -c '.data.executeComposedOperations.operationResults // []')
            local result_count=$(echo "$operation_results" | jq 'length')
            
            echo_with_color $CYAN "      📊 Found $result_count operation results to store"
            
            for ((op_idx=0; op_idx<$result_count; op_idx++)); do
                local op_result=$(echo "$operation_results" | jq -c ".[$op_idx]")
                local op_type=$(echo "$op_result" | jq -r '.operationType // empty')
                
                echo_with_color $BLUE "        • Operation $op_idx ($op_type): storing outputs..."
                
                # Extract all fields from this operation result and store with format: command_name-op_index.field_name
                # Common fields across all operations
                local op_message=$(echo "$op_result" | jq -r '.message // empty')
                local op_success=$(echo "$op_result" | jq -r '.success // empty')
                
                [[ -n "$op_message" ]] && store_command_output "${command_name}[${op_idx}]" "message" "$op_message"
                [[ -n "$op_success" ]] && store_command_output "${command_name}[${op_idx}]" "success" "$op_success"
                
                # Operation-specific fields
                case "$op_type" in
                    "Deposit")
                        local payment_id=$(echo "$op_result" | jq -r '.paymentId // empty')
                        local contract_id=$(echo "$op_result" | jq -r '.contractId // empty')
                        local amount=$(echo "$op_result" | jq -r '.amount // empty')
                        
                        [[ -n "$payment_id" ]] && store_command_output "${command_name}[${op_idx}]" "payment_id" "$payment_id"
                        [[ -n "$contract_id" ]] && store_command_output "${command_name}[${op_idx}]" "contract_id" "$contract_id"
                        [[ -n "$amount" ]] && store_command_output "${command_name}[${op_idx}]" "amount" "$amount"
                        ;;
                    "InstantSend")
                        local payment_id=$(echo "$op_result" | jq -r '.paymentId // empty')
                        local contract_id=$(echo "$op_result" | jq -r '.contractId // empty')
                        local amount=$(echo "$op_result" | jq -r '.amount // empty')
                        local id_hash=$(echo "$op_result" | jq -r '.idHash // empty')
                        local destination_id=$(echo "$op_result" | jq -r '.destinationId // empty')
                        
                        [[ -n "$payment_id" ]] && store_command_output "${command_name}[${op_idx}]" "payment_id" "$payment_id"
                        [[ -n "$contract_id" ]] && store_command_output "${command_name}[${op_idx}]" "contract_id" "$contract_id"
                        [[ -n "$amount" ]] && store_command_output "${command_name}[${op_idx}]" "amount" "$amount"
                        [[ -n "$id_hash" ]] && store_command_output "${command_name}[${op_idx}]" "id_hash" "$id_hash"
                        [[ -n "$destination_id" ]] && store_command_output "${command_name}[${op_idx}]" "destination_id" "$destination_id"
                        ;;
                    "CreateObligation")
                        local contract_id=$(echo "$op_result" | jq -r '.contractId // empty')
                        local obligation_id=$(echo "$op_result" | jq -r '.obligationId // empty')
                        local id_hash=$(echo "$op_result" | jq -r '.idHash // empty')
                        
                        [[ -n "$contract_id" ]] && store_command_output "${command_name}[${op_idx}]" "contract_id" "$contract_id"
                        [[ -n "$obligation_id" ]] && store_command_output "${command_name}[${op_idx}]" "obligation_id" "$obligation_id"
                        [[ -n "$id_hash" ]] && store_command_output "${command_name}[${op_idx}]" "id_hash" "$id_hash"
                        ;;
                    "AcceptObligation"|"TransferObligation"|"CancelObligation")
                        local contract_id=$(echo "$op_result" | jq -r '.contractId // empty')
                        local obligation_id=$(echo "$op_result" | jq -r '.obligationId // empty')
                        
                        [[ -n "$contract_id" ]] && store_command_output "${command_name}[${op_idx}]" "contract_id" "$contract_id"
                        [[ -n "$obligation_id" ]] && store_command_output "${command_name}[${op_idx}]" "obligation_id" "$obligation_id"
                        ;;
                    "CreateSwap"|"CompleteSwap"|"CancelSwap")
                        local swap_id=$(echo "$op_result" | jq -r '.swapId // empty')
                        
                        [[ -n "$swap_id" ]] && store_command_output "${command_name}[${op_idx}]" "swap_id" "$swap_id"
                        ;;
                esac
            done
            
            echo_with_color $CYAN "      ✅ Individual operation outputs stored for variable substitution"
            echo_with_color $CYAN "         Format: \$${command_name}[{op_index}].{field_name}"
            echo_with_color $CYAN "         Example: \$${command_name}[0].payment_id, \$${command_name}[1].contract_id"
        else
            echo_with_color $YELLOW "      ⚠️  No operationResults array in response - individual operation outputs not available"
            echo_with_color $YELLOW "         Backend may need to be updated to return operationResults"
        fi
        
        echo_with_color $GREEN "    ✅ Composed operation successful!"
        echo_with_color $BLUE "      Message: $message"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Composed ID: $composed_id"
        echo_with_color $BLUE "      Account Address: $account_address (from JWT)"
        echo_with_color $BLUE "      Operation Count: $operation_count"
        echo_with_color $CYAN "      📝 Stored outputs for variable substitution:"
        echo_with_color $CYAN "        ${command_name}_message, ${command_name}_message_id, ${command_name}_composed_id, ${command_name}_account_address, ${command_name}_operation_count"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // "Unknown error"')
        echo_with_color $RED "    ❌ Composed operation failed: $error_message"
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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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

# Function to execute transfer obligation command using GraphQL
execute_transfer_obligation() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local contract_id="$4"
    local destination_id="$5"
    local idempotency_key="$6"
    local group_name="$7"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing transfer obligation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL transfer obligation mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="contractId: \\\"$contract_id\\\", destinationId: \\\"$destination_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { transferObligation(input: { $input_params }) { success message accountAddress obligationId destinationId destinationAddress transferResult messageId transactionId signature timestamp } }"
    
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
    local success=$(echo "$http_response" | jq -r '.data.transferObligation.success // empty')
    if [[ "$success" == "true" ]]; then
        local message=$(echo "$http_response" | jq -r '.data.transferObligation.message // empty')
        local account_address=$(echo "$http_response" | jq -r '.data.transferObligation.accountAddress // empty')
        local obligation_id=$(echo "$http_response" | jq -r '.data.transferObligation.obligationId // empty')
        local destination_id_result=$(echo "$http_response" | jq -r '.data.transferObligation.destinationId // empty')
        local destination_address=$(echo "$http_response" | jq -r '.data.transferObligation.destinationAddress // empty')
        local transfer_result=$(echo "$http_response" | jq -r '.data.transferObligation.transferResult // empty')
        local message_id=$(echo "$http_response" | jq -r '.data.transferObligation.messageId // empty')
        local transaction_id=$(echo "$http_response" | jq -r '.data.transferObligation.transactionId // empty')
        local signature=$(echo "$http_response" | jq -r '.data.transferObligation.signature // empty')
        local timestamp=$(echo "$http_response" | jq -r '.data.transferObligation.timestamp // empty')
        
        # Store outputs for variable substitution in future commands
        store_command_output "$command_name" "contract_id" "$contract_id"
        store_command_output "$command_name" "destination_id" "$destination_id_result"
        store_command_output "$command_name" "destination_address" "$destination_address"
        store_command_output "$command_name" "obligation_id" "$obligation_id"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        echo_with_color $GREEN "    ✅ Transfer obligation submitted successfully!"
        
        echo_with_color $BLUE "  📋 Transfer Obligation Information:"
        echo_with_color $BLUE "      Contract ID: $contract_id"
        echo_with_color $BLUE "      Destination ID: $destination_id_result"
        echo_with_color $BLUE "      Destination Address: $destination_address"
        echo_with_color $BLUE "      Obligation ID: $obligation_id"
        echo_with_color $BLUE "      Message ID: $message_id"
        echo_with_color $BLUE "      Transaction ID: $transaction_id"
        echo_with_color $BLUE "      Signature: ${signature:0:20}..."
        echo_with_color $BLUE "      Timestamp: $timestamp"
        if [[ -n "$transfer_result" ]]; then
            echo_with_color $BLUE "      Transfer Result: $transfer_result"
        fi
        
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.errors[0].message // .data.transferObligation.message // "Unknown error"')
        echo_with_color $RED "    ❌ Transfer obligation failed: $error_message"
        echo_with_color $RED "    📋 Full response: $http_response"
        return 1
    fi
}

# Function to execute cancel obligation command using GraphQL
execute_cancel_obligation() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local contract_id="$4"
    local idempotency_key="$5"
    local group_name="$6"  # Optional group name for delegation
    
    echo_with_color $CYAN "❌ Executing cancel obligation command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL cancel obligation mutation..."
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="contractId: \\\"$contract_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { cancelObligation(input: { $input_params }) { success message accountAddress obligationId cancelResult messageId transactionId signature timestamp } }"
    
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
    local success=$(echo "$http_response" | jq -r '.data.cancelObligation.success // empty')
    local message=$(echo "$http_response" | jq -r '.data.cancelObligation.message // empty')
    local account_address=$(echo "$http_response" | jq -r '.data.cancelObligation.accountAddress // empty')
    local obligation_id=$(echo "$http_response" | jq -r '.data.cancelObligation.obligationId // empty')
    local cancel_result=$(echo "$http_response" | jq -r '.data.cancelObligation.cancelResult // empty')
    local message_id=$(echo "$http_response" | jq -r '.data.cancelObligation.messageId // empty')
    local transaction_id=$(echo "$http_response" | jq -r '.data.cancelObligation.transactionId // empty')
    local signature=$(echo "$http_response" | jq -r '.data.cancelObligation.signature // empty')
    local timestamp=$(echo "$http_response" | jq -r '.data.cancelObligation.timestamp // empty')
    
    # Check for errors
    local error_message=$(echo "$http_response" | jq -r '.errors[0].message // empty')
    
    if [[ -n "$error_message" ]]; then
        echo_with_color $RED "  ❌ GraphQL Error: $error_message"
        return 1
    fi
    
    # Display results
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "  ✅ Cancel obligation successful!"
        echo_with_color $BLUE "    📋 Message: $message"
        echo_with_color $BLUE "    🏦 Account: $account_address"
        echo_with_color $BLUE "    🆔 Obligation ID: $obligation_id"
        echo_with_color $BLUE "    ❌ Cancel Result: $cancel_result"
        echo_with_color $BLUE "    📨 Message ID: $message_id"
        echo_with_color $BLUE "    🔗 Transaction ID: $transaction_id"
        echo_with_color $BLUE "    ✍️  Signature: ${signature:0:20}..."
        echo_with_color $BLUE "    ⏰ Timestamp: $timestamp"
        
        # Store variables for future use
        store_command_output "$command_name" "success" "true"
        store_command_output "$command_name" "message" "$message"
        store_command_output "$command_name" "account_address" "$account_address"
        store_command_output "$command_name" "obligation_id" "$obligation_id"
        store_command_output "$command_name" "cancel_result" "$cancel_result"
        store_command_output "$command_name" "message_id" "$message_id"
        store_command_output "$command_name" "transaction_id" "$transaction_id"
        store_command_output "$command_name" "signature" "$signature"
        store_command_output "$command_name" "timestamp" "$timestamp"
        
        return 0
    else
        echo_with_color $RED "  ❌ Cancel obligation failed!"
        echo_with_color $RED "    📋 Message: $message"
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
    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/total_supply?$query_params"
    local http_response=$(curl -s -X GET "${PAY_SERVICE_URL}/total_supply?$query_params" \
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
    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/mint?$query_params"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/mint?$query_params" \
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
    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/burn?$query_params"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/burn?$query_params" \
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
    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/obligations"
    local http_response=$(curl -s -X GET "${PAY_SERVICE_URL}/obligations" \
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
        local payments_array=$(echo "$expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "0") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "0") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "0") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "0") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\" }"' | tr '\n' ',' | sed 's/,$//')
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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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
    echo_with_color $YELLOW "  ℹ️  Note: Expected payments are now retrieved from stored swap data"
    
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
    echo_with_color $PURPLE "    swap_id: '$swap_id'"
    echo_with_color $PURPLE "    idempotency_key: '$idempotency_key'"
    echo_with_color $PURPLE "    Note: expected_payments parameters are ignored (retrieved from stored data)"
    
    # Prepare GraphQL mutation - simplified to only use swap_id and optional idempotency_key
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    graphql_mutation="mutation { completeSwap(input: { $input_params }) { success message accountAddress swapId completeResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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
        echo_with_color $GREEN "  ✅ Expected payments were retrieved from stored swap data"
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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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



# Function to execute unified create swap command using GraphQL
execute_create_swap() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local swap_id="$4"
    local counterparty_id="$5"
    local deadline="$6"
    local initiator_obligation_ids_json="$7"
    local initiator_expected_payments_amount="$8"
    local initiator_expected_payments_denomination="$9"
    local initiator_expected_payments_obligor="${10}"
    local initiator_expected_payments_json="${11}"
    local counterparty_obligation_ids_json="${12}"
    local counterparty_expected_payments_amount="${13}"
    local counterparty_expected_payments_denomination="${14}"
    local counterparty_expected_payments_obligor="${15}"
    local counterparty_expected_payments_json="${16}"
    local idempotency_key="${17}"
    local group_name="${18}"  # Optional group name for delegation
    
    echo_with_color $CYAN "✅ Executing unified create swap command via GraphQL: $command_name"
    
    # Login to get JWT token (with optional group delegation)
    local jwt_token=$(login_user "$user_email" "$user_password" "$group_name")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    if [[ -n "$group_name" ]]; then
        echo_with_color $CYAN "  🏢 Using delegation JWT for group: $group_name"
    fi
    echo_with_color $BLUE "  📤 Sending GraphQL unified create swap mutation..."
    
    # Debug: Show parsed values
    echo_with_color $PURPLE "  🔍 DEBUG: Parsed values:"
    echo_with_color $PURPLE "    swap_id: '$swap_id'"
    echo_with_color $PURPLE "    counterparty_id: '$counterparty_id'"
    echo_with_color $PURPLE "    deadline: '$deadline'"
    echo_with_color $PURPLE "    initiator_obligation_ids_json: '$initiator_obligation_ids_json'"
    echo_with_color $PURPLE "    initiator_expected_payments_amount: '$initiator_expected_payments_amount'"
    echo_with_color $PURPLE "    initiator_expected_payments_denomination: '$initiator_expected_payments_denomination'"
    echo_with_color $PURPLE "    initiator_expected_payments_obligor: '$initiator_expected_payments_obligor'"
    echo_with_color $PURPLE "    initiator_expected_payments_json: '$initiator_expected_payments_json'"
    echo_with_color $PURPLE "    counterparty_obligation_ids_json: '$counterparty_obligation_ids_json'"
    echo_with_color $PURPLE "    counterparty_expected_payments_amount: '$counterparty_expected_payments_amount'"
    echo_with_color $PURPLE "    counterparty_expected_payments_denomination: '$counterparty_expected_payments_denomination'"
    echo_with_color $PURPLE "    counterparty_expected_payments_obligor: '$counterparty_expected_payments_obligor'"
    
    # Prepare GraphQL mutation
    local graphql_mutation
    local input_params="swapId: \\\"$swap_id\\\", counterparty: \\\"$counterparty_id\\\", deadline: \\\"$deadline\\\""
    
    # Add idempotency_key if provided
    if [[ -n "$idempotency_key" ]]; then
        input_params="$input_params, idempotencyKey: \\\"$idempotency_key\\\""
    fi
    
    # Add initiator obligation IDs if provided
    if [[ -n "$initiator_obligation_ids_json" && "$initiator_obligation_ids_json" != "[]" && "$initiator_obligation_ids_json" != "null" ]]; then
        # Convert JSON array to GraphQL format
        local initiator_obligation_ids_array=$(echo "$initiator_obligation_ids_json" | jq -r '.[] | "\\\"" + . + "\\\""' | tr '\n' ',' | sed 's/,$//')
        input_params="$input_params, initiatorObligationIds: [$initiator_obligation_ids_array]"
    fi
    
    # Add initiator expected payments if provided
    # Debug: Check why condition might fail
    if [[ -z "$initiator_expected_payments_amount" || "$initiator_expected_payments_amount" == "null" ]]; then
        echo_with_color $YELLOW "  ⚠️  initiator_expected_payments_amount is empty/null - cannot add initiatorExpectedPayments to mutation"
    fi
    if [[ -z "$initiator_expected_payments_json" || "$initiator_expected_payments_json" == "[]" || "$initiator_expected_payments_json" == "null" ]]; then
        echo_with_color $YELLOW "  ⚠️  initiator_expected_payments_json is empty/null/[] - cannot add initiatorExpectedPayments to mutation"
        echo_with_color $YELLOW "      Value was: '$initiator_expected_payments_json'"
    fi
    
    if [[ -n "$initiator_expected_payments_amount" && "$initiator_expected_payments_amount" != "null" && -n "$initiator_expected_payments_json" && "$initiator_expected_payments_json" != "[]" && "$initiator_expected_payments_json" != "null" ]]; then
        local initiator_expected_payments_input="initiatorExpectedPayments: { amount: \\\"$initiator_expected_payments_amount\\\""
        
        if [[ -n "$initiator_expected_payments_denomination" && "$initiator_expected_payments_denomination" != "null" ]]; then
            initiator_expected_payments_input="$initiator_expected_payments_input, denomination: \\\"$initiator_expected_payments_denomination\\\""
        fi
        
        if [[ -n "$initiator_expected_payments_obligor" && "$initiator_expected_payments_obligor" != "null" ]]; then
            initiator_expected_payments_input="$initiator_expected_payments_input, obligor: \\\"$initiator_expected_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local initiator_payments_array=$(echo "$initiator_expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "0") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "0") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "0") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "0") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\", linearVesting: " + ((.linear_vesting // false) | tostring) + " }"' | tr '\n' ',' | sed 's/,$//')
        initiator_expected_payments_input="$initiator_expected_payments_input, payments: [$initiator_payments_array] }"
        
        input_params="$input_params, $initiator_expected_payments_input"
    fi
    
    # Add counterparty obligation IDs if provided
    if [[ -n "$counterparty_obligation_ids_json" && "$counterparty_obligation_ids_json" != "[]" && "$counterparty_obligation_ids_json" != "null" ]]; then
        # Convert JSON array to GraphQL format
        local counterparty_obligation_ids_array=$(echo "$counterparty_obligation_ids_json" | jq -r '.[] | "\\\"" + . + "\\\""' | tr '\n' ',' | sed 's/,$//')
        input_params="$input_params, counterpartyObligationIds: [$counterparty_obligation_ids_array]"
    fi
    
    # Add counterparty expected payments if provided
    if [[ -n "$counterparty_expected_payments_amount" && "$counterparty_expected_payments_amount" != "null" && -n "$counterparty_expected_payments_json" && "$counterparty_expected_payments_json" != "[]" && "$counterparty_expected_payments_json" != "null" ]]; then
        local counterparty_expected_payments_input="counterpartyExpectedPayments: { amount: \\\"$counterparty_expected_payments_amount\\\""
        
        if [[ -n "$counterparty_expected_payments_denomination" && "$counterparty_expected_payments_denomination" != "null" ]]; then
            counterparty_expected_payments_input="$counterparty_expected_payments_input, denomination: \\\"$counterparty_expected_payments_denomination\\\""
        fi
        
        if [[ -n "$counterparty_expected_payments_obligor" && "$counterparty_expected_payments_obligor" != "null" ]]; then
            counterparty_expected_payments_input="$counterparty_expected_payments_input, obligor: \\\"$counterparty_expected_payments_obligor\\\""
        fi
        
        # Convert JSON array to GraphQL format - use proper escaping
        local counterparty_payments_array=$(echo "$counterparty_expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "0") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "0") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "0") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "0") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\", linearVesting: " + ((.linear_vesting // false) | tostring) + " }"' | tr '\n' ',' | sed 's/,$//')
        counterparty_expected_payments_input="$counterparty_expected_payments_input, payments: [$counterparty_payments_array] }"
        
        input_params="$input_params, $counterparty_expected_payments_input"
    fi
    
    graphql_mutation="mutation { createSwap(input: { $input_params }) { success message accountAddress swapId counterparty swapResult messageId transactionId signature timestamp } }"
    
    local graphql_payload="{\"query\": \"$graphql_mutation\"}"
    
    echo_with_color $BLUE "  📋 GraphQL mutation:"
    echo_with_color $BLUE "    $graphql_mutation"
    
    # Debug: Show the final input_params
    echo_with_color $PURPLE "  🔍 DEBUG: Final input_params:"
    echo_with_color $PURPLE "    $input_params"
    
    # Send GraphQL request to payments service
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$graphql_payload")
    
    # Check if request was successful
    if [[ $? -ne 0 ]]; then
        echo_with_color $RED "❌ Failed to send GraphQL request"
        return 1
    fi
    
    # Parse and display response
    local success=$(echo "$http_response" | jq -r '.data.createSwap.success // false')
    local message=$(echo "$http_response" | jq -r '.data.createSwap.message // "No message"')
    local swap_id_result=$(echo "$http_response" | jq -r '.data.createSwap.swapId // "No swap ID"')
    local message_id=$(echo "$http_response" | jq -r '.data.createSwap.messageId // "No message ID"')
    
    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Create unified swap completed successfully"
        echo_with_color $BLUE "  📊 Swap ID: $swap_id_result"
        echo_with_color $BLUE "  📊 Message ID: $message_id"
        echo_with_color $BLUE "  📊 Message: $message"
        
        # Store command output for variable substitution
        store_command_output "$command_name" "swap_id" "$swap_id_result"
        store_command_output "$command_name" "message_id" "$message_id"
        
        return 0
    else
        echo_with_color $RED "❌ Create unified swap failed"
        echo_with_color $RED "  📊 Message: $message"
        echo_with_color $RED "  📊 Full response: $http_response"
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
        local payments_array=$(echo "$initial_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "0") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "0") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "0") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "0") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\", linearVesting: " + ((.linear_vesting // false) | tostring) + " }"' | tr '\n' ',' | sed 's/,$//')
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
        local payments_array=$(echo "$expected_payments_json" | jq -r '.[] | "{ oracleAddress: \\\"" + ("" | tostring) + "\\\", oracleOwner: \\\"" + ("" | tostring) + "\\\", oracleKeySender: \\\"" + (.payer.key // "0") + "\\\", oracleValueSenderSecret: \\\"" + (.payer.valueSecret // "0") + "\\\", oracleKeyRecipient: \\\"" + (.payee.key // "0") + "\\\", oracleValueRecipientSecret: \\\"" + (.payee.valueSecret // "0") + "\\\", unlockSender: \\\"" + (.payer.unlock // "") + "\\\", unlockReceiver: \\\"" + (.payee.unlock // "") + "\\\" }"' | tr '\n' ',' | sed 's/,$//')
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
    echo_with_color $BLUE "  🌐 Making GraphQL request to: ${PAY_SERVICE_URL}/graphql"
    local http_response=$(curl -s -X POST "${PAY_SERVICE_URL}/graphql" \
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

# Function to execute create unified swap command using GraphQL

# Function to execute add_owner command using Auth Service
execute_add_owner() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local new_owner="$4"
    local group_name="$5"
    
    echo_with_color $CYAN "👤 Executing add_owner command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    echo_with_color $BLUE "  🔑 JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending add owner request..."
    
    # Make request to add owner
    local http_response=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/groups/${group_id}/add-owner" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "{\"new_owner\": \"$new_owner\"}")
    
    echo_with_color $BLUE "  📡 Response: $http_response"
    
    # Check if successful
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        echo_with_color $GREEN "    ✅ Add owner successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      New Owner: $new_owner"
        
        store_command_output "$command_name" "group_id" "$group_id"
        store_command_output "$command_name" "new_owner" "$new_owner"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Add owner failed: $error_message"
        return 1
    fi
}

# Function to execute remove_owner command using Auth Service
execute_remove_owner() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local old_owner="$4"
    local group_name="$5"
    
    echo_with_color $CYAN "👤 Executing remove_owner command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending remove owner request..."
    
    # Make request to remove owner
    local http_response=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/groups/${group_id}/remove-owner" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "{\"old_owner\": \"$old_owner\"}")
    
    echo_with_color $BLUE "  📡 Response: $http_response"
    
    # Check if successful
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        echo_with_color $GREEN "    ✅ Remove owner successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      Removed Owner: $old_owner"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Remove owner failed: $error_message"
        return 1
    fi
}

# Function to execute add_account_member command using Auth Service
execute_add_account_member() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local obligation_address="$4"
    local obligation_id="$5"
    local group_name="$6"
    
    echo_with_color $CYAN "👥 Executing add_account_member command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending add account member request..."
    
    # Build JSON payload - obligation_address is optional (backend will use default)
    local json_payload
    if [[ -n "$obligation_address" && "$obligation_address" != "null" && "$obligation_address" != "" ]]; then
        json_payload="{\"obligation_address\": \"$obligation_address\", \"obligation_id\": \"$obligation_id\"}"
    else
        json_payload="{\"obligation_id\": \"$obligation_id\"}"
        echo_with_color $YELLOW "  ℹ️  Using default obligation_address from backend (CONFIDENTIAL_OBLIGATION_ADDRESS)"
    fi
    
    # Make request to add member
    echo_with_color $BLUE "  📋 Request payload: $json_payload"
    local http_response=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/groups/${group_id}/add-account-member" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$json_payload")
    
    echo_with_color $BLUE "  📡 Response: $http_response"
    
    # Check if the response is empty
    if [[ -z "$http_response" || "$http_response" == "" ]]; then
        echo_with_color $RED "    ❌ Add account member failed: Empty response from server"
        echo_with_color $YELLOW "    💡 This may indicate the contract_id '${obligation_id}' cannot be resolved to an obligation_id yet."
        echo_with_color $YELLOW "    💡 The obligation may still be processing. Wait for it to complete before adding account members."
        return 1
    fi
    
    # Check if it's a valid JSON response
    if ! echo "$http_response" | jq . >/dev/null 2>&1; then
        echo_with_color $RED "    ❌ Add account member failed: Invalid JSON response: $http_response"
        return 1
    fi
    
    # Check if successful
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        echo_with_color $GREEN "    ✅ Add account member successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      Obligation Address: $obligation_address"
        echo_with_color $BLUE "      Obligation ID: $obligation_id"
        
        local member_type
        if [[ "$obligation_id" == "0" ]]; then
            member_type="direct address"
        else
            member_type="NFT-based (ID: $obligation_id)"
        fi
        echo_with_color $CYAN "      Member Type: $member_type"
        
        store_command_output "$command_name" "group_id" "$group_id"
        store_command_output "$command_name" "obligation_address" "$obligation_address"
        store_command_output "$command_name" "obligation_id" "$obligation_id"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Add account member failed: $error_message"
        echo_with_color $BLUE "      Full response: $http_response"
        if [[ "$error_message" == *"Cannot resolve"* ]] || [[ "$error_message" == *"token_id"* ]]; then
            echo_with_color $YELLOW "    💡 The contract_id '${obligation_id}' may not have a token_id yet."
            echo_with_color $YELLOW "    💡 Wait for the obligation to complete processing before adding account members."
        fi
        return 1
    fi
}

# Function to execute remove_account_member command using Auth Service
execute_remove_account_member() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local obligation_address="$4"
    local obligation_id="$5"
    local group_name="$6"
    
    echo_with_color $CYAN "👥 Executing remove_account_member command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending remove account member request..."
    
    # Build JSON payload - obligation_address is optional (backend will use default)
    local json_payload
    if [[ -n "$obligation_address" && "$obligation_address" != "null" && "$obligation_address" != "" ]]; then
        json_payload="{\"obligation_address\": \"$obligation_address\", \"obligation_id\": \"$obligation_id\"}"
    else
        json_payload="{\"obligation_id\": \"$obligation_id\"}"
        echo_with_color $YELLOW "  ℹ️  Using default obligation_address from backend (CONFIDENTIAL_OBLIGATION_ADDRESS)"
    fi
    
    # Make request to remove member
    local http_response=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/groups/${group_id}/remove-account-member" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $jwt_token" \
        -d "$json_payload")
    
    echo_with_color $BLUE "  📡 Response: $http_response"
    
    # Check if successful
    local status=$(echo "$http_response" | jq -r '.status // empty')
    if [[ "$status" == "success" ]]; then
        echo_with_color $GREEN "    ✅ Remove account member successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      Removed Obligation Address: $obligation_address"
        echo_with_color $BLUE "      Removed Obligation ID: $obligation_id"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Remove account member failed: $error_message"
        return 1
    fi
}

# Function to execute get_account_owners command using Auth Service
execute_get_account_owners() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local group_name="$4"
    
    echo_with_color $CYAN "👥 Executing get_account_owners command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending get account owners request..."
    
    # Make request to get account owners
    local http_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/${group_id}/account-owners" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Response received"
    
    # Check if successful
    if echo "$http_response" | jq -e '.owners' >/dev/null 2>&1; then
        local owners_count=$(echo "$http_response" | jq '.owners | length')
        local account_address=$(echo "$http_response" | jq -r '.account_address')
        
        echo_with_color $GREEN "    ✅ Get account owners successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      Account Address: $account_address"
        echo_with_color $BLUE "      Owners Count: $owners_count"
        
        if [[ $owners_count -gt 0 ]]; then
            echo_with_color $CYAN "      👥 Owners:"
            echo "$http_response" | jq -r '.owners[] | "        • \(.owner_address) (Added: \(.added_at), Active: \(.is_active))"'
        fi
        
        store_command_output "$command_name" "owners" "$(echo "$http_response" | jq -c '.owners')"
        store_command_output "$command_name" "owners_count" "$owners_count"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Get account owners failed: $error_message"
        return 1
    fi
}

# Function to execute get_account_members command using Auth Service
execute_get_account_members() {
    local command_name="$1"
    local user_email="$2"
    local user_password="$3"
    local group_name="$4"
    
    echo_with_color $CYAN "👥 Executing get_account_members command via Auth Service: $command_name"
    
    # Login to get JWT token
    local jwt_token=$(login_user "$user_email" "$user_password")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $user_email"
        return 1
    fi
    
    # Get group ID from group name
    local groups_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/user" \
        -H "Authorization: Bearer $jwt_token")
    
    local group_id=$(echo "$groups_response" | jq -r ".[] | select(.name == \"$group_name\") | .id")
    
    if [[ -z "$group_id" || "$group_id" == "null" ]]; then
        echo_with_color $RED "❌ Group not found: $group_name"
        return 1
    fi
    
    echo_with_color $BLUE "  📤 Sending get account members request..."
    
    # Make request to get account members
    local http_response=$(curl -s -X GET "${AUTH_SERVICE_URL}/auth/groups/${group_id}/account-members" \
        -H "Authorization: Bearer $jwt_token")
    
    echo_with_color $BLUE "  📡 Response received"
    
    # Check if successful
    if echo "$http_response" | jq -e '.members' >/dev/null 2>&1; then
        local members_count=$(echo "$http_response" | jq '.members | length')
        local account_address=$(echo "$http_response" | jq -r '.account_address')
        
        echo_with_color $GREEN "    ✅ Get account members successful!"
        echo_with_color $BLUE "      Group: $group_name ($group_id)"
        echo_with_color $BLUE "      Account Address: $account_address"
        echo_with_color $BLUE "      Members Count: $members_count"
        
        if [[ $members_count -gt 0 ]]; then
            echo_with_color $CYAN "      👥 Members:"
            echo "$http_response" | jq -r '.members[] | "        • \(.obligation_address) (ID: \(.obligation_id), Type: \(.member_type), Active: \(.is_active))"'
        fi
        
        store_command_output "$command_name" "members" "$(echo "$http_response" | jq -c '.members')"
        store_command_output "$command_name" "members_count" "$members_count"
        return 0
    else
        local error_message=$(echo "$http_response" | jq -r '.message // .error // "Unknown error"')
        echo_with_color $RED "    ❌ Get account members failed: $error_message"
        return 1
    fi
}
