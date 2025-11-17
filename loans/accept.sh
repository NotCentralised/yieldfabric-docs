#!/bin/bash

# Script to accept a loan via GraphQL.
# Mirrors the conventions used in create.sh but focuses on the acceptLoan mutation.

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
LOAN_ID="${1:-${LOAN_ID:-}}"
PAYMENT_ID="${PAYMENT_ID:-}"

if [[ -z "$LOAN_ID" ]]; then
    echo "Usage: $0 <loan-id>"
    echo "       or set LOAN_ID environment variable"
    exit 1
fi

# ANSI colors (same palette as other loan scripts)
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

run_accept_mutation() {
    local jwt_token="$1"
    local variables_json="$2"

    # Primary attempt using loanFlow wrapper
    local wrapped_mutation='mutation AcceptLoan($input: AcceptLoanInput!) {
  loanFlow {
    acceptLoan(input: $input) {
      success
      message
      loan {
        id
        status
        mainContractId
        states {
          id
          state
          term
        }
      }
    }
  }
}'

    local response
    response=$(graphql_post "$wrapped_mutation" "$variables_json" "$jwt_token")

    if echo "$response" | jq -e '.errors' >/dev/null 2>&1; then
        local error_text
        error_text=$(echo "$response" | jq -r '.errors | map(.message) | join("; ")')

        if echo "$error_text" | grep -qi 'Cannot query field "loanFlow"'; then
            echo_with_color $YELLOW "  ⚠️ loanFlow wrapper not available, attempting direct acceptLoan mutation"
            local direct_mutation='mutation AcceptLoan($input: AcceptLoanInput!) {
  acceptLoan(input: $input) {
    success
    message
    loan {
      id
      status
      mainContractId
      states {
        id
        state
        term
      }
    }
  }
}'
            response=$(graphql_post "$direct_mutation" "$variables_json" "$jwt_token")
        fi
    fi

    echo "$response"
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
main() {
    require_cmd curl
    require_cmd jq
    maybe_mine_block

    echo_with_color $CYAN "🤝 Accepting Loan"
    echo_with_color $BLUE "📋 Configuration:" \
        "\n  API Base URL: ${PAY_SERVICE_URL}" \
        "\n  GraphQL Endpoint: ${GRAPHQL_ENDPOINT}" \
        "\n  Auth Service: ${AUTH_SERVICE_URL}" \
        "\n  Loan ID: ${LOAN_ID}" \
        "\n  Payment ID: ${PAYMENT_ID:-<auto>}"

    check_service_running "Auth Service" "$AUTH_SERVICE_URL" || exit 1
    check_service_running "Payments Service" "$PAY_SERVICE_URL" || exit 1

    echo ""
    echo_with_color $CYAN "🔐 Authenticating borrower..."
    local borrower_email="${BORROWER_EMAIL:-issuer@yieldfabric.com}"
    local password="${PASSWORD:-issuer_password}"

    local jwt_token
    if ! jwt_token=$(obtain_jwt_token "$borrower_email" "$password"); then
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
    echo_with_color $CYAN "📡 Submitting acceptLoan mutation"
    echo "$variables" | jq '.' | sed 's/^/    /'

    local response
    response=$(run_accept_mutation "$jwt_token" "$variables")

    echo ""
    echo_with_color $BLUE "📡 Raw GraphQL Response:"
    if ! echo "$response" | jq '.' 2>/dev/null; then
        echo_with_color $RED "  ⚠️ Response is not valid JSON"
        echo "$response"
        exit 1
    fi

    local success
    success=$(echo "$response" | jq -r '.data.loanFlow.acceptLoan.success // .data.acceptLoan.success // false')
    local message
    message=$(echo "$response" | jq -r '.data.loanFlow.acceptLoan.message // .data.acceptLoan.message // "(no message)"')
    local loan
    loan=$(echo "$response" | jq '.data.loanFlow.acceptLoan.loan // .data.acceptLoan.loan // null')

    if [[ "$success" == "true" ]]; then
        echo_with_color $GREEN "✅ Loan accepted successfully!"
        echo_with_color $BLUE "  Message: ${message}"
        if [[ "$loan" != "null" ]]; then
            echo_with_color $PURPLE "  Loan Snapshot:"
            echo "$loan" | jq '.' | sed 's/^/    /'
        fi
    else
        echo_with_color $RED "❌ Loan acceptance failed"
        echo_with_color $RED "  Message: ${message}"
        if echo "$response" | jq -e '.errors' >/dev/null 2>&1; then
            echo_with_color $RED "  Errors:"
            echo "$response" | jq '.errors'
        fi
        exit 1
    fi
}

main "$@"

