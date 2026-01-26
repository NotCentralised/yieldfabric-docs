#!/bin/bash

# YieldFabric Onramping Workflow Test Script
# 
# This script tests the complete onramping workflow:
# 1. Mint tokens based on amount and token type
# 2. Deposit tokens to vault
# 3. Create instant payment to destination
#
# The workflow runs asynchronously and this script polls for completion.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    source "${SCRIPT_DIR}/.env"
fi

# Service URLs - can be overridden by environment variables
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:3000}"
PAY_SERVICE_URL="${PAY_SERVICE_URL:-http://localhost:3002}"

# Default test parameters (can be overridden via command line args)
USER_EMAIL="${1:-issuer@yieldfabric.com}"
USER_PASSWORD="${2:-issuer_password}"
AMOUNT="${3:-1000000000000000000000000}"
# AMOUNT="${3:-1000000 000000000000000000}"
TOKEN="${4:-aud-token-asset}"
DESTINATION="${5:-investor@yieldfabric.com}"
POLICY_SECRET="${6:-998855e3-fa0e-47f3-9867-0652b0402ec7}"

# Polling configuration
MAX_POLLS=60  # Maximum number of status checks
POLL_INTERVAL=5  # Seconds between polls

echo_with_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to login and get JWT token
login_user() {
    local email="$1"
    local password="$2"
    
    echo_with_color $BLUE "🔐 Logging in user: $email" >&2
    
    # Validate password is provided
    if [[ -z "$password" ]]; then
        echo_with_color $RED "❌ Login failed: password is required" >&2
        return 1
    fi
    
    local services_json='["vault", "payments"]'
    local url="${AUTH_SERVICE_URL}/auth/login/with-services"
    local payload="{\"email\": \"$email\", \"password\": \"$password\", \"services\": $services_json}"
    
    echo_with_color $CYAN "   URL: $url" >&2
    echo_with_color $CYAN "   Using password: ${password:0:3}***" >&2
    
    # Use temp file to capture response body
    local temp_file=$(mktemp)
    
    # Run curl: response body goes to temp file, HTTP status code goes to stdout
    local http_code=$(curl -s -w "%{http_code}" -o "$temp_file" -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)
    
    local response=$(cat "$temp_file" 2>/dev/null)
    rm -f "$temp_file"
    
    # Check if curl failed (http_code should be 3 digits)
    if ! [[ "$http_code" =~ ^[0-9]{3}$ ]]; then
        echo_with_color $RED "❌ Login failed: service unreachable or curl error" >&2
        echo_with_color $YELLOW "   Check if auth service is running at: $AUTH_SERVICE_URL" >&2
        return 1
    fi
    
    echo_with_color $CYAN "   HTTP Status: $http_code" >&2
    
    if [[ -z "$response" ]]; then
        echo_with_color $RED "❌ Login failed: no response (HTTP $http_code)" >&2
        return 1
    fi
    
    # Check if response is HTML (error page)
    if [[ "$response" =~ ^\<html\> ]]; then
        echo_with_color $RED "❌ Login failed: server returned HTML error page (HTTP $http_code)" >&2
        echo_with_color $YELLOW "   Response preview: $(echo "$response" | head -5 | tr '\n' ' ')" >&2
        return 1
    fi
    
    local token=$(echo "$response" | jq -r '.token // .access_token // .jwt // empty' 2>/dev/null)
    
    if [[ -z "$token" || "$token" == "null" ]]; then
        echo_with_color $RED "❌ Login failed: no token in response (HTTP $http_code)" >&2
        echo_with_color $YELLOW "Response: $response" >&2
        return 1
    fi
    
    echo_with_color $GREEN "✅ Login successful" >&2
    
    # Only output token to stdout (for command substitution)
    echo "$token"
}

# Function to start onramp workflow
start_onramp_workflow() {
    local token="$1"
    local amount="$2"
    local token_asset="$3"
    local destination="$4"
    local policy_secret="${5:-}"
    
    echo_with_color $BLUE "🚀 Starting onramp workflow..." >&2
    echo_with_color $CYAN "   Amount: $amount" >&2
    echo_with_color $CYAN "   Token: $token_asset" >&2
    echo_with_color $CYAN "   Destination: $destination" >&2
    
    local payload="{\"amount\": \"$amount\", \"token\": \"$token_asset\", \"destination\": \"$destination\""
    if [[ -n "$policy_secret" ]]; then
        payload="${payload}, \"policy_secret\": \"$policy_secret\""
    fi
    payload="${payload}}"
    
    local http_code=$(curl -s -o /tmp/onramp_start_response.json -w "%{http_code}" -X POST "${PAY_SERVICE_URL}/api/onramp/workflow" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d "$payload" 2>&1)
    
    local response=$(cat /tmp/onramp_start_response.json 2>/dev/null)
    rm -f /tmp/onramp_start_response.json
    
    if [[ -z "$response" ]]; then
        echo_with_color $RED "❌ Failed to start workflow: no response (HTTP $http_code)" >&2
        return 1
    fi
    
    # Check if response is HTML (nginx error page)
    if [[ "$response" =~ ^\<html\> ]]; then
        echo_with_color $RED "❌ Server returned HTML error page (HTTP $http_code)" >&2
        echo_with_color $YELLOW "   This usually means the endpoint doesn't exist or nginx rejected the request" >&2
        echo_with_color $YELLOW "   Check that the route is registered: POST ${PAY_SERVICE_URL}/api/onramp/workflow" >&2
        return 1
    fi
    
    # Show raw response for debugging on error
    if [[ "$http_code" != "200" ]]; then
        echo_with_color $YELLOW "   HTTP Status: $http_code" >&2
        echo_with_color $YELLOW "   Response: $response" >&2
    fi
    
    local status=$(echo "$response" | jq -r '.status' 2>/dev/null)
    local workflow_id=$(echo "$response" | jq -r '.workflow_id' 2>/dev/null)
    local error=$(echo "$response" | jq -r '.error // empty' 2>/dev/null)
    
    # Check if jq parsing failed (likely invalid JSON)
    if [[ -z "$status" && -n "$response" ]]; then
        echo_with_color $RED "❌ Failed to parse JSON response" >&2
        echo_with_color $YELLOW "   Response: $response" >&2
        return 1
    fi
    
    if [[ "$status" != "accepted" ]]; then
        echo_with_color $RED "❌ Failed to start workflow: status=$status, error=$error" >&2
        echo_with_color $YELLOW "Full response: $response" >&2
        return 1
    fi
    
    if [[ -z "$workflow_id" || "$workflow_id" == "null" ]]; then
        echo_with_color $RED "❌ No workflow_id in response" >&2
        echo_with_color $YELLOW "Response: $response" >&2
        return 1
    fi
    
    echo_with_color $GREEN "✅ Workflow started successfully" >&2
    echo_with_color $CYAN "   Workflow ID: $workflow_id" >&2
    
    # Only output workflow_id to stdout (for command substitution)
    echo "$workflow_id"
}

# Function to get workflow status
get_workflow_status() {
    local token="$1"
    local workflow_id="$2"
    
    local http_code=$(curl -s -o /tmp/onramp_status_response.json -w "%{http_code}" -X GET "${PAY_SERVICE_URL}/api/onramp/workflow/${workflow_id}" \
        -H "Authorization: Bearer $token")
    
    local response=$(cat /tmp/onramp_status_response.json 2>/dev/null)
    rm -f /tmp/onramp_status_response.json
    
    if [[ -z "$response" ]]; then
        echo_with_color $RED "❌ Failed to get workflow status: no response (HTTP $http_code)"
        return 1
    fi
    
    # Check if response is HTML (nginx error page)
    if [[ "$response" =~ ^\<html\> ]]; then
        echo_with_color $RED "❌ Server returned HTML error page (HTTP $http_code)" >&2
        echo_with_color $YELLOW "   This usually means the endpoint doesn't exist or nginx rejected the request" >&2
        return 1
    fi
    
    # If HTTP error, show response
    if [[ "$http_code" != "200" ]]; then
        echo_with_color $YELLOW "   HTTP Status: $http_code" >&2
        echo_with_color $YELLOW "   Response: $response" >&2
    fi
    
    # Only output response JSON to stdout (for command substitution)
    echo "$response"
}

# Function to poll workflow until completion
poll_workflow() {
    local token="$1"
    local workflow_id="$2"
    
    echo_with_color $BLUE "⏳ Polling workflow status (max $MAX_POLLS polls, every ${POLL_INTERVAL}s)..."
    
    local poll_count=0
    while [ $poll_count -lt $MAX_POLLS ]; do
        poll_count=$((poll_count + 1))
        
        local status_response=$(get_workflow_status "$token" "$workflow_id")
        
        if [[ -z "$status_response" ]]; then
            echo_with_color $YELLOW "⚠️  Poll $poll_count: No response, retrying..."
            sleep $POLL_INTERVAL
            continue
        fi
        
        # Debug: Show raw response on first poll or if parsing fails
        if [[ $poll_count -eq 1 ]] || [[ -z "$status_response" ]]; then
            echo_with_color $YELLOW "   Raw response: $status_response"
        fi
        
        local workflow_status=$(echo "$status_response" | jq -r '.workflow_status // empty' 2>/dev/null)
        local current_step=$(echo "$status_response" | jq -r '.current_step // empty' 2>/dev/null)
        local error=$(echo "$status_response" | jq -r '.error // empty' 2>/dev/null)
        local result=$(echo "$status_response" | jq -r '.result // empty' 2>/dev/null)
        local response_status=$(echo "$status_response" | jq -r '.status // empty' 2>/dev/null)
        
        # Check if jq parsing failed
        if [[ -z "$workflow_status" && -n "$status_response" ]]; then
            echo_with_color $YELLOW "   ⚠️  jq parsing may have failed. Raw response: $status_response"
        fi
        
        echo_with_color $CYAN "📊 Poll $poll_count/$MAX_POLLS: Status=$workflow_status, Step=$current_step, Response=$response_status"
        
        case "$workflow_status" in
            "completed")
                echo_with_color $GREEN "✅ Workflow completed successfully!"
                
                if [[ "$result" != "null" && -n "$result" ]]; then
                    local mint_id=$(echo "$result" | jq -r '.mint_message_id // "N/A"' 2>/dev/null)
                    local deposit_id=$(echo "$result" | jq -r '.deposit_message_id // "N/A"' 2>/dev/null)
                    local instant_id=$(echo "$result" | jq -r '.instant_message_id // "N/A"' 2>/dev/null)
                    local payment_id=$(echo "$result" | jq -r '.payment_id // "N/A"' 2>/dev/null)
                    
                    echo_with_color $GREEN "📋 Workflow Results:"
                    echo_with_color $CYAN "   Mint Message ID: $mint_id"
                    echo_with_color $CYAN "   Deposit Message ID: $deposit_id"
                    echo_with_color $CYAN "   Instant Payment Message ID: $instant_id"
                    echo_with_color $CYAN "   Payment ID: $payment_id"
                fi
                
                echo "$status_response"
                return 0
                ;;
            "failed")
                echo_with_color $RED "❌ Workflow failed: $error"
                echo_with_color $YELLOW "Full response: $status_response"
                return 1
                ;;
            "pending"|"running")
                echo_with_color $YELLOW "   ⏳ Still processing... (step: $current_step)"
                sleep $POLL_INTERVAL
                ;;
            *)
                echo_with_color $YELLOW "   ⚠️  Unknown status: $workflow_status"
                sleep $POLL_INTERVAL
                ;;
        esac
    done
    
    echo_with_color $RED "❌ Workflow timed out after $MAX_POLLS polls"
    return 1
}

# Function to check if endpoint exists
check_endpoint_exists() {
    local token="$1"
    
    echo_with_color $BLUE "🔍 Checking if onramp workflow endpoint exists..." >&2
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS "${PAY_SERVICE_URL}/api/onramp/workflow" \
        -H "Authorization: Bearer $token" 2>&1)
    
    # Try a HEAD request if OPTIONS doesn't work
    if [[ "$http_code" == "405" ]] || [[ "$http_code" == "000" ]]; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${PAY_SERVICE_URL}/api/onramp/workflow" \
            -H "Authorization: Bearer $token" 2>&1)
    fi
    
    # 404 means endpoint doesn't exist, 405 means method not allowed (but endpoint exists), 400/500 means endpoint exists but has issues
    if [[ "$http_code" == "404" ]]; then
        echo_with_color $RED "❌ Endpoint not found (404). The onramp workflow route may not be deployed." >&2
        echo_with_color $YELLOW "   This endpoint needs to be compiled and deployed to the payments service." >&2
        echo_with_color $YELLOW "   Route should be: POST ${PAY_SERVICE_URL}/api/onramp/workflow" >&2
        return 1
    elif [[ "$http_code" == "405" ]]; then
        echo_with_color $GREEN "✅ Endpoint exists (405 Method Not Allowed is expected for GET/OPTIONS)" >&2
        return 0
    elif [[ "$http_code" =~ ^[45] ]]; then
        echo_with_color $YELLOW "⚠️  Endpoint responded with HTTP $http_code (endpoint may exist but have issues)" >&2
        return 0
    else
        echo_with_color $YELLOW "⚠️  Could not determine endpoint status (HTTP $http_code)" >&2
        return 0
    fi
}

# Main execution
main() {
    echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
    echo_with_color $PURPLE "  YieldFabric Onramping Workflow Test"
    echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
    echo ""
    echo_with_color $CYAN "Configuration:"
    echo_with_color $CYAN "  Auth Service: $AUTH_SERVICE_URL"
    echo_with_color $CYAN "  Payments Service: $PAY_SERVICE_URL"
    echo_with_color $CYAN "  User: $USER_EMAIL"
    if [[ -n "$USER_PASSWORD" ]]; then
        echo_with_color $CYAN "  Password: ${USER_PASSWORD:0:3}*** (hidden)"
    else
        echo_with_color $RED "  Password: NOT SET"
    fi
    echo_with_color $CYAN "  Amount: $AMOUNT"
    echo_with_color $CYAN "  Token: $TOKEN"
    echo_with_color $CYAN "  Destination: $DESTINATION"
    echo ""
    
    # Validate password is provided
    if [[ -z "$USER_PASSWORD" ]]; then
        echo_with_color $RED "❌ Error: Password is required for login"
        echo_with_color $YELLOW "   Usage: $0 [email] [password] [amount] [token] [destination] [policy_secret]"
        exit 1
    fi
    
    # Step 1: Login
    local jwt_token
    jwt_token=$(login_user "$USER_EMAIL" "$USER_PASSWORD")
    local login_result=$?
    
    # Check if login failed
    if [[ $login_result -ne 0 || -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Authentication failed"
        exit 1
    fi
    
    echo ""
    
    # Step 1.5: Check if endpoint exists (optional check)
    if ! check_endpoint_exists "$jwt_token"; then
        echo_with_color $YELLOW ""
        echo_with_color $YELLOW "💡 Tip: To test locally, set these environment variables:"
        echo_with_color $CYAN "   export AUTH_SERVICE_URL=http://localhost:3000"
        echo_with_color $CYAN "   export PAY_SERVICE_URL=http://localhost:3002"
        echo_with_color $YELLOW ""
        echo_with_color $YELLOW "Or deploy the updated payments service with the onramp workflow routes."
        echo_with_color $YELLOW ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo ""
    
    # Step 2: Start workflow
    local workflow_id=$(start_onramp_workflow "$jwt_token" "$AMOUNT" "$TOKEN" "$DESTINATION" "$POLICY_SECRET")
    local start_result=$?
    
    if [[ $start_result -ne 0 || -z "$workflow_id" ]]; then
        echo_with_color $RED "❌ Failed to start workflow or get workflow_id"
        if [[ -n "$workflow_id" ]]; then
            echo_with_color $YELLOW "   Got workflow_id: $workflow_id"
        fi
        exit 1
    fi
    
    # Validate workflow_id format (should be a UUID)
    if ! echo "$workflow_id" | grep -qE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
        echo_with_color $RED "❌ Invalid workflow_id format (expected UUID): $workflow_id" >&2
        echo_with_color $YELLOW "   This usually means the workflow start failed. Check the error messages above." >&2
        exit 1
    fi
    
    echo ""
    
    # Step 3: Poll for completion
    echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
    echo_with_color $PURPLE "  Polling Workflow Status"
    echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
    echo ""
    
    poll_workflow "$jwt_token" "$workflow_id"
    local poll_result=$?
    
    echo ""
    
    # Final status
    if [[ $poll_result -eq 0 ]]; then
        echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
        echo_with_color $GREEN "  ✅ Test Completed Successfully!"
        echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
        exit 0
    else
        echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
        echo_with_color $RED "  ❌ Test Failed"
        echo_with_color $PURPLE "═══════════════════════════════════════════════════════════"
        exit 1
    fi
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo_with_color $RED "❌ Error: jq is required but not installed"
    echo_with_color $YELLOW "Install jq: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo_with_color $RED "❌ Error: curl is required but not installed"
    exit 1
fi

# Run main function
main "$@"
