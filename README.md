# YieldFabric Authentication Scripts

This folder contains authentication management scripts for testing YieldFabric services. All scripts are designed to run from the `scripts/` folder and use separate token files to avoid conflicts.

## 🚀 **Quick Start (Recommended)**

For first-time users or anyone who wants a simple experience:

```bash
# One command sets up everything automatically
./yieldfabric-auth.sh setup
# OR use the shorter alias:
./auth.sh setup

# Check status anytime
./yieldfabric-auth.sh status
# OR use the shorter alias:
./auth.sh status
```

This automatically:
- Checks if services are running
- Creates all necessary tokens (admin, test, and delegation)
- Handles permission granting automatically
- Creates groups and adds users as members
- Provides clear guidance if something is missing
- Shows comprehensive status

## 📋 **What You Can Do (Use Cases)**

### **🔐 Authentication Management**
- **Get admin access**: Full system privileges for administrative tasks
- **Get test access**: Service-enabled tokens for testing vault and payments
- **Create delegation tokens**: Limited-scope tokens for specific group operations

### **👥 Group Management**
- **Create groups**: Set up new groups for organizing users and permissions
- **Manage members**: Add/remove users and assign roles within groups
- **Control access**: Set group-level permissions and restrictions

### **🎫 Delegation System**
- **Create delegation JWTs**: Generate time-limited tokens with specific scopes
- **Enforce permissions**: Ensure tokens only allow intended operations
- **Audit operations**: Track who did what and when

## 🛠️ **Scripts Overview**

### 1. `yieldfabric-auth.sh` - **Main Authentication Manager** ⭐
- **Purpose**: One-stop solution for all authentication needs
- **Best For**: First-time users, daily testing, quick setup
- **Commands**: `setup`, `status`, `admin`, `test`, `delegate`, `clean`, `help`
- **Use Case**: Primary authentication management for all users
- **Features**:
  - Automatic token creation and renewal
  - Permission management and granting
  - Group creation and user management
  - Delegation JWT creation
  - Comprehensive error handling and debugging

### 2. `auth.sh` - Short Alias
- **Purpose**: Convenient shortcut for `yieldfabric-auth.sh`
- **Use Case**: Quick access to authentication commands

## 📚 **Usage Guide**

### **Quick Start (Recommended)**
```bash
# First time setup - creates all tokens automatically
./yieldfabric-auth.sh setup

# Check current status
./yieldfabric-auth.sh status

# Get admin token for manual testing
./yieldfabric-auth.sh admin

# Get test token for service testing
./yieldfabric-auth.sh test

# Create delegation token manually
./yieldfabric-auth.sh delegate

# Clean up all tokens
./yieldfabric-auth.sh clean

# Show help
./yieldfabric-auth.sh help
```

### **What Each Command Does**

| Command | Purpose | What It Creates |
|---------|---------|-----------------|
| `setup` | One-time setup | All tokens (admin, test, delegation) |
| `status` | Check system health | Current status of all tokens and services |
| `admin` | Get admin access | SuperAdmin JWT token |
| `test` | Get test access | Service-enabled JWT token |
| `delegate` | Create delegation | Limited-scope JWT token |
| `clean` | Remove tokens | Cleans up all stored tokens |
| `help` | Show usage | Available commands and examples |

## 🔑 **Permissions Guide**

### **What Permissions Do You Need?**

The system automatically grants these permissions, but here's what they enable:

| What You Want to Do | Required Permission | API Endpoint | Description |
|---------------------|-------------------|--------------|-------------|
| **Create a new group** | `CreateGroup` | `POST /auth/groups` | Set up new groups for organizing users |
| **View group details** | `ReadGroup` | `GET /auth/groups/{id}` | See group information and settings |
| **Update group info** | `UpdateGroup` | `PUT /auth/groups/{id}` | Modify group name, description, etc. |
| **Delete a group** | `DeleteGroup` | `DELETE /auth/groups/{id}` | Remove groups and all associated data |
| **Add user to group** | `AddGroupMember` | `POST /auth/groups/{id}/members` | Include users in groups with roles |
| **Remove user from group** | `RemoveGroupMember` | `DELETE /auth/groups/{id}/members/{user_id}` | Remove users from groups |
| **Manage group permissions** | `ManageGroupPermissions` | Various endpoints | Control what group members can do |
| **Create delegation JWT** | `CreateDelegationToken` | `POST /auth/delegation/jwt` | Generate limited-scope tokens |

### **Permission Categories**

| Category | Permissions | What It Enables |
|----------|-------------|-----------------|
| **User Management** | `CreateUser`, `ReadUser`, `UpdateUser`, `DeleteUser`, `UsersManage` | Manage system users |
| **Entity Management** | `CreateEntity`, `ReadEntity`, `UpdateEntity`, `DeleteEntity` | Manage system entities |
| **Group Management** | `CreateGroup`, `ReadGroup`, `UpdateGroup`, `DeleteGroup` | Full group lifecycle |
| **Group Operations** | `ManageGroupMembers`, `ManageGroupPermissions`, `ManageGroupEntityScope` | Control group behavior |
| **Delegation** | `CreateDelegationToken`, `ViewDelegationTokens`, `RevokeDelegationToken` | Manage delegation system |
| **System Access** | `SystemConfig`, `ViewLogs`, `ManageRoles`, `ApiRead`, `ApiWrite`, `ApiAdmin` | System administration |
| **Crypto Operations** | `CryptoOperations` | Cryptographic operations |

### **User Roles and Capabilities**

| Role | Access Level | What They Can Do |
|------|-------------|------------------|
| **SuperAdmin** | Full system access | Everything - user creation, permission management, system config |
| **Operator** | Service access + limited admin | Use services, manage groups, create delegation tokens |
| **Viewer** | Read-only access | View information but cannot modify anything |

### **Group Member Roles**

| Role | Permissions | What They Can Do |
|------|-------------|------------------|
| **Owner** | Full control | Everything in the group, including deletion |
| **Admin** | Member management | Add/remove members, manage permissions |
| **Member** | Group operations | Perform group-specific tasks |
| **Viewer** | Read-only | View group information and members |

## 🏗️ **How It Works (Technical Details)**

### **Token Creation Flow**
1. **Admin Token**: Creates user with SuperAdmin role, then logs in
2. **Test Token**: Creates user with Operator role, then logs in with services
3. **Delegation Token**: 
   - Grants necessary permissions to test user
   - Creates or finds existing group
   - Adds user to group as member
   - Creates delegation JWT with CryptoOperations scope

### **Permission Management**
The script automatically grants these permissions to enable delegation:
- `CreateGroup`, `ManageGroup`, `AddGroupMember`, `RemoveGroupMember`
- `ManageGroupPermissions`, `CreateDelegationToken`

### **Group Management**
- Automatically creates groups if none exist
- Adds users as members with appropriate roles
- Handles both existing and new group scenarios

## 🔧 **API Examples**

### **1. Admin Token Creation**
```bash
# Step 1: Create user with SuperAdmin role
POST /auth/users
{
  "email": "test@yieldfabric.com",
  "password": "testpass123", 
  "role": "SuperAdmin"
}

# Step 2: Login with services
POST /auth/login/with-services
{
  "email": "test@yieldfabric.com",
  "password": "testpass123",
  "services": ["vault", "payments"]
}
```

### **2. Group Operations**
```bash
# Create a group
POST /auth/groups
{
  "name": "My Test Group",
  "description": "Group for testing",
  "group_type": "project"
}

# Add a member to a group
POST /auth/groups/{group_id}/members
{
  "user_id": "user-uuid-here",
  "role": "admin"
}

# List group members
GET /auth/groups/{group_id}/members
```

### **3. Delegation JWT Creation**
```bash
# Create delegation JWT with specific scope
POST /auth/delegation/jwt
{
  "group_id": "group-uuid-here",
  "delegation_scope": ["ReadGroup", "UpdateGroup"],
  "expiry_seconds": 3600
}
```

## 🧪 **Testing**

### **Quick Test (Recommended)**
```bash
# Test the main authentication manager
./yieldfabric-auth.sh status
```

### **Full Setup Test**
```bash
# Clean start
./yieldfabric-auth.sh clean

# Full setup
./yieldfabric-auth.sh setup

# Verify everything works
./yieldfabric-auth.sh status
```

### **Comprehensive Testing**
```bash
# Run the full delegation system test
./test_delegation_system.sh

# Run the comprehensive crypto system test
./test_crypto_system.sh
```

## 🔐 **Crypto System Testing (`test_crypto_system.sh`)**

The `test_crypto_system.sh` script is a comprehensive test that demonstrates the entire cryptographic system working together. It tests all major components and their integration.

### **What This Test Demonstrates**

This test proves that the YieldFabric crypto system is **production-ready** by testing:

1. **🔐 Authentication Management**: Automatic token creation and management
2. **🔑 Crypto Flow Operations**: Complete encryption/decryption/signing/verification cycles
3. **👥 Group Key Management**: Group-specific cryptographic operations
4. **🎫 Delegation System**: Limited-scope token operations for groups
5. **🔍 Security Enforcement**: Proper access control and permission boundaries
6. **🔗 System Integration**: All components working together seamlessly

### **Test Flow and What Happens**

#### **Phase 1: Setup and Authentication (Tests 1-4)**
```bash
# Test 1: Health Check
✅ Verifies auth service is running and responsive

# Test 2: Authentication Setup
✅ Runs yieldfabric-auth.sh setup to create all necessary tokens
✅ Creates admin, test, and delegation tokens automatically
✅ Handles permission granting and group setup

# Test 3: Token Status Verification
✅ Confirms all tokens are valid and not expired
✅ Shows current authentication status

# Test 4: Token Retrieval
✅ Extracts test token for user operations
✅ Extracts delegation token for group operations
```

#### **Phase 2: Group and Key Management (Tests 5-6)**
```bash
# Test 5: Group Creation
✅ Creates a test group for crypto operations
✅ Demonstrates group CRUD operations
✅ Shows proper permission enforcement

# Test 6: Group Keypair Creation
✅ Generates cryptographic keypair for the group
✅ Stores keys in polymorphic keypairs table
✅ Distinguishes between user and group entities
```

#### **Phase 3: Crypto Flow Operations (Tests 7-10)**
```bash
# Test 7: Local Encryption
✅ Creates user keypair for user operations
✅ Encrypts data using public key (fast, local operation)
✅ Demonstrates asymmetric encryption

# Test 8: Remote Decryption
✅ Decrypts data through auth service (secure, centralized)
✅ Verifies data integrity (decrypted matches original)
✅ Shows secure private key handling

# Test 9: Remote Signing
✅ Signs data using private key stored in auth service
✅ Demonstrates secure centralized signing
✅ Shows proper authentication and authorization

# Test 10: Local Signature Verification
✅ Verifies signatures using public key (fast, local operation)
✅ Demonstrates signature validation
✅ Shows complete sign/verify cycle
```

#### **Phase 4: Group Operations with Delegation (Tests 11-12)**
```bash
# Test 11: Group Key Operations
✅ Uses delegation JWT for group operations
✅ Signs data as the group (not as the user)
✅ Demonstrates proper delegation scope enforcement
✅ Shows group keypair usage with delegation

# Test 12: Security Restrictions
✅ Tests that regular JWT cannot access group keys
✅ Verifies access control is properly enforced
✅ Confirms security model is working
```

#### **Phase 5: Vault Integration (Test 13)**
```bash
# Test 13: Real Signature Authentication
✅ Tests vault endpoints (/api/v1/vault/sign, /api/v1/vault/decrypt)
✅ Demonstrates remote keystore integration
✅ Shows both user and group vault operations working
✅ Tests public key retrieval endpoints
✅ Verifies signature verification through crypto endpoints
```

#### **Phase 6: Advanced Features (Tests 14-16)**
```bash
# Test 14: Public Key Retrieval
✅ Tests public key access for local operations
✅ Shows keypair listing and retrieval

# Test 15: Delegation JWT Analysis
✅ Analyzes delegation JWT payload and scope
✅ Verifies CryptoOperations scope is properly set
✅ Shows delegation token configuration

# Test 16: Integration Testing
✅ Tests multi-operation group key usage
✅ Demonstrates encrypt/decrypt cycle with group keys
✅ Shows all components working together
```

#### **Phase 7: Cleanup and Verification (Tests 17-19)**
```bash
# Test 17: Resource Cleanup
✅ Deletes test group and all associated data
✅ Removes keypairs and group information

# Test 18: Cleanup Verification
✅ Confirms group was actually deleted
✅ Verifies 404 response for deleted group

# Test 19: Final Status Check
✅ Shows final token status after testing
✅ Confirms system is in clean state
```

### **Key Technical Achievements Demonstrated**

| Component | What It Proves | Technical Details |
|-----------|----------------|-------------------|
| **🔐 Authentication** | Full JWT lifecycle management | Admin → Test → Delegation token flow |
| **🔑 Crypto Operations** | Complete cryptographic cycles | Encrypt → Decrypt → Sign → Verify |
| **👥 Group Management** | Polymorphic entity handling | Users vs Groups in keypairs table |
| **🎫 Delegation System** | Scope-based access control | CryptoOperations scope enforcement |
| **🔍 Security Model** | Proper permission boundaries | Regular JWT cannot access group keys |
| **🔗 System Integration** | All components working together | Seamless operation between services |
| **🧹 Resource Management** | Proper cleanup and verification | No resource leaks or orphaned data |

### **What Makes This Test Production-Ready**

1. **🔄 Idempotent Operations**: Safe to run multiple times
2. **🔒 Security Validation**: Tests access control and permission boundaries
3. **📊 Comprehensive Coverage**: Tests all major system components
4. **🧪 Real-World Scenarios**: Uses actual API endpoints and data flows
5. **🔍 Error Handling**: Robust error detection and reporting
6. **📝 Audit Trail**: Logs all operations for debugging
7. **🧹 Resource Management**: Proper cleanup and verification
8. **🔗 Integration Testing**: Tests components working together

### **🔑 Required Permissions and JWT Usage**

The test requires specific permissions and uses different JWT types for different operations. Here's the complete breakdown:

| **Operation Type** | **Required Permission** | **JWT Type** | **Endpoints** | **What It Enables** |
|-------------------|------------------------|--------------|---------------|---------------------|
| **User Management** | `ManageUsers` | `ADMIN_TOKEN` | `/auth/users/*` | Create, read, update, delete users |
| **Group Management** | `ManageGroups` | `ADMIN_TOKEN` | `/auth/groups/*` | Create, read, update, delete groups |
| **Permission Management** | `ManageUsers` | `ADMIN_TOKEN` | `/auth/permissions/*` | Grant, revoke, check permissions |
| **Crypto Operations** | `CryptoOperations` | `TEST_TOKEN` | `/api/v1/*` | Encryption, decryption, signing, verification |
| **Group Crypto Operations** | `CryptoOperations` | `DELEGATION_TOKEN` | `/api/v1/vault/*` | Group-level crypto operations |
| **User Profile Access** | None (own user) | `TEST_TOKEN` | `/auth/users/me` | Access own user information |
| **Group Membership** | `ManageGroups` | `ADMIN_TOKEN` | `/auth/groups/*/members` | Add/remove group members |
| **Delegation JWT Creation** | `ManageGroups` | `ADMIN_TOKEN` | `/auth/delegation/jwt` | Create delegation tokens |

### **🔐 JWT Token Types Explained**

- **`ADMIN_TOKEN`**: Full administrative access, can perform all operations
- **`TEST_TOKEN`**: Regular user token with limited permissions, used for crypto operations and user-specific actions
- **`DELEGATION_TOKEN`**: Limited-scope token for group operations, has `CryptoOperations` scope and acts "as" a specific group

### **📝 Practical Examples**

```bash
# Grant permissions to a user
curl -X POST "$BASE_URL/auth/permissions/$USER_ID/ManageGroups/grant" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Check if user has specific permission
curl -X GET "$BASE_URL/auth/permissions/$USER_ID/ManageGroups/check" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Use delegation JWT for group crypto operations
curl -X POST "$BASE_URL/api/v1/vault/sign" \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -d '{"data": "message", "contact_id": "$GROUP_ID", "data_format": "utf8"}'
```

## 🧪 **Advanced Permission Testing**

The test scripts now include comprehensive permission testing that covers all aspects of the permission system:

### **Permission Management Testing (`test_delegation_system.sh`)**
- **Single permission operations**: Grant, revoke, check individual permissions
- **Multiple permission operations**: Grant, revoke, replace permission arrays
- **Permission validation**: Verify that permissions actually work after being granted
- **Permission lifecycle**: Complete grant → verify → revoke → verify cycle

### **Advanced Permission Scenarios (`test_crypto_system.sh`)**
- **Permission boundary testing**: Operations with insufficient permissions
- **Cross-user permission testing**: Delegation with different permission sets
- **Security restriction validation**: Admin-only endpoint access control
- **Delegation scope validation**: JWT scope limitation enforcement

### **Permission Verification (`yieldfabric-auth.sh`)**
- **Permission status checking**: See what permissions the current tokens have
- **Permission validation**: Test that granted permissions actually work
- **Comprehensive testing**: Admin, test, and delegation token validation

### **🔍 New Commands Available**

```bash
# Check permission status for current user
./yieldfabric-auth.sh permissions

# Test all authentication components
./yieldfabric-auth.sh test

# Run comprehensive permission testing
./test_delegation_system.sh

# Run advanced permission scenarios
./test_crypto_system.sh
```

## 🎯 **What Makes This Testing Comprehensive**

1. **🔄 Complete Permission Lifecycle**: Grant → Verify → Revoke → Verify
2. **🔒 Security Boundary Testing**: Ensures insufficient permissions are properly blocked
3. **🎭 Delegation Scope Validation**: Tests that JWT scopes are properly enforced
4. **👥 Cross-User Operations**: Tests permission isolation between users
5. **📊 HTTP Status Validation**: Proper error code handling and response parsing
6. **🧹 Resource Management**: Creates and cleans up test users and groups
7. **🔍 Detailed Logging**: Comprehensive output for debugging and verification

## 🚀 **Getting Started with Permission Testing**

```bash
# 1. Set up authentication system
./yieldfabric-auth.sh setup

# 2. Check current permission status
./yieldfabric-auth.sh permissions

# 3. Run comprehensive permission tests
./test_delegation_system.sh

# 4. Run advanced permission scenarios
./test_crypto_system.sh

# 5. Verify everything is working
./yieldfabric-auth.sh test
```

This comprehensive testing approach ensures that your permission system is robust, secure, and properly integrated with all other system components.

## 📋 **Prerequisites**

- Docker services running (use the docker-compose setup)
- `jq` command-line JSON processor installed
- `curl` for HTTP requests
- Bash shell
- YieldFabric auth service running on port 3000

## 🚨 **Troubleshooting**

### **Common Issues**
1. **Service not running**: Ensure Docker services are started
2. **Permission denied**: The script automatically handles permission granting
3. **Token expired**: Run `./yieldfabric-auth.sh setup` to refresh all tokens
4. **Group creation fails**: Check if user has necessary permissions

### **Debug Mode**
The script provides detailed logging for troubleshooting:
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
├── test_delegation_system.sh   # 🧪 Comprehensive delegation testing
├── README.md                   # This file
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
3. **Use the test script** - Run `./test_delegation_system.sh` to verify everything works

### **For Daily Development**
1. **Reuse tokens** - The system automatically manages token expiration
2. **Check permissions** - Use the status command to see what permissions you have
3. **Clean when needed** - Use `./yieldfabric-auth.sh clean` if you encounter issues

### **For Production**
1. **Review permissions** - Ensure users only have necessary permissions
2. **Monitor usage** - Track delegation token creation and usage
3. **Regular cleanup** - Periodically clean up unused tokens

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
