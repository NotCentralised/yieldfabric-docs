#!/bin/bash

# YieldFabric GraphQL Commands Execution Script - Refactored
# Reads a YAML file (default: commands.yaml) and executes each command sequentially using GraphQL mutations
# Gets JWT tokens for users and makes GraphQL API calls based on command type

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env file if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    echo "Loading environment variables from .env file..."
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Command execution delay (in seconds) - can be overridden by environment variable
COMMAND_DELAY="${COMMAND_DELAY:-3}"

# Source all module files
source "$SCRIPT_DIR/utils.sh"
source "$SCRIPT_DIR/auth.sh"
source "$SCRIPT_DIR/executors.sh"
source "$SCRIPT_DIR/executors_additional.sh"
source "$SCRIPT_DIR/validation.sh"
source "$SCRIPT_DIR/help.sh"

# Parse command line arguments to get the YAML file
YAML_FILE="${1:-commands.yaml}"
COMMANDS_FILE="$SCRIPT_DIR/$YAML_FILE"
# AUTH_SCRIPT="$SCRIPT_DIR/yieldfabric-auth.sh"  # Not used in refactored version
TOKENS_DIR="$SCRIPT_DIR/tokens"

# Ensure tokens directory exists
mkdir -p "$TOKENS_DIR"

# Global arrays to store command outputs for variable substitution
# Using regular arrays instead of associative arrays for compatibility
COMMAND_OUTPUT_KEYS=()
COMMAND_OUTPUT_VALUES=()

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
    local asset_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.asset_id")
    local obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligor")
    
    # Parse account management specific parameters
    local new_owner=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.new_owner")
    local old_owner=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.old_owner")
    local obligation_address=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligation_address")
    local obligation_id_param=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligation_id")
    
    # Use asset_id if denomination is not provided (for backward compatibility)
    if [[ -z "$denomination" || "$denomination" == "null" ]]; then
        denomination="$asset_id"
    fi
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
    
    # Parse transfer_obligation specific parameters
    local transfer_contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.contract_id")
    local transfer_destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.destination_id")
    
    # Parse cancel_obligation specific parameters
    local cancel_contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.contract_id")
    
    # Parse treasury specific parameters
    local policy_secret=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.policy_secret")
    
    # Parse swap specific parameters (legacy format)
    local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.swap_id")
    local counterparty=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty")
    local obligation_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.obligation_id")
    local deadline=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.deadline")
    local expected_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.amount")
    local expected_payments_denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.denomination")
    local expected_payments_obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.obligor")
    local expected_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.expected_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    local key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.key")
    local value=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.value")
    
    # Parse unified swap specific parameters (new format)
    local initiator_obligation_ids_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.initiator.obligation_ids" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    local initiator_expected_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initiator.expected_payments.amount")
    local initiator_expected_payments_denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initiator.expected_payments.denomination")
    local initiator_expected_payments_obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initiator.expected_payments.obligor")
    local initiator_expected_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.initiator.expected_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    
    local counterparty_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty.id")
    local counterparty_obligation_ids_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.counterparty.obligation_ids" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    local counterparty_expected_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty.expected_payments.amount")
    local counterparty_expected_payments_denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty.expected_payments.denomination")
    local counterparty_expected_payments_obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty.expected_payments.obligor")
    local counterparty_expected_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.counterparty.expected_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    
    # Parse create_payment_swap specific parameters
    local initial_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initial_payments.amount")
    local initial_payments_denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initial_payments.denomination")
    local initial_payments_obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.initial_payments.obligor")
    local initial_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.initial_payments.payments" "$COMMANDS_FILE" 2>/dev/null || echo "[]")
    
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
    
    # Apply variable substitution to JSON arrays
    initiator_obligation_ids_json=$(substitute_variables "$initiator_obligation_ids_json")
    counterparty_obligation_ids_json=$(substitute_variables "$counterparty_obligation_ids_json")
    
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
    
    # Apply variable substitution to transfer_obligation specific parameters
    transfer_contract_id=$(substitute_variables "$transfer_contract_id")
    transfer_destination_id=$(substitute_variables "$transfer_destination_id")
    
    # Apply variable substitution to cancel_obligation specific parameters
    cancel_contract_id=$(substitute_variables "$cancel_contract_id")
    
    # Apply variable substitution to treasury specific parameters
    policy_secret=$(substitute_variables "$policy_secret")
    
    # Apply variable substitution to swap specific parameters (legacy format)
    swap_id=$(substitute_variables "$swap_id")
    counterparty=$(substitute_variables "$counterparty")
    obligation_id=$(substitute_variables "$obligation_id")
    deadline=$(substitute_variables "$deadline")
    expected_payments_amount=$(substitute_variables "$expected_payments_amount")
    expected_payments_denomination=$(substitute_variables "$expected_payments_denomination")
    expected_payments_obligor=$(substitute_variables "$expected_payments_obligor")
    key=$(substitute_variables "$key")
    value=$(substitute_variables "$value")
    
    # Apply variable substitution to unified swap specific parameters (new format)
    initiator_obligation_ids_json=$(substitute_variables "$initiator_obligation_ids_json")
    initiator_expected_payments_amount=$(substitute_variables "$initiator_expected_payments_amount")
    initiator_expected_payments_denomination=$(substitute_variables "$initiator_expected_payments_denomination")
    initiator_expected_payments_obligor=$(substitute_variables "$initiator_expected_payments_obligor")
    initiator_expected_payments_json=$(substitute_variables "$initiator_expected_payments_json")
    
    counterparty_id=$(substitute_variables "$counterparty_id")
    counterparty_obligation_ids_json=$(substitute_variables "$counterparty_obligation_ids_json")
    counterparty_expected_payments_amount=$(substitute_variables "$counterparty_expected_payments_amount")
    counterparty_expected_payments_denomination=$(substitute_variables "$counterparty_expected_payments_denomination")
    counterparty_expected_payments_obligor=$(substitute_variables "$counterparty_expected_payments_obligor")
    counterparty_expected_payments_json=$(substitute_variables "$counterparty_expected_payments_json")
    
    # Apply variable substitution to create_payment_swap specific parameters
    initial_payments_amount=$(substitute_variables "$initial_payments_amount")
    initial_payments_denomination=$(substitute_variables "$initial_payments_denomination")
    initial_payments_obligor=$(substitute_variables "$initial_payments_obligor")
    
    # Apply variable substitution to account management specific parameters
    new_owner=$(substitute_variables "$new_owner")
    old_owner=$(substitute_variables "$old_owner")
    obligation_address=$(substitute_variables "$obligation_address")
    obligation_id_param=$(substitute_variables "$obligation_id_param")
    
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
    
    # Display transfer_obligation specific parameters
    if [[ -n "$transfer_contract_id" ]]; then echo_with_color $BLUE "    transfer_contract_id: $transfer_contract_id"; fi
    if [[ -n "$transfer_destination_id" ]]; then echo_with_color $BLUE "    transfer_destination_id: $transfer_destination_id"; fi
    
    # Display cancel_obligation specific parameters
    if [[ -n "$cancel_contract_id" ]]; then echo_with_color $BLUE "    cancel_contract_id: $cancel_contract_id"; fi
    
    # Display treasury specific parameters
    if [[ -n "$policy_secret" ]]; then echo_with_color $BLUE "    policy_secret: ${policy_secret:0:8}..."; fi
    
    # Display swap specific parameters (legacy format)
    if [[ -n "$swap_id" ]]; then echo_with_color $BLUE "    swap_id: $swap_id"; fi
    if [[ -n "$counterparty" ]]; then echo_with_color $BLUE "    counterparty: $counterparty"; fi
    if [[ -n "$obligation_id" ]]; then echo_with_color $BLUE "    obligation_id: $obligation_id"; fi
    if [[ -n "$deadline" ]]; then echo_with_color $BLUE "    deadline: $deadline"; fi
    if [[ -n "$expected_payments_amount" ]]; then echo_with_color $BLUE "    expected_payments_amount: $expected_payments_amount"; fi
    if [[ -n "$expected_payments_denomination" ]]; then echo_with_color $BLUE "    expected_payments_denomination: $expected_payments_denomination"; fi
    if [[ -n "$expected_payments_obligor" ]]; then echo_with_color $BLUE "    expected_payments_obligor: $expected_payments_obligor"; fi
    if [[ -n "$key" ]]; then echo_with_color $BLUE "    key: $key"; fi
    if [[ -n "$value" ]]; then echo_with_color $BLUE "    value: $value"; fi
    
    # Display unified swap specific parameters (new format)
    if [[ -n "$initiator_obligation_ids_json" && "$initiator_obligation_ids_json" != "[]" ]]; then echo_with_color $BLUE "    initiator_obligation_ids: $initiator_obligation_ids_json"; fi
    if [[ -n "$initiator_expected_payments_amount" ]]; then echo_with_color $BLUE "    initiator_expected_payments_amount: $initiator_expected_payments_amount"; fi
    if [[ -n "$initiator_expected_payments_denomination" ]]; then echo_with_color $BLUE "    initiator_expected_payments_denomination: $initiator_expected_payments_denomination"; fi
    if [[ -n "$initiator_expected_payments_obligor" ]]; then echo_with_color $BLUE "    initiator_expected_payments_obligor: $initiator_expected_payments_obligor"; fi
    if [[ -n "$counterparty_id" ]]; then echo_with_color $BLUE "    counterparty_id: $counterparty_id"; fi
    if [[ -n "$counterparty_obligation_ids_json" && "$counterparty_obligation_ids_json" != "[]" ]]; then echo_with_color $BLUE "    counterparty_obligation_ids: $counterparty_obligation_ids_json"; fi
    if [[ -n "$counterparty_expected_payments_amount" ]]; then echo_with_color $BLUE "    counterparty_expected_payments_amount: $counterparty_expected_payments_amount"; fi
    if [[ -n "$counterparty_expected_payments_denomination" ]]; then echo_with_color $BLUE "    counterparty_expected_payments_denomination: $counterparty_expected_payments_denomination"; fi
    if [[ -n "$counterparty_expected_payments_obligor" ]]; then echo_with_color $BLUE "    counterparty_expected_payments_obligor: $counterparty_expected_payments_obligor"; fi
    
    # Display create_payment_swap specific parameters
    if [[ -n "$initial_payments_amount" ]]; then echo_with_color $BLUE "    initial_payments_amount: $initial_payments_amount"; fi
    if [[ -n "$initial_payments_denomination" ]]; then echo_with_color $BLUE "    initial_payments_denomination: $initial_payments_denomination"; fi
    if [[ -n "$initial_payments_obligor" ]]; then echo_with_color $BLUE "    initial_payments_obligor: $initial_payments_obligor"; fi
    
    # Display account management specific parameters
    if [[ -n "$new_owner" && "$new_owner" != "null" ]]; then echo_with_color $BLUE "    new_owner: $new_owner"; fi
    if [[ -n "$old_owner" && "$old_owner" != "null" ]]; then echo_with_color $BLUE "    old_owner: $old_owner"; fi
    if [[ -n "$obligation_address" && "$obligation_address" != "null" ]]; then echo_with_color $BLUE "    obligation_address: $obligation_address"; fi
    if [[ -n "$obligation_id_param" && "$obligation_id_param" != "null" ]]; then echo_with_color $BLUE "    obligation_id: $obligation_id_param"; fi
    
    # Execute command based on type
    case "$command_type" in
        "deposit")
            execute_deposit "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$idempotency_key" "$group_name"
            ;;
        "withdraw")
            execute_withdraw "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$idempotency_key" "$group_name"
            ;;
        "instant")
            execute_instant "$command_name" "$user_email" "$user_password" "$denomination" "$amount" "$destination_id" "$idempotency_key" "$obligor" "$group_name"
            ;;
        "accept")
            execute_accept "$command_name" "$user_email" "$user_password" "$payment_id" "$amount" "$idempotency_key" "$group_name"
            ;;
        "accept_all")
            execute_accept_all "$command_name" "$user_email" "$user_password" "$denomination" "$obligor" "$idempotency_key" "$group_name"
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
        "transfer_obligation")
            execute_transfer_obligation "$command_name" "$user_email" "$user_password" "$transfer_contract_id" "$transfer_destination_id" "$idempotency_key" "$group_name"
            ;;
        "cancel_obligation")
            execute_cancel_obligation "$command_name" "$user_email" "$user_password" "$cancel_contract_id" "$idempotency_key" "$group_name"
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
        "create_obligation_swap")
            execute_create_obligation_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$counterparty" "$obligation_id" "$deadline" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "create_payment_swap")
            execute_create_payment_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$counterparty" "$deadline" "$initial_payments_amount" "$initial_payments_denomination" "$initial_payments_obligor" "$initial_payments_json" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "create_swap")
            execute_create_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$counterparty_id" "$deadline" "$initiator_obligation_ids_json" "$initiator_expected_payments_amount" "$initiator_expected_payments_denomination" "$initiator_expected_payments_obligor" "$initiator_expected_payments_json" "$counterparty_obligation_ids_json" "$counterparty_expected_payments_amount" "$counterparty_expected_payments_denomination" "$counterparty_expected_payments_obligor" "$counterparty_expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "complete_swap")
            execute_complete_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "cancel_swap")
            execute_cancel_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$key" "$value" "$idempotency_key" "$group_name"
            ;;
        "list_groups")
            execute_list_groups "$command_name" "$user_email" "$user_password" "$group_name"
            ;;
        "add_owner")
            execute_add_owner "$command_name" "$user_email" "$user_password" "$new_owner" "$group_name"
            ;;
        "remove_owner")
            execute_remove_owner "$command_name" "$user_email" "$user_password" "$old_owner" "$group_name"
            ;;
        "add_account_member")
            execute_add_account_member "$command_name" "$user_email" "$user_password" "$obligation_address" "$obligation_id_param" "$group_name"
            ;;
        "remove_account_member")
            execute_remove_account_member "$command_name" "$user_email" "$user_password" "$obligation_address" "$obligation_id_param" "$group_name"
            ;;
        "get_account_owners")
            execute_get_account_owners "$command_name" "$user_email" "$user_password" "$group_name"
            ;;
        "get_account_members")
            execute_get_account_members "$command_name" "$user_email" "$user_password" "$group_name"
            ;;
        *)
            echo_with_color $RED "❌ Unknown command type: $command_type"
            return 1
            ;;
    esac
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
    if ! check_service_running "Auth Service" "$AUTH_SERVICE_URL"; then
        echo_with_color $RED "❌ Auth service is not reachable at $AUTH_SERVICE_URL"
        echo_with_color $YELLOW "Please check your connection or start the auth service:"
        echo "   Local: cd ../yieldfabric-auth && cargo run"
        echo "   Remote: Verify $AUTH_SERVICE_URL is accessible"
        return 1
    fi
    
    if ! check_service_running "Payments Service" "$PAY_SERVICE_URL"; then
        echo_with_color $RED "❌ Payments service is not reachable at $PAY_SERVICE_URL"
        echo_with_color $YELLOW "Please check your connection or start the payments service:"
        echo "   Local: cd ../yieldfabric-payments && cargo run"
        echo_with_color $BLUE "   GraphQL endpoint will be available at: $PAY_SERVICE_URL/graphql"
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
        
        # Add configurable wait between commands (except for the last command)
        if [[ $((i+1)) -lt $command_count ]]; then
            echo_with_color $CYAN "⏳ Waiting $COMMAND_DELAY seconds before next command..."
            sleep "$COMMAND_DELAY"
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
