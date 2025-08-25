# YieldFabric Payment System Operations Manual

This manual provides practical instructions for using the YieldFabric payment system. Learn how to execute payment operations, manage payment flows, and integrate with the authentication and vault services.

## 🚀 **Quick Start Guide**

### **1. Start Required Services**
```bash
# Start authentication service
cd yieldfabric-auth && cargo run

# Start payments service  
cd yieldfabric-payments && cargo run

# Start vault service (if needed for crypto operations)
cd yieldfabric-vault && cargo run
```

### **2. Check Service Status**
```bash
# Check if all services are running
./execute_commands.sh status

# Expected output:
#   Auth Service (port 3000) - Running
#   Payments Service (port 3002) - Running
```

### **3. Execute Your First Payment Flow**
```bash
# Run all commands from commands.yaml
./execute_commands.sh execute

# Or validate your commands first
./execute_commands.sh validate
```

## 🏗️ **Payment System Architecture**

### **Service Layer**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Auth Service  │    │  Payments       │    │   Vault         │
│   (Port 3000)   │    │  Service        │    │   Service       │
│                 │    │  (Port 3002)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   JWT Token     │
                    │   Validation    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Payment        │
                    │  Execution      │
                    └─────────────────┘
```

### **Payment Flow Types**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Deposit       │    │   Instant       │    │   Accept        │
│   Operations    │    │   Payments      │    │   Operations    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Command       │
                    │   Chaining      │
                    └─────────────────┘
```

## 💰 **Payment Operations**

### **1. Deposit Operations**
Fund an account with tokens:

```bash
# Direct API call
curl -X POST http://localhost:3002/deposit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "token_id": "token-AUD",
    "amount": "10",
    "idempotency_key": "deposit-1"
  }'

# Response
{
  "success": true,
  "account_address": "account_abc123",
  "message": "Deposit successful",
  "message_id": "msg_xyz789"
}
```

**Parameters:**
- **`token_id`**: Token identifier (e.g., "token-AUD", "token-USD")
- **`amount`**: Amount to deposit (numeric string)
- **`idempotency_key`**: Unique identifier to prevent duplicate deposits

### **2. Instant Payments**
Send tokens immediately to another user:

```bash
# Direct API call
curl -X POST http://localhost:3002/instant \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "token_id": "token-AUD",
    "amount": "5",
    "destination_id": "recipient@yieldfabric.com",
    "idempotency_key": "instant-1"
  }'

# Response
{
  "success": true,
  "account_address": "account_abc123",
  "destination_id": "recipient@yieldfabric.com",
  "message": "Instant payment successful",
  "id_hash": "hash_123456",
  "message_id": "msg_xyz789"
}
```

**Parameters:**
- **`token_id`**: Token identifier for the payment
- **`amount`**: Amount to send
- **`destination_id`**: Recipient's email address
- **`idempotency_key`**: Unique identifier for the transaction

### **3. Accept Operations**
Accept incoming payments using the ID hash:

```bash
# Direct API call
curl -X POST http://localhost:3002/accept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "id_hash": "hash_123456",
    "idempotency_key": "accept-1"
  }'

# Response
{
  "success": true,
  "account_address": "account_def456",
  "message": "Payment accepted successfully",
  "id_hash": "hash_123456",
  "message_id": "msg_abc123"
}
```

**Parameters:**
- **`id_hash`**: Hash from the instant payment response
- **`idempotency_key`**: Unique identifier for the acceptance

## 📋 **Command Configuration (commands.yaml)**

### **Basic Structure**
```yaml
commands:
  - name: issuer_deposit
    type: deposit
    user: 
      id: issuer@yieldfabric.com
      password: issuerpass456
    parameters:
      token_id: token-AUD
      amount: 10
      idempotency_key: deposit-1
```

### **Command Types**
| **Type** | **Description** | **Required Parameters** | **Optional Parameters** |
|----------|----------------|------------------------|------------------------|
| **`deposit`** | Fund an account | `token_id`, `amount` | `idempotency_key` |
| **`instant`** | Send immediate payment | `token_id`, `amount`, `destination_id` | `idempotency_key` |
| **`accept`** | Accept incoming payment | `id_hash` | `idempotency_key` |

### **User Configuration**
```yaml
user: 
  id: user@yieldfabric.com      # User's email address
  password: userpassword123     # User's password
```

### **Parameter Reference**
| **Parameter** | **Type** | **Description** | **Example** |
|---------------|----------|-----------------|-------------|
| **`token_id`** | String | Token identifier | `"token-AUD"`, `"token-USD"` |
| **`amount`** | String | Numeric amount | `"10"`, `"100.50"` |
| **`destination_id`** | String | Recipient email | `"recipient@company.com"` |
| **`id_hash`** | String | Payment hash | `"hash_abc123"` |
| **`idempotency_key`** | String | Unique identifier | `"txn_001"`, `"payment_2024_001"` |

## 🔗 **Command Chaining with Variables**

### **Variable Substitution**
Reference outputs from previous commands using the format `$command_name.field_name`:

```yaml
commands:
  - name: issuer_send_1
    type: instant
    user: 
      id: issuer@yieldfabric.com
      password: issuerpass456
    parameters:
      token_id: token-AUD
      amount: 5
      destination_id: counterpart@yieldfabric.com
      idempotency_key: instant-1

  - name: counterpart_accept
    type: accept
    user: 
      id: counterpart@yieldfabric.com
      password: counterpass789
    parameters:
      id_hash: $issuer_send_1.id_hash    # Use id_hash from previous command
      idempotency_key: accept-1
```

### **Available Output Fields**
| **Command Type** | **Available Fields** | **Description** |
|------------------|---------------------|-----------------|
| **`deposit`** | `account_address`, `message`, `message_id` | Account details and confirmation |
| **`instant`** | `account_address`, `destination_id`, `message`, `id_hash`, `message_id` | Payment details and hash |
| **`accept`** | `account_address`, `message`, `id_hash`, `message_id` | Acceptance confirmation |

### **Variable Usage Examples**
```yaml
# Use amount from previous deposit
amount: $issuer_deposit.amount

# Use id_hash from instant payment
id_hash: $issuer_send_1.id_hash

# Use message_id for tracking
reference: $instant_payment.message_id
```

## 🛠️ **Command Execution**

### **Execute All Commands**
```bash
# Run all commands sequentially
./execute_commands.sh execute

# Commands execute in order with 2-second delays
# Variable substitution happens automatically
```

### **Validate Commands**
```bash
# Check commands.yaml structure
./execute_commands.sh validate

# Validates:
# - Required fields are present
# - Command types are supported
# - User credentials are provided
# - Parameters match command type
```

### **Check Status**
```bash
# View service status and requirements
./execute_commands.sh status

# Shows:
# - Service availability (ports 3000, 3002)
# - Commands.yaml file status
# - YAML parser availability
# - Command count and details
```

### **View Variables**
```bash
# Show stored variables for chaining
./execute_commands.sh variables

# Displays:
# - All stored command outputs
# - Variable names for substitution
# - Usage examples
```

## 🔐 **Authentication Integration**

### **JWT Token Flow**
```bash
# 1. User login with services
curl -X POST "http://localhost:3000/auth/login/with-services" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@yieldfabric.com",
    "password": "userpass123",
    "services": ["vault", "payments"]
  }'

# 2. Extract JWT token from response
# 3. Use token for payment operations
```

### **Required Services**
- **Auth Service**: Port 3000 for user authentication
- **Payments Service**: Port 3002 for payment operations
- **Vault Service**: For cryptographic operations (if needed)

## 📊 **Payment Flow Examples**

### **Example 1: Simple Deposit and Send**
```yaml
commands:
  # Step 1: Fund the issuer account
  - name: issuer_deposit
    type: deposit
    user: 
      id: issuer@yieldfabric.com
      password: issuerpass456
    parameters:
      token_id: token-AUD
      amount: 100
      idempotency_key: deposit-100

  # Step 2: Send payment to counterparty
  - name: issuer_send
    type: instant
    user: 
      id: issuer@yieldfabric.com
      password: issuerpass456
    parameters:
      token_id: token-AUD
      amount: 50
      destination_id: counterpart@yieldfabric.com
      idempotency_key: send-50

  # Step 3: Counterparty accepts payment
  - name: counterpart_accept
    type: accept
    user: 
      id: counterpart@yieldfabric.com
      password: counterpass789
    parameters:
      id_hash: $issuer_send.id_hash
      idempotency_key: accept-50
```

### **Example 2: Multiple Recipients**
```yaml
commands:
  # Fund account
  - name: fund_account
    type: deposit
    user: 
      id: sender@yieldfabric.com
      password: senderpass123
    parameters:
      token_id: token-USD
      amount: 200
      idempotency_key: fund-200

  # Send to first recipient
  - name: send_to_alice
    type: instant
    user: 
      id: sender@yieldfabric.com
      password: senderpass123
    parameters:
      token_id: token-USD
      amount: 75
      destination_id: alice@yieldfabric.com
      idempotency_key: alice-75

  # Send to second recipient
  - name: send_to_bob
    type: instant
    user: 
      id: sender@yieldfabric.com
      password: senderpass123
    parameters:
      token_id: token-USD
      amount: 50
      destination_id: bob@yieldfabric.com
      idempotency_key: bob-50

  # Alice accepts
  - name: alice_accept
    type: accept
    user: 
      id: alice@yieldfabric.com
      password: alicepass456
    parameters:
      id_hash: $send_to_alice.id_hash
      idempotency_key: alice-accept

  # Bob accepts
  - name: bob_accept
    type: accept
    user: 
      id: bob@yieldfabric.com
      password: bobpass789
    parameters:
      id_hash: $send_to_bob.id_hash
      idempotency_key: bob-accept
```

## 🔧 **Troubleshooting**

### **Common Issues and Solutions**

#### **Service Not Running**
```bash
# Check service status
./execute_commands.sh status

# Start missing services
cd yieldfabric-auth && cargo run      # Port 3000
cd yieldfabric-payments && cargo run  # Port 3002
```

#### **Authentication Failed**
```bash
# Verify user credentials in commands.yaml
# Check if user exists in auth service
# Ensure services are included in login request
```

#### **Command Validation Failed**
```bash
# Validate commands.yaml structure
./execute_commands.sh validate

# Common issues:
# - Missing required parameters
# - Invalid command type
# - Missing user credentials
```

#### **Variable Substitution Issues**
```bash
# Check available variables
./execute_commands.sh variables

# Ensure previous commands completed successfully
# Verify field names match command outputs
```

### **Debug Mode**
```bash
# Enable verbose logging
export DEBUG=1
./execute_commands.sh execute

# Shows:
# - Variable substitution details
# - API request/response details
# - Command execution flow
```

## 📁 **File Structure**

```
yieldfabric-docs/
├── PAYMENTS.md                    # This payment operations manual
├── README.md                      # Main system operations manual
├── BANKING.md                     # Banking system documentation
└── scripts/
    ├── execute_commands.sh        # Payment command executor
    ├── commands.yaml              # Payment flow configuration
    └── yieldfabric-auth.sh        # Authentication manager
```

## 💡 **Best Practices**

### **Security**
- Use strong, unique passwords for each user
- Rotate idempotency keys regularly
- Monitor payment flows for anomalies
- Validate all input parameters

### **Performance**
- Use idempotency keys to prevent duplicate operations
- Chain commands efficiently with variable substitution
- Monitor service response times
- Implement proper error handling

### **Maintenance**
- Regularly validate commands.yaml structure
- Monitor service logs for errors
- Test payment flows in development first
- Keep user credentials secure and updated

## 🎯 **Production Deployment**

### **Environment Configuration**
```bash
# Set production environment
export YIELDFABRIC_ENV=production

# Configure production endpoints
export AUTH_SERVICE_URL=https://auth.yieldfabric.com
export PAYMENTS_SERVICE_URL=https://payments.yieldfabric.com
export VAULT_SERVICE_URL=https://vault.yieldfabric.com
```

### **Monitoring**
- Set up alerts for failed payment operations
- Monitor authentication success rates
- Track payment flow completion times
- Log all payment operations for audit

### **Backup and Recovery**
- Regularly backup commands.yaml configurations
- Document payment flow dependencies
- Test recovery procedures
- Maintain user credential backups

## 📚 **Additional Resources**

- **Main System**: See [README.md](./README.md) for comprehensive system operations
- **Banking System**: See [BANKING.md](./BANKING.md) for banking integration details
- **API Documentation**: Available at `/docs` endpoint when services are running
- **Source Code**: Available in the respective service repositories

---

**Ready to start making payments?** Run `./execute_commands.sh execute` to begin your payment flow!
