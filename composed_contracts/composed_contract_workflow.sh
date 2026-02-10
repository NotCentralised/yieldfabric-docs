#!/bin/bash

# Test script for the generic Composed Contract workflow API endpoint
# This workflow supports parametric actions through workflow_config.actions array
# Actions are executed in the order specified, making it completely flexible

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

composed_contract_workflow() {
    local jwt_token=$1
    local name=$2
    local description=$3
    local obligations_json=$4
    local counterparty=$5
    local payment_amount=$6
    local payment_denomination=$7
    local deadline=$8
    local actions_json=$9
    local transfer_destination_id=${10}
    local transfer_destination_wallet_id=${11}

    echo_with_color $CYAN "🏦 Starting generic composed contract workflow..." >&2

    # Build request body with optional fields
    local request_body
    if [[ -n "$actions_json" && "$actions_json" != "null" && "$actions_json" != "[]" ]]; then
        # Check if create_swap is in actions
        local has_swap=false
        if echo "$actions_json" | jq -e 'index("create_swap") != null' >/dev/null 2>&1; then
            has_swap=true
        fi
        
        # Check if create_transfer is in actions
        local has_transfer=false
        if echo "$actions_json" | jq -e 'index("create_transfer") != null' >/dev/null 2>&1; then
            has_transfer=true
        fi
        
        # Request with workflow_config.actions
        if [[ "$has_swap" == "true" && -n "$counterparty" && "$counterparty" != "null" && -n "$payment_amount" && -n "$payment_denomination" ]]; then
            # Has swap fields
            if [[ -n "$deadline" && "$deadline" != "null" ]]; then
                if [[ "$has_transfer" == "true" && -n "$transfer_destination_id" && "$transfer_destination_id" != "null" ]]; then
                    # Has both swap and transfer
                    request_body=$(jq -n \
                        --arg name "$name" \
                        --arg description "$description" \
                        --argjson obligations "$obligations_json" \
                        --arg counterparty "$counterparty" \
                        --arg payment_amount "$payment_amount" \
                        --arg payment_denomination "$payment_denomination" \
                        --arg deadline "$deadline" \
                        --arg transfer_destination_id "$transfer_destination_id" \
                        --argjson actions "$actions_json" \
                        '{
                            name: $name,
                            description: $description,
                            obligations: $obligations,
                            counterparty: $counterparty,
                            payment_amount: $payment_amount,
                            payment_denomination: $payment_denomination,
                            deadline: $deadline,
                            transfer_destination_id: $transfer_destination_id,
                            workflow_config: {
                                actions: $actions
                            }
                        }')
                else
                    # Has swap only
                    request_body=$(jq -n \
                        --arg name "$name" \
                        --arg description "$description" \
                        --argjson obligations "$obligations_json" \
                        --arg counterparty "$counterparty" \
                        --arg payment_amount "$payment_amount" \
                        --arg payment_denomination "$payment_denomination" \
                        --arg deadline "$deadline" \
                        --argjson actions "$actions_json" \
                        '{
                            name: $name,
                            description: $description,
                            obligations: $obligations,
                            counterparty: $counterparty,
                            payment_amount: $payment_amount,
                            payment_denomination: $payment_denomination,
                            deadline: $deadline,
                            workflow_config: {
                                actions: $actions
                            }
                        }')
                fi
            else
                if [[ "$has_transfer" == "true" && -n "$transfer_destination_id" && "$transfer_destination_id" != "null" ]]; then
                    # Has both swap and transfer (no deadline)
                    request_body=$(jq -n \
                        --arg name "$name" \
                        --arg description "$description" \
                        --argjson obligations "$obligations_json" \
                        --arg counterparty "$counterparty" \
                        --arg payment_amount "$payment_amount" \
                        --arg payment_denomination "$payment_denomination" \
                        --arg transfer_destination_id "$transfer_destination_id" \
                        --argjson actions "$actions_json" \
                        '{
                            name: $name,
                            description: $description,
                            obligations: $obligations,
                            counterparty: $counterparty,
                            payment_amount: $payment_amount,
                            payment_denomination: $payment_denomination,
                            transfer_destination_id: $transfer_destination_id,
                            workflow_config: {
                                actions: $actions
                            }
                        }')
                else
                    # Has swap only (no deadline)
                    request_body=$(jq -n \
                        --arg name "$name" \
                        --arg description "$description" \
                        --argjson obligations "$obligations_json" \
                        --arg counterparty "$counterparty" \
                        --arg payment_amount "$payment_amount" \
                        --arg payment_denomination "$payment_denomination" \
                        --argjson actions "$actions_json" \
                        '{
                            name: $name,
                            description: $description,
                            obligations: $obligations,
                            counterparty: $counterparty,
                            payment_amount: $payment_amount,
                            payment_denomination: $payment_denomination,
                            workflow_config: {
                                actions: $actions
                            }
                        }')
                fi
            fi
        elif [[ "$has_transfer" == "true" && -n "$transfer_destination_id" && "$transfer_destination_id" != "null" ]]; then
            # Has transfer only (no swap)
            request_body=$(jq -n \
                --arg name "$name" \
                --arg description "$description" \
                --argjson obligations "$obligations_json" \
                --arg transfer_destination_id "$transfer_destination_id" \
                --argjson actions "$actions_json" \
                '{
                    name: $name,
                    description: $description,
                    obligations: $obligations,
                    transfer_destination_id: $transfer_destination_id,
                    workflow_config: {
                        actions: $actions
                    }
                }')
        else
            # No swap or transfer fields
            request_body=$(jq -n \
                --arg name "$name" \
                --arg description "$description" \
                --argjson obligations "$obligations_json" \
                --argjson actions "$actions_json" \
                '{
                    name: $name,
                    description: $description,
                    obligations: $obligations,
                    workflow_config: {
                        actions: $actions
                    }
                }')
        fi
    else
        # Default actions (backward compatible - no workflow_config)
        if [[ -n "$counterparty" && "$counterparty" != "null" && -n "$payment_amount" && -n "$payment_denomination" ]]; then
            if [[ -n "$deadline" && "$deadline" != "null" ]]; then
                request_body=$(jq -n \
                    --arg name "$name" \
                    --arg description "$description" \
                    --argjson obligations "$obligations_json" \
                    --arg counterparty "$counterparty" \
                    --arg payment_amount "$payment_amount" \
                    --arg payment_denomination "$payment_denomination" \
                    --arg deadline "$deadline" \
                    '{
                        name: $name,
                        description: $description,
                        obligations: $obligations,
                        counterparty: $counterparty,
                        payment_amount: $payment_amount,
                        payment_denomination: $payment_denomination,
                        deadline: $deadline
                    }')
            else
                request_body=$(jq -n \
                    --arg name "$name" \
                    --arg description "$description" \
                    --argjson obligations "$obligations_json" \
                    --arg counterparty "$counterparty" \
                    --arg payment_amount "$payment_amount" \
                    --arg payment_denomination "$payment_denomination" \
                    '{
                        name: $name,
                        description: $description,
                        obligations: $obligations,
                        counterparty: $counterparty,
                        payment_amount: $payment_amount,
                        payment_denomination: $payment_denomination
                    }')
            fi
        else
            # No swap fields, no workflow_config (default actions)
            request_body=$(jq -n \
                --arg name "$name" \
                --arg description "$description" \
                --argjson obligations "$obligations_json" \
                '{
                    name: $name,
                    description: $description,
                    obligations: $obligations
                }')
        fi
    fi

    echo_with_color $BLUE "  📋 Request body:" >&2
    echo "$request_body" | jq '.' | sed 's/^/    /' >&2

    echo_with_color $BLUE "  🌐 Making REST API request to: ${PAY_SERVICE_URL}/api/composed_contract/workflow" >&2

    local temp_file
    temp_file=$(mktemp)
    local http_code
    http_code=$(curl -s -w "%{http_code}" -o "$temp_file" -X POST "${PAY_SERVICE_URL}/api/composed_contract/workflow" \
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
        # Use unified workflow status endpoint - works for all workflow types
        local url="${PAY_SERVICE_URL}/api/workflows/${workflow_id}"
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
            
            local workflow_type
            workflow_type=$(echo "$response" | jq -r '.workflow_type // empty' 2>/dev/null)

            echo_with_color $BLUE "  🔎 Current workflow_status: ${workflow_status:-unknown}" >&2
            if [[ -n "$workflow_type" && "$workflow_type" != "null" ]]; then
                echo_with_color $CYAN "  📋 Workflow type: ${workflow_type}" >&2
            fi
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
    echo_with_color $CYAN "🚀 Starting Generic Composed Contract WorkFlow API Test"
    echo ""

    # Parse command-line arguments for username and password
    # Usage: ./composed_contract_workflow.sh [username] [password] [action_mode]
    # action_mode: "default" | "issue_only" | "issue_accept" | "issue_swap" | "all"
    # If not provided, falls back to environment variables, then defaults
    if [[ $# -ge 1 ]]; then
        USER_EMAIL="$1"
    elif [[ -n "${USER_EMAIL}" ]]; then
        # Use environment variable if set
        USER_EMAIL="${USER_EMAIL}"
    else
        # Default username
        USER_EMAIL="issuer@yieldfabric.com"
    fi

    if [[ $# -ge 2 ]]; then
        PASSWORD="$2"
    elif [[ -n "${PASSWORD}" ]]; then
        # Use environment variable if set
        PASSWORD="${PASSWORD}"
    else
        # Default password
        PASSWORD="issuer_password"
    fi

    # Action mode: determines which actions to include
    ACTION_MODE="${ACTION_MODE:-all}"
    if [[ $# -ge 3 ]]; then
        ACTION_MODE="$3"
    fi
    
    # Transfer destination (optional - only needed if create_transfer is in actions)
    TRANSFER_DESTINATION_ID="${TRANSFER_DESTINATION_ID:-investor@yieldfabric.com}"

    # Test parameters
    DENOMINATION="${DENOMINATION:-aud-token-asset}"
    COUNTERPART="${COUNTERPART:-investor@yieldfabric.com}"
    END_DATE="${END_DATE:-2027-01-31}"

    # Obligation amounts
    COUPON_AMOUNT="${COUPON_AMOUNT:-10000000000000000000000}"
    OBLIGATION_1_NAME="${OBLIGATION_1_NAME:-Coupons}"
    OBLIGATION_1_DESCRIPTION="${OBLIGATION_1_DESCRIPTION:-Coupon Strip}"
    
    OBLIGATION_2_NOTIONAL="${OBLIGATION_2_NOTIONAL:-100000000000000000000000}"
    OBLIGATION_2_NAME="${OBLIGATION_2_NAME:-Redemption}"
    OBLIGATION_2_DESCRIPTION="${OBLIGATION_2_DESCRIPTION:-Redemption Obligation}"

    # Payment expected from counterparty (optional - only needed if create_swap is in actions)
    PAYMENT_AMOUNT="${PAYMENT_AMOUNT:-12500000000000000000000}"
    PAYMENT_DENOMINATION="${PAYMENT_DENOMINATION:-$DENOMINATION}"
    DEADLINE="${DEADLINE:-${END_DATE}T23:59:59Z}"

    # Composed contract details
    COMPOSED_CONTRACT_NAME="${COMPOSED_CONTRACT_NAME:-Corporate Bond}"
    COMPOSED_CONTRACT_DESCRIPTION="${COMPOSED_CONTRACT_DESCRIPTION:-A generic composed contract with parametric actions}"

    # Determine actions based on mode
    local actions_json
    local use_swap_fields=false
    local use_transfer_fields=false
    
    case "$ACTION_MODE" in
        "issue_only")
            actions_json='["create_obligation"]'
            use_swap_fields=false
            use_transfer_fields=false
            echo_with_color $PURPLE "📋 Action Mode: Issue Only (create_obligation)"
            ;;
        "issue_accept")
            actions_json='["create_obligation", "accept_obligation", "wait_for_acceptance"]'
            use_swap_fields=false
            use_transfer_fields=false
            echo_with_color $PURPLE "📋 Action Mode: Issue + Accept (create_obligation, accept_obligation, wait_for_acceptance)"
            ;;
        "issue_accept_transfer")
            actions_json='["create_obligation", "accept_obligation", "wait_for_acceptance", "create_transfer"]'
            use_swap_fields=false
            use_transfer_fields=true
            echo_with_color $PURPLE "📋 Action Mode: Issue + Accept + Transfer (create_obligation, accept_obligation, wait_for_acceptance, create_transfer)"
            ;;
        "issue_swap")
            actions_json='["create_obligation", "create_swap"]'
            use_swap_fields=true
            use_transfer_fields=false
            echo_with_color $PURPLE "📋 Action Mode: Issue + Swap (create_obligation, create_swap)"
            ;;
        "all"|*)
            actions_json='["create_obligation", "accept_obligation", "wait_for_acceptance", "create_swap"]'
            use_swap_fields=true
            use_transfer_fields=false
            echo_with_color $PURPLE "📋 Action Mode: All Actions (create_obligation, accept_obligation, wait_for_acceptance, create_swap)"
            ;;
    esac
    echo ""

    # Coupon dates for obligation 1
    COUPON_DATES=(
        "2027-12-01T00:00:00Z"
        "2027-12-05T00:00:00Z"
        "2027-12-10T00:00:00Z"
        "2027-12-15T00:00:00Z"
        "2027-12-20T00:00:00Z"
    )

    # Build coupon payments array JSON using jq
    local coupon_payments_json
    coupon_payments_json=$(printf '%s\n' "${COUPON_DATES[@]}" | jq -R '{oracleAddress: null, oracleOwner: null, oracleKeySender: null, oracleValueSenderSecret: null, oracleKeyRecipient: null, oracleValueRecipientSecret: null, unlockSender: ., unlockReceiver: ., linearVesting: null}' | jq -s '.')

    # Build Obligation 1 JSON (Annuity stream with multiple payments)
    # NOTE: counterpart = obligor = issuer so that issuer can auto-accept
    local obligation_1_notional
    obligation_1_notional=$(jq -n --arg coupon "$COUPON_AMOUNT" --arg count "${#COUPON_DATES[@]}" '($coupon | tonumber) * ($count | tonumber) | tostring')
    
    OBLIGATION_1_NOTIONAL="${OBLIGATION_1_NOTIONAL:-$obligation_1_notional}"
    
    local obligation_1_json
    obligation_1_json=$(jq -n \
        --arg counterpart "$USER_EMAIL" \
        --arg denomination "$DENOMINATION" \
        --arg obligor "$USER_EMAIL" \
        --arg notional "$OBLIGATION_1_NOTIONAL" \
        --arg end_date "${END_DATE}T23:59:59Z" \
        --arg name "$OBLIGATION_1_NAME" \
        --arg description "$OBLIGATION_1_DESCRIPTION" \
        --arg coupon_amount "$COUPON_AMOUNT" \
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
    if [[ "$use_swap_fields" == "true" ]]; then
        echo_with_color $BLUE "  Counterparty: ${COUNTERPART}"
    fi
    echo_with_color $BLUE "  Denomination: ${DENOMINATION}"
    echo_with_color $BLUE "  End Date: ${END_DATE}"
    echo ""
    echo_with_color $PURPLE "📦 Composed Contract:"
    echo_with_color $BLUE "    Name: ${COMPOSED_CONTRACT_NAME}"
    echo_with_color $BLUE "    Description: ${COMPOSED_CONTRACT_DESCRIPTION}"
    echo ""
    echo_with_color $PURPLE "📄 Obligation 1 (${OBLIGATION_1_NAME}):"
    echo_with_color $BLUE "    Coupon Amount (per payment): ${COUPON_AMOUNT}"
    echo_with_color $BLUE "    Total Notional: ${OBLIGATION_1_NOTIONAL}"
    echo_with_color $BLUE "    Payments: ${#COUPON_DATES[@]} coupon payments"
    echo ""
    echo_with_color $PURPLE "📄 Obligation 2 (${OBLIGATION_2_NAME}):"
    echo_with_color $BLUE "    Notional: ${OBLIGATION_2_NOTIONAL}"
    echo_with_color $BLUE "    Payments: 1 redemption payment"
    echo ""
    
    if [[ "$use_swap_fields" == "true" ]]; then
        echo_with_color $PURPLE "💱 Swap Terms:"
        echo_with_color $BLUE "    Expected Payment from Counterparty: ${PAYMENT_AMOUNT} ${PAYMENT_DENOMINATION}"
        echo_with_color $BLUE "    Deadline: ${DEADLINE}"
        echo ""
    fi
    
    if [[ "$use_transfer_fields" == "true" ]]; then
        echo_with_color $PURPLE "🔄 Transfer Terms:"
        echo_with_color $BLUE "    Transfer Destination: ${TRANSFER_DESTINATION_ID}"
        echo ""
    fi

    if ! check_service_running "Auth Service" "$AUTH_SERVICE_URL"; then
        echo_with_color $RED "❌ Auth service is not reachable at $AUTH_SERVICE_URL"
        return 1
    fi

    if ! check_service_running "Payments Service" "$PAY_SERVICE_URL"; then
        echo_with_color $RED "❌ Payments service is not reachable at $PAY_SERVICE_URL"
        echo_with_color $YELLOW "Please start the payments service:"
        echo "   Local: cd ../yieldfabric-payments && cargo run"
        echo_with_color $BLUE "   REST API endpoint will be available at: $PAY_SERVICE_URL/api/composed_contract/workflow"
        return 1
    fi

    # Check if the endpoint exists (basic check)
    local endpoint_check
    endpoint_check=$(curl -s -o /dev/null -w "%{http_code}" "${PAY_SERVICE_URL}/api/composed_contract/workflow" -X POST -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
    if [[ "$endpoint_check" == "404" ]]; then
        echo_with_color $YELLOW "⚠️  Warning: Endpoint returned 404. The server may need to be restarted to pick up the new routes."
        echo_with_color $YELLOW "   Make sure the server was built with the latest code including composed_contract workflow."
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

    echo_with_color $CYAN "📤 Calling generic composed contract workflow endpoint..."
    echo ""

    # Combine obligations into an array
    local obligations_json
    obligations_json=$(jq -n --argjson ob1 "$obligation_1_json" --argjson ob2 "$obligation_2_json" '[$ob1, $ob2]')

    local start_response
    if [[ "$use_swap_fields" == "true" ]]; then
        if [[ "$use_transfer_fields" == "true" ]]; then
            # Has both swap and transfer fields
            start_response=$(composed_contract_workflow \
                "$jwt_token" \
                "$COMPOSED_CONTRACT_NAME" \
                "$COMPOSED_CONTRACT_DESCRIPTION" \
                "$obligations_json" \
                "$COUNTERPART" \
                "$PAYMENT_AMOUNT" \
                "$PAYMENT_DENOMINATION" \
                "$DEADLINE" \
                "$actions_json" \
                "$TRANSFER_DESTINATION_ID" \
                "")
        else
            # Has swap fields only
            start_response=$(composed_contract_workflow \
                "$jwt_token" \
                "$COMPOSED_CONTRACT_NAME" \
                "$COMPOSED_CONTRACT_DESCRIPTION" \
                "$obligations_json" \
                "$COUNTERPART" \
                "$PAYMENT_AMOUNT" \
                "$PAYMENT_DENOMINATION" \
                "$DEADLINE" \
                "$actions_json" \
                "" \
                "")
        fi
    else
        if [[ "$use_transfer_fields" == "true" ]]; then
            # Has transfer fields only (no swap)
            start_response=$(composed_contract_workflow \
                "$jwt_token" \
                "$COMPOSED_CONTRACT_NAME" \
                "$COMPOSED_CONTRACT_DESCRIPTION" \
                "$obligations_json" \
                "" \
                "" \
                "" \
                "" \
                "$actions_json" \
                "$TRANSFER_DESTINATION_ID" \
                "")
        else
            # No swap or transfer fields
            start_response=$(composed_contract_workflow \
                "$jwt_token" \
                "$COMPOSED_CONTRACT_NAME" \
                "$COMPOSED_CONTRACT_DESCRIPTION" \
                "$obligations_json" \
                "" \
                "" \
                "" \
                "" \
                "$actions_json" \
                "" \
                "")
        fi
    fi

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
            echo_with_color $BLUE "      2. The server was restarted after adding the composed_contract workflow"
            echo_with_color $BLUE "      3. The route is registered at: /api/composed_contract/workflow"
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
        echo_with_color $GREEN "    ✅ Generic composed contract workflow completed successfully!"
        echo ""
        echo_with_color $BLUE "  📋 Result Details:"
        echo_with_color $BLUE "      Composed Contract ID: $(echo "$final_response" | jq -r '.result.composed_contract_id // "N/A"')"
        
        # Display obligation IDs from the array
        local obligation_ids
        obligation_ids=$(echo "$final_response" | jq -r '.result.obligation_ids // []' 2>/dev/null)
        if [[ -n "$obligation_ids" && "$obligation_ids" != "[]" && "$obligation_ids" != "null" ]]; then
            local obligation_count
            obligation_count=$(echo "$obligation_ids" | jq 'length' 2>/dev/null || echo "0")
            echo_with_color $BLUE "      Obligations ($obligation_count):"
            echo "$obligation_ids" | jq -r '.[]' | while IFS= read -r obligation_id; do
                echo_with_color $BLUE "        • $obligation_id"
            done
        else
            echo_with_color $BLUE "      Obligations: N/A"
        fi
        
        # Swap IDs are optional (only present if create_swap was in actions)
        local swap_id
        swap_id=$(echo "$final_response" | jq -r '.result.swap_id // empty' 2>/dev/null)
        if [[ -n "$swap_id" && "$swap_id" != "null" ]]; then
            echo_with_color $BLUE "      Swap ID: $swap_id"
            echo_with_color $BLUE "      Swap Message ID: $(echo "$final_response" | jq -r '.result.swap_message_id // "N/A"')"
        else
            echo_with_color $BLUE "      Swap ID: N/A (create_swap not in actions)"
        fi
        
        # Transfer IDs are optional (only present if create_transfer was in actions)
        local transfer_message_id
        transfer_message_id=$(echo "$final_response" | jq -r '.result.transfer_message_id // empty' 2>/dev/null)
        if [[ -n "$transfer_message_id" && "$transfer_message_id" != "null" ]]; then
            echo_with_color $BLUE "      Transfer Message ID: $transfer_message_id"
            echo_with_color $BLUE "      Transfer Composed ID: $(echo "$final_response" | jq -r '.result.transfer_composed_id // "N/A"')"
        else
            echo_with_color $BLUE "      Transfer ID: N/A (create_transfer not in actions)"
        fi
        echo ""
        echo_with_color $GREEN "🎉 Generic composed contract workflow test completed successfully! ✨"
        echo ""
        echo_with_color $CYAN "📝 Summary:"
        echo_with_color $BLUE "   • Created composed contract: ${COMPOSED_CONTRACT_NAME}"
        echo_with_color $BLUE "   • Created 2 obligations (${OBLIGATION_1_NAME} and ${OBLIGATION_2_NAME})"
        if echo "$actions_json" | jq -e 'index("accept_obligation") != null' >/dev/null 2>&1; then
            echo_with_color $BLUE "   • Accepted both obligations"
        fi
        if echo "$actions_json" | jq -e 'index("create_swap") != null' >/dev/null 2>&1; then
            echo_with_color $BLUE "   • Created swap: both obligations vs ${PAYMENT_AMOUNT} ${PAYMENT_DENOMINATION} from ${COUNTERPART}"
        fi
        if echo "$actions_json" | jq -e 'index("create_transfer") != null' >/dev/null 2>&1; then
            echo_with_color $BLUE "   • Transferred composed contract to: ${TRANSFER_DESTINATION_ID}"
        fi
        echo_with_color $BLUE "   • Actions executed: $(echo "$actions_json" | jq -r 'join(", ")')"
        return 0
    else
        echo_with_color $RED "    ❌ Generic composed contract workflow ended in status: ${workflow_status}"
        local error_msg
        error_msg=$(echo "$final_response" | jq -r '.error // "Unknown error"' 2>/dev/null)
        echo_with_color $RED "    Error: ${error_msg}"
        echo_with_color $BLUE "    Full response:"
        echo "$final_response" | sed 's/^/      /'
        return 1
    fi
}

# Show usage if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0 [username] [password] [action_mode]"
    echo ""
    echo "Arguments:"
    echo "  username    User email for authentication (default: issuer@yieldfabric.com)"
    echo "  password    User password for authentication (default: issuer_password)"
    echo "  action_mode Action configuration mode:"
    echo "              - 'default' or omit: Uses default actions (backward compatible)"
    echo "              - 'issue_only': Only create obligations [\"create_obligation\"]"
    echo "              - 'issue_accept': Create and accept [\"create_obligation\", \"accept_obligation\", \"wait_for_acceptance\"]"
    echo "              - 'issue_accept_transfer': Create, accept, and transfer [\"create_obligation\", \"accept_obligation\", \"wait_for_acceptance\", \"create_transfer\"]"
    echo "              - 'issue_swap': Create and swap [\"create_obligation\", \"create_swap\"]"
    echo "              - 'all': All actions [\"create_obligation\", \"accept_obligation\", \"wait_for_acceptance\", \"create_swap\"]"
    echo ""
    echo "Environment variables (used as fallback if arguments not provided):"
    echo "  USER_EMAIL    User email for authentication"
    echo "  PASSWORD      User password for authentication"
    echo "  ACTION_MODE   Action configuration mode (see above)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Default actions (backward compatible)"
    echo "  $0 user@example.com mypassword       # Default actions with custom credentials"
    echo "  $0 user@example.com mypassword issue_only  # Only create obligations"
    echo "  $0 user@example.com mypassword issue_accept  # Create and accept obligations"
    echo "  $0 user@example.com mypassword issue_accept_transfer  # Create, accept, and transfer obligations"
    echo "  $0 user@example.com mypassword issue_swap  # Create obligations and swap"
    echo "  $0 user@example.com mypassword all   # All actions (default if action_mode specified)"
    echo "  ACTION_MODE=issue_only $0            # Using environment variable"
    exit 0
fi

main "$@"

