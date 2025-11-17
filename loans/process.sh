#!/bin/bash

# Script to trigger loan payment processing via GraphQL.
# Mirrors the structure of create.sh / accept.sh but targets the processLoan mutation.

set -euo pipefail

# -----------------------------------------------------------------------------
# Environment bootstrap
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PAY_SERVICE_URL="${PAY_SERVICE_URL:-https://pay.yieldfabric.io}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth.yieldfabric.io}"
GRAPHQL_ENDPOINT="${GRAPHQL_ENDPOINT:-${PAY_SERVICE_URL}/graphql}"
ETH_RPC_URL="${ETH_RPC_URL:-http://127.0.0.1:8545/}"
ENABLE_WORKFLOW_POLLING="${ENABLE_WORKFLOW_POLLING:-true}"
WORKFLOW_POLL_INTERVAL="${WORKFLOW_POLL_INTERVAL:-5}"
WORKFLOW_POLL_ATTEMPTS="${WORKFLOW_POLL_ATTEMPTS:-24}"
LOAN_ID="${1:-${LOAN_ID:-}}"
PAYMENT_ID="${PAYMENT_ID:-}"

if [[ -z "$LOAN_ID" ]]; then
    echo "Usage: $0 <loan-id>"
    echo "       or set LOAN_ID environment variable"
    exit 1
fi

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
echo_with_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

require_cmd() {
    local cmd=$1
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo_with_color $RED "❌ Missing dependency: $cmd"
        exit 1
    fi
}

maybe_mine_block() {
    curl -s -X POST \
        --data '{"jsonrpc":"2.0","method":"evm_mine","params":[],"id":2}' \
        "$ETH_RPC_URL" >/dev/null 2>&1 || true
}

to_lower() {
    echo "${1:-}" | tr '[:upper:]' '[:lower:]'
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
        if nc -z localhost "$service_url" 2>/dev/null; then
            echo_with_color $GREEN "    ✅ ${service_name} is running on port ${service_url}"
            return 0
        else
            echo_with_color $RED "    ❌ ${service_name} is not running on port ${service_url}"
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
        fi

        echo_with_color $RED "    ❌ No token in response" >&2
        echo_with_color $YELLOW "    Response: $http_response" >&2
        return 1
    fi

    echo_with_color $RED "    ❌ Login failed: no response" >&2
    return 1
}

obtain_jwt_token() {
    local email="$1"
    local password="$2"

    if [[ -n "${JWT_TOKEN:-}" ]]; then
        echo_with_color $GREEN "  ✅ Using JWT token from environment"
        echo "$JWT_TOKEN"
        return 0
    fi

    login_user "$email" "$password"
}

graphql_post() {
    local query="$1"
    local variables_json="$2"
    local jwt_token="$3"

    local payload
    payload=$(jq -n --arg query "$query" --argjson variables "$variables_json" '{query: $query, variables: $variables}')

    curl -s -X POST "$GRAPHQL_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt_token}" \
        -d "$payload"
}

run_process_mutation() {
    local jwt_token="$1"
    local variables_json="$2"

    local wrapped_mutation='mutation ProcessLoan($input: ProcessLoanInput!) {
  loanFlow {
    processLoan(input: $input) {
      success
      workflowId
      message
    }
  }
}'

    local response
    response=$(graphql_post "$wrapped_mutation" "$variables_json" "$jwt_token")

    if echo "$response" | jq -e '.errors' >/dev/null 2>&1; then
        local error_text
        error_text=$(echo "$response" | jq -r '.errors | map(.message) | join("; ")')

        if echo "$error_text" | grep -qi 'Cannot query field "loanFlow"'; then
            echo_with_color $YELLOW "  ⚠️ loanFlow wrapper not available, attempting direct processLoan mutation"
            local direct_mutation='mutation ProcessLoan($input: ProcessLoanInput!) {
  processLoan(input: $input) {
    success
    workflowId
    message
  }
}'
            response=$(graphql_post "$direct_mutation" "$variables_json" "$jwt_token")
        fi
    fi

    echo "$response"
}

poll_workflow_status() {
    local workflow_id="$1"

    if [[ -z "${PAY_SERVICE_URL:-}" ]]; then
        echo_with_color $YELLOW "  ⚠️ PAY_SERVICE_URL not set; skipping workflow polling."
        return 0
    fi

    local base="${PAY_SERVICE_URL%/}"
    local url="${base}/api/loan/process_workflow/${workflow_id}"

    echo_with_color $BLUE "  🔁 Polling workflow status (${WORKFLOW_POLL_ATTEMPTS} attempts, every ${WORKFLOW_POLL_INTERVAL}s)"

    for ((attempt = 1; attempt <= WORKFLOW_POLL_ATTEMPTS; attempt++)); do
        local status_payload
        status_payload=$(curl -s "$url" || true)

        if [[ -z "$status_payload" ]]; then
            echo_with_color $YELLOW "    ⚠️ Empty response while polling (attempt ${attempt})"
        else
            local workflow_status current_step error_msg
            workflow_status=$(echo "$status_payload" | jq -r '.workflow_status // .workflowStatus // empty' 2>/dev/null || true)
            current_step=$(echo "$status_payload" | jq -r '.current_step // .currentStep // empty' 2>/dev/null || true)
            error_msg=$(echo "$status_payload" | jq -r '.error // empty' 2>/dev/null || true)

            if [[ -n "$workflow_status" ]]; then
                echo_with_color $CYAN "    [${attempt}] Status: ${workflow_status} (step: ${current_step:-unknown})"
                if [[ "$workflow_status" == "completed" || "$workflow_status" == "failed" || "$workflow_status" == "cancelled" ]]; then
                    if [[ -n "$error_msg" && "$error_msg" != "null" ]]; then
                        echo_with_color $RED "    ⚠️ Error reported: ${error_msg}"
                    fi
                    return 0
                fi
            else
                echo_with_color $YELLOW "    ⚠️ Unexpected payload while polling (attempt ${attempt})"
            fi
        fi

        sleep "$WORKFLOW_POLL_INTERVAL"
    done

    echo_with_color $YELLOW "  ⚠️ Workflow did not reach a terminal state within allotted attempts"
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
main() {
    require_cmd curl
    require_cmd jq
    require_cmd nc
    maybe_mine_block

    echo_with_color $CYAN "⚙️  Processing Loan Payment"
    echo_with_color $BLUE "📋 Configuration:" \
        "\n  API Base URL: ${PAY_SERVICE_URL}" \
        "\n  GraphQL Endpoint: ${GRAPHQL_ENDPOINT}" \
        "\n  Auth Service: ${AUTH_SERVICE_URL}" \
        "\n  Loan ID: ${LOAN_ID}" \
        "\n  Payment ID: ${PAYMENT_ID:-<auto>}"

    check_service_running "Auth Service" "$AUTH_SERVICE_URL" || exit 1
    check_service_running "Payments Service" "$PAY_SERVICE_URL" || exit 1

    echo ""
    echo_with_color $CYAN "🔐 Authenticating processor..."
    local processor_email="${PROCESSOR_EMAIL:-investor@yieldfabric.com}"
    local password="${PASSWORD:-investor_password}"

    local jwt_token
    if ! jwt_token=$(obtain_jwt_token "$processor_email" "$password"); then
        echo_with_color $RED "❌ Failed to obtain JWT token"
        exit 1
    fi
    echo_with_color $GREEN "  ✅ JWT token obtained (first 50 chars): ${jwt_token:0:50}..."

    local variables
    variables=$(jq -n \
        --arg loan_id "$LOAN_ID" \
        --arg payment_id "$PAYMENT_ID" \
        '{
            input: {
                loanId: $loan_id
            }
        }
        | if ($payment_id | length) > 0 then .input.paymentId = $payment_id else . end')

    echo ""
    echo_with_color $CYAN "📡 Submitting processLoan mutation"
    echo "$variables" | jq '.' | sed 's/^/    /'

    local response
    response=$(run_process_mutation "$jwt_token" "$variables")

    echo ""
    echo_with_color $BLUE "📡 Raw GraphQL Response:"
    if ! echo "$response" | jq '.' 2>/dev/null; then
        echo_with_color $RED "  ⚠️ Response is not valid JSON"
        echo "$response"
        exit 1
    fi

    local success
    success=$(echo "$response" | jq -r '.data.loanFlow.processLoan.success // .data.processLoan.success // false')
    local message
    message=$(echo "$response" | jq -r '.data.loanFlow.processLoan.message // .data.processLoan.message // "(no message)"')
    local workflow_id
    workflow_id=$(echo "$response" | jq -r '.data.loanFlow.processLoan.workflowId // .data.processLoan.workflowId // empty')

    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Loan processing request accepted"
        echo_with_color $BLUE "  Message: ${message}"
        if [[ -n "$workflow_id" && "$workflow_id" != "null" ]]; then
            echo_with_color $CYAN "  🧭 Workflow ID: ${workflow_id}"
            if [[ "$(to_lower "${ENABLE_WORKFLOW_POLLING}")" == "true" ]]; then
                poll_workflow_status "$workflow_id"
            else
                echo_with_color $YELLOW "  ℹ️ Workflow polling disabled (set ENABLE_WORKFLOW_POLLING=true to enable)."
            fi
        else
            echo_with_color $YELLOW "  ⚠️ Workflow ID missing from response (cannot poll status)."
        fi
    else
        echo_with_color $RED "❌ Loan processing failed"
        echo_with_color $RED "  Message: ${message}"
        if echo "$response" | jq -e '.errors' >/dev/null 2>&1; then
            echo_with_color $RED "  Errors:"
            echo "$response" | jq '.errors'
        fi
        exit 1
    fi
}

main "$@"

