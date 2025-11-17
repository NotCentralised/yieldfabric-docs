#!/usr/bin/env bash

# Retrieve loan details from the payments GraphQL API in a concise, DRY way.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_PURPLE='\033[0;35m'
COLOR_CYAN='\033[0;36m'
COLOR_RESET='\033[0m'

log() {
    local color=$1 symbol=$2; shift 2
    printf "%b%s%b %s\n" "${color}" "${symbol}" "${COLOR_RESET}" "$*"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        log "$COLOR_RED" "❌" "Missing dependency: $1"
        exit 1
    }
}

load_env_files() {
    local file
    for file in "${REPO_ROOT}/.env" "${REPO_ROOT}/.env.local" "${SCRIPT_DIR}/.env"; do
        if [[ -f "$file" ]]; then
            # shellcheck disable=SC1090
            source "$file"
        fi
    done
}

maybe_mine_block() {
    local url=${1:-http://127.0.0.1:8545/}
    curl -s -X POST \
        --data '{"jsonrpc":"2.0","method":"evm_mine","params":[],"id":2}' \
        "$url" >/dev/null 2>&1 || true
}

check_service() {
    local name=$1 url=$2
    log "$COLOR_BLUE" "🔍" "Checking ${name} @ ${url}"

    if [[ "$url" =~ ^https?:// ]]; then
        if curl -sSf --max-time 5 "${url}/health" >/dev/null 2>&1 || \
           curl -sSf --max-time 5 "$url" >/dev/null 2>&1; then
            log "$COLOR_GREEN" "✅" "${name} reachable"
            return 0
        fi
    else
        if nc -z 127.0.0.1 "$url" >/dev/null 2>&1; then
            log "$COLOR_GREEN" "✅" "${name} reachable"
            return 0
        fi
    fi

    log "$COLOR_RED" "❌" "${name} unreachable"
    return 1
}

log_err() {
    local color=$1 symbol=$2; shift 2
    printf "%b%s%b %s\n" "${color}" "${symbol}" "${COLOR_RESET}" "$*" >&2
}

login() {
    local email=$1 password=$2
    log_err "$COLOR_BLUE" "🔐" "Authenticating ${email}"

    local response
    response=$(curl -sS -X POST "${AUTH_SERVICE_URL}/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\",\"password\":\"${password}\",\"services\":[\"vault\",\"payments\"]}")

    local token
    token=$(jq -r '.token // .access_token // .jwt // empty' <<<"$response")

    if [[ -z "$token" || "$token" == "null" ]]; then
        log_err "$COLOR_RED" "❌" "Authentication failed"
        log_err "$COLOR_YELLOW" "ℹ️" "Response: $response"
        return 1
    fi

    log_err "$COLOR_GREEN" "✅" "Authentication succeeded"
    printf "%s" "$token"
}

graphql_post() {
    local query=$1 variables_json=$2 token=$3
    local payload
    payload=$(jq -n --arg query "$query" --argjson variables "$variables_json" \
        '{query:$query, variables:$variables}')

    curl -sS -X POST "$GRAPHQL_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "$payload"
}

query_body() {
    cat <<'EOF'
query LoanDetails($loanId: String!) {
  loanFlow {
    loans(loanId: $loanId) {
      id
      status
      mainContractId
      mainContract {
        id
        name
        status
        contractType
        currency
        startDate
        expiryDate
        createdAt
        token { id address tokenId }
        parties { role entity { id name } }
        payments {
          id
          amount
          asset { id name }
          token { id address tokenId }
          status
          dueDate
          unlockSender
          unlockReceiver
          description
          transactionId
        }
      }
      totalTerms
      initialLoanAmount
      loanAssetId
      loanRepaymentDate
      expectedPaymentDate
      expectedPaymentAmount
      expectedPaymentAssetId
      createdAt
      annexContractIds
      withdrawalIds
      repaymentIds
      stateIds
      states {
        id
        term
        balance
        nextPayment
        interestPct
        interestAmount
        arrears
        state
        createdAt
        transactionId
      }
      withdrawals {
        id
        amount
        assetId
        withdrawalDate
        status
        transactionId
      }
      repayments {
        id
        amount
        assetId
        repaymentDate
        status
        transactionId
      }
    }
  }
}
EOF
    return 0
}

print_loan_summary() {
    local json=$1

    jq -r '
      [
        "🔎 Loan ID: \(.id)",
        "   Status: \(.status)",
        "   Main Contract: \(.mainContractId // "-")",
        "   Terms: \(.totalTerms // "-")",
        "   Principal: \(.initialLoanAmount // "-") \(.loanAssetId // "")",
        "   Expected Payment: \(.expectedPaymentAmount // "-") \(.expectedPaymentAssetId // "") on \(.expectedPaymentDate // "-")",
        "   Repayment Date: \(.loanRepaymentDate // "-")",
        "   Created At: \(.createdAt // "-")",
        "   Withdrawals: \((.withdrawals // []) | length) entries",
        "   Repayments: \((.repayments // []) | length) entries",
        "   States: \((.states // []) | length) entries"
      ] | .[]' <<<"$json"

    log "$COLOR_CYAN" "📊" "Latest Loan State"
    jq '(.states // []) | sort_by(.term) | last // "(no states recorded)"' <<<"$json"

    log "$COLOR_CYAN" "💸" "Most Recent Withdrawal"
    jq '(.withdrawals // []) | sort_by(.withdrawalDate) | last // "(no withdrawals recorded)"' <<<"$json"

    log "$COLOR_CYAN" "💰" "Most Recent Repayment"
    jq '(.repayments // []) | sort_by(.repaymentDate) | last // "(no repayments recorded)"' <<<"$json"

    log "$COLOR_CYAN" "🏛️" "Main Contract"
    jq '(.mainContract // "No main contract details available.")' <<<"$json"
}

main() {
    require_cmd curl
    require_cmd jq
    require_cmd nc

    load_env_files

    PAY_SERVICE_URL=${PAY_SERVICE_URL:-https://pay.yieldfabric.io}
    AUTH_SERVICE_URL=${AUTH_SERVICE_URL:-https://auth.yieldfabric.io}
    GRAPHQL_ENDPOINT=${GRAPHQL_ENDPOINT:-${PAY_SERVICE_URL}/graphql}

    local loan_id=${1:-${LOAN_ID:-}}
    if [[ -z "$loan_id" ]]; then
        echo "Usage: $0 <loan-id>"
        echo "   or set LOAN_ID environment variable"
        exit 1
    fi

    maybe_mine_block

    log "$COLOR_CYAN" "📄" "Fetching Loan ${loan_id}"
    log "$COLOR_BLUE" "📋" "GraphQL endpoint: ${GRAPHQL_ENDPOINT}"

    check_service "Auth Service" "$AUTH_SERVICE_URL"
    check_service "Payments Service" "$PAY_SERVICE_URL"

    local user_email=${USER_EMAIL:-investor@yieldfabric.com}
    local password=${PASSWORD:-investor_password}
    local token
    if [[ -n "${JWT_TOKEN:-}" ]]; then
        log "$COLOR_GREEN" "✅" "Using JWT token from environment"
        token="$JWT_TOKEN"
    else
        token=$(login "$user_email" "$password")
        if [[ -z "$token" ]]; then
            log "$COLOR_RED" "❌" "Unable to authenticate user ${user_email}"
            exit 1
        fi
    fi

    log "$COLOR_CYAN" "🔍" "Resolving loan via GraphQL"
    local query
    if ! query=$(query_body); then
        log "$COLOR_RED" "❌" "Failed to build GraphQL query"
        exit 1
    fi

    local variables
    variables=$(jq -n --arg loanId "$loan_id" '{loanId:$loanId}')

    local response
    response=$(graphql_post "$query" "$variables" "$token")

    if jq -e '.errors' <<<"$response" >/dev/null 2>&1; then
        log "$COLOR_RED" "❌" "GraphQL returned errors:"
        jq '.errors' <<<"$response"
        exit 1
    fi

    local results
    results=$(jq '.data.loanFlow.loans // []' <<<"$response")

    if [[ $(jq 'length' <<<"$results") -eq 0 ]]; then
        log "$COLOR_RED" "❌" "Loan ${loan_id} not found"
        exit 1
    fi

    print_loan_summary "$(jq -c '.[0]' <<<"$results")"
    log "$COLOR_PURPLE" "========" "End of Loan Snapshot"
}

main "$@"