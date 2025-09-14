#!/bin/bash

# YieldFabric Help Module
# Contains functions for showing help and stored variables

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
