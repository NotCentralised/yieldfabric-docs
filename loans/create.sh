#!/bin/bash

# Test script for the Create Loan GraphQL endpoint
# Mirrors the conventions from yieldfabric-docs/annuities/issue_annuity.sh

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

# ANSI colors (same palette as annuity script)
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

# -----------------------------------------------------------------------------
# GraphQL request builders
# -----------------------------------------------------------------------------
build_create_loan_mutation() {
    if [[ "$LOAN_MUTATION_WRAPPER" == "loanFlow" ]]; then
        cat <<'EOF'
mutation CreateLoan($input: CreateLoanInput!) {
  loanFlow {
    createLoan(input: $input) {
      success
      message
      loan {
        id
        status
        totalTerms
        initialLoanAmount
        states {
          id
          term
          balance
          interestPct
          interestAmount
          state
          nextPayment
        }
      }
    }
  }
}
EOF
    else
        cat <<'EOF'
mutation CreateLoan($input: CreateLoanInput!) {
  createLoan(input: $input) {
    success
    message
    loan {
      id
      status
      totalTerms
      initialLoanAmount
      states {
        id
        term
        balance
        interestPct
        interestAmount
        state
        nextPayment
      }
    }
  }
}
EOF
    fi
}

# -----------------------------------------------------------------------------
# API call helpers
# -----------------------------------------------------------------------------
create_loan() {
    local jwt_token=$1
    shift
    local loan_input_json=$*

    echo_with_color $CYAN "🏦 Creating loan via GraphQL" >&2
    echo_with_color $BLUE "  🌐 Endpoint: ${GRAPHQL_ENDPOINT}" >&2
    echo_with_color $BLUE "  📋 Variables:" >&2
    echo "$loan_input_json" | jq '.' | sed 's/^/    /' >&2

    local mutation
    mutation=$(build_create_loan_mutation)

    local request_body
    request_body=$(jq -n --arg mutation "$mutation" --argjson variables "{\"input\": $loan_input_json}" '{query: $mutation, variables: $variables}')

    local temp_file
    temp_file=$(mktemp)

    local http_code
    http_code=$(curl -s -w "%{http_code}" -o "$temp_file" \
        -X POST "$GRAPHQL_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt_token}" \
        -d "$request_body")

    local response
    response=$(cat "$temp_file")
    rm -f "$temp_file"

    echo_with_color $BLUE "  📡 Response received (HTTP $http_code)" >&2
    echo "$response"
}

# -----------------------------------------------------------------------------
# Schema capability detection
# -----------------------------------------------------------------------------
detect_loan_mutation_entrypoint() {
    local jwt_token="$1"

    echo_with_color $BLUE "🔍 Inspecting GraphQL schema for loan support..."

    local schema_probe='query LoanMutationSchema {\n  loanFlow {\n    mutationSchema {\n      wrapperField\n      directField\n      inputType\n    }\n  }\n}'

    local request_body
    request_body=$(jq -n --arg query "$schema_probe" '{query: $query}')

    local response
    response=$(curl -s -X POST "$GRAPHQL_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt_token}" \
        -d "$request_body")

    local errors_present
    errors_present=$(echo "$response" | jq -e '.errors' >/dev/null 2>&1 && echo "true" || echo "false")

    if [[ "$errors_present" != "true" ]]; then
        local wrapper_field
        local direct_field
        local input_type
        wrapper_field=$(echo "$response" | jq -r '.data.loanFlow.mutationSchema.wrapperField // "loanFlow"')
        direct_field=$(echo "$response" | jq -r '.data.loanFlow.mutationSchema.directField // "createLoan"')
        input_type=$(echo "$response" | jq -r '.data.loanFlow.mutationSchema.inputType // "CreateLoanInput"')

        if [[ -n "$input_type" && "$input_type" != "null" ]]; then
            LOAN_MUTATION_WRAPPER="$wrapper_field"
            LOAN_MUTATION_DIRECT="$direct_field"
            LOAN_MUTATION_INPUT_TYPE="$input_type"

            if [[ "$LOAN_MUTATION_WRAPPER" == "loanFlow" ]]; then
                echo_with_color $GREEN "    ✅ Detected loanFlow wrapper for loan mutations"
            elif [[ "$LOAN_MUTATION_WRAPPER" == "none" ]]; then
                echo_with_color $GREEN "    ✅ Detected direct ${LOAN_MUTATION_DIRECT} mutation"
            else
                echo_with_color $GREEN "    ✅ Detected loan mutation wrapper: ${LOAN_MUTATION_WRAPPER}"
            fi

            return 0
        fi
    fi

    # Fallback to introspection for legacy deployments
    local introspection_query='query LoanSchemaCheck {
      __schema {
        mutationType {
          fields {
            name
          }
        }
      }
      loanInput: __type(name: "CreateLoanInput") {
        name
      }
    }'

    request_body=$(jq -n --arg query "$introspection_query" '{query: $query}')
    response=$(curl -s -X POST "$GRAPHQL_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt_token}" \
        -d "$request_body")

    errors_present=$(echo "$response" | jq -e '.errors' >/dev/null 2>&1 && echo "true" || echo "false")

    if [[ "$errors_present" == "true" ]]; then
        echo_with_color $RED "    ❌ Introspection failed: $(echo "$response" | jq -r '.errors[0].message')"
        return 1
    fi

    local loan_input_present
    loan_input_present=$(echo "$response" | jq -r 'if (.data.loanInput.name // null) != null then "true" else "false" end')

    if [[ "$loan_input_present" != "true" ]]; then
        echo_with_color $RED "    ❌ CreateLoanInput type is not available on ${GRAPHQL_ENDPOINT}."
        echo_with_color $YELLOW "       This environment has not been updated with the loan APIs yet."
        return 1
    fi

    local mutation_entrypoint
    mutation_entrypoint=$(echo "$response" | jq -r '
        if any(.data.__schema.mutationType.fields[]?.name; . == "loanFlow") then "loanFlow"
        elif any(.data.__schema.mutationType.fields[]?.name; . == "createLoan") then "createLoan"
        else "none" end')

    if [[ "$mutation_entrypoint" == "none" ]]; then
        echo_with_color $RED "    ❌ Neither loanFlow nor createLoan mutation entry points are available."
        echo_with_color $YELLOW "       Please deploy the latest payments service before running this script."
        return 1
    fi

    LOAN_MUTATION_WRAPPER="$mutation_entrypoint"

    if [[ "$LOAN_MUTATION_WRAPPER" == "loanFlow" ]]; then
        echo_with_color $GREEN "    ✅ Detected loanFlow wrapper for loan mutations"
    else
        echo_with_color $GREEN "    ✅ Detected direct createLoan mutation"
    fi

    return 0
}

# -----------------------------------------------------------------------------
# Main execution
# -----------------------------------------------------------------------------
main() {
    echo_with_color $CYAN "🚀 Starting Create Loan API Test"
    echo ""

    USER_EMAIL="${USER_EMAIL:-investor@yieldfabric.com}"
    PASSWORD="${PASSWORD:-investor_password}"

    # Default loan payload (feel free to tweak)
    LOAN_ID="${LOAN_ID:-}" # leave empty for auto-generation
    MAIN_CONTRACT_ID="${MAIN_CONTRACT_ID:-}"
    BORROWER="${BORROWER:-issuer@yieldfabric.com}"
    TOTAL_TERMS="${TOTAL_TERMS:-18}"
    INITIAL_AMOUNT="${INITIAL_AMOUNT:-900000}"
    LOAN_ASSET_ID="${LOAN_ASSET_ID:-aud-token-asset}"
    local default_iso_ts
    default_iso_ts=$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat().replace("+00:00", "Z"))
PY
)

    REPAYMENT_DATE="${REPAYMENT_DATE:-$default_iso_ts}"
    EXPECTED_PAYMENT_DATE="${EXPECTED_PAYMENT_DATE:-$default_iso_ts}"
    EXPECTED_PAYMENT_AMOUNT="${EXPECTED_PAYMENT_AMOUNT:-34500}"
    EXPECTED_PAYMENT_ASSET_ID="${EXPECTED_PAYMENT_ASSET_ID:-aud-token-asset}"
    INTEREST_PCT="${INTEREST_PCT:-3}"
    STATUS="${STATUS:-PERFORMING}"

    local main_contract_display="${MAIN_CONTRACT_ID:-auto-generated}"

    echo_with_color $BLUE "📋 Configuration:" \
        "\n  API Base URL: ${PAY_SERVICE_URL}" \
        "\n  GraphQL Endpoint: ${GRAPHQL_ENDPOINT}" \
        "\n  Auth Service: ${AUTH_SERVICE_URL}" \
        "\n  User: ${USER_EMAIL}" \
        "\n  Borrower: ${BORROWER}" \
        "\n  Main Contract: ${main_contract_display}" \
        "\n  Total Terms: ${TOTAL_TERMS}" \
        "\n  Initial Amount: ${INITIAL_AMOUNT}" \
        "\n  Interest %: ${INTEREST_PCT}" \
        "\n"

    if ! check_service_running "Auth Service" "$AUTH_SERVICE_URL"; then
        echo_with_color $RED "❌ Auth service is not reachable at $AUTH_SERVICE_URL"
        return 1
    fi

    if ! check_service_running "Payments Service" "$PAY_SERVICE_URL"; then
        echo_with_color $RED "❌ Payments service is not reachable at $PAY_SERVICE_URL"
        return 1
    fi

    echo ""
    echo_with_color $CYAN "🔐 Authenticating..."
    local jwt_token
    jwt_token=$(login_user "$USER_EMAIL" "$PASSWORD")
    if [[ -z "$jwt_token" ]]; then
        echo_with_color $RED "❌ Failed to obtain JWT token"
        return 1
    fi
    echo_with_color $GREEN "  ✅ JWT token obtained (first 50 chars): ${jwt_token:0:50}..."
    echo ""

    if ! detect_loan_mutation_entrypoint "$jwt_token"; then
        echo_with_color $RED "❌ Loan GraphQL mutations are not available on this endpoint yet."
        echo_with_color $YELLOW "   Please ensure the payments service running at ${GRAPHQL_ENDPOINT} has the loan API deployed."
        return 1
    fi

    local loan_payload
    loan_payload=$(jq -n \
        --arg loan_id "$LOAN_ID" \
        --arg main_contract_id "$MAIN_CONTRACT_ID" \
        --arg borrower "$BORROWER" \
        --arg status "$STATUS" \
        --arg loan_asset_id "$LOAN_ASSET_ID" \
        --arg expected_payment_asset_id "$EXPECTED_PAYMENT_ASSET_ID" \
        --arg json_repayment_date "$REPAYMENT_DATE" \
        --arg json_expected_payment_date "$EXPECTED_PAYMENT_DATE" \
        --arg total_terms "$TOTAL_TERMS" \
        --arg initial_amount "$INITIAL_AMOUNT" \
        --arg expected_payment_amount "$EXPECTED_PAYMENT_AMOUNT" \
        --arg interest_pct "$INTEREST_PCT" \
        '(
             {
                 borrower: $borrower,
                 status: $status,
                 totalTerms: (try ($total_terms | tonumber) catch null),
                 initialLoanAmount: (try ($initial_amount | tonumber) catch 0),
                 loanAssetId: $loan_asset_id,
                 loanRepaymentDate: $json_repayment_date,
                 expectedPaymentDate: $json_expected_payment_date,
                 expectedPaymentAmount: (try ($expected_payment_amount | tonumber) catch 0),
                 expectedPaymentAssetId: $expected_payment_asset_id,
                 firstStateInterestPct: (try ($interest_pct | tonumber) catch 0)
             }

            | if .totalTerms == null then del(.totalTerms) else . end
            | if $loan_id != "" then .loanId = $loan_id else . end
            | if $main_contract_id != "" then .mainContractId = $main_contract_id else . end
        )')

    local response
    response=$(create_loan "$jwt_token" "$loan_payload")
    echo ""
    echo_with_color $BLUE "📡 Raw GraphQL Response:"
    if ! echo "$response" | jq '.' 2>/dev/null; then
        echo_with_color $RED "  ⚠️ Response is not valid JSON"
        echo "$response"
        return 1
    fi

    local success
    success=$(echo "$response" | jq -r '.data.loanFlow.createLoan.success // false')
    local message
    message=$(echo "$response" | jq -r '.data.loanFlow.createLoan.message // "(no message)"')

    if [[ "$success" == "true" ]]; then
        echo ""
        echo_with_color $GREEN "✅ Loan created successfully!"
        echo_with_color $BLUE "  Loan ID: $(echo "$response" | jq -r '.data.loanFlow.createLoan.loan.id')"
        echo_with_color $BLUE "  Status: $(echo "$response" | jq -r '.data.loanFlow.createLoan.loan.status')"
        echo_with_color $BLUE "  Initial State:"
        echo "$response" | jq '.data.loanFlow.createLoan.loan.states[0]' | sed 's/^/    /'
    else
        echo ""
        echo_with_color $RED "❌ Loan creation failed"
        echo_with_color $RED "  Message: $message"
        echo_with_color $YELLOW "  Full response logged above for debugging"
        return 1
    fi
}

main "$@"
