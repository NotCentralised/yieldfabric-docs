# Cryptographic Operations Guide

Complete guide to YieldFabric's cryptographic infrastructure, including key management, encryption, and digital signatures.

---

## Overview

YieldFabric provides a comprehensive cryptographic infrastructure that enables:
- **Zero-Knowledge Privacy**: Confidential transactions using ZK-proof technology
- **Secure Key Management**: Asymmetric cryptography with secure keystore
- **Digital Signatures**: Cryptographic verification for high-security operations
- **Encryption/Decryption**: Data protection using public/private key pairs

---

## Key Management

### Generate User Keypair

Create cryptographic keys for a user:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/keypairs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'
```

**Response:**
```json
{
  "success": true,
  "keypair_id": "kp_user_abc123",
  "public_key": "04a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "message": "Keypair generated successfully"
}
```

### Generate Group Keypair

Create cryptographic keys for a group:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/keypairs \
  -H "Authorization: Bearer $DELEGATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "group",
    "entity_id": "group_xyz789"
  }'
```

### List Keypairs

View all keypairs for an entity:

```bash
curl -X GET https://auth.yieldfabric.com/api/v1/crypto/keypairs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'
```

---

## Encryption and Decryption

### Encrypt Data

Encrypt sensitive data using a public key:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/encrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Confidential business data",
    "public_key": "04a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  }'
```

**Response:**
```json
{
  "success": true,
  "encrypted_data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "encryption_method": "RSA-OAEP",
  "key_id": "kp_user_abc123"
}
```

### Decrypt Data

Decrypt data using the corresponding private key:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/decrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "encrypted_data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'
```

**Response:**
```json
{
  "success": true,
  "decrypted_data": "Confidential business data",
  "key_id": "kp_user_abc123"
}
```

---

## Digital Signatures

### Sign Data

Create a digital signature for data:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/sign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Contract terms to sign",
    "entity_type": "user",
    "entity_id": "user_abc123"
  }'
```

**Response:**
```json
{
  "success": true,
  "signature": "3045022100a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0221001234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "public_key": "04a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "signing_method": "ECDSA-SHA256"
}
```

### Verify Signature

Verify a digital signature:

```bash
curl -X POST https://auth.yieldfabric.com/api/v1/crypto/verify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "Contract terms to sign",
    "signature": "3045022100a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0221001234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "public_key": "04a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  }'
```

**Response:**
```json
{
  "success": true,
  "verified": true,
  "signature_valid": true,
  "message": "Signature verification successful"
}
```

---

## Zero-Knowledge Proof Operations

### Generate ZK Proof

Create zero-knowledge proofs for confidential transactions:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { generateZKProof(input: { proofType: \"BALANCE\", amount: \"100\", assetId: \"aud-token-asset\" }) { success proofHash proofData } }"
  }'
```

### Verify ZK Proof

Verify zero-knowledge proofs:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { verifyZKProof(input: { proofHash: \"0xabc123...\", proofData: \"...\" }) { success verified } }"
  }'
```

---

## Cryptographic Architecture

### Key Storage

**Secure Keystore:**
- Private keys stored encrypted in secure keystore
- Public keys stored for verification and encryption
- Key rotation and backup procedures
- Hardware security module (HSM) integration

**Key Types:**
- **User Keys**: Personal cryptographic operations
- **Group Keys**: Shared group operations
- **Service Keys**: System-level operations
- **Delegation Keys**: Temporary access keys

### Encryption Methods

**Asymmetric Encryption:**
- **RSA-OAEP**: For data encryption/decryption
- **ECDSA**: For digital signatures
- **Ed25519**: For high-performance signatures

**Symmetric Encryption:**
- **AES-256-GCM**: For bulk data encryption
- **ChaCha20-Poly1305**: For high-performance encryption

### Zero-Knowledge Proofs

**Proof Types:**
- **Balance Proofs**: Prove balance without revealing amount
- **Range Proofs**: Prove value is within range
- **Equality Proofs**: Prove two values are equal
- **Membership Proofs**: Prove value is in set

**Privacy Features:**
- Confidential transaction amounts
- Hidden account balances
- Private payment flows
- Anonymous transaction verification

---

## Security Best Practices

### Key Management

1. **Regular Key Rotation**: Rotate keys periodically
2. **Secure Storage**: Use hardware security modules when possible
3. **Access Control**: Limit key access to authorized users
4. **Audit Logging**: Log all cryptographic operations

### Encryption Guidelines

1. **Use Strong Keys**: Generate keys with sufficient entropy
2. **Proper Key Exchange**: Use secure key exchange protocols
3. **Data Classification**: Encrypt sensitive data appropriately
4. **Regular Updates**: Keep cryptographic libraries updated

### Signature Security

1. **Unique Nonces**: Use unique nonces for each signature
2. **Timestamp Validation**: Include timestamps in signed data
3. **Key Verification**: Verify public keys before use
4. **Signature Validation**: Always verify signatures before processing

---

## Error Handling

### Common Cryptographic Errors

**Invalid Key Format:**
```json
{
  "error": "Invalid public key format",
  "details": "Key must be 65 bytes for uncompressed ECDSA"
}
```

**Decryption Failed:**
```json
{
  "error": "Decryption failed",
  "details": "Invalid encrypted data or wrong private key"
}
```

**Signature Verification Failed:**
```json
{
  "error": "Signature verification failed",
  "details": "Invalid signature or data tampering detected"
}
```

**Insufficient Permissions:**
```json
{
  "error": "Insufficient permissions",
  "details": "CryptoOperations permission required"
}
```

---

## Performance Considerations

### Key Generation
- User keypairs: ~100ms
- Group keypairs: ~150ms
- Service keypairs: ~200ms

### Encryption/Decryption
- Small data (<1KB): ~10ms
- Medium data (1-10KB): ~50ms
- Large data (>10KB): ~200ms

### Signature Operations
- Sign: ~5ms
- Verify: ~10ms
- Batch verify: ~2ms per signature

---

## Integration Examples

### Payment with Encryption

```bash
# Encrypt payment details
ENCRYPTED_AMOUNT=$(curl -s -X POST https://auth.yieldfabric.com/api/v1/crypto/encrypt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": "100", "public_key": "$RECIPIENT_PUBLIC_KEY"}' | jq -r '.encrypted_data')

# Send encrypted payment
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { instant(input: { assetId: \"aud-token-asset\", amount: \"100\", destinationId: \"recipient@yieldfabric.com\", encryptedAmount: \"'$ENCRYPTED_AMOUNT'\" }) { success paymentId } }"
  }'
```

### Contract with Digital Signature

```bash
# Sign contract data
SIGNATURE=$(curl -s -X POST https://auth.yieldfabric.com/api/v1/crypto/sign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": "Contract terms", "entity_type": "user", "entity_id": "user_abc123"}' | jq -r '.signature')

# Create signed contract
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { createObligation(input: { counterpart: \"buyer@yieldfabric.com\", denomination: \"aud-token-asset\", notional: \"1000\", signature: \"'$SIGNATURE'\" }) { success contractId } }"
  }'
```

---

## Next Steps

1. **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** - Understand permissions for crypto operations
2. **[05-PAYMENTS.md](./05-PAYMENTS.md)** - Use crypto in payment operations
3. **[04-CONTRACTS.md](./04-CONTRACTS.md)** - Apply signatures to contracts
4. **[08-REFERENCE.md](./08-REFERENCE.md)** - Error codes and troubleshooting
