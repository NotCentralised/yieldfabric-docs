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
```

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
