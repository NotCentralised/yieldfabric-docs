#!/usr/bin/env bash
# Query Jena/Fuseki for a Payment record and whether its linked Token exists.
# Usage: ./query_jena_payment_and_token.sh [base_url] [payment_id]
# Example: ./query_jena_payment_and_token.sh http://localhost:3030/ds PAY-INITIAL-CONTRACT-OBLIGATION-177078693401183774468-0
set -e

BASE_URL="${1:-http://localhost:3030/ds}"
PAYMENT_ID="${2:-PAY-INITIAL-CONTRACT-OBLIGATION-177078693401183774468-0}"
USER="${JENA_USERNAME:-admin}"
PASS="${JENA_PASSWORD:-yieldfabric123}"
QUERY_URL="${BASE_URL}/query"

echo "=== Payment and linked token in Jena (endpoint: $QUERY_URL) ==="
echo "Payment ID: $PAYMENT_ID"
echo ""

# 1) Get the payment record: what token_id does it link to? (payments use pay: token -> unit:tokenId)
echo "--- 1) Payment record(s) and linked token_id ---"
curl -s -X POST "$QUERY_URL" \
  -u "$USER:$PASS" \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @- << SPARQL
PREFIX pay: <http://example.org/payments#>
PREFIX unit: <http://example.org/units#>
PREFIX txn: <http://example.org/transactions#>
SELECT ?paymentId ?tokenId ?status ?amount ?contractId ?createdAt
WHERE {
  ?paymentResource a pay:Payment ;
    pay:id ?paymentUnit ;
    pay:status ?status ;
    pay:amount ?amount ;
    pay:contract ?contractUnit ;
    pay:transaction ?txn .
  ?paymentUnit unit:id ?paymentId .
  ?contractUnit unit:id ?contractId .
  ?txn txn:createdAt ?createdAt .
  OPTIONAL {
    ?paymentResource pay:token ?tokenUnit .
    BIND(REPLACE(STR(?tokenUnit), ".*#", "") AS ?tokenId)
  }
  FILTER(?paymentId = "$PAYMENT_ID")
}
ORDER BY DESC(?createdAt)
LIMIT 5
SPARQL
echo ""

# 2) Does that token exist in the Token store? (use token_id from convention if not in result: payment_id + "-payment-token")
TOKEN_ID="${PAYMENT_ID}-payment-token"
echo "--- 2) Token store: does token '$TOKEN_ID' exist? ---"
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

# 3) Any token that references this payment in name or description (in case it was created under a different id)
echo "--- 3) Any token whose name/description contains this payment id? ---"
curl -s -X POST "$QUERY_URL" \
  -u "$USER:$PASS" \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @- << SPARQL
PREFIX : <http://example.org/tokens#>
PREFIX unit: <http://example.org/units#>
PREFIX txn: <http://example.org/transactions#>
SELECT ?id ?name ?description ?createdAt
WHERE {
    ?resource a :Token ;
        :id ?unitId ;
        :name ?name ;
        :description ?description ;
        :transaction ?transaction .
    ?unitId unit:id ?id .
    ?transaction txn:createdAt ?createdAt .
    FILTER(CONTAINS(?name, "$PAYMENT_ID") || CONTAINS(?description, "$PAYMENT_ID"))
}
ORDER BY DESC(?createdAt)
SPARQL
echo ""

echo "=== Done ==="
