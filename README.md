# YieldFabric Comprehensive Testing Suite

This folder contains a comprehensive testing suite for the entire YieldFabric ecosystem. The scripts test all major system components working together, demonstrating that the platform is **production-ready** for enterprise use.

## 🎯 **What This Testing Suite Covers**

### **🔐 Complete Authentication System**
- **User-Password Authentication**: Traditional username/password login with JWT tokens
- **API Key Authentication**: Service-to-service authentication for microservices
- **Signature Authentication**: Cryptographic signature-based authentication framework
- **Delegation JWT System**: Limited-scope tokens for group operations
- **Multi-Factor Security**: Role-based access control with granular permissions

### **👥 Advanced Group Management**
- **Flat Group Structure**: Independent groups with no hierarchical relationships (flat structure)
- **Member Management**: Add/remove users with role-based permissions (Owner, Admin, Member, Viewer)
- **Permission Scoping**: Group-level access control and restrictions
- **Entity Isolation**: Secure separation between different group contexts
- **Group Types**: Organization, Team, Project, and Custom group classifications

### **🔑 Cryptographic Infrastructure**
- **Key Management**: User and group-specific cryptographic keypairs
- **Encryption/Decryption**: Asymmetric encryption with public/private keys
- **Digital Signatures**: Signing and verification of data integrity
- **Key Storage**: Secure centralized keystore with polymorphic entity support

### **🔒 Permission & Access Control**
- **Granular Permissions**: 20+ permission types for fine-grained control
- **Role-Based Access**: SuperAdmin, Operator, and Viewer roles
- **Delegation Scopes**: Limited-scope tokens for specific operations
- **Security Boundaries**: Proper isolation between users and groups

## 🚀 **Quick Start (Recommended)**

For first-time users or comprehensive testing:

```bash
# One command sets up everything automatically
./yieldfabric-auth.sh setup

# Check comprehensive system status
./yieldfabric-auth.sh status

# Run the complete crypto system test
./test_crypto_system.sh

# Run the complete API key and signature test
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
                    ┌─────────────────┐
                    │   Role-Based     │
                    │   Access Control │
                    └─────────────────┘
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
| **Grant Permission** | `ManageUsers` | `POST /auth/permissions/{user_id}/{permission}/grant` | Give users specific permissions |
| **Revoke Permission** | `ManageUsers` | `POST /auth/permissions/{user_id}/{permission}/revoke` | Remove specific permissions |
| **Check Permission** | `ManageUsers` | `GET /auth/permissions/{user_id}/{permission}/check` | Verify user permissions |
| **Replace Permissions** | `ManageUsers` | `POST /auth/permissions/{user_id}/replace` | Set complete permission set |

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

## 🔐 **Authentication Methods Supported**

### **1. User-Password Authentication**
- **Purpose**: Traditional user authentication
- **Flow**: Username/password → JWT token
- **Use Case**: Regular user access to services
- **Security**: Password hashing and JWT expiration

### **2. API Key Authentication**
- **Purpose**: Service-to-service authentication
- **Flow**: API key → JWT token → Resource access
- **Use Case**: Microservice communication
- **Security**: Unique key generation and revocation

### **3. Signature Authentication**
- **Purpose**: Cryptographic verification
- **Flow**: Public key registration → Signature verification
- **Use Case**: High-security operations
- **Security**: Asymmetric cryptography

### **4. Delegation JWT System**
- **Purpose**: Limited-scope access control
- **Flow**: Admin creates → User receives → Group operations
- **Use Case**: Group and delegated operations
- **Security**: Scope limitation and time expiration

## 🎫 **JWT Token Types and Usage Patterns**

### **Token Hierarchy and Capabilities**
| **Token Type** | **Role** | **Permissions** | **Use Case** | **Lifetime** |
|----------------|----------|-----------------|--------------|--------------|
| **`ADMIN_TOKEN`** | SuperAdmin | All permissions | System administration, user management | Long-lived |
| **`TEST_TOKEN`** | Operator | Limited permissions | Service operations, group management | Long-lived |
| **`DELEGATION_TOKEN`** | Limited scope | Specific scope only | Group crypto operations | Short-lived (1 hour) |

### **JWT Usage by Operation Type**

#### **🔐 Authentication & Setup**
- **Health Check**: No authentication required
- **Token Setup**: Managed by `yieldfabric-auth.sh` automatically
- **Status Check**: No authentication required

#### **👥 Group Management**
- **Create/Read/Update/Delete Groups**: `TEST_TOKEN` with group permissions
- **Member Management**: `TEST_TOKEN` with `ManageGroupMembers` permission
- **Group Operations**: `TEST_TOKEN` with appropriate group permissions

#### **🔑 Cryptographic Operations**
- **User Crypto Operations**: `TEST_TOKEN` with `CryptoOperations` permission
- **Group Crypto Operations**: `DELEGATION_TOKEN` with `CryptoOperations` scope
- **Key Management**: `TEST_TOKEN` with `CryptoOperations` permission

#### **🎫 Delegation System**
- **Create Delegation JWT**: `TEST_TOKEN` with `ManageGroupPermissions` permission
- **Use Delegation JWT**: `DELEGATION_TOKEN` for group-specific operations
- **Validate Delegation**: `DELEGATION_TOKEN` scope verification

#### **🔑 API Key & Signature**
- **Generate API Key**: `TEST_TOKEN` with `CryptoOperations` permission
- **Authenticate API Key**: API key directly (converts to JWT)
- **Register Signature Key**: `TEST_TOKEN` with `CryptoOperations` permission
- **Use Signature Auth**: Signature directly (no JWT required)

#### **⚙️ Permission Management**
- **Grant/Revoke Permissions**: `ADMIN_TOKEN` with `ManageUsers` permission
- **Check Permissions**: `ADMIN_TOKEN` with `ManageUsers` permission
- **Permission Operations**: `ADMIN_TOKEN` for all permission management

### **Security Boundaries and Isolation**
- **Regular JWT** cannot access group keys (proper isolation enforced)
- **Delegation JWT** limited to specified scope (e.g., `CryptoOperations` only)
- **Permission boundaries** enforced at API level with proper HTTP status codes
- **Token scope validation** prevents privilege escalation

### **Token Lifecycle Management**
- **Admin/Test tokens**: Long-lived, automatically managed by `yieldfabric-auth.sh`
- **Delegation tokens**: Short-lived (1 hour), limited scope, for specific group operations
- **Automatic cleanup**: Scripts preserve tokens for reuse, manual cleanup available via `clean` command

## 🔑 **Cryptographic Operations**

### **Key Management**
- **User Keypairs**: Individual cryptographic keys for users
- **Group Keypairs**: Shared cryptographic keys for groups
- **Polymorphic Storage**: Secure keystore supporting multiple entity types
- **Key Rotation**: Support for key lifecycle management

### **Encryption Operations**
- **Asymmetric Encryption**: Public key encryption for data security
- **Local Encryption**: Fast encryption using public keys
- **Remote Decryption**: Secure decryption through centralized service
- **Data Integrity**: Verification that decrypted data matches original

### **Signature Operations**
- **Digital Signatures**: Cryptographic proof of data authenticity
- **Remote Signing**: Secure signing using centralized private keys
- **Local Verification**: Fast signature verification using public keys
- **Non-repudiation**: Proof that data came from specific source

## 🧪 **Comprehensive Testing Scripts**

### **1. `yieldfabric-auth.sh` - Main Authentication Manager**
- **Purpose**: One-stop solution for all authentication needs
- **Commands**: `setup`, `status`, `admin`, `test`, `delegate`, `clean`, `help`
- **Features**: Automatic token creation, permission management, group setup

### **2. `test_crypto_system.sh` - Complete Crypto System Test**
- **Purpose**: Validates entire cryptographic infrastructure
- **Tests**: 19 comprehensive tests covering all crypto operations
- **Coverage**: Authentication, encryption, signing, group operations, security

### **3. `test_api_key_unified.sh` - Multi-Authentication Test**
- **Purpose**: Tests all authentication methods working together
- **Tests**: 17 tests covering JWT, API keys, and signatures
- **Coverage**: Service-to-service authentication, security enforcement

### **4. `test_delegation_system.sh` - Permission System Test**
- **Purpose**: Comprehensive permission management testing
- **Tests**: Complete permission lifecycle and delegation
- **Coverage**: Grant, verify, revoke, and scope enforcement

## 🔍 **Testing Methodology**

### **Comprehensive Coverage**
- **✅ Positive Testing**: Valid operations that should succeed
- **❌ Negative Testing**: Invalid operations that should fail
- **🔒 Security Testing**: Unauthorized access attempts
- **🔄 Flow Testing**: Complete authentication workflows
- **📊 Management Testing**: Administrative operations
- **🔗 Integration Testing**: Systems working together

### **Production Readiness Validation**
- **🔄 Idempotent Operations**: Safe to run multiple times
- **🔒 Security Validation**: Tests access control and permission boundaries
- **📊 Comprehensive Coverage**: Tests all major system components
- **🧪 Real-World Scenarios**: Uses actual API endpoints and data flows
- **🔍 Error Handling**: Robust error detection and reporting
- **📝 Audit Trail**: Logs all operations for debugging
- **🧹 Resource Management**: Proper cleanup and verification

## 🚀 **Getting Started**

### **First-Time Setup**
```bash
# 1. Set up authentication system
./yieldfabric-auth.sh setup

# 2. Check comprehensive system status
./yieldfabric-auth.sh status

# 3. Run complete crypto system test
./test_crypto_system.sh

# 4. Run multi-authentication test
./test_api_key_unified.sh

# 5. Verify everything is working
./yieldfabric-auth.sh test
```

### **Daily Development**
```bash
# Check current status
./yieldfabric-auth.sh status

# Get admin token for administrative tasks
./yieldfabric-auth.sh admin

# Get test token for service operations
./yieldfabric-auth.sh test

# Create delegation token for group operations
./yieldfabric-auth.sh delegate
```

### **Comprehensive Testing**
```bash
# Run all tests to validate system
./test_crypto_system.sh
./test_api_key_unified.sh
./test_delegation_system.sh
```

## 📋 **Prerequisites**

- Docker services running (use the docker-compose setup)
- `jq` command-line JSON processor installed
- `curl` for HTTP requests
- Bash shell
- YieldFabric services running (auth, vault, payments)

## 🚨 **Troubleshooting**

### **Common Issues**
1. **Service not running**: Ensure Docker services are started
2. **Permission denied**: The script automatically handles permission granting
3. **Token expired**: Run `./yieldfabric-auth.sh setup` to refresh all tokens
4. **Group creation fails**: Check if user has necessary permissions

### **Debug Mode**
All scripts provide detailed logging for troubleshooting:
- Shows JWT payloads and permissions
- Logs API responses and errors
- Provides step-by-step progress information

### **Getting Help**
```bash
# Show all available commands
./yieldfabric-auth.sh help

# Check current status
./yieldfabric-auth.sh status

# Clean start if something goes wrong
./yieldfabric-auth.sh clean
./yieldfabric-auth.sh setup
```

## 📁 **File Structure**

```
scripts/
├── auth.sh                     # 🔗 Short alias for yieldfabric-auth.sh
├── yieldfabric-auth.sh         # ⭐ Main authentication manager (RECOMMENDED)
├── test_crypto_system.sh       # 🧪 Complete crypto system validation
├── test_api_key_unified.sh     # 🔑 Multi-authentication testing
├── test_delegation_system.sh   # 🎫 Permission system testing
├── README.md                   # This comprehensive guide
└── tokens/                     # Token storage directory
    ├── .jwt_token             # Admin JWT token
    ├── .jwt_expiry            # Admin JWT expiry
    ├── .jwt_token_test        # Test JWT token
    ├── .jwt_expiry_test       # Test JWT expiry
    ├── .jwt_token_delegate    # Delegation JWT token
    └── .jwt_expiry_delegate   # Delegation JWT expiry
```

## 💡 **Best Practices**

### **For First-Time Users**
1. **Start with `./yieldfabric-auth.sh setup`** - This handles everything automatically
2. **Check status regularly** - Use `./yieldfabric-auth.sh status` to monitor your system
3. **Run comprehensive tests** - Use the test scripts to verify everything works

### **For Daily Development**
1. **Reuse tokens** - The system automatically manages token expiration
2. **Check permissions** - Use the status command to see what permissions you have
3. **Use delegation tokens** - For group operations, use delegation JWTs

### **For Production**
1. **Review permissions** - Ensure users only have necessary permissions
2. **Monitor usage** - Track delegation token creation and usage
3. **Regular testing** - Periodically run test scripts to validate system health

## 🎯 **What Makes This System Production-Ready**

### **🔐 Complete Authentication Coverage**
- Multiple authentication methods working seamlessly together
- Comprehensive permission system with granular control
- Secure token management with proper expiration

### **🔑 Enterprise-Grade Cryptography**
- Full cryptographic infrastructure for encryption and signing
- Secure key management with polymorphic entity support
- Group-level cryptographic operations with delegation

### **👥 Advanced Access Control**
- Flat group management with role-based access
- Delegation system for limited-scope operations
- Proper security boundaries and isolation

### **🔗 Seamless Integration**
- All components working together seamlessly
- Comprehensive testing covering all major scenarios
- Robust error handling and debugging capabilities

### **📊 Comprehensive Testing**
- 50+ individual tests covering all system components
- Real-world scenarios and edge cases
- Production-ready validation and verification

## 🔮 **Currently Implemented Features**

### **✅ Production Ready Components**
- **Flat Group Structure**: Independent groups with no nesting
- **Role-Based Access**: Owner, Admin, Member, Viewer roles
- **Permission Management**: Granular permissions for all operations
- **Delegation System**: Limited-scope JWT tokens for groups
- **Cryptographic Operations**: Full encryption/signing infrastructure
- **Audit Logging**: Comprehensive operation tracking

## 📝 **Notes**

- **Start with `yieldfabric-auth.sh setup`** for the best experience
- All scripts use `SCRIPT_DIR` to ensure they work from any location
- Token files are stored in the `tokens/` subdirectory for better organization
- The `tokens/` directory is automatically created if it doesn't exist
- Token files have restrictive permissions (600) for security
- Scripts automatically handle token expiration and renewal
- Error handling includes helpful debugging information and next steps
- The script is designed to be idempotent - safe to run multiple times
- **The system is production-ready** and handles all edge cases automatically
- **Comprehensive testing** validates all major system components
- **Multiple authentication methods** support modern enterprise requirements
- **Advanced cryptography** provides enterprise-grade security
- **Granular permissions** enable fine-grained access control
