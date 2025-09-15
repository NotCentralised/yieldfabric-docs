# YieldFabric Group Management System

## Introduction

The YieldFabric group management system provides comprehensive organizational structure management with role-based access control, blockchain account deployment, and delegation capabilities. Groups enable users to collaborate, share resources, and manage permissions collectively.

### Technical Architecture

The group management system is built on top of the authentication system and includes:

- **Group Entity Management**: Database storage and RDF graph store integration
- **Member Management**: Role-based membership with granular permissions
- **Account Deployment**: Automatic blockchain account creation for groups
- **Delegation System**: Token-based group operations and permissions
- **Permission Management**: Group-specific permissions and access control

### Core Components

1. **GroupService**: Handles group creation, updates, and management
2. **GroupMemberService**: Manages group membership and roles
3. **GroupPermissionService**: Handles group-specific permissions
4. **GroupAccountService**: Manages blockchain account deployment for groups
5. **GroupDelegationService**: Handles delegation tokens for group operations

## Group Types

The system supports different types of groups for various organizational needs:

### Organization
- **Purpose**: Company or large organizational units
- **Features**: Full administrative control, multiple owners, complex permission structures
- **Use Cases**: Corporate departments, business units, subsidiaries

### Department
- **Purpose**: Functional departments within organizations
- **Features**: Department-specific permissions, member management
- **Use Cases**: Engineering, Finance, HR, Marketing teams

### Project
- **Purpose**: Temporary or project-based groups
- **Features**: Time-limited access, project-specific resources
- **Use Cases**: Software projects, research initiatives, temporary collaborations

### Team
- **Purpose**: Small working groups or teams
- **Features**: Collaborative permissions, shared resources
- **Use Cases**: Development teams, cross-functional groups

## Group Management

### Viewing Groups

The system provides two ways to view groups:

#### List All Groups
```bash
# Get all groups in the system
curl -X GET "http://localhost:3000/auth/groups" \
  -H "Authorization: Bearer <user_token>"
```

This endpoint returns all groups in the system that the user has permission to view.

#### Get User's Groups
```bash
# Get only groups that the current user is a member of
curl -X GET "http://localhost:3000/auth/groups/user" \
  -H "Authorization: Bearer <user_token>"
```

This endpoint returns only the groups where the current user is an active member, along with their role in each group.

### Creating Groups

#### 1. Create a Group

```bash
# Create a new group
curl -X POST "http://localhost:3000/auth/groups" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <user_token>" \
  -d '{
    "name": "Finance Team",
    "description": "Financial operations team",
    "group_type": "Department"
  }'
```

**Response:**
```json
{
  "group": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Finance Team",
    "description": "Financial operations team",
    "group_type": "Department",
    "account_address": "0xabcdef1234567890...",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 2. Group Creation Process

The group creation process follows a secure, sequential flow:

1. **Database Creation**: Group is created in the database
2. **Key Pair Generation**: Default encryption keys are generated
3. **Account Deployment**: Blockchain account is deployed via MQ system
4. **Address Storage**: Account address is stored in database
5. **Graph Store Integration**: Group entity is created in RDF graph store
6. **Wallet Creation**: Wallet entity is created for the group

### Group Member Management

#### Supported Group Roles

- **owner**: Full control over group, can manage all aspects
- **admin**: Administrative access within group, can manage members
- **member**: Standard group membership with group permissions
- **viewer**: Read-only group access

#### Adding Members to Group

```bash
# Add user to group with specific role
curl -X POST "http://localhost:3000/auth/groups/{group_id}/members" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "admin"
  }'
```

**Response:**
```json
{
  "member": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "group_id": "550e8400-e29b-41d4-a716-446655440001",
    "role": "admin",
    "joined_at": "2024-01-01T00:00:00Z",
    "is_active": true
  }
}
```

#### Getting User's Groups

```bash
# Get groups that the current user is a member of
curl -X GET "http://localhost:3000/auth/groups/user" \
  -H "Authorization: Bearer <user_token>"
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Finance Team",
    "description": "Financial operations team",
    "group_type": "Department",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "name": "Engineering Team",
    "description": "Software development team",
    "group_type": "Team",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### Listing Group Members

```bash
# Get all group members
curl -X GET "http://localhost:3000/auth/groups/{group_id}/members" \
  -H "Authorization: Bearer <user_token>"
```

**Response:**
```json
{
  "members": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "group_id": "550e8400-e29b-41d4-a716-446655440001",
      "role": "owner",
      "joined_at": "2024-01-01T00:00:00Z",
      "is_active": true,
      "user": {
        "email": "admin@example.com",
        "role": "Admin"
      }
    }
  ]
}
```

#### Updating Member Role

```bash
# Update member role
curl -X PUT "http://localhost:3000/auth/groups/{group_id}/members/{member_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <owner_token>" \
  -d '{
    "role": "admin"
  }'
```

#### Removing Group Members

```bash
# Remove member from group
curl -X DELETE "http://localhost:3000/auth/groups/{group_id}/members/{member_id}" \
  -H "Authorization: Bearer <admin_token>"
```

### Group Account Management

#### Account Deployment

Groups automatically get blockchain accounts deployed during creation, but you can also trigger deployment manually:

```bash
# Deploy blockchain account for group
curl -X POST "http://localhost:3000/auth/groups/{group_id}/deploy-account" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "message": "Account deployment initiated",
  "account_address": "0xabcdef1234567890...",
  "deployment_id": "deploy_uuid"
}
```

#### Account Status

```bash
# Check group account status
curl -X GET "http://localhost:3000/auth/groups/{group_id}/account-status" \
  -H "Authorization: Bearer <user_token>"
```

**Response:**
```json
{
  "account_address": "0xabcdef1234567890...",
  "is_deployed": true,
  "deployment_status": "completed",
  "deployed_at": "2024-01-01T00:00:00Z"
}
```

### Group Permissions

#### Group-Specific Permissions

Groups can have their own permission sets that apply to all members:

- **GroupRead**: Read group information and members
- **GroupWrite**: Modify group settings and information
- **GroupManage**: Full group management capabilities
- **GroupMembers**: Manage group membership
- **GroupPermissions**: Manage group permissions
- **GroupDelegation**: Create and manage delegation tokens

#### Managing Group Permissions

```bash
# Grant permission to group
curl -X POST "http://localhost:3000/auth/groups/{group_id}/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <owner_token>" \
  -d '{
    "permission": "GroupMembers"
  }'
```

#### Listing Group Permissions

```bash
# Get group permissions
curl -X GET "http://localhost:3000/auth/groups/{group_id}/permissions" \
  -H "Authorization: Bearer <user_token>"
```

## Delegation System

### Creating Delegation Tokens

Delegation tokens allow users to act on behalf of groups with specific permissions:

```bash
# Create delegation token for group operations
curl -X POST "http://localhost:3000/auth/delegation/jwt" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <user_token>" \
  -d '{
    "group_id": "550e8400-e29b-41d4-a716-446655440001",
    "delegation_scope": [
      "CryptoOperations",
      "ReadGroup",
      "UpdateGroup",
      "ManageGroupMembers"
    ],
    "expiry_seconds": 3600
  }'
```

**Response:**
```json
{
  "delegation_jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "delegation_token_id": "550e8400-e29b-41d4-a716-446655440003",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

### Delegation Token Structure

```json
{
  "sub": "user_uuid",
  "aud": ["yieldfabric"],
  "exp": 1640995200,
  "iat": 1640908800,
  "role": "User",
  "permissions": [],
  "entity_scope": ["entity_uuid_1", "entity_uuid_2"],
  "session_id": "session_uuid",
  "auth_method": "delegation",
  "entity_type": "user",
  "email": "user@example.com",
  "account_address": "0x1234...",
  "group_account_address": "0xabcd...",
  "acting_as": "group_uuid",
  "delegation_scope": [
    "CryptoOperations",
    "ReadGroup",
    "UpdateGroup",
    "ManageGroupMembers"
  ],
  "delegation_token_id": "delegation_token_uuid"
}
```

### Supported Delegation Scopes

- **CryptoOperations**: Perform cryptographic operations on behalf of group
- **ReadGroup**: Read group information and members
- **UpdateGroup**: Modify group settings and information
- **ManageGroupMembers**: Add/remove group members
- **CreateDelegationToken**: Create additional delegation tokens
- **GroupPermissions**: Manage group permissions

## API Reference

### Group Management Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/groups` | Create group | User token |
| GET | `/auth/groups` | List all groups | User token |
| GET | `/auth/groups/user` | Get current user's groups | User token |
| GET | `/auth/groups/{id}` | Get group details | User token |
| PUT | `/auth/groups/{id}` | Update group | Owner/Admin token |
| DELETE | `/auth/groups/{id}` | Delete group | Owner token |

### Group Member Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/groups/{id}/members` | Add group member | Admin token |
| GET | `/auth/groups/{id}/members` | List group members | User token |
| PUT | `/auth/groups/{id}/members/{member_id}` | Update member role | Owner token |
| DELETE | `/auth/groups/{id}/members/{member_id}` | Remove member | Admin token |

### Group Account Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/groups/{id}/deploy-account` | Deploy group account | Admin token |
| GET | `/auth/groups/{id}/account-status` | Get account status | User token |
| POST | `/auth/groups/{id}/add-owner` | Add account owner | Delegation token |

### Group Permission Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/auth/groups/{id}/permissions` | List group permissions | User token |
| POST | `/auth/groups/{id}/permissions` | Grant permission | Owner token |
| DELETE | `/auth/groups/{id}/permissions/{permission}` | Revoke permission | Owner token |

### Delegation Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/delegation/jwt` | Create delegation token | User token |
| GET | `/auth/delegation-tokens` | List delegation tokens | User token |
| DELETE | `/auth/delegation-tokens/{id}` | Revoke delegation token | User token |

## Error Handling

### Common HTTP Status Codes

- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (invalid/missing token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found (group or member not found)
- **409**: Conflict (member already exists)
- **500**: Internal Server Error

### Error Response Format

```json
{
  "error": "Error message",
  "details": "Additional error details",
  "code": "ERROR_CODE"
}
```

## Security Model & Permission Requirements

### Authentication Requirements

**All group management endpoints require valid JWT authentication.** Every request must include a valid JWT token in the Authorization header:

```bash
Authorization: Bearer <jwt_token>
```

### Permission-Based Access Control

The system uses a multi-layered permission model:

#### 1. **Global Permissions** (User-Level)
These permissions are granted to individual users and apply system-wide:

- **`CreateGroup`**: Create new groups
- **`ReadGroup`**: View group information and members
- **`UpdateGroup`**: Modify group settings
- **`DeleteGroup`**: Delete groups
- **`ManageGroupMembers`**: Add/remove group members
- **`CreateDelegationToken`**: Create delegation tokens
- **`ViewDelegationTokens`**: View delegation tokens
- **`RevokeDelegationToken`**: Revoke delegation tokens
- **`ManageGroupEntityScope`**: Manage group entity scope
- **`ViewGroupEntityScope`**: View group entity scope
- **`ManageGroupPermissions`**: Manage group permissions

#### 2. **Role-Based Access** (Group-Level)
Users must be members of groups to perform group-specific operations:

- **`Owner`**: Full control over group, can manage all aspects
- **`Admin`**: Administrative access within group, can manage members
- **`Member`**: Standard group membership with group permissions
- **`Viewer`**: Read-only group access

#### 3. **SuperAdmin Override**
Some operations require SuperAdmin role for system-wide access:

- **`list_groups`**: Only SuperAdmins can see all groups in the system

### Permission Requirements by Endpoint

#### Group Management Endpoints

| Endpoint | Method | Required Permission | Group Membership | Notes |
|----------|--------|-------------------|------------------|-------|
| `/auth/groups` | POST | `CreateGroup` | N/A | Creates group, user becomes owner |
| `/auth/groups` | GET | `SuperAdmin` role | N/A | Lists ALL groups (SuperAdmin only) |
| `/auth/groups/user` | GET | `ReadGroup` | N/A | Lists user's groups only |
| `/auth/groups/{id}` | GET | `ReadGroup` | ✅ Required | Must be member of group |
| `/auth/groups/{id}` | PUT | `UpdateGroup` | ✅ Required | Must be member of group |
| `/auth/groups/{id}` | DELETE | `DeleteGroup` | ✅ Required | Must be member of group |

#### Group Member Endpoints

| Endpoint | Method | Required Permission | Group Membership | Notes |
|----------|--------|-------------------|------------------|-------|
| `/auth/groups/{id}/members` | POST | `ManageGroupMembers` | ✅ Required | Must be member of group |
| `/auth/groups/{id}/members` | GET | `ReadGroup` | ✅ Required | Must be member of group |
| `/auth/groups/{id}/members/{user_id}` | PUT | `ManageGroupMembers` | ✅ Required | Must be member of group |
| `/auth/groups/{id}/members/{user_id}` | DELETE | `ManageGroupMembers` | ✅ Required | Must be member of group |

#### Group Account Endpoints

| Endpoint | Method | Required Permission | Group Membership | Notes |
|----------|--------|-------------------|------------------|-------|
| `/auth/groups/{id}/deploy-account` | POST | `CreateGroup` | N/A | Can deploy any group account |
| `/auth/groups/{id}/account-status` | GET | `ReadGroup` | N/A | Can check any group account |
| `/auth/groups/{id}/add-owner` | POST | `ManageGroupMembers` | ✅ Required | Must be member of group |

#### Delegation Endpoints

| Endpoint | Method | Required Permission | Group Membership | Notes |
|----------|--------|-------------------|------------------|-------|
| `/auth/delegation/jwt` | POST | `ManageGroupPermissions` | ✅ Required | Must be member of group |
| `/auth/delegation/tokens` | GET | `ViewDelegationTokens` | N/A | Lists user's delegation tokens |
| `/auth/delegation/tokens/{id}` | DELETE | `RevokeDelegationToken` | N/A | Can revoke own tokens |

### Permission Checking Flow

For group-specific operations, the system performs a two-step permission check:

1. **Global Permission Check**: Verifies user has the required system-wide permission
2. **Group Membership Check**: Verifies user is a member of the specific group

```rust
// Example permission check flow
if !has_permission(&auth_context, "ReadGroup") {
    return Err(StatusCode::FORBIDDEN);
}

check_group_permission(&auth_context, &group_id, "ReadGroup", &auth_service).await?;
```

### Delegation Token Permissions

When using delegation tokens, the permission model changes:

- **Delegation tokens** use `delegation_scope` instead of user permissions
- **Group membership** is still required for group-specific operations
- **Delegation scope** must include the required permissions

```json
{
  "delegation_scope": [
    "CryptoOperations",
    "ReadGroup", 
    "UpdateGroup",
    "ManageGroupMembers"
  ],
  "acting_as": "group_uuid"
}
```

### Error Responses

#### 401 Unauthorized
```json
{
  "error": "Invalid or missing JWT token"
}
```

#### 403 Forbidden
```json
{
  "error": "Insufficient permissions",
  "details": "User does not have required permission: ReadGroup"
}
```

#### 403 Forbidden (Group Membership)
```json
{
  "error": "Access denied",
  "details": "User is not a member of this group"
}
```

### Developer Implementation Guide

#### 1. **Obtain JWT Token**
```bash
# Login to get JWT token
curl -X POST "http://localhost:3000/auth/login/with-services" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password",
    "services": ["vault", "payments"]
  }'
```

#### 2. **Check User Permissions**
```bash
# Get user info to check permissions
curl -X GET "http://localhost:3000/auth/protected" \
  -H "Authorization: Bearer <jwt_token>"
```

#### 3. **Handle Permission Errors**
```javascript
// Example error handling
try {
  const response = await fetch('/auth/groups', {
    headers: {
      'Authorization': `Bearer ${jwtToken}`
    }
  });
  
  if (response.status === 403) {
    throw new Error('Insufficient permissions');
  }
  
  if (response.status === 401) {
    throw new Error('Invalid or expired token');
  }
  
} catch (error) {
  console.error('Permission error:', error.message);
}
```

#### 4. **Use Delegation Tokens for Group Operations**
```bash
# Create delegation token for group operations
curl -X POST "http://localhost:3000/auth/delegation/jwt" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <user_token>" \
  -d '{
    "group_id": "group_uuid",
    "delegation_scope": ["ReadGroup", "ManageGroupMembers"],
    "expiry_seconds": 3600
  }'
```

### Security Best Practices

1. **Always validate JWT tokens** before making requests
2. **Handle permission errors gracefully** in your application
3. **Use delegation tokens** for group operations when appropriate
4. **Implement token refresh** for long-running applications
5. **Log permission failures** for security monitoring
6. **Use least privilege principle** - only request necessary permissions

## Security Considerations

1. **Role-Based Access**: Group operations require appropriate roles
2. **Delegation Scoping**: Delegation tokens are limited to specific scopes
3. **Account Ownership**: Group accounts are owned by group creators
4. **Permission Inheritance**: Group permissions apply to all members
5. **Audit Logging**: All group operations are logged for compliance
6. **Token Expiration**: Delegation tokens have configurable expiration times
7. **Multi-Layer Security**: Global permissions + group membership + role-based access
8. **SuperAdmin Override**: System-wide operations require SuperAdmin role

## Development Setup

### Prerequisites

- Auth service running on port 3000
- Database with group tables initialized
- MQ system for account deployment
- Graph store for entity management

### Quick Start

1. Start the auth service:
   ```bash
   cd yieldfabric-auth && cargo run
   ```

2. Create your first group:
   ```bash
   # Get admin token first
   ./scripts/yieldfabric-auth.sh admin
   
   # Create group
   curl -X POST "http://localhost:3000/auth/groups" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin_token>" \
     -d '{
       "name": "My Team",
       "description": "My first group",
       "group_type": "Team"
     }'
   ```

3. Add members to the group:
   ```bash
   curl -X POST "http://localhost:3000/auth/groups/{group_id}/members" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin_token>" \
     -d '{
       "user_id": "user_uuid",
       "role": "member"
     }'
   ```

This group management system provides a robust foundation for building collaborative applications with proper organizational structure, role-based access control, and delegation capabilities.
