#!/usr/bin/env bash
# Query Jena/Fuseki for Token data (e.g. payment tokens).
# Usage: ./query_jena_tokens.sh [base_url]
# Default: http://localhost:3030/ds (override if Fuseki is elsewhere, e.g. http://graph_fuseki:3030/ds)
set -e

BASE_URL="${1:-http://localhost:3030/ds}"
USER="${JENA_USERNAME:-admin}"
PASS="${JENA_PASSWORD:-yieldfabric123}"
QUERY_URL="${BASE_URL}/query"

echo "=== Jena/Fuseki token queries (endpoint: $QUERY_URL) ==="

# 1) Query for the specific initial payment token that was reported missing
TOKEN_ID="${2:-PAY-INITIAL-CONTRACT-OBLIGATION-177078693401183774468-0-payment-token}"
echo ""
echo "--- 1) Token by id: $TOKEN_ID ---"
curl -s -X POST "$QUERY_URL" \
  -u "$USER:$PASS" \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @- << SPARQL
PREFIX : <http://example.org/tokens#>
PREFIX unit: <http://example.org/units#>
PREFIX txn: <http://example.org/transactions#>
SELECT ?id ?chainId ?address ?name ?createdAt ?deleted
WHERE {
    ?resource a :Token ;
        :id ?unitId ;
        :chainId ?chainId ;
        :address ?address ;
        :name ?name ;
        :transaction ?transaction .
    ?unitId unit:id ?id .
    ?transaction txn:createdAt ?createdAt .
    OPTIONAL { ?resource :deleted ?deleted }
    FILTER(?id = "$TOKEN_ID")
}
ORDER BY DESC(?createdAt)
LIMIT 5
SPARQL
echo ""

# 2) List all token IDs that look like payment tokens
echo "--- 2) All token IDs containing 'payment-token' ---"
curl -s -X POST "$QUERY_URL" \
  -u "$USER:$PASS" \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @- << 'SPARQL'
PREFIX : <http://example.org/tokens#>
PREFIX unit: <http://example.org/units#>
PREFIX txn: <http://example.org/transactions#>
SELECT ?id ?createdAt ?deleted
WHERE {
    ?resource a :Token ; :id ?unitId ; :transaction ?transaction .
    ?unitId unit:id ?id .
    ?transaction txn:createdAt ?createdAt .
    OPTIONAL { ?resource :deleted ?deleted }
    FILTER(CONTAINS(?id, "payment-token"))
}
ORDER BY DESC(?createdAt)
SPARQL
echo ""

echo "=== Done ==="
