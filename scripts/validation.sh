#!/bin/bash

# YieldFabric Validation Module
# Contains functions for validating commands and showing status

# Service URLs - can be overridden by environment variables
PAY_SERVICE_URL="${PAY_SERVICE_URL:-https://pay.yieldfabric.io}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth.yieldfabric.io}"

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
            "withdraw")
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
            "accept_all")
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                # obligor is optional for accept_all - if not specified, accepts all obligors
                
                if [[ -z "$denomination" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.denomination' field"
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
                local denomination=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.denomination")
                
                if [[ -z "$counterpart" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterpart' field"
                    return 1
                fi
                
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
            "transfer_obligation")
                local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.contract_id")
                local destination_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.destination_id")
                
                if [[ -z "$contract_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.contract_id' field"
                    return 1
                fi
                
                if [[ -z "$destination_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.destination_id' field"
                    return 1
                fi
                ;;
            "cancel_obligation")
                local contract_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.contract_id")
                
                if [[ -z "$contract_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.contract_id' field"
                    return 1
                fi
                ;;
            "obligations")
                # Obligations command doesn't require any specific parameters
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
            "create_obligation_swap")
                local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.swap_id")
                local counterparty=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterparty")
                local obligation_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligation_id")
                local deadline=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.deadline")
                
                if [[ -z "$swap_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.swap_id' field"
                    return 1
                fi
                
                if [[ -z "$counterparty" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterparty' field"
                    return 1
                fi
                
                if [[ -z "$obligation_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.obligation_id' field"
                    return 1
                fi
                
                if [[ -z "$deadline" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.deadline' field"
                    return 1
                fi
                ;;
            "create_payment_swap")
                local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.swap_id")
                local counterparty=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterparty")
                local deadline=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.deadline")
                
                if [[ -z "$swap_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.swap_id' field"
                    return 1
                fi
                
                if [[ -z "$counterparty" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterparty' field"
                    return 1
                fi
                
                if [[ -z "$deadline" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.deadline' field"
                    return 1
                fi
                ;;
            "complete_swap")
                local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.swap_id")
                
                if [[ -z "$swap_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.swap_id' field"
                    return 1
                fi
                ;;
            "cancel_swap")
                local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.swap_id")
                local key=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.key")
                local value=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.value")
                
                if [[ -z "$swap_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.swap_id' field"
                    return 1
                fi
                
                if [[ -z "$key" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.key' field"
                    return 1
                fi
                
                if [[ -z "$value" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.value' field"
                    return 1
                fi
                ;;
            "list_groups")
                # list_groups doesn't require any specific parameters
                # It only needs user credentials which are already validated above
                ;;
            "add_owner")
                local new_owner=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.new_owner")
                
                if [[ -z "$new_owner" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.new_owner' field"
                    return 1
                fi
                ;;
            "remove_owner")
                local old_owner=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.old_owner")
                
                if [[ -z "$old_owner" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.old_owner' field"
                    return 1
                fi
                ;;
            "add_account_member")
                local obligation_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligation_id")
                
                # obligation_address is optional - backend will use CONFIDENTIAL_OBLIGATION_ADDRESS by default
                if [[ -z "$obligation_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.obligation_id' field"
                    return 1
                fi
                ;;
            "remove_account_member")
                local obligation_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.obligation_id")
                
                # obligation_address is optional - backend will use CONFIDENTIAL_OBLIGATION_ADDRESS by default
                if [[ -z "$obligation_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.obligation_id' field"
                    return 1
                fi
                ;;
            "get_account_owners")
                # get_account_owners doesn't require any specific parameters
                # It only needs user credentials and group which are already validated
                ;;
            "get_account_members")
                # get_account_members doesn't require any specific parameters
                # It only needs user credentials and group which are already validated
                ;;
            "create_swap")
                local swap_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.swap_id")
                local counterparty_id=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterparty.id")
                local deadline=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.deadline")
                
                if [[ -z "$swap_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.swap_id' field"
                    return 1
                fi
                
                if [[ -z "$counterparty_id" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.counterparty.id' field"
                    return 1
                fi
                
                if [[ -z "$deadline" ]]; then
                    echo_with_color $RED "Error: Command '$command_name' missing 'parameters.deadline' field"
                    return 1
                fi
                
                # Validate initiator parameters (optional but if present, should be valid)
                local initiator_obligation_ids=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.initiator.obligation_ids")
                local initiator_expected_payments=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.initiator.expected_payments")
                
                # Validate counterparty parameters (optional but if present, should be valid)
                local counterparty_obligation_ids=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterparty.obligation_ids")
                local counterparty_expected_payments=$(parse_yaml "$COMMANDS_FILE" ".commands[$i].parameters.counterparty.expected_payments")
                
                # Note: For create_swap, at least one of initiator or counterparty should have obligations or expected payments
                if [[ -z "$initiator_obligation_ids" && -z "$initiator_expected_payments" && -z "$counterparty_obligation_ids" && -z "$counterparty_expected_payments" ]]; then
                    echo_with_color $YELLOW "Warning: Command '$command_name' has no obligations or expected payments for either initiator or counterparty"
                fi
                ;;
            *)
                echo_with_color $RED "Error: Command '$command_name' has unsupported type: '$command_type'"
                echo_with_color $YELLOW "Supported types: deposit, withdraw, instant, accept, accept_all, balance, create_obligation, accept_obligation, transfer_obligation, cancel_obligation, obligations, total_supply, mint, burn, create_obligation_swap, create_payment_swap, create_swap, complete_swap, cancel_swap, list_groups, add_owner, remove_owner, add_account_member, remove_account_member, get_account_owners, get_account_members"
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
        echo_with_color $BLUE "   GraphQL endpoint available at: ${PAY_SERVICE_URL}/graphql"
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
