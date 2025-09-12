#!/bin/bash

# YieldFabric Script Utilities
# Contains common utility functions used across all modules

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
