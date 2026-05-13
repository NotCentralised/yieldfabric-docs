#!/bin/bash

# Composed-contract issuance via the agents-side deal flow.
#
# The legacy REST endpoint `/api/composed_contract/workflow` (and its
# sister routes) was removed in commit c3119db. This script runs the
# replacement path: build a `DealPlan` containing a
# `create_composed_contract` action (and optional `create_swap` follow-on),
# then drive it through `proposeDeal` → counterparty `signDeal` →
# proposer `activateDeal`, and poll `dealById` until terminal.
#
# Auth on port 3000, agents GraphQL on port 3001 (env-overridable).

set -e

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

AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:3000}"
AGENTS_SERVICE_URL="${AGENTS_SERVICE_URL:-${AGENTS_API_URL:-http://localhost:3001}}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_with_color() { echo -e "${1}${2}${NC}"; }

check_service() {
    local name=$1; local url=$2
    echo_with_color "$BLUE" "  🔍 Checking ${name} (${url})..."
    if curl -s -f -o /dev/null --max-time 5 "${url}/health" 2>/dev/null \
       || curl -s -f -o /dev/null --max-time 5 "${url}" 2>/dev/null; then
        echo_with_color "$GREEN" "    ✅ ${name} reachable"
        return 0
    fi
    echo_with_color "$RED" "    ❌ ${name} not reachable"
    return 1
}

login_user() {
    local email="$1"; local password="$2"
    echo_with_color "$BLUE" "  🔐 Logging in: $email" >&2
    local resp
    resp=$(curl -s -X POST "${AUTH_SERVICE_URL}/auth/login/with-services" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\", \"password\": \"$password\", \"services\": [\"vault\", \"payments\"]}")
    local token
    token=$(echo "$resp" | jq -r '.token // .access_token // .jwt // empty')
    if [[ -z "$token" || "$token" == "null" ]]; then
        echo_with_color "$RED" "    ❌ Login failed for $email — response: $resp" >&2
        return 1
    fi
    # The deal flow's caller-identity check compares JWT sub (user.id
    # UUID) to the deal's counterparty_entity_id. Emails don't match,
    # so we surface the canonical entity-id alongside the JWT.
    local entity_id
    entity_id=$(echo "$resp" | jq -r '.user.id // .user.entity_id // empty')
    if [[ -z "$entity_id" || "$entity_id" == "null" ]]; then
        echo_with_color "$RED" "    ❌ Login response missing user.id — response: $resp" >&2
        return 1
    fi
    jq -n --arg token "$token" --arg entity_id "$entity_id" '{token: $token, entity_id: $entity_id}'
}

# Send a GraphQL operation against the agents service.
# Args: JWT, query, variables-json. Echoes the raw response body.
graphql_call() {
    local jwt=$1; local query=$2; local variables=$3
    curl -s -X POST "${AGENTS_SERVICE_URL}/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${jwt}" \
        -d "$(jq -n --arg q "$query" --argjson v "$variables" '{query: $q, variables: $v}')"
}

# Construct the DealPlan envelope. One node ("compose") for the
# composed-contract issuance; optional second node ("swap") wires
# the obligations into a CreateSwap.
build_plan() {
    local contract_name=$1
    local contract_description=$2
    local counterparty=$3
    local obligations_json=$4  # array of {denomination, notional, obligor, expiry, ...}
    local payment_amount=$5    # empty → no swap
    local payment_denomination=$6
    local deadline=$7

    local compose_inputs
    compose_inputs=$(jq -n \
        --arg name "$contract_name" \
        --arg desc "$contract_description" \
        --arg cp "$counterparty" \
        --argjson obs "$obligations_json" \
        '{
            name: $name,
            description: $desc,
            counterpart: $cp,
            obligations: $obs
        }')

    local compose_node
    compose_node=$(jq -n --argjson inp "$compose_inputs" '{
        step_id: "compose",
        task_name: "create_composed_contract",
        inputs: $inp
    }')

    if [[ -n "$payment_amount" ]]; then
        local swap_node
        swap_node=$(jq -n \
            --arg cp "$counterparty" \
            --arg amount "$payment_amount" \
            --arg denom "$payment_denomination" \
            --arg deadline "$deadline" \
            --arg name "${contract_name} swap" \
            '{
                step_id: "swap",
                task_name: "create_swap",
                inputs: {
                    counterparty: $cp,
                    initiator_obligations: "$step.compose.obligation_ids",
                    counterparty_payment_amount: $amount,
                    counterparty_payment_denomination: $denom,
                    deadline: $deadline,
                    name: $name
                }
            }')
        jq -n --argjson c "$compose_node" --argjson s "$swap_node" '{
            nodes: [$c, $s],
            edges: [{ from: "compose", to: "swap" }],
            entry_step_ids: ["compose"]
        }'
    else
        jq -n --argjson c "$compose_node" '{
            nodes: [$c],
            edges: [],
            entry_step_ids: ["compose"]
        }'
    fi
}

propose_deal() {
    local jwt=$1; local plan_json=$2; local counterparty=$3
    local query='mutation Propose($input: ProposeDealInput!) {
        dealFlow {
            proposeDeal(input: $input) {
                success message deal { id status workflowId }
            }
        }
    }'
    local variables
    variables=$(jq -n --argjson plan "$plan_json" --arg cp "$counterparty" \
        '{ input: { counterpartyEntityId: $cp, plan: $plan } }')
    graphql_call "$jwt" "$query" "$variables"
}

sign_deal() {
    local jwt=$1; local deal_id=$2
    local query='mutation Sign($input: SignDealInput!) {
        dealFlow {
            signDeal(input: $input) {
                success message deal { id status }
            }
        }
    }'
    local variables
    variables=$(jq -n --arg id "$deal_id" '{ input: { dealId: $id } }')
    graphql_call "$jwt" "$query" "$variables"
}

activate_deal() {
    local jwt=$1; local deal_id=$2
    local query='mutation Activate($input: ActivateDealInput!) {
        dealFlow {
            activateDeal(input: $input) {
                success message deal { id status workflowId }
            }
        }
    }'
    local variables
    variables=$(jq -n --arg id "$deal_id" '{ input: { dealId: $id } }')
    graphql_call "$jwt" "$query" "$variables"
}

poll_deal_until_terminal() {
    local jwt=$1; local deal_id=$2
    local max_attempts=${3:-120}; local delay=${4:-2}
    # Pull the event payload too so the per-attempt log can show what
    # the deal is actually doing — `step_ready (compose)` vs
    # `step_completed (swap)` vs `workflow_completed` carries far more
    # signal than a flat `ACTIVE` repeated 30 times. The payload field
    # carries the canonical mirror shape (`{step_key, result, ...}`)
    # and is JSONB on the wire, deserialised here with jq.
    local query='query DealStatus($id: String!) {
        dealFlow {
            dealById(id: $id) {
                id status workflowId
                events { sequence eventType occurredAt payload }
            }
        }
    }'
    local variables
    variables=$(jq -n --arg id "$deal_id" '{ id: $id }')

    local last_seq=-1
    for ((attempt=1; attempt<=max_attempts; attempt++)); do
        local resp
        resp=$(graphql_call "$jwt" "$query" "$variables")
        local status
        status=$(echo "$resp" | jq -r '.data.dealFlow.dealById.status // empty')

        # Tail of the events array — most recent activity. Prefer the
        # event's step_key (when present) so `step_completed` rows
        # disambiguate between compose and swap; fall back to the
        # bare event_type otherwise (proposed / signed / activated /
        # workflow_completed / completed all carry no step).
        local latest
        latest=$(echo "$resp" | jq -r '
            .data.dealFlow.dealById.events // []
            | sort_by(.sequence)
            | last
            | if . == null then "—"
              else
                ((.payload.step_key // "") as $sk
                  | if $sk == "" then .eventType
                    else "\(.eventType) (\($sk))" end)
              end
        ')
        local latest_seq
        latest_seq=$(echo "$resp" | jq -r '
            .data.dealFlow.dealById.events // []
            | sort_by(.sequence)
            | last
            | if . == null then -1 else .sequence end
        ')

        # Only print the per-attempt line when something changed
        # (status flip OR a new event landed). Reduces 30+ identical
        # `status=ACTIVE` lines to one line per actual transition.
        if [[ "$latest_seq" != "$last_seq" ]]; then
            echo_with_color "$BLUE" "  📡 attempt ${attempt}/${max_attempts} — status=${status:-?} — latest=${latest}" >&2
            last_seq="$latest_seq"
        fi

        case "$status" in
            COMPLETED|CANCELLED|REJECTED|DEFAULTED|FAILED_AFTER_PARTIAL_EXECUTION)
                echo "$resp"
                return 0
                ;;
        esac
        if [[ $attempt -lt $max_attempts ]]; then
            sleep "$delay"
        fi
    done
    echo_with_color "$RED" "  ❌ Deal did not reach a terminal status within ${max_attempts} attempts" >&2
    return 1
}

print_usage() {
    cat <<EOF
Usage: $0 [proposer_email] [proposer_password] [counterparty_email] [counterparty_password] [mode]

  mode: "compose_only"  — just create_composed_contract
        "compose_swap"  — create_composed_contract + create_swap (default)

Defaults read from env: USER_EMAIL, PASSWORD, COUNTERPARTY_EMAIL,
COUNTERPARTY_PASSWORD, ACTION_MODE. Compose-time fixtures
(DENOMINATION, COUPON_AMOUNT, …) carry over from the legacy script.

Environment:
  AUTH_SERVICE_URL    (default http://localhost:3000)
  AGENTS_SERVICE_URL  (default http://localhost:3001 — DMS lives in agents)
EOF
}

main() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        print_usage; exit 0
    fi

    local USER_EMAIL="${1:-${USER_EMAIL:-issuer@yieldfabric.com}}"
    local PASSWORD="${2:-${PASSWORD:-issuer_password}}"
    local COUNTERPARTY_EMAIL="${3:-${COUNTERPARTY_EMAIL:-investor@yieldfabric.com}}"
    local COUNTERPARTY_PASSWORD="${4:-${COUNTERPARTY_PASSWORD:-investor_password}}"
    local ACTION_MODE="${5:-${ACTION_MODE:-compose_swap}}"

    local DENOMINATION="${DENOMINATION:-aud-token-asset}"
    local END_DATE="${END_DATE:-2027-01-31}"
    # Raw token-unit amounts (× 10^18 for 18-decimal tokens). The
    # deal-flow bridge passes amounts through verbatim — same
    # contract the wallet UX uses (it pre-scales client-side and
    # payments accepts raw).
    local COUPON_AMOUNT="${COUPON_AMOUNT:-10000000000000000000000}"
    local OBLIGATION_2_NOTIONAL="${OBLIGATION_2_NOTIONAL:-100000000000000000000000}"
    local PAYMENT_AMOUNT="${PAYMENT_AMOUNT:-12500000000000000000000}"
    local PAYMENT_DENOMINATION="${PAYMENT_DENOMINATION:-$DENOMINATION}"
    local DEADLINE="${DEADLINE:-${END_DATE}T23:59:59Z}"
    local CONTRACT_NAME="${COMPOSED_CONTRACT_NAME:-Structured Loan}"
    local CONTRACT_DESCRIPTION="${COMPOSED_CONTRACT_DESCRIPTION:-A composed contract issued via the deal flow}"

    echo_with_color "$CYAN" "🚀 Composed Contract — deal-flow integration test"
    echo_with_color "$BLUE" "  Auth:    $AUTH_SERVICE_URL"
    echo_with_color "$BLUE" "  Agents:  $AGENTS_SERVICE_URL"
    echo_with_color "$BLUE" "  Mode:    $ACTION_MODE"
    echo_with_color "$BLUE" "  Proposer:     $USER_EMAIL"
    echo_with_color "$BLUE" "  Counterparty: $COUNTERPARTY_EMAIL"
    echo ""

    check_service "Auth Service" "$AUTH_SERVICE_URL" || exit 1
    check_service "Agents Service" "$AGENTS_SERVICE_URL" || exit 1
    echo ""

    echo_with_color "$CYAN" "🔐 Authenticating proposer + counterparty..."
    local proposer_login
    proposer_login=$(login_user "$USER_EMAIL" "$PASSWORD") || exit 1
    local counterparty_login
    counterparty_login=$(login_user "$COUNTERPARTY_EMAIL" "$COUNTERPARTY_PASSWORD") || exit 1
    local proposer_jwt
    proposer_jwt=$(echo "$proposer_login" | jq -r '.token')
    local proposer_entity_id
    proposer_entity_id=$(echo "$proposer_login" | jq -r '.entity_id')
    local counterparty_jwt
    counterparty_jwt=$(echo "$counterparty_login" | jq -r '.token')
    local counterparty_entity_id
    counterparty_entity_id=$(echo "$counterparty_login" | jq -r '.entity_id')
    echo_with_color "$BLUE" "  Proposer entity:     $proposer_entity_id"
    echo_with_color "$BLUE" "  Counterparty entity: $counterparty_entity_id"
    echo ""

    # Build obligations array — proposer is the obligor on each leg,
    # counterparty is the holder. Use canonical entity ids (UUIDs);
    # the deal-flow rejects email-shaped strings at signDeal time.
    local coupon_dates
    coupon_dates='["2027-12-01T00:00:00Z","2027-12-05T00:00:00Z","2027-12-10T00:00:00Z","2027-12-15T00:00:00Z","2027-12-20T00:00:00Z"]'
    local coupon_count
    coupon_count=$(echo "$coupon_dates" | jq 'length')
    # Big-number math: jq treats numbers as f64 (53-bit mantissa), so
    # `(COUPON_AMOUNT | tonumber) * coupon_count | tostring` would
    # round 1e22 × 5 to f64 and emit "5e+22" — which the on-chain
    # u128 amount parser then rejects ("Invalid initial payment
    # amount: not a valid unsigned integer"). bc handles arbitrary
    # precision, keeping the result as the literal "50000000000000000000000".
    local coupon_total
    coupon_total=$(echo "$COUPON_AMOUNT * $coupon_count" | bc)

    local payments_array
    payments_array=$(echo "$coupon_dates" | jq '[.[] | {
        oracle_address: null, oracle_owner: null,
        oracle_key_sender: null, oracle_value_sender_secret: null,
        oracle_key_recipient: null, oracle_value_recipient_secret: null,
        unlock_sender: ., unlock_receiver: ., linear_vesting: null
    }]')

    # Per-obligation `counterpart` = the HOLDER who initially
    # receives the NFT. Setting counterpart=proposer means the
    # issuer holds each obligation right after creation, which is
    # what the swap needs (only the HOLDER can include an
    # obligation in a swap). The swap then transfers them to the
    # investor as the initiator's leg.
    local obligation_1
    obligation_1=$(jq -n \
        --arg counterpart "$proposer_entity_id" \
        --arg denomination "$DENOMINATION" \
        --arg obligor "$proposer_entity_id" \
        --arg notional "$coupon_total" \
        --arg expiry "${END_DATE}T23:59:59Z" \
        --argjson payments "$payments_array" \
        '{
            counterpart: $counterpart,
            denomination: $denomination,
            obligor: $obligor,
            notional: $notional,
            expiry: $expiry,
            data: { name: "Coupons", description: "Coupon Strip" },
            payments: $payments
        }')

    local obligation_2
    obligation_2=$(jq -n \
        --arg counterpart "$proposer_entity_id" \
        --arg denomination "$DENOMINATION" \
        --arg obligor "$proposer_entity_id" \
        --arg notional "$OBLIGATION_2_NOTIONAL" \
        --arg expiry "${END_DATE}T23:59:59Z" \
        '{
            counterpart: $counterpart,
            denomination: $denomination,
            obligor: $obligor,
            notional: $notional,
            expiry: $expiry,
            data: { name: "Redemption", description: "Redemption Obligation" },
            payments: [{
                unlock_sender: $expiry, unlock_receiver: $expiry
            }]
        }')

    local obligations_json
    obligations_json=$(jq -n --argjson a "$obligation_1" --argjson b "$obligation_2" '[$a, $b]')

    local plan_json
    if [[ "$ACTION_MODE" == "compose_only" ]]; then
        plan_json=$(build_plan "$CONTRACT_NAME" "$CONTRACT_DESCRIPTION" \
            "$counterparty_entity_id" "$obligations_json" "" "" "")
    else
        plan_json=$(build_plan "$CONTRACT_NAME" "$CONTRACT_DESCRIPTION" \
            "$counterparty_entity_id" "$obligations_json" \
            "$PAYMENT_AMOUNT" "$PAYMENT_DENOMINATION" "$DEADLINE")
    fi

    echo_with_color "$PURPLE" "📦 DealPlan:"
    echo "$plan_json" | jq '.' | sed 's/^/  /'
    echo ""

    echo_with_color "$CYAN" "📤 Proposing deal..."
    local propose_resp
    propose_resp=$(propose_deal "$proposer_jwt" "$plan_json" "$counterparty_entity_id")
    echo "$propose_resp" | jq '.' | sed 's/^/  /'
    local deal_id
    deal_id=$(echo "$propose_resp" | jq -r '.data.dealFlow.proposeDeal.deal.id // empty')
    if [[ -z "$deal_id" ]]; then
        echo_with_color "$RED" "❌ proposeDeal did not return a deal id"; exit 1
    fi
    echo_with_color "$GREEN" "  ✅ Deal proposed: $deal_id"
    echo ""

    echo_with_color "$CYAN" "✍️  Counterparty signing..."
    local sign_resp
    sign_resp=$(sign_deal "$counterparty_jwt" "$deal_id")
    echo "$sign_resp" | jq '.' | sed 's/^/  /'
    local sign_status
    sign_status=$(echo "$sign_resp" | jq -r '.data.dealFlow.signDeal.deal.status // empty')
    if [[ "$sign_status" != "ACCEPTED" ]]; then
        echo_with_color "$RED" "❌ signDeal did not move the deal to ACCEPTED (got: $sign_status)"; exit 1
    fi
    echo_with_color "$GREEN" "  ✅ Deal signed → ACCEPTED"
    echo ""

    echo_with_color "$CYAN" "🚀 Activating deal..."
    local activate_resp
    activate_resp=$(activate_deal "$proposer_jwt" "$deal_id")
    echo "$activate_resp" | jq '.' | sed 's/^/  /'
    local workflow_id
    workflow_id=$(echo "$activate_resp" | jq -r '.data.dealFlow.activateDeal.deal.workflowId // empty')
    if [[ -z "$workflow_id" ]]; then
        echo_with_color "$YELLOW" "  ⚠️  activateDeal returned no workflowId — pipeline runtime may not have spawned a workflow"
    else
        echo_with_color "$GREEN" "  ✅ Workflow spawned: $workflow_id"
    fi
    echo ""

    echo_with_color "$CYAN" "🔄 Polling deal status..."
    local final_resp
    final_resp=$(poll_deal_until_terminal "$proposer_jwt" "$deal_id") || exit 1
    echo "$final_resp" | jq '.' | sed 's/^/  /'

    local final_status
    final_status=$(echo "$final_resp" | jq -r '.data.dealFlow.dealById.status')
    if [[ "$final_status" == "COMPLETED" ]]; then
        echo_with_color "$GREEN" "🎉 Deal completed: $deal_id"
    else
        echo_with_color "$RED" "❌ Deal terminal but not completed: $final_status"
        exit 1
    fi
}

main "$@"
