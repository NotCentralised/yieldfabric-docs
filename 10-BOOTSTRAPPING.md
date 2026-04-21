# Bootstrapping & Root User Setup

## Overview

YieldFabric uses a **manifest-driven bootstrap** process. The first admin user is created automatically on auth service startup from the system manifest (`config/system.yaml`). No manual database seeding is required.

---

## Prerequisites

Before starting the auth service:

1. **PostgreSQL** running (default: `localhost:5433`)
2. **RabbitMQ** running (default: `localhost:5672`)
3. **Jena Fuseki** running (default: `localhost:3030`)
4. **`.env` file** with database URLs, JWT secret, and key provider settings
5. **`config/system.yaml`** — copy from `config/system.example.yaml` and adjust

See `env.example` for the full list of required environment variables.

---

## System Manifest

All services read configuration from a shared YAML manifest:

```
yieldfabric-auth/config/system.yaml
yieldfabric-payments/config/system.yaml
yieldfabric-mq/config/system.yaml
```

The manifest defines bootstrap users, JWT settings, chain configuration (contract addresses, RPC URLs), and infrastructure connections.

### Bootstrap Users Section

```yaml
auth:
  bootstrap_users:
    - email: admin@yieldfabric.io
      role: SuperAdmin
    - email: ops@yieldfabric.io
      role: Operator
```

Each entry creates a user on first startup if they don't already exist. **Existing users are skipped** — the bootstrap does not update roles or passwords for users that are already in the database.

---

## Password Delivery

Bootstrap passwords are provided via **email-keyed environment variables**. The env var name is derived from the email address:

| Email | Env Var |
|-------|---------|
| `admin@yieldfabric.io` | `BOOTSTRAP_PASSWORD_admin_at_yieldfabric_io` |
| `ops@yieldfabric.io` | `BOOTSTRAP_PASSWORD_ops_at_yieldfabric_io` |

The derivation rule: `@` → `_at_`, `.` → `_`, prefixed with `BOOTSTRAP_PASSWORD_`.

### Development Mode

When `system.environment` is `development` and the env var is missing:
- A random 36-character hex password is generated
- Logged once at startup: `"Generated bootstrap password for admin@yieldfabric.io (change immediately): a1b2c3..."`
- **Check the auth service logs** to find the generated password

### Production Mode

When `system.environment` is `production`:
- The env var is **required** — startup fails if missing
- Minimum 12 characters enforced

---

## First Login Flow

1. **Login** with the bootstrap email and password:
   ```
   POST /auth/login
   { "email": "admin@yieldfabric.io", "password": "<bootstrap_password>" }
   ```
   Or with service scoping (used by the frontend):
   ```
   POST /auth/login/with-services
   { "email": "admin@yieldfabric.io", "password": "<bootstrap_password>", "services": ["vault", "payments"] }
   ```

2. The response includes a JWT with `password_change_only: true`. This is a **restricted token** — the payments service rejects it for all operations (the `protected_jwt` validation endpoint returns `403`). Auth service endpoints that don't go through `protected_jwt` are not restricted by this flag.

3. **Change password** using the restricted token:
   ```
   POST /auth/change-password
   Authorization: Bearer <restricted_token>
   { "current_password": "<bootstrap_password>", "new_password": "<your_new_password>" }
   ```

   - Minimum 12 characters
   - All refresh tokens and sessions are invalidated
   - The `must_change_password` flag is cleared
   - **Note**: Any access tokens issued before the password change remain valid until they expire (up to 15 minutes). This is a documented tradeoff to avoid the complexity of a token blacklist.

4. **Re-login** with the new password to get a full JWT:
   ```
   POST /auth/login
   { "email": "admin@yieldfabric.io", "password": "<your_new_password>" }
   ```

5. The auth service logs a reminder:
   ```
   Bootstrap credentials for admin@yieldfabric.io have been superseded by user-set password.
   Clear BOOTSTRAP_PASSWORD_* env vars.
   ```

---

## Role Hierarchy

Bootstrap users are assigned roles from the manifest. The available roles:

```
SuperAdmin ─── All permissions
Admin ──────── Administrative access (no delete, no system config)
Manager ────── Operational management (read/update, group member management)
Operator ───── Read-only with delegation view
Viewer ─────── Read-only
ApiClient ──── API read/write only
```

The permission matrix is defined in code. The manifest can optionally **override** specific roles:

```yaml
auth:
  roles:
    Manager:
      - ReadUser
      - UpdateUser
      - ReadEntity
      - UpdateEntity
      - ApiRead
      - ApiWrite
      - CreateEntity        # extra permission for this deployment
```

If a role is not listed in the manifest, code defaults apply.

---

## Self-Protection

The auth service enforces guards to prevent accidental lockout:

- **Last SuperAdmin guard**: Cannot demote or deactivate the last active SuperAdmin. Uses `SELECT ... FOR UPDATE` to prevent race conditions with concurrent requests.
- **Self-demotion**: A SuperAdmin can demote themselves only if at least one other active SuperAdmin exists (voluntary succession).
- **Self-deactivation blocked**: A user cannot deactivate their own account — a peer must do it.
- **Deactivation cleanup**: When a user is deactivated, all their JWT sessions, API keys, and delegation tokens are revoked atomically.

---

## Audit Trail

All bootstrap and administrative actions are logged to `admin_audit_log`:

| Action | When |
|--------|------|
| `bootstrap_user` | User created from manifest at startup |
| `change_role` | User role changed |
| `deactivate_user` | User deactivated |
| `grant_permission` / `revoke_permission` | Permission changes |
| `change_password` | Password changed |
| `create_user` | User created via API |
| `create_group` / `delete_group` | Group lifecycle |
| `add_group_member` / `remove_group_member` | Group membership |
| `brute_force_alert` | >20 failed logins for admin account |

System actions (bootstrap) have `actor_id = NULL`. User actions include the actor's ID and email.

All audit entries are also emitted via `tracing::info!` for centralized log aggregation.

---

## Rate Limiting

Both `/auth/login` and `/auth/login/with-services` use progressive delays per IP to prevent brute force:

| Consecutive failures | Response delay |
|---------------------|---------------|
| 1–3 | Instant |
| 4–5 | 2 seconds |
| 6–8 | 5 seconds |
| 9+ | 10 seconds |

Counters reset after 15 minutes of inactivity from that IP. A hard backstop of 60 requests per IP per minute is enforced via middleware.

When a SuperAdmin or Admin account exceeds 20 failed login attempts within 24 hours, a `brute_force_alert` is written to the audit log and emitted as a `tracing::warn!`.

---

## Quick Start Checklist

```bash
# 1. Ensure infrastructure is running (PostgreSQL, RabbitMQ, Jena Fuseki)
#    See yieldfabric-containers for docker-compose setup

# 2. Ensure system.yaml exists
cp config/system.example.yaml config/system.yaml

# 3. Ensure .env exists with database URLs and JWT secret
cp env.example .env
# Edit .env with your database credentials

# 4. Set the bootstrap password (or omit for dev auto-generation)
export BOOTSTRAP_PASSWORD_admin_at_yieldfabric_io="MySecurePassword123"

# 5. Start the auth service
cargo run

# 6. Check logs for bootstrap output
#    "Bootstrap user created: admin@yieldfabric.io (role: SuperAdmin)"

# 7. Login
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yieldfabric.io","password":"MySecurePassword123"}'
# Response includes a restricted JWT (password_change_only: true)

# 8. Change password (using the restricted token from step 7)
curl -X POST http://localhost:3000/auth/change-password \
  -H "Authorization: Bearer <token_from_step_7>" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"MySecurePassword123","new_password":"NewSecure456!"}'

# 9. Re-login with new password — full access
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yieldfabric.io","password":"NewSecure456!"}'
```

---

## Manifest Reference

See `config/system.example.yaml` for the complete manifest structure including chain configuration, infrastructure, and auth settings.
