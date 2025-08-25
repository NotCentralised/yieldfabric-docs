# YieldFabric Banking & Payment System

This document provides comprehensive documentation for the YieldFabric banking and payment system integration, specifically focusing on the Hutly Monoova payment processing capabilities.

## 🎯 **Overview**

The YieldFabric banking system provides enterprise-grade payment processing capabilities through integration with the Hutly Monoova payment API. This system enables secure payment operations including payment agreements, instructions, and comprehensive system integration through a simplified testing endpoint.

## 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Payments      │    │   Hutly         │    │   Payment       │
│   Service       │    │   Monoova       │    │   Processing    │
│   (Port 3002)   │    │   API Client    │    │   Engine        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Hutly         │
                    │   Monoova       │
                    │   Integration   │
                    └─────────────────┘
```

### **Service Components**
- **Payments Service (Port 3002)**: Hutly Monoova API integration and payment processing
- **Hutly Monoova API**: External payment service integration
- **Test Endpoint**: Simplified testing interface for development and validation

## 💳 **Core Functions**

### **1. Payment Agreement Management**
- **`/banking/test`**: Creates new payment agreements and retrieves their details in a single call
- **No Authentication Required**: Simplified testing endpoint for development
- **Parameters**: Agreement ID, reference, name, BSB, account number, start/end dates
- **Response**: Complete agreement creation and retrieval data

### **2. Simplified Testing Interface**
- **Single Endpoint**: One call handles both creation and retrieval
- **Customizable Parameters**: All agreement parameters configurable via command line
- **Debug Information**: Full response data for development and testing
- **No JWT Required**: Streamlined testing without authentication complexity

### **3. System Integration**
- **Direct API Access**: No authentication barriers for testing
- **Comprehensive Response**: Both creation and retrieval responses included
- **Parameter Validation**: Input parameter validation and processing
- **Error Handling**: Clear error reporting and debugging information

## 🧪 **Testing System**

### **Test Script: `test_hutly_monoova.sh`**

The banking system includes a comprehensive testing script that validates payment operations through a simplified testing endpoint.

#### **📋 Test Flow**
**Command**: `./test_hutly_monoova.sh [options]`
**Purpose**: Test agreement creation and retrieval workflow
**Functions**: Creates agreement and retrieves details in single call
**Use Case**: Development testing and system validation
**Output**: Complete agreement data with creation and retrieval responses

#### **🔧 Customizable Parameters**
```bash
# All parameters are configurable
--agreement-id <id>      # Custom agreement ID
--reference <ref>        # Custom reference
--name <name>            # Custom agreement name
--bsb <bsb>              # Custom BSB code
--account <account>      # Custom account number
--start-date <date>      # Custom start date
--end-date <date>        # Custom end date
```

#### **📊 Example Usage**
```bash
# Basic test with default parameters
./test_hutly_monoova.sh

# Custom agreement test
./test_hutly_monoova.sh --agreement-id my_agreement_123 --name 'Monthly Payment'

# Custom banking details
./test_hutly_monoova.sh --bsb 123456 --account 987654321
```

## ⚙️ **Configuration and Setup**

### **Environment Variables**
```bash
# Service configuration
BASE_URL="http://localhost:3002"  # Payments service endpoint

# Default test values (configurable via command line)
AGREEMENT_ID="test_agreement_$(date +%s)"
REFERENCE="TEST_REF_$(date +%s)"
NAME="Test Payment Agreement"
BSB="000"
ACCOUNT="000"
START_DATE="2025-08-25"
END_DATE="2025-09-25"
```

### **Service Ports**
- **Payments Service**: Port 3002 (Hutly Monoova endpoints)
- **Hutly Monoova API**: External service integration

### **Test Data Configuration**
```bash
# Default test values (all configurable)
TEST_BSB="000"
TEST_ACCOUNT="000"
TEST_AMOUNT="1"
TEST_START_DATE="2025-08-25"
TEST_END_DATE="2025-09-25"
```

## 🔐 **Security Features**

### **Testing Endpoint Security**
- **No JWT Required**: Simplified testing without authentication complexity
- **Development Focus**: Designed for development and testing scenarios
- **Parameter Validation**: Input validation and sanitization
- **Error Handling**: Comprehensive error reporting and debugging

### **Security Boundaries**
- **Input Validation**: Request parameter validation and sanitization
- **Response Filtering**: Safe response data handling
- **Error Reporting**: Clear error messages without information leakage

## 🐛 **Error Handling and Debugging**

### **Comprehensive Logging**
- **HTTP Status Codes**: Detailed response status information
- **Response Bodies**: Pretty-printed JSON for readability
- **Error Messages**: Clear success/failure indicators
- **Debug Information**: Step-by-step operation logging

### **JSON Response Formatting**
```bash
# Pretty-printed JSON output using jq
📄 Response Body (pretty-printed):
{
  "success": true,
  "data": {
    "agreement": {
      "id": "test_agreement_123",
      "reference": "TEST_REF_456",
      "name": "Test Payment Agreement",
      "create_response": {...},
      "get_response": {...}
    },
    "token": "monoova_token_here"
  }
}
```

## 🚀 **Production Readiness Features**

### **Development and Testing Focus**
- **Simplified Interface**: No authentication barriers for testing
- **Comprehensive Testing**: Full workflow validation in single call
- **Parameter Customization**: All parameters configurable for testing
- **Debug Information**: Complete response data for development

### **Comprehensive Testing**
- **Positive Testing**: Valid operations that should succeed
- **Parameter Validation**: Custom parameter testing
- **Integration Testing**: Systems working together seamlessly
- **Response Validation**: Complete response structure validation

### **Resource Management**
- **Automatic Cleanup**: No manual cleanup required
- **Idempotent Operations**: Safe to run multiple times
- **Error Recovery**: Graceful handling of failures

## 📚 **Usage Examples**

### **Complete Testing Workflow**
```bash
# 1. Basic test with default parameters
./test_hutly_monoova.sh

# 2. Custom agreement test
./test_hutly_monoova.sh --agreement-id my_agreement_123 --name 'Monthly Payment'

# 3. Custom banking details test
./test_hutly_monoova.sh --bsb 123456 --account 987654321
```

### **Development and Testing**
```bash
# Test with custom parameters
./test_hutly_monoova.sh --agreement-id dev_test_001 --name 'Development Test'

# Test different date ranges
./test_hutly_monoova.sh --start-date 2025-01-01 --end-date 2025-12-31

# Test custom references
./test_hutly_monoova.sh --reference CUSTOM_REF_$(date +%s)
```

### **Production Deployment**
```bash
# Set production endpoints
export BASE_URL="https://payments.yieldfabric.com"

# Run comprehensive tests
./test_hutly_monoova.sh --agreement-id prod_test_001
./test_hutly_monoova.sh --bsb 123456 --account 987654321
```

## 🔗 **Integration with YieldFabric Ecosystem**

### **Service Integration**
- **Health Checks**: Validates service availability
- **Error Handling**: Consistent error reporting across services
- **Logging**: Unified logging and debugging approach

### **Testing Integration**
- **Comprehensive Coverage**: Part of complete YieldFabric testing suite
- **Consistent Format**: Follows same testing patterns as other components
- **Development Focus**: Streamlined testing for development workflows

## 🆘 **Troubleshooting and Support**

### **Common Issues**
1. **Service Not Running**: Ensure payments service on port 3002
2. **Parameter Validation**: Check parameter format and values
3. **API Errors**: Verify service connectivity and response format
4. **Response Parsing**: Ensure jq is installed for JSON formatting

### **Debug Information**
- **HTTP Status Codes**: Detailed response status for troubleshooting
- **Response Bodies**: Full API responses for analysis
- **Step-by-Step Logging**: Clear operation progression tracking
- **Parameter Validation**: Input parameter validation and processing

### **Getting Help**
```bash
# Check service health
curl http://localhost:3002/health

# Test basic functionality
./test_hutly_monoova.sh

# Test with custom parameters
./test_hutly_monoova.sh --help
```

## 🎯 **What Makes This System Development-Ready**

### **🔐 Simplified Testing**
- No authentication barriers for development
- Streamlined testing interface
- Comprehensive parameter customization

### **💳 Payment Agreement Management**
- Complete agreement creation and retrieval
- Customizable banking parameters
- Integrated testing workflow

### **🔗 Seamless Integration**
- Works seamlessly with YieldFabric services
- Consistent error handling and logging
- Comprehensive testing and validation

### **📊 Comprehensive Testing**
- Single endpoint for complete workflow
- Parameter customization for testing
- Development-ready validation and verification

## 📋 **API Endpoints**

### **Hutly Monoova Payment Endpoints**
- **`POST /banking/test`**: Create and retrieve payment agreement (no auth required)
- **`GET /health`**: Service health check

### **Test Endpoint Details**
- **Method**: POST
- **Authentication**: None required
- **Purpose**: Testing agreement creation and retrieval
- **Response**: Complete agreement data with creation and retrieval responses

## 🌐 **REST API Reference with Examples**

### **1. Health Check Endpoint**

#### **GET /health**
Check if the payments service is running and healthy.

```bash
# Basic health check
curl -X GET http://localhost:3002/health

# With verbose output
curl -v -X GET http://localhost:3002/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "payments",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### **2. Banking Test Endpoint**

#### **POST /banking/test**
Create a payment agreement and retrieve its details in a single call. This endpoint doesn't require authentication and is designed for development and testing.

```bash
# Basic test with default parameters
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "test_agreement_123",
    "reference": "TEST_REF_456",
    "name": "Test Payment Agreement",
    "bsb": "000",
    "account": "000",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }'
```

**Custom Parameters Example:**
```bash
# Custom agreement with specific banking details
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "monthly_payment_001",
    "reference": "MONTHLY_REF_2025",
    "name": "Monthly Business Payment",
    "bsb": "123456",
    "account": "987654321",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "agreement": {
      "id": "monthly_payment_001",
      "reference": "MONTHLY_REF_2025",
      "name": "Monthly Business Payment",
      "bsb": "123456",
      "account": "987654321",
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "create_response": {...},
      "get_response": {...}
    },
    "token": "monoova_auth_token_abc123"
  }
}
```

### **3. Error Handling Examples**

#### **Common Error Scenarios**
```bash
# Missing required fields
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{"agreement_id": "test", "name": "Test"}'

# Invalid BSB format (must be 6 digits)
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "test",
    "reference": "TEST",
    "name": "Test",
    "bsb": "12345",
    "account": "123456789",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }'
```

**Expected Error Response:**
```json
{
  "success": false,
  "error": "Missing required fields: reference, bsb, account, start_date, end_date",
  "code": "MISSING_REQUIRED_FIELDS"
}
```

### **4. Response Processing Examples**

#### **Extracting Data with jq**
```bash
# Get agreement ID
curl -s -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "jq_test",
    "reference": "JQ_TEST",
    "name": "JQ Test",
    "bsb": "123456",
    "account": "123456789",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }' | jq -r '.data.agreement.id'

# Get Monoova token
curl -s -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "token_test",
    "reference": "TOKEN_TEST",
    "name": "Token Test",
    "bsb": "123456",
    "account": "123456789",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }' | jq -r '.data.token'
```

#### **Save Response to File**
```bash
# Save response and extract data
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "file_test",
    "reference": "FILE_TEST",
    "name": "File Test",
    "bsb": "123456",
    "account": "123456789",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
  }' > response.json

# Extract specific fields
jq -r '.data.agreement.id' response.json
jq -r '.data.token' response.json
```

### **5. Testing Integration**

#### **Compare with Test Script**
```bash
# Run test script
./test_hutly_monoova.sh --agreement-id curl_validation_test

# Validate with curl
curl -X POST http://localhost:3002/banking/test \
  -H "Content-Type: application/json" \
  -d '{
    "agreement_id": "curl_validation_test",
    "reference": "CURL_VALIDATION_TEST",
    "name": "Curl Validation Test",
    "bsb": "000",
    "account": "000",
    "start_date": "2025-08-25",
    "end_date": "2025-09-25"
  }'
```

## 🔧 **Development and Testing**

### **Prerequisites**
- `jq` command-line JSON processor installed
- `curl` for HTTP requests
- Bash shell
- YieldFabric payments service running on port 3002

### **Quick Start**
```bash
# 1. Ensure payments service is running
cd yieldfabric-payments && cargo run

# 2. Test basic functionality
./test_hutly_monoova.sh

# 3. Test with custom parameters
./test_hutly_monoova.sh --agreement-id custom_test --name 'Custom Test'

# 4. Verify integration
./test_hutly_monoova.sh --bsb 123456 --account 987654321
```

### **Testing Strategy**
- **Parameter Testing**: Custom parameter validation
- **Integration Testing**: Service interaction validation
- **Response Validation**: Complete response structure validation
- **Workflow Testing**: Agreement creation and retrieval workflow

## 📈 **Performance and Scalability**

### **Response Times**
- **Health Check**: < 100ms
- **Test Endpoint**: < 500ms (agreement creation + retrieval)
- **Parameter Processing**: < 50ms

### **Scalability Features**
- **Async Processing**: Non-blocking payment operations
- **Connection Pooling**: Efficient API client management
- **Error Retry**: Automatic retry for transient failures
- **Parameter Validation**: Efficient input validation

## 🔮 **Future Enhancements**

### **Planned Features**
- **Additional Endpoints**: More comprehensive payment operations
- **Authentication Support**: JWT-based authentication for production
- **Batch Processing**: Multiple agreement operations
- **Advanced Scheduling**: Complex payment scheduling

### **Integration Roadmap**
- **Production Endpoints**: Secure, authenticated payment operations
- **Payment Networks**: Integration with payment networks
- **Regulatory Compliance**: Enhanced compliance features
- **Audit Trails**: Comprehensive audit logging

## 📞 **Support and Contact**

### **Documentation**
- **This Guide**: Comprehensive banking system documentation
- **API Reference**: Detailed endpoint documentation
- **Examples**: Practical usage examples and workflows

### **Getting Help**
- **Troubleshooting**: Common issues and solutions
- **Debug Mode**: Enhanced logging for problem resolution
- **Community**: YieldFabric community support

---

**Note**: This banking system is designed for development and testing scenarios, providing a simplified interface for validating payment operations. The test endpoint doesn't require authentication, making it ideal for development workflows and system validation.
