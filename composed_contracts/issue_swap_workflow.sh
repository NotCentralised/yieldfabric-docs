#!/bin/bash

# Test script for the workflow-based Issue and Swap Composed Contract API endpoint
# This workflow creates two obligations, accepts both, and creates a swap for both vs payment

# Load environment variables from .env files (if present)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

for env_file in "${REPO_ROOT}/.env" "${REPO_ROOT}/.env.local" "${SCRIPT_DIR}/.env"; do
    if [ -f "$env_file" ]; then
        # shellcheck disable=SC1090
        set -a
        source "$env_file"
        set +a
    fi
done

# Configuration
# To test locally, set: export PAY_SERVICE_URL=http://localhost:3002
# To test locally, set: export AUTH_SERVICE_URL=http://localhost:3000
PAY_SERVICE_URL="${PAY_SERVICE_URL:-https://pay.yieldfabric.com}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth.yieldfabric.com}"

# Colors for output (matching executor scripts)
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

check_service_running() {
    local service_name=$1
    local service_url=$2

    echo_with_color $BLUE "  🔍 Checking if ${service_name} is running..."

    if [[ "$service_url" =~ ^https?:// ]]; then
        if curl -s -f -o /dev/null --max-time 5 "${service_url}/health" 2>/dev/null || \
           curl -s -f -o /dev/null --max-time 5 "$service_url" 2>/dev/null; then
            echo_with_color $GREEN "    ✅ ${service_name} is reachable"
            return 0
        else
            echo_with_color $RED "    ❌ ${service_name} is not reachable at ${service_url}"
            return 1
        fi
    else
        local port=$service_url
        if nc -z localhost $port 2>/dev/null; then
            echo_with_color $GREEN "    ✅ ${service_name} is running on port ${port}"
            return 0
        else
            echo_with_color $RED "    ❌ ${service_name} is not running on port ${port}"
            return 1
        fi
    fi
}

login_user() {
    local email="$1"
    local password="$2"
    local services_json='["vault", "payments"]'

    echo_with_color $BLUE "  🔐 Logging in user: $email" >&2

    local http_response
    http_response=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\", \"password\": \"$password\", \"services\": $services_json}")

    echo_with_color $BLUE "    📡 Login response received" >&2

    if [[ -n "$http_response" ]]; then
        local token
        token=$(echo "$http_response" | jq -r '.token // .access_token // .jwt // empty')
        if [[ -n "$token" && "$token" != "null" ]]; then
            echo_with_color $GREEN "    ✅ Login successful" >&2
            echo "$token"
            return 0
        else
            echo_with_color $RED "    ❌ No token in response" >&2
            echo_with_color $YELLOW "    Response: $http_response" >&2
            return 1
        fi
    else
        echo_with_color $RED "    ❌ Login failed: no response" >&2
        return 1
    fi
}

issue_and_swap_workflow() {
    local jwt_token=$1
    local obligation_1_json=$2
    local obligation_2_json=$3
    local counterparty=$4
    local payment_amount=$5
    local payment_denomination=$6
    local deadline=$7

    echo_with_color $CYAN "🏦 Starting issue and swap workflow..." >&2

    local request_body
    if [[ -n "$deadline" && "$deadline" != "null" ]]; then
        request_body=$(jq -n \
            --argjson obligation_1 "$obligation_1_json" \
            --argjson obligation_2 "$obligation_2_json" \
            --arg counterparty "$counterparty" \
            --arg payment_amount "$payment_amount" \
            --arg payment_denomination "$payment_denomination" \
            --arg deadline "$deadline" \
            '{
                obligation_1: $obligation_1,
                obligation_2: $obligation_2,
                counterparty: $counterparty,
                payment_amount: $payment_amount,
                payment_denomination: $payment_denomination,
                deadline: $deadline
            }')
    else
        request_body=$(jq -n \
            --argjson obligation_1 "$obligation_1_json" \
            --argjson obligation_2 "$obligation_2_json" \
            --arg counterparty "$counterparty" \
            --arg payment_amount "$payment_amount" \
            --arg payment_denomination "$payment_denomination" \
            '{
                obligation_1: $obligation_1,
                obligation_2: $obligation_2,
                counterparty: $counterparty,
                payment_amount: $payment_amount,
                payment_denomination: $payment_denomination
            }')
    fi

    echo_with_color $BLUE "  📋 Request body:" >&2
    echo "$request_body" | jq '.' | sed 's/^/    /' >&2

    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/api/composed_contract/issue_swap_workflow" >&2

    local temp_file
    temp_file=$(mktemp)
    local http_code
    http_code=$(curl -s -w "%{http_code}" -o "$temp_file" -X POST "${PAY_SERVICE_URL}/api/composed_contract/issue_swap_workflow" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt_token}" \
        -d "$request_body")

    local http_response
    http_response=$(cat "$temp_file")
    rm -f "$temp_file"

    echo_with_color $BLUE "  📡 Response received (HTTP $http_code)" >&2

    if [[ -z "$http_response" ]]; then
        echo_with_color $YELLOW "  ⚠️  Warning: Empty response body" >&2
    fi

    # Log the full response for debugging (especially for 422 errors)
    if [[ "$http_code" == "422" ]]; then
        echo_with_color $YELLOW "  ⚠️  Validation error - full response:" >&2
        echo "$http_response" | jq '.' 2>/dev/null | sed 's/^/    /' >&2 || echo "$http_response" | sed 's/^/    /' >&2
    fi

    echo "$http_response"
}

poll_workflow_status() {
    local workflow_id=$1
    local max_attempts=${2:-120}
    local delay_seconds=${3:-1}

    echo_with_color $CYAN "🔄 Polling workflow status for ID: ${workflow_id}" >&2

    local attempt
    for ((attempt=1; attempt<=max_attempts; attempt++)); do
        local url="${PAY_SERVICE_URL}/api/composed_contract/issue_swap_workflow/${workflow_id}"
        echo_with_color $BLUE "  📡 Attempt ${attempt}/${max_attempts}: GET ${url}" >&2

        local response
        response=$(curl -s "$url")

        if [[ -z "$response" ]]; then
            echo_with_color $YELLOW "  ⚠️  Empty response from status endpoint" >&2
        else
            local workflow_status
            workflow_status=$(echo "$response" | jq -r '.workflow_status // empty' 2>/dev/null)
            
            local current_step
            current_step=$(echo "$response" | jq -r '.current_step // empty' 2>/dev/null)

            echo_with_color $BLUE "  🔎 Current workflow_status: ${workflow_status:-unknown}" >&2
            if [[ -n "$current_step" && "$current_step" != "unknown" ]]; then
                echo_with_color $CYAN "  📍 Current step: ${current_step}" >&2
            fi

            if [[ "$workflow_status" == "completed" || "$workflow_status" == "failed" || "$workflow_status" == "cancelled" ]]; then
                echo "$response"
                return 0
            fi
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            sleep "$delay_seconds"
        fi
    done

    echo_with_color $RED "  ❌ Workflow did not complete within ${max_attempts} attempts" >&2
    return 1
}

main() {
    echo_with_color $CYAN "🚀 Starting Issue and Swap Composed Contract WorkFlow API Test"
    echo ""

    # Test parameters
    USER_EMAIL="${USER_EMAIL:-issuer@yieldfabric.com}"
    PASSWORD="${PASSWORD:-issuer_password}"
    DENOMINATION="${DENOMINATION:-aud-token-asset}"
    COUNTERPART="${COUNTERPART:-investor@yieldfabric.com}"
    END_DATE="${END_DATE:-2025-12-31}"

    # Obligation amounts
    OBLIGATION_1_NOTIONAL="${OBLIGATION_1_NOTIONAL:-100}"
    OBLIGATION_1_NAME="${OBLIGATION_1_NAME:-Annuity Stream}"
    OBLIGATION_1_DESCRIPTION="${OBLIGATION_1_DESCRIPTION:-Annuity Stream Obligation}"
    
    OBLIGATION_2_NOTIONAL="${OBLIGATION_2_NOTIONAL:-50}"
    OBLIGATION_2_NAME="${OBLIGATION_2_NAME:-Redemption}"
    OBLIGATION_2_DESCRIPTION="${OBLIGATION_2_DESCRIPTION:-Redemption Obligation}"

    # Payment expected from counterparty
    PAYMENT_AMOUNT="${PAYMENT_AMOUNT:-125}"
    PAYMENT_DENOMINATION="${PAYMENT_DENOMINATION:-$DENOMINATION}"
    DEADLINE="${DEADLINE:-${END_DATE}T23:59:59Z}"

    # Coupon dates for obligation 1
    COUPON_DATES=(
        "2025-12-01T00:00:00Z"
        "2025-12-05T00:00:00Z"
        "2025-12-10T00:00:00Z"
        "2025-12-15T00:00:00Z"
        "2025-12-20T00:00:00Z"
    )

    # Build coupon payments array JSON using jq
    local coupon_payments_json
    coupon_payments_json=$(printf '%s\n' "${COUPON_DATES[@]}" | jq -R '{oracleAddress: null, oracleOwner: null, oracleKeySender: null, oracleValueSenderSecret: null, oracleKeyRecipient: null, oracleValueRecipientSecret: null, unlockSender: ., unlockReceiver: ., linearVesting: null}' | jq -s '.')

    # Build Obligation 1 JSON (Annuity stream with multiple payments)
    # NOTE: counterpart = obligor = issuer so that issuer can auto-accept
    # The swap will transfer these obligations to the actual counterparty (investor)
    local obligation_1_json
    obligation_1_json=$(jq -n \
        --arg counterpart "$USER_EMAIL" \
        --arg denomination "$DENOMINATION" \
        --arg obligor "$USER_EMAIL" \
        --arg notional "$OBLIGATION_1_NOTIONAL" \
        --arg end_date "${END_DATE}T23:59:59Z" \
        --arg name "$OBLIGATION_1_NAME" \
        --arg description "$OBLIGATION_1_DESCRIPTION" \
        --arg coupon_amount "$(( OBLIGATION_1_NOTIONAL / ${#COUPON_DATES[@]} ))" \
        --argjson payments "$coupon_payments_json" \
        '{
            counterpart: $counterpart,
            denomination: $denomination,
            obligor: $obligor,
            notional: $notional,
            expiry: $end_date,
            data: {
                name: $name,
                description: $description
            },
            initialPayments: {
                amount: $coupon_amount,
                denomination: $denomination,
                payments: $payments
            }
        }')

    # Build Obligation 2 JSON (Redemption with single payment)
    # NOTE: counterpart = obligor = issuer so that issuer can auto-accept
    # The swap will transfer these obligations to the actual counterparty (investor)
    local obligation_2_json
    obligation_2_json=$(jq -n \
        --arg counterpart "$USER_EMAIL" \
        --arg denomination "$DENOMINATION" \
        --arg obligor "$USER_EMAIL" \
        --arg notional "$OBLIGATION_2_NOTIONAL" \
        --arg end_date "${END_DATE}T23:59:59Z" \
        --arg name "$OBLIGATION_2_NAME" \
        --arg description "$OBLIGATION_2_DESCRIPTION" \
        '{
            counterpart: $counterpart,
            denomination: $denomination,
            obligor: $obligor,
            notional: $notional,
            expiry: $end_date,
            data: {
                name: $name,
                description: $description
            },
            initialPayments: {
                amount: $notional,
                denomination: $denomination,
                payments: [{
                    oracleAddress: null,
                    oracleOwner: null,
                    oracleKeySender: null,
                    oracleValueSenderSecret: null,
                    oracleKeyRecipient: null,
                    oracleValueRecipientSecret: null,
                    unlockSender: $end_date,
                    unlockReceiver: $end_date,
                    linearVesting: null
                }]
            }
        }')

    echo_with_color $BLUE "📋 Configuration:"
    echo_with_color $BLUE "  API Base URL: ${PAY_SERVICE_URL}"
    echo_with_color $BLUE "  Auth Service: ${AUTH_SERVICE_URL}"
    echo_with_color $BLUE "  User (Initiator): ${USER_EMAIL}"
    echo_with_color $BLUE "  Counterparty: ${COUNTERPART}"
    echo_with_color $BLUE "  Denomination: ${DENOMINATION}"
    echo_with_color $BLUE "  End Date: ${END_DATE}"
    echo ""
    echo_with_color $PURPLE "📄 Obligation 1 (${OBLIGATION_1_NAME}):"
    echo_with_color $BLUE "    Notional: ${OBLIGATION_1_NOTIONAL}"
    echo_with_color $BLUE "    Payments: ${#COUPON_DATES[@]} coupon payments"
    echo ""
    echo_with_color $PURPLE "📄 Obligation 2 (${OBLIGATION_2_NAME}):"
    echo_with_color $BLUE "    Notional: ${OBLIGATION_2_NOTIONAL}"
    echo_with_color $BLUE "    Payments: 1 redemption payment"
    echo ""
    echo_with_color $PURPLE "💱 Swap Terms:"
    echo_with_color $BLUE "    Expected Payment from Counterparty: ${PAYMENT_AMOUNT} ${PAYMENT_DENOMINATION}"
    echo_with_color $BLUE "    Deadline: ${DEADLINE}"
    echo ""

    if ! check_service_running "Auth Service" "$AUTH_SERVICE_URL"; then
        echo_with_color $RED "❌ Auth service is not reachable at $AUTH_SERVICE_URL"
        return 1
    fi

    if ! check_service_running "Payments Service" "$PAY_SERVICE_URL"; then
        echo_with_color $RED "❌ Payments service is not reachable at $PAY_SERVICE_URL"
        echo_with_color $YELLOW "Please start the payments service:"
        echo "   Local: cd ../yieldfabric-payments && cargo run"
        echo_with_color $BLUE "   REST API endpoint will be available at: $PAY_SERVICE_URL/api/composed_contract/issue_swap_workflow"
        return 1
    fi

    # Check if the endpoint exists (basic check)
    local endpoint_check
    endpoint_check=$(curl -s -o /dev/null -w "%{http_code}" "${PAY_SERVICE_URL}/api/composed_contract/issue_swap_workflow" -X POST -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
    if [[ "$endpoint_check" == "404" ]]; then
        echo_with_color $YELLOW "⚠️  Warning: Endpoint returned 404. The server may need to be restarted to pick up the new routes."
        echo_with_color $YELLOW "   Make sure the server was built with the latest code including composed_contract_issue_swap workflow."
        echo ""
    fi

    echo ""

    echo_with_color $CYAN "🔐 Authenticating..."
    local jwt_token
    jwt_token=$(login_user "$USER_EMAIL" "$PASSWORD")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to get JWT token for user: $USER_EMAIL"
        return 1
    fi

    echo_with_color $GREEN "  ✅ JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    echo ""

    echo_with_color $CYAN "📤 Calling issue and swap workflow endpoint..."
    echo ""

    local start_response
    start_response=$(issue_and_swap_workflow \
        "$jwt_token" \
        "$obligation_1_json" \
        "$obligation_2_json" \
        "$COUNTERPART" \
        "$PAYMENT_AMOUNT" \
        "$PAYMENT_DENOMINATION" \
        "$DEADLINE")

    echo_with_color $BLUE "📡 Start API Response:"
    echo "$start_response" | jq '.' 2>/dev/null | sed 's/^/  /' || {
        echo_with_color $RED "  ⚠️  Start response is not valid JSON:"
        echo "$start_response" | sed 's/^/  /'
    }
    echo ""

    local workflow_id
    workflow_id=$(echo "$start_response" | jq -r '.workflow_id // empty' 2>/dev/null)

    if [[ -z "$workflow_id" || "$workflow_id" == "null" ]]; then
        echo_with_color $RED "❌ No workflow_id returned from start endpoint"
        
        # Check if we got a 404 (route not found)
        if echo "$start_response" | grep -qi "404\|not found" || [[ -z "$start_response" ]]; then
            echo_with_color $YELLOW "    ⚠️  Received 404 or empty response - the endpoint may not be registered"
            echo_with_color $YELLOW "    This usually means the server needs to be restarted with the latest code"
            echo_with_color $BLUE "    Please ensure:"
            echo_with_color $BLUE "      1. The server was built with: cd yieldfabric-payments && cargo build"
            echo_with_color $BLUE "      2. The server was restarted after adding the composed_contract_issue_swap workflow"
            echo_with_color $BLUE "      3. The route is registered at: /api/composed_contract/issue_swap_workflow"
        else
            local error_msg
            error_msg=$(echo "$start_response" | jq -r '.error // .message // "Unknown error"' 2>/dev/null)
            if [[ -z "$error_msg" || "$error_msg" == "null" ]]; then
                echo_with_color $RED "    Error: Invalid request (HTTP 422 - Unprocessable Entity)"
                echo_with_color $YELLOW "    Full response:"
                echo "$start_response" | jq '.' 2>/dev/null | sed 's/^/      /' || echo "$start_response" | sed 's/^/      /'
            else
                echo_with_color $RED "    Error: ${error_msg}"
            fi
        fi
        return 1
    fi

    echo_with_color $GREEN "  ✅ Workflow started with ID: ${workflow_id}"
    echo ""

    local final_response
    if ! final_response=$(poll_workflow_status "$workflow_id"); then
        echo_with_color $RED "❌ Workflow did not complete successfully"
        return 1
    fi

    echo_with_color $BLUE "📡 Final Workflow Status Response:"
    echo "$final_response" | jq '.' 2>/dev/null | sed 's/^/  /' || {
        echo_with_color $RED "  ⚠️  Final response is not valid JSON:"
        echo "$final_response" | sed 's/^/  /'
    }
    echo ""

    local workflow_status
    workflow_status=$(echo "$final_response" | jq -r '.workflow_status // empty' 2>/dev/null)

    if [[ "$workflow_status" == "completed" ]]; then
        echo_with_color $GREEN "    ✅ Issue and swap workflow completed successfully!"
        echo ""
        echo_with_color $BLUE "  📋 Result Details:"
        echo_with_color $BLUE "      Obligation 1 ID: $(echo "$final_response" | jq -r '.result.obligation_1_id // "N/A"')"
        echo_with_color $BLUE "      Obligation 2 ID: $(echo "$final_response" | jq -r '.result.obligation_2_id // "N/A"')"
        echo_with_color $BLUE "      Swap ID: $(echo "$final_response" | jq -r '.result.swap_id // "N/A"')"
        echo_with_color $BLUE "      Swap Message ID: $(echo "$final_response" | jq -r '.result.swap_message_id // "N/A"')"
        echo ""
        echo_with_color $GREEN "🎉 Issue and swap workflow test completed successfully! ✨"
        echo ""
        echo_with_color $CYAN "📝 Summary:"
        echo_with_color $BLUE "   • Created 2 obligations (${OBLIGATION_1_NAME} and ${OBLIGATION_2_NAME})"
        echo_with_color $BLUE "   • Accepted both obligations"
        echo_with_color $BLUE "   • Created swap: both obligations vs ${PAYMENT_AMOUNT} ${PAYMENT_DENOMINATION} from ${COUNTERPART}"
        return 0
    else
        echo_with_color $RED "    ❌ Issue and swap workflow ended in status: ${workflow_status}"
        local error_msg
        error_msg=$(echo "$final_response" | jq -r '.error // "Unknown error"' 2>/dev/null)
        echo_with_color $RED "    Error: ${error_msg}"
        echo_with_color $BLUE "    Full response:"
        echo "$final_response" | sed 's/^/      /'
        return 1
    fi
}

main "$@"

