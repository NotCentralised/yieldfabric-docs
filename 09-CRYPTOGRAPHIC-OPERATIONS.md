# Cryptographic Operations Guide

Complete guide to YieldFabric's cryptographic infrastructure, including key management, encryption, and digital signatures.

---

## Overview

YieldFabric provides a comprehensive cryptographic infrastructure that enables:
- **Zero-Knowledge Privacy**: Confidential transactions using ZK-proof technology (handled transparently by the platform — no user-facing ZK mutations)
- **Secure Key Management**: Asymmetric key pairs backed by OpenSSL, HSM, or hybrid providers
- **Digital Signatures**: Sign and verify data with ECDSA
- **Encryption/Decryption**: Protect data using key pairs managed by the auth service

All cryptographic endpoints live on the **Auth Service** at `https://auth.yieldfabric.com/api/v1/`.

---

## Key Management

### Generate Keypair

Create a key pair for a contact (user or group). The service automatically determines the entity type.

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/generate-keypair \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider_type": "OpenSSL"
  }'
```

**Parameters:**
- `contact_id` (required): UUID of the user or group to generate keys for
- `provider_type` (optional): `"OpenSSL"` (default), `"HSM"`, or `"Hybrid"`

**Response:**
```json
{
  "success": true,
  "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "public_key": "04a1b2c3d4e5f6...",
  "entity_type": "user",
  "entity_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider_type": "OpenSSL"
}
```

**Permissions:**
- Requires `CryptoOperations` permission
- Users can only generate keys for themselves unless they have Admin/SuperAdmin role
- Group keys require a delegation JWT with `CryptoOperations` in delegation scope

### Get Key Info

Retrieve information about a specific key pair:

```bash
curl -X GET https://auth.yieldfabric.com/api/v1/keys/{key_id}/info \
  -H "Authorization: Bearer $TOKEN"
```

### Get Public Key by Contact

Look up a contact's public key:

```bash
curl -X GET https://auth.yieldfabric.com/api/v1/public-key/{contact_id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## Digital Signatures

### Sign Data

Create a digital signature for arbitrary data:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/sign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "entity_type": "user",
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "data": "Contract terms to sign",
    "data_format": "utf8"
  }'
```

**Parameters:**
- `key_id` (required): UUID of the key pair to use
- `entity_type` (required): `"user"` or `"group"`
- `entity_id` (required): UUID of the entity that owns the key
- `data` (required): The data to sign
- `data_format` (optional): `"utf8"` (default), `"hex"`, or `"base64"`
- `provider_type` (optional): Override the key's default provider

**Response:**
```json
{
  "success": true,
  "result": "3045022100a1b2c3d4...",
  "result_format": "hex",
  "provider_type": "OpenSSL",
  "operation_id": "d4e5f6a7-b8c9-0123-def4-567890abcdef",
  "metadata": {}
}
```

**Notes:**
- External keys cannot be used for server-side signing
- MCP sessions use the `mcp_selected_key` from the JWT automatically

### Verify Signature

Verify a digital signature:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "data": "Contract terms to sign",
    "signature": "3045022100a1b2c3d4...",
    "signature_format": "hex",
    "data_format": "utf8"
  }'
```

**Parameters:**
- `key_id` (required): UUID of the key pair used for signing
- `data` (required): The original data that was signed
- `signature` (required): The signature to verify
- `signature_format` (optional): `"hex"` (default), `"base64"`, or `"der"`
- `data_format` (optional): `"utf8"` (default), `"hex"`, or `"base64"`
- `user_id` (optional): UUID of the key owner (optional with delegation JWTs)
- `provider_type` (optional): Override the key's default provider

**Response:**
```json
{
  "success": true,
  "result": "true",
  "result_format": "boolean",
  "provider_type": "OpenSSL",
  "operation_id": "e5f6a7b8-c901-2345-ef56-7890abcdef01",
  "metadata": {}
}
```

---

## Encryption and Decryption

### Encrypt Data

Encrypt data using a key pair's public key:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/encrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "data": "Confidential business data",
    "data_format": "utf8"
  }'
```

**Parameters:**
- `key_id` (required): UUID of the key pair to encrypt with
- `data` (required): The data to encrypt
- `data_format` (optional): `"utf8"` (default), `"hex"`, or `"base64"`
- `user_id` (optional): UUID of the key owner
- `provider_type` (optional): Override the key's default provider

**Response:**
```json
{
  "success": true,
  "result": "eyJhbGciOiJIUzI1NiIs...",
  "result_format": "base64",
  "provider_type": "OpenSSL",
  "operation_id": "f6a7b8c9-0123-4567-f012-3456789abcde",
  "metadata": {}
}
```

### Decrypt Data

Decrypt data using a key pair's private key:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/decrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "encrypted_data": "eyJhbGciOiJIUzI1NiIs...",
    "encrypted_data_format": "base64"
  }'
```

**Parameters:**
- `key_id` (required): UUID of the key pair to decrypt with
- `encrypted_data` (required): The encrypted data
- `encrypted_data_format` (optional): `"base64"` (default), `"hex"`
- `user_id` (optional): UUID of the key owner
- `provider_type` (optional): Override the key's default provider

**Response:**
```json
{
  "success": true,
  "result": "Confidential business data",
  "result_format": "utf8",
  "provider_type": "OpenSSL",
  "operation_id": "a7b8c901-2345-6789-0123-456789abcdef",
  "metadata": {}
}
```

---

## Vault-Specific Endpoints

The auth service exposes dedicated endpoints for the vault service (internal use):

- `POST /api/v1/vault/decrypt` — Decrypt data for vault operations
- `POST /api/v1/vault/sign` — Sign data for vault transactions

These are used internally by the vault service for blockchain transaction signing and balance decryption. They follow the same request/response structure as the standard endpoints.

---

## Key Providers

YieldFabric supports multiple cryptographic providers:

| Provider | Description | Use Case |
|----------|-------------|----------|
| **OpenSSL** | Software-based cryptography (default) | Development, standard operations |
| **HSM** | Hardware Security Module integration | Production, high-security environments |
| **Hybrid** | Combination of OpenSSL + HSM | Flexible deployments |
| **External** | Externally managed keys (public key only) | Client-side signing, third-party key management |

**External keys** can only be used for verification and encryption (public-key operations). They cannot be used for signing or decryption on the server.

---

## Zero-Knowledge Proofs

ZK-proofs are used internally by YieldFabric for:
- **Confidential balances**: Private balance amounts are encrypted on-chain and decrypted by the vault service
- **Amount hashing**: Payment amounts are hashed for on-chain verification without revealing the actual amount
- **Distribution Merkle trees**: Distribution payments use Merkle proofs for recipient verification

**These operations are handled transparently** by the platform when you use the GraphQL API (e.g., `instant`, `deposit`, `createDistribution`). There are no user-facing ZK mutations — the system generates and verifies proofs automatically as part of payment processing.

---

## Delegation and Group Keys

When operating on behalf of a group using a delegation JWT:

1. **Access control**: Delegation JWTs can only access keys belonging to the authenticated user or the delegated group
2. **Scope check**: The delegation scope must include `CryptoOperations`
3. **Group keys**: Use the group's `contact_id` when generating keys with a delegation token
4. **Audit trail**: All operations are logged with both the user and group identifiers

```bash
# Generate a key pair for a group using delegation
curl -X POST https://auth.yieldfabric.com/api/v1/generate-keypair \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "group-uuid-here",
    "provider_type": "OpenSSL"
  }'
```

---

## Error Handling

### Common Errors

**Key Not Found:**
```json
{
  "error": "Key pair not found"
}
```

**External Key Restriction:**
```json
{
  "error": "External keys cannot be used for server-side signing operations"
}
```

**Insufficient Permissions:**
```json
{
  "error": "Insufficient permissions: CryptoOperations required"
}
```

**Delegation Scope Missing:**
```json
{
  "error": "Delegation JWT scope does not include CryptoOperations"
}
```

**Invalid Key Format:**
```json
{
  "error": "Invalid contact_id format"
}
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/generate-keypair` | POST | Generate key pair for a contact |
| `/api/v1/keys/{key_id}/info` | GET | Get key pair information |
| `/api/v1/public-key/{contact_id}` | GET | Get public key by contact |
| `/api/v1/sign` | POST | Sign data |
| `/api/v1/verify` | POST | Verify signature |
| `/api/v1/encrypt` | POST | Encrypt data |
| `/api/v1/decrypt` | POST | Decrypt data |
| `/api/v1/vault/sign` | POST | Sign for vault (internal) |
| `/api/v1/vault/decrypt` | POST | Decrypt for vault (internal) |

All endpoints require `Authorization: Bearer $TOKEN` with `CryptoOperations` permission.

---

## Next Steps

1. **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** - Understand permissions and delegation for crypto operations
2. **[05-PAYMENTS.md](./05-PAYMENTS.md)** - Payments that use crypto behind the scenes
3. **[04-CONTRACTS.md](./04-CONTRACTS.md)** - Apply signatures to contracts
4. **[08-REFERENCE.md](./08-REFERENCE.md)** - Error codes and troubleshooting
