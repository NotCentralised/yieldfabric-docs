#!/bin/bash

# YieldFabric Test Hutly Monoova Handler Test
# Test script for the test_hutly_monoova_handler endpoint (no JWT auth required)

BASE_URL="http://localhost:3002"

# Function to show usage
show_usage() {
    echo "🚀 YieldFabric Test Hutly Monoova Handler Test"
    echo "=================================================================="
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --agreement-id <id>      - Custom agreement ID (default: auto-generated)"
    echo "  --reference <ref>        - Custom reference (default: auto-generated)"
    echo "  --name <name>            - Custom agreement name (default: Test Agreement)"
    echo "  --bsb <bsb>              - Custom BSB code (default: 000)"
    echo "  --account <account>      - Custom account number (default: 000)"
    echo "  --start-date <date>      - Custom start date (default: 2025-01-01)"
    echo "  --end-date <date>        - Custom end date (default: 2025-12-31)"
    echo "  --help                   - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 --agreement-id my_agreement_123 --name 'Monthly Payment'"
    echo "  $0 --bsb 123456 --account 987654321"
    echo ""
    exit 1
}

# Function to pretty print JSON response
pretty_print_json() {
    local response_body="$1"
    if [ -n "$response_body" ]; then
        echo "   📄 Response Body (pretty-printed):"
        echo "$response_body" | jq '.' 2>/dev/null || echo "   (Raw response - jq not available): $response_body"
    else
        echo "   📄 Response Body: (empty)"
    fi
}

# Default values
AGREEMENT_ID="test_agreement_$(date +%s)"
REFERENCE="TEST_REF_$(date +%s)"
NAME="Test Payment Agreement"
BSB="000"
ACCOUNT="000"
START_DATE="2025-08-25"
END_DATE="2025-09-25"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agreement-id)
            AGREEMENT_ID="$2"
            shift 2
            ;;
        --reference)
            REFERENCE="$2"
            shift 2
            ;;
        --name)
            NAME="$2"
            shift 2
            ;;
        --bsb)
            BSB="$2"
            shift 2
            ;;
        --account)
            ACCOUNT="$2"
            shift 2
            ;;
        --start-date)
            START_DATE="$2"
            shift 2
            ;;
        --end-date)
            END_DATE="$2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "❌ Error: Unknown option $1"
            show_usage
            ;;
    esac
done

echo "🚀 Testing YieldFabric Test Hutly Monoova Handler"
echo "=================================================================="
echo "Endpoint: $BASE_URL/banking/test"
echo "Method: POST"
echo "Authentication: None required"
echo ""
echo "Test Parameters:"
echo "   Agreement ID: $AGREEMENT_ID"
echo "   Reference: $REFERENCE"
echo "   Name: $NAME"
echo "   BSB: $BSB"
echo "   Account: $ACCOUNT"
echo "   Start Date: $START_DATE"
echo "   End Date: $END_DATE"
echo ""

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 3

# Test 1: Health Check
echo -e "\n🔍 Test 1: Health Check"
echo "   Endpoint: $BASE_URL/health"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if [ $? -eq 0 ]; then
    echo "   ✅ Service responding"
else
    echo "   ❌ Health check failed"
    exit 1
fi

# Test 2: Test Hutly Monoova Handler
echo -e "\n🧪 Test 2: Test Hutly Monoova Handler"
echo "   Endpoint: $BASE_URL/banking/test"
echo "   Creating agreement and retrieving its details with provided parameters..."

# Prepare the request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "agreement_id": "$AGREEMENT_ID",
  "reference": "$REFERENCE",
  "name": "$NAME",
  "bsb": "$BSB",
  "account": "$ACCOUNT",
  "start_date": "$START_DATE",
  "end_date": "$END_DATE"
}
EOF
)

echo "   Request Payload:"
echo "$REQUEST_PAYLOAD" | jq '.' 2>/dev/null || echo "$REQUEST_PAYLOAD"

# Make the API call
echo -e "\n   📡 Making API call..."
TEST_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "$BASE_URL/banking/test" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD")

# Extract HTTP status and response body
HTTP_STATUS=$(echo "$TEST_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
RESPONSE_BODY=$(echo "$TEST_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

echo "   HTTP Status: $HTTP_STATUS"
pretty_print_json "$RESPONSE_BODY"

# Analyze the response
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
    echo "   ✅ Test completed successfully!"
    
    # Check if response has the expected structure
    if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
        echo "   ✅ Response has correct structure"
        
        # Extract and display key information
        if echo "$RESPONSE_BODY" | jq -e '.data.agreement.id' >/dev/null 2>&1; then
            AGREEMENT_ID_RESPONSE=$(echo "$RESPONSE_BODY" | jq -r '.data.agreement.id')
            echo "   📋 Agreement ID in response: $AGREEMENT_ID_RESPONSE"
        fi
        
        if echo "$RESPONSE_BODY" | jq -e '.data.agreement.create_response' >/dev/null 2>&1; then
            echo "   ✅ Agreement creation response available"
        fi
        
        if echo "$RESPONSE_BODY" | jq -e '.data.agreement.get_response' >/dev/null 2>&1; then
            echo "   ✅ Agreement retrieval response available"
        fi
        
        if echo "$RESPONSE_BODY" | jq -e '.data.token' >/dev/null 2>&1; then
            TOKEN_RESPONSE=$(echo "$RESPONSE_BODY" | jq -r '.data.token')
            echo "   🔑 Monoova token received: ${TOKEN_RESPONSE:0:20}..."
        fi
        
        # Validate that the response contains our input parameters
        echo "   🔍 Validating response data..."
        if echo "$RESPONSE_BODY" | jq -e --arg id "$AGREEMENT_ID" '.data.agreement.id == $id' >/dev/null 2>&1; then
            echo "   ✅ Agreement ID matches input"
        else
            echo "   ⚠️  Agreement ID mismatch"
        fi
        
        if echo "$RESPONSE_BODY" | jq -e --arg ref "$REFERENCE" '.data.agreement.reference == $ref' >/dev/null 2>&1; then
            echo "   ✅ Reference matches input"
        else
            echo "   ⚠️  Reference mismatch"
        fi
        
        if echo "$RESPONSE_BODY" | jq -e --arg name "$NAME" '.data.agreement.name == $name' >/dev/null 2>&1; then
            echo "   ✅ Name matches input"
        else
            echo "   ⚠️  Name mismatch"
        fi
        
    else
        echo "   ❌ Response missing 'success' field"
    fi
else
    echo "   ❌ Test failed - HTTP $HTTP_STATUS"
    
    # Try to extract error information
    if [ -n "$RESPONSE_BODY" ]; then
        ERROR_MSG=$(echo "$RESPONSE_BODY" | jq -r '.message // .error // "Unknown error"' 2>/dev/null)
        if [ "$ERROR_MSG" != "null" ] && [ "$ERROR_MSG" != "" ]; then
            echo "   📝 Error message: $ERROR_MSG"
        fi
    fi
fi

# Summary
echo -e "\n🎉 Test Hutly Monoova Handler Testing Completed!"
echo "   Endpoint: $BASE_URL/banking/test"
echo "   HTTP Status: $HTTP_STATUS"
echo "   Authentication: None required (as expected)"
echo "   Test Parameters: All provided parameters used"
echo ""
echo "🔍 Test Results:"
echo "   - Health check: ✅ Service responding"
echo "   - API call: $(if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then echo "✅ Success"; else echo "❌ Failed"; fi)"
echo "   - Response structure: $(if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then echo "✅ Valid"; else echo "❌ Invalid"; fi)"
echo "   - Using payments service on port 3002"
echo ""
echo "💡 Usage Tips:"
echo "   - This endpoint doesn't require JWT authentication"
echo "   - All parameters are customizable via command line options"
echo "   - The endpoint creates agreement and retrieves its details"
echo "   - Response includes both creation and retrieval responses for debugging"
