#!/bin/bash

# YieldFabric GraphQL Commands Execution Script - Refactored
# Reads a YAML file (default: commands.yaml) and executes each command sequentially using GraphQL mutations
# Gets JWT tokens for users and makes GraphQL API calls based on command type

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    
    # Use asset_id if denomination is not provided (for backward compatibility)
    if [[ -z "$denomination" || "$denomination" == "null" ]]; then
        denomination="$asset_id"
    fi
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
    
    # Parse treasury specific parameters
    local policy_secret=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.policy_secret")
    
    # Parse swap specific parameters
    local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.swap_id")
    local counterparty=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.counterparty")
    local deal_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.deal_id")
    local deadline=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.deadline")
    local expected_payments_amount=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.amount")
    local expected_payments_denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.denomination")
    local expected_payments_obligor=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.expected_payments.obligor")
    local expected_payments_json=$(yq eval -o json -I 0 ".commands[$command_index].parameters.expected_payments" "$COMMANDS_FILE" 2>/dev/null || echo "{}")
    local key=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.key")
    local value=$(parse_yaml "$COMMANDS_FILE" ".commands[$command_index].parameters.value")
    
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
    
    # Apply variable substitution to treasury specific parameters
    policy_secret=$(substitute_variables "$policy_secret")
    
    # Apply variable substitution to swap specific parameters
    swap_id=$(substitute_variables "$swap_id")
    counterparty=$(substitute_variables "$counterparty")
    deal_id=$(substitute_variables "$deal_id")
    deadline=$(substitute_variables "$deadline")
    expected_payments_amount=$(substitute_variables "$expected_payments_amount")
    expected_payments_denomination=$(substitute_variables "$expected_payments_denomination")
    expected_payments_obligor=$(substitute_variables "$expected_payments_obligor")
    key=$(substitute_variables "$key")
    value=$(substitute_variables "$value")
    
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
    
    # Display treasury specific parameters
    if [[ -n "$policy_secret" ]]; then echo_with_color $BLUE "    policy_secret: ${policy_secret:0:8}..."; fi
    
    # Display swap specific parameters
    if [[ -n "$swap_id" ]]; then echo_with_color $BLUE "    swap_id: $swap_id"; fi
    if [[ -n "$counterparty" ]]; then echo_with_color $BLUE "    counterparty: $counterparty"; fi
    if [[ -n "$deal_id" ]]; then echo_with_color $BLUE "    deal_id: $deal_id"; fi
    if [[ -n "$deadline" ]]; then echo_with_color $BLUE "    deadline: $deadline"; fi
    if [[ -n "$expected_payments_amount" ]]; then echo_with_color $BLUE "    expected_payments_amount: $expected_payments_amount"; fi
    if [[ -n "$expected_payments_denomination" ]]; then echo_with_color $BLUE "    expected_payments_denomination: $expected_payments_denomination"; fi
    if [[ -n "$expected_payments_obligor" ]]; then echo_with_color $BLUE "    expected_payments_obligor: $expected_payments_obligor"; fi
    if [[ -n "$key" ]]; then echo_with_color $BLUE "    key: $key"; fi
    if [[ -n "$value" ]]; then echo_with_color $BLUE "    value: $value"; fi
    
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
        "create_deal")
            execute_create_deal_ergonomic "$command_name" "$user_email" "$user_password" "$counterpart" "$deal_address" "$deal_group_id" "$denomination" "$obligor" "$notional" "$expiry" "$data" "$initial_payments_amount" "$initial_payments_json" "$idempotency_key" "$group_name"
            ;;
        "accept_deal")
            execute_accept_deal "$command_name" "$user_email" "$user_password" "$contract_id" "$idempotency_key" "$group_name"
            ;;
        "deals")
            execute_deals "$command_name" "$user_email" "$user_password" "$group_name"
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
        "create_deal_swap")
            execute_create_deal_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$counterparty" "$deal_id" "$deadline" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "create_deal_swap_ergonomic")
            execute_create_deal_swap_ergonomic "$command_name" "$user_email" "$user_password" "$swap_id" "$counterparty" "$deal_id" "$deadline" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "complete_swap")
            execute_complete_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$expected_payments_amount" "$expected_payments_denomination" "$expected_payments_obligor" "$expected_payments_json" "$idempotency_key" "$group_name"
            ;;
        "cancel_swap")
            execute_cancel_swap "$command_name" "$user_email" "$user_password" "$swap_id" "$key" "$value" "$idempotency_key" "$group_name"
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
