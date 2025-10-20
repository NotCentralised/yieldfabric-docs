# YieldFabric System Operations Manual

This manual provides practical instructions for using the YieldFabric ecosystem. Learn how to authenticate, manage users and groups, perform cryptographic operations, and integrate with payment systems.

## 📖 **About YieldFabric**

YieldFabric is a comprehensive enterprise platform that provides secure authentication, advanced cryptography, and integrated payment processing capabilities. The system is designed for production use with enterprise-grade security, role-based access control, and seamless service integration.

### **Core Services**
- **🔐 Authentication & Authorization**: Multi-method authentication with JWT tokens, API keys, and cryptographic signatures
- **🔑 Cryptographic Infrastructure**: Full encryption, decryption, and digital signature capabilities with secure key management
- **👥 Group Management**: Advanced permission systems with delegation and role-based access control
- **💰 Payment Processing**: Integrated payment operations with command chaining and variable substitution
- **🏦 Banking Integration**: Hutly Monoova payment system integration for enterprise banking operations

### **Specialized Documentation**
- **[PAYMENTS.md](./PAYMENTS.md)**: Complete payment system operations with command execution and flow management
- **[BANKING.md](./BANKING.md)**: Banking system integration and Hutly Monoova API documentation

## 🚀 **Quick Start Guide**

### **1. Initial System Setup**
```bash
# Set up the complete authentication system
./yieldfabric-auth.sh setup

# Verify everything is working
./yieldfabric-auth.sh status
```

### **2. Get Your Access Tokens**
```bash
# Get admin token for system administration
./yieldfabric-auth.sh admin

# Get test token for regular operations
./yieldfabric-auth.sh test

# Create delegation token for group operations
./yieldfabric-auth.sh delegate
```

### **3. Run Your First Operations**
```bash
# Test the complete system
./test_crypto_system.sh

# Test authentication methods
./test_api_key_unified.sh
```

## 🏗️ **System Architecture Overview**

### **Authentication Layer**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User/Password │    │    API Keys     │    │   Signatures    │
│   Authentication│    │  Authentication │    │ Authentication  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   JWT Token     │
                    │   Generation    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Permission     │
                    │  Validation     │
                    └─────────────────┘
```

### **Group & Permission Layer**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User          │    │   Group         │    │   Permission    │
│   Management    │    │   Management    │    │   Management    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌──────────────────┐
                    │   Role-Based     │
                    │   Access Control │
                    └──────────────────┘
```

### **Cryptographic Layer**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Keypair       │    │   Encryption    │    │   Signatures    │
│   Management    │    │   Operations    │    │   Operations    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Secure        │
                    │   Keystore      │
                    └─────────────────┘
```

## 🔑 **Required Permissions for Operations**

### **User Management Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Create User** | `CreateUser` | `POST /auth/users` | Register new users in the system |
| **Read User** | `ReadUser` | `GET /auth/users/{id}` | View user information and profiles |
| **Update User** | `UpdateUser` | `PUT /auth/users/{id}` | Modify user details and settings |
| **Delete User** | `DeleteUser` | `DELETE /auth/users/{id}` | Remove users from the system |
| **Manage Users** | `UsersManage` | Various endpoints | Full user lifecycle management |

### **Group Management Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Create Group** | `CreateGroup` | `POST /auth/groups` | Set up new groups for organizing users |
| **Read Group** | `ReadGroup` | `GET /auth/groups/{id}` | View group information and settings |
| **Update Group** | `UpdateGroup` | `PUT /auth/groups/{id}` | Modify group name, description, etc. |
| **Delete Group** | `DeleteGroup` | `DELETE /auth/groups/{id}` | Remove groups and all associated data |
| **Manage Groups** | `ManageGroups` | Various endpoints | Full group lifecycle management |

### **Group Member Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Add Member** | `AddGroupMember` | `POST /auth/groups/{id}/members` | Include users in groups with roles |
| **Remove Member** | `RemoveGroupMember` | `DELETE /auth/groups/{id}/members/{user_id}` | Remove users from groups |
| **Manage Members** | `ManageGroupMembers` | Various endpoints | Full member lifecycle management |

### **Permission Management Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Grant Permission** | `ManageUsers` | `POST /auth/users/{user_id}/permissions/{permission}` | Give users specific permissions |
| **Revoke Permission** | `ManageUsers` | `DELETE /auth/users/{user_id}/permissions/{permission}` | Remove specific permissions |
| **Check Permission** | `ManageUsers` | `GET /auth/users/{user_id}/permissions/{permission}` | Verify user permissions |
| **Grant Multiple Permissions** | `ManageUsers` | `POST /auth/users/{user_id}/permissions` | Grant multiple permissions at once |
| **Revoke Multiple Permissions** | `ManageUsers` | `DELETE /auth/users/{user_id}/permissions` | Revoke multiple permissions at once |
| **Replace Permissions** | `ManageUsers` | `PUT /auth/users/{user_id}/permissions` | Set complete permission set |
| **Get User Permissions** | `ManageUsers` | `GET /auth/users/{user_id}/permissions` | Retrieve all user permissions |

### **Cryptographic Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Encrypt Data** | `CryptoOperations` | `POST /api/v1/crypto/encrypt` | Encrypt data using public keys |
| **Decrypt Data** | `CryptoOperations` | `POST /api/v1/crypto/decrypt` | Decrypt data using private keys |
| **Sign Data** | `CryptoOperations` | `POST /api/v1/crypto/sign` | Create digital signatures |
| **Verify Signatures** | `CryptoOperations` | `POST /api/v1/crypto/verify` | Verify digital signatures |
| **Manage Keypairs** | `CryptoOperations` | Various endpoints | Create and manage cryptographic keys |

### **Delegation Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **Create Delegation JWT** | `CreateDelegationToken` | `POST /auth/delegation/jwt` | Generate limited-scope tokens |
| **View Delegation Tokens** | `ViewDelegationTokens` | `GET /auth/delegation/jwt` | List active delegation tokens |
| **Revoke Delegation Token** | `RevokeDelegationToken` | `DELETE /auth/delegation/jwt/{id}` | Invalidate delegation tokens |

### **System Administration Operations**
| **Operation** | **Required Permission** | **API Endpoint** | **Description** |
|---------------|------------------------|------------------|-----------------|
| **System Configuration** | `SystemConfig` | Various endpoints | Modify system-wide settings |
| **View Logs** | `ViewLogs` | Various endpoints | Access system logs and audit trails |
| **Manage Roles** | `ManageRoles` | Various endpoints | Create and modify user roles |
| **API Access** | `ApiRead`, `ApiWrite`, `ApiAdmin` | Various endpoints | Control API access levels |

## 🎭 **User Roles and Capabilities**

### **SuperAdmin Role**
- **Access Level**: Full system access
- **Permissions**: All permissions automatically granted
- **Use Case**: System administration and management
- **Operations**: Can perform any operation in the system

### **Operator Role**
- **Access Level**: Service access + limited administration
- **Permissions**: Service operations + group management
- **Use Case**: Service operation and group administration
- **Operations**: Use services, manage groups, create delegation tokens

### **Viewer Role**
- **Access Level**: Read-only access
- **Permissions**: Read operations only
- **Use Case**: Information viewing and monitoring
- **Operations**: View information but cannot modify anything

## 👥 **Group Member Roles**

### **Owner Role**
- **Permissions**: Full control over the group
- **Capabilities**: Everything in the group, including deletion
- **Use Case**: Group leadership and ultimate control

### **Admin Role**
- **Permissions**: Member management and group operations
- **Capabilities**: Add/remove members, manage permissions
- **Use Case**: Group administration and day-to-day management

### **Member Role**
- **Permissions**: Group operations and participation
- **Capabilities**: Perform group-specific tasks and operations
- **Use Case**: Active group participation

### **Viewer Role**
- **Permissions**: Read-only access to group information
- **Capabilities**: View group information and members
- **Use Case**: Group monitoring and information access

## 🔐 **Authentication Methods**

### **1. User-Password Authentication**
- **Purpose**: Traditional user authentication
- **Flow**: Username/password → JWT token
- **Use Case**: Regular user access to services
- **Security**: Password hashing and JWT expiration

```bash
# Login with username/password
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Response includes JWT token
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### **2. API Key Authentication**
- **Purpose**: Service-to-service authentication
- **Flow**: API key → JWT token → Resource access
- **Use Case**: Microservice communication
- **Security**: Unique key generation and revocation

```bash
# Generate API key for a service
curl -X POST http://localhost:8080/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "payment-service", "permissions": ["CryptoOperations"]}'

# Use API key for authentication
curl -X POST http://localhost:8080/api/v1/crypto/encrypt \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": "sensitive information", "public_key": "..."}'
```

### **3. Signature Authentication**
- **Purpose**: Cryptographic verification
- **Flow**: Public key registration → Signature verification
- **Use Case**: High-security operations
- **Security**: Asymmetric cryptography

```bash
# Register your public key
curl -X POST http://localhost:8080/auth/signature-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"public_key": "04a1b2c3d4e5f6...", "user_id": "user123"}'

# Authenticate using signature
curl -X POST http://localhost:8080/api/v1/crypto/sign \
  -H "X-Signature: $SIGNATURE" \
  -H "X-Public-Key: $PUBLIC_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": "data to sign"}'
```

### **4. Delegation JWT System**
- **Purpose**: Limited-scope access control
- **Flow**: Admin creates → User receives → Group operations
- **Use Case**: Group and delegated operations
- **Security**: Scope limitation and time expiration
- **🔧 Enhanced**: Robust JWT parsing with base64 padding handling for reliable token extraction

## 👥 **User and Group Management**

### **Creating Users**
```bash
# Create a new user
curl -X POST http://localhost:8080/auth/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@company.com",
    "password": "securepassword123",
    "role": "Operator"
  }'

# Response
{
  "user_id": "user_abc123",
  "username": "john.doe",
  "email": "john@company.com",
  "role": "Operator",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### **Managing Groups**
```bash
# Create a new group
curl -X POST http://localhost:8080/auth/groups \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering Team",
    "description": "Software development team",
    "group_type": "Team"
  }'

# Add member to group
curl -X POST http://localhost:8080/auth/groups/group_xyz789/members \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "role": "Member"
  }'
```

### **Group Member Roles**
- **Owner**: Full control, can delete the group
- **Admin**: Manage members and group operations
- **Member**: Participate in group activities
- **Viewer**: Read-only access to group information

## 🔑 **Cryptographic Operations**

### **Key Management**
```bash
# Generate user keypair
curl -X POST http://localhost:8080/api/v1/crypto/keypairs \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_type": "user", "entity_id": "user_abc123"}'

# Generate group keypair
curl -X POST http://localhost:8080/api/v1/crypto/keypairs \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_type": "group", "entity_id": "group_xyz789"}'
```

### **Encryption and Decryption**
```bash
# Encrypt data using public key
curl -X POST http://localhost:8080/api/v1/crypto/encrypt \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Confidential business data",
    "public_key": "04a1b2c3d4e5f6..."
  }'

# Decrypt data using private key (handled by service)
curl -X POST http://localhost:8080/api/v1/crypto/decrypt \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "encrypted_data": "encrypted_base64_string",
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'
```

### **Digital Signatures**
```bash
# Sign data
curl -X POST http://localhost:8080/api/v1/crypto/sign \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Contract terms to sign",
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'

# Verify signature
curl -X POST http://localhost:8080/api/v1/crypto/verify \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Contract terms to sign",
    "signature": "signature_base64_string",
    "public_key": "04a1b2c3d4e5f6..."
  }'
```

## 🎫 **Delegation System**

### **Creating Delegation Tokens**
```bash
# Create limited-scope token for group operations
curl -X POST http://localhost:8080/auth/delegation/jwt \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "scope": ["CryptoOperations"],
    "group_id": "group_xyz789",
    "expires_in": 3600
  }'

# Response
{
  "delegation_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-01-15T11:30:00Z",
  "scope": ["CryptoOperations"],
  "group_id": "group_xyz789"
}
```

### **Using Delegation Tokens**
```bash
# Use delegation token for group crypto operations
curl -X POST http://localhost:8080/api/v1/crypto/encrypt \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Group-shared data",
    "public_key": "group_public_key_here"
  }'
```

## 🔐 **Permission Management**

### **Granting Permissions**
```bash
# Grant single permission
curl -X POST http://localhost:8080/auth/users/user_abc123/permissions/CryptoOperations \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Grant multiple permissions
curl -X POST http://localhost:8080/auth/users/user_abc123/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "permissions": ["CryptoOperations", "CreateGroup", "ManageGroupMembers"]
  }'
```

### **Checking Permissions**
```bash
# Check if user has specific permission
curl -X GET http://localhost:8080/auth/users/user_abc123/permissions/CryptoOperations \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get all user permissions
curl -X GET http://localhost:8080/auth/users/user_abc123/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### **Revoking Permissions**
```bash
# Revoke single permission
curl -X DELETE http://localhost:8080/auth/users/user_abc123/permissions/CryptoOperations \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Revoke multiple permissions
curl -X DELETE http://localhost:8080/auth/users/user_abc123/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "permissions": ["CryptoOperations", "CreateGroup"]
  }'
```

## 💰 **Payment System Integration**

### **Monoova Payment Operations**
```bash
# Create payment agreement
curl -X POST http://localhost:8080/api/v1/payments/monoova/agreements \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.00,
    "currency": "AUD",
    "description": "Service payment",
    "recipient": "recipient@company.com"
  }'

# Get payment agreement details
curl -X GET http://localhost:8080/api/v1/payments/monoova/agreements/agreement_123 \
  -H "Authorization: Bearer $TEST_TOKEN"

# Instruct payment
curl -X POST http://localhost:8080/api/v1/payments/monoova/agreements/agreement_123/instruct \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_date": "2024-01-20",
    "reference": "INV-2024-001"
  }'
```

## 🛠️ **Daily Operations**

### **Check System Status**
```bash
# View current system status
./yieldfabric-auth.sh status

# Check token validity
./yieldfabric-auth.sh test
```

### **Token Management**
```bash
# Get fresh admin token
./yieldfabric-auth.sh admin

# Get fresh test token
./yieldfabric-auth.sh test

# Create new delegation token
./yieldfabric-auth.sh delegate
```

### **Cleanup Operations**
```bash
# Clean up expired tokens
./yieldfabric-auth.sh clean

# Reset system (use with caution)
./yieldfabric-auth.sh clean
./yieldfabric-auth.sh setup
```

## 📋 **Required Permissions Reference**

### **User Management**
| Operation | Permission | Endpoint |
|-----------|------------|----------|
| Create User | `CreateUser` | `POST /auth/users` |
| Read User | `ReadUser` | `GET /auth/users/{id}` |
| Update User | `UpdateUser` | `PUT /auth/users/{id}` |
| Delete User | `DeleteUser` | `DELETE /auth/users/{id}` |

### **Group Management**
| Operation | Permission | Endpoint |
|-----------|------------|----------|
| Create Group | `CreateGroup` | `POST /auth/groups` |
| Read Group | `ReadGroup` | `GET /auth/groups/{id}` |
| Update Group | `UpdateGroup` | `PUT /auth/groups/{id}` |
| Delete Group | `DeleteGroup` | `DELETE /auth/groups/{id}` |

### **Cryptographic Operations**
| Operation | Permission | Endpoint |
|-----------|------------|----------|
| Encrypt/Decrypt | `CryptoOperations` | `POST /api/v1/crypto/encrypt` |
| Sign/Verify | `CryptoOperations` | `POST /api/v1/crypto/sign` |
| Key Management | `CryptoOperations` | `POST /api/v1/crypto/keypairs` |

## 🔧 **Troubleshooting**

### **Common Issues and Solutions**

#### **Token Expired**
```bash
# Refresh all tokens
./yieldfabric-auth.sh setup

# Or refresh specific token
./yieldfabric-auth.sh admin
```

#### **Permission Denied**
```bash
# Check current permissions
./yieldfabric-auth.sh status

# Grant necessary permissions (requires admin)
curl -X POST http://localhost:8080/auth/users/your_user_id/permissions/RequiredPermission \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### **Service Not Responding**
```bash
# Check if Docker services are running
docker ps

# Restart services if needed
docker-compose restart
```

### **Debug Mode**
All scripts provide detailed logging:
```bash
# Enable verbose logging
export DEBUG=1
./yieldfabric-auth.sh status
```

## 📁 **File Structure**

```
scripts/
├── yieldfabric-auth.sh         # Main authentication manager
├── test_crypto_system.sh       # System validation tests
├── test_api_key_unified.sh     # Authentication method tests
├── test_delegation_system.sh   # Permission system tests
└── tokens/                     # Token storage
    ├── .jwt_token             # Admin JWT token
    ├── .jwt_token_test        # Test JWT token
    └── .jwt_token_delegate    # Delegation JWT token
```

## 💡 **Best Practices**

### **Security**
- Use delegation tokens for group operations
- Regularly rotate API keys
- Grant minimal required permissions
- Monitor token expiration

### **Performance**
- Reuse tokens when possible
- Use appropriate authentication method for each operation
- Cache frequently accessed data

### **Maintenance**
- Run status checks regularly
- Monitor system logs
- Test critical operations periodically
- Keep tokens organized and secure

## 🎯 **Production Deployment**

### **Environment Setup**
```bash
# Set production environment
export YIELDFABRIC_ENV=production

# Configure production endpoints
export AUTH_SERVICE_URL=https://auth.yieldfabric.com
export VAULT_SERVICE_URL=https://vault.yieldfabric.com
export PAYMENTS_SERVICE_URL=https://payments.yieldfabric.com
```

### **Monitoring**
- Set up alerts for token expiration
- Monitor API usage and rate limits
- Track permission changes and delegation token creation
- Log all cryptographic operations for audit

### **Backup and Recovery**
- Regularly backup user and group data
- Document permission configurations
- Test recovery procedures
- Maintain secure key backup procedures

## 📚 **Additional Resources**

- **Banking System**: See [BANKING.md](./BANKING.md) for comprehensive payment system documentation
- **API Documentation**: Available at `/docs` endpoint when services are running
- **Source Code**: Available in the respective service repositories
- **Support**: Check service logs and use debug mode for troubleshooting

---

**Ready to get started?** Run `./yieldfabric-auth.sh setup` to begin using the YieldFabric system!