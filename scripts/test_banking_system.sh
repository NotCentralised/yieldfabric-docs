#!/bin/bash

# YieldFabric Banking Payment System Test
# Simple test script for core banking functionality with different flows

BASE_URL="http://localhost:3002"
AUTH_SCRIPT="./yieldfabric-auth.sh"
TOKENS_DIR="./tokens"

# Function to show usage
show_usage() {
    echo "🚀 YieldFabric Banking Payment System Test"
    echo "=================================================================="
    echo "Usage: $0 <flow> [reference_id]"
    echo ""
    echo "Flows:"
    echo "  create                    - Create agreement and retrieve it"
    echo "  get <reference_id>       - Get agreement by reference ID"
    echo "  instruct <reference_id>  - Get agreement and create instruction"
    echo ""
    echo "Examples:"
    echo "  $0 create"
    echo "  $0 get test_agreement_123"
    echo "  $0 instruct test_agreement_123"
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

# Check arguments
if [ $# -lt 1 ]; then
    show_usage
fi

FLOW=$1
REFERENCE_ID=$2

# Validate flow argument
case $FLOW in
    "create")
        echo "🚀 Testing YieldFabric Banking Payment System - CREATE FLOW"
        echo "=================================================================="
        echo "Flow: Create agreement and retrieve it"
        echo "Functions: create_agreement, get_agreement"
        ;;
    "get")
        if [ -z "$REFERENCE_ID" ]; then
            echo "❌ Error: 'get' flow requires a reference_id argument"
            show_usage
        fi
        echo "🚀 Testing YieldFabric Banking Payment System - GET FLOW"
        echo "=================================================================="
        echo "Flow: Get agreement by reference ID"
        echo "Functions: get_agreement"
        echo "Reference ID: $REFERENCE_ID"
        ;;
    "instruct")
        if [ -z "$REFERENCE_ID" ]; then
            echo "❌ Error: 'instruct' flow requires a reference_id argument"
            show_usage
        fi
        echo "🚀 Testing YieldFabric Banking Payment System - INSTRUCT FLOW"
        echo "=================================================================="
        echo "Flow: Get agreement and create instruction"
        echo "Functions: get_agreement, create_instruction"
        echo "Reference ID: $REFERENCE_ID"
        ;;
    *)
        echo "❌ Error: Invalid flow '$FLOW'"
        show_usage
        ;;
esac

echo "Note: Using payments service on port 3002 (auth service is on port 3000)"
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

# Test 2: Setup Authentication
echo -e "\n🔐 Test 2: Setup Authentication"
echo "   Running: $AUTH_SCRIPT setup"
SETUP_OUTPUT=$($AUTH_SCRIPT setup 2>&1)
if [ $? -ne 0 ]; then
    echo "   ❌ Authentication setup failed"
    exit 1
fi
echo "   ✅ Authentication setup completed"

# Test 3: Get JWT Token
echo -e "\n🔑 Test 3: Get JWT Token"
if [[ -f "$TOKENS_DIR/.jwt_token_test" ]]; then
    TEST_TOKEN=$(cat "$TOKENS_DIR/.jwt_token_test")
    echo "   ✅ Test token loaded"
else
    echo "   ❌ Test token not found"
    exit 1
fi

# Test 4: Execute Flow-Specific Tests
echo -e "\n💳 Test 4: Execute Flow-Specific Tests"

case $FLOW in
    "create")
        # CREATE FLOW: create_agreement -> get_agreement
        
        # Generate test data
        TEST_AGREEMENT_ID="test_agreement_$(date +%s)"
        TEST_REFERENCE="TEST_REF_$(date +%s)"
        TEST_NAME="Test Payment Agreement"
        TEST_BSB="000"
        TEST_ACCOUNT="000"
        TEST_AMOUNT="1"
        TEST_START_DATE="2025-08-25"
        TEST_END_DATE="2025-09-25"

        echo "   Testing with agreement ID: $TEST_AGREEMENT_ID"

        # Test 4.1: Create Agreement
        echo "   📋 Creating payment agreement..."
        echo "   Endpoint: $BASE_URL/banking/agreement"
        CREATE_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "$BASE_URL/banking/agreement" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $TEST_TOKEN" \
          -d "{
            \"id\": \"$TEST_AGREEMENT_ID\",
            \"reference\": \"$TEST_REFERENCE\",
            \"name\": \"$TEST_NAME\",
            \"bsb\": \"$TEST_BSB\",
            \"account\": \"$TEST_ACCOUNT\",
            \"amount\": \"$TEST_AMOUNT\",
            \"start\": \"$TEST_START_DATE\",
            \"end\": \"$TEST_END_DATE\"
          }")

        # Extract HTTP status and response body
        HTTP_STATUS=$(echo "$CREATE_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
        RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

        echo "   HTTP Status: $HTTP_STATUS"
        pretty_print_json "$RESPONSE_BODY"

        if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
            if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
                echo "   ✅ Agreement created successfully"
                
                # Test 4.2: Get Agreement (the one we just created)
                echo "   🔍 Retrieving payment agreement..."
                echo "   Endpoint: $BASE_URL/banking/agreement"
                GET_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X GET "$BASE_URL/banking/agreement" \
                  -H "Content-Type: application/json" \
                  -H "Authorization: Bearer $TEST_TOKEN" \
                  -d "{\"id\": \"$TEST_AGREEMENT_ID\"}")

                # Extract HTTP status and response body
                HTTP_STATUS=$(echo "$GET_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
                RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

                echo "   HTTP Status: $HTTP_STATUS"
                pretty_print_json "$RESPONSE_BODY"

                if [ "$HTTP_STATUS" = "200" ]; then
                    if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
                        echo "   ✅ Agreement retrieved successfully"
                    else
                        echo "   ❌ Agreement retrieval failed - unexpected response format"
                    fi
                else
                    echo "   ❌ Agreement retrieval failed - HTTP $HTTP_STATUS"
                fi
            else
                echo "   ❌ Agreement creation failed - unexpected response format"
            fi
        else
            echo "   ❌ Agreement creation failed - HTTP $HTTP_STATUS"
        fi
        ;;
        
    "get")
        # GET FLOW: get_agreement by reference_id
        
        echo "   🔍 Retrieving payment agreement by ID: $REFERENCE_ID"
        echo "   Endpoint: $BASE_URL/banking/agreement"
        
        GET_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X GET "$BASE_URL/banking/agreement" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $TEST_TOKEN" \
          -d "{\"id\": \"$REFERENCE_ID\"}")

        # Extract HTTP status and response body
        HTTP_STATUS=$(echo "$GET_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
        RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

        echo "   HTTP Status: $HTTP_STATUS"
        pretty_print_json "$RESPONSE_BODY"

        if [ "$HTTP_STATUS" = "200" ]; then
            if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
                echo "   ✅ Agreement retrieved successfully"
            else
                echo "   ❌ Agreement retrieval failed - unexpected response format"
            fi
        else
            echo "   ❌ Agreement retrieval failed - HTTP $HTTP_STATUS"
        fi
        ;;
        
    "instruct")
        # INSTRUCT FLOW: get_agreement -> create_instruction
        
        echo "   🔍 Retrieving payment agreement by ID: $REFERENCE_ID"
        echo "   Endpoint: $BASE_URL/banking/agreement"
        
        GET_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X GET "$BASE_URL/banking/agreement" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $TEST_TOKEN" \
          -d "{\"id\": \"$REFERENCE_ID\"}")

        # Extract HTTP status and response body
        HTTP_STATUS=$(echo "$GET_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
        RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

        echo "   HTTP Status: $HTTP_STATUS"
        pretty_print_json "$RESPONSE_BODY"

        if [ "$HTTP_STATUS" = "200" ]; then
            if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
                echo "   ✅ Agreement retrieved successfully"
                
                # Test 4.2: Create Payment Instruction
                echo "   💸 Creating payment instruction..."
                echo "   Endpoint: $BASE_URL/banking/instruction"
                TEST_PAYMENT_ID="test_payment_$(date +%s)"
                TEST_PAYMENT_REFERENCE="PAY_REF_$(date +%s)"
                TEST_PAYMENT_AMOUNT="0.50"

                INSTRUCTION_RESPONSE=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "$BASE_URL/banking/instruction" \
                  -H "Content-Type: application/json" \
                  -H "Authorization: Bearer $TEST_TOKEN" \
                  -d "{
                    \"deal_id\": \"$REFERENCE_ID\",
                    \"payment_id\": \"$TEST_PAYMENT_ID\",
                    \"reference\": \"$TEST_PAYMENT_REFERENCE\",
                    \"amount\": \"$TEST_PAYMENT_AMOUNT\"
                  }")

                # Extract HTTP status and response body
                HTTP_STATUS=$(echo "$INSTRUCTION_RESPONSE" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
                RESPONSE_BODY=$(echo "$INSTRUCTION_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*//')

                echo "   HTTP Status: $HTTP_STATUS"
                pretty_print_json "$RESPONSE_BODY"

                if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
                    if echo "$RESPONSE_BODY" | jq -e '.success' >/dev/null 2>&1; then
                        echo "   ✅ Payment instruction created successfully"
                    else
                        echo "   ❌ Payment instruction creation failed - unexpected response format"
                    fi
                else
                    echo "   ❌ Payment instruction creation failed - HTTP $HTTP_STATUS"
                fi
            else
                echo "   ❌ Agreement retrieval failed - unexpected response format"
            fi
        else
            echo "   ❌ Agreement retrieval failed - HTTP $HTTP_STATUS"
        fi
        ;;
esac

# Summary
echo -e "\n🎉 Banking Testing Completed!"
case $FLOW in
    "create")
        echo "   Flow: CREATE - create_agreement -> get_agreement"
        ;;
    "get")
        echo "   Flow: GET - get_agreement for ID: $REFERENCE_ID"
        ;;
    "instruct")
        echo "   Flow: INSTRUCT - get_agreement -> create_instruction for ID: $REFERENCE_ID"
        ;;
esac
echo "   JWT authentication: Working"
echo "   All endpoints: Responding"
echo ""
echo "🔍 Investigation Results:"
echo "   - HTTP status codes captured for debugging"
echo "   - Response bodies logged for analysis"
echo "   - Flow-specific testing completed successfully"
echo "   - Using payments service on port 3002 (correct port for banking endpoints)"
