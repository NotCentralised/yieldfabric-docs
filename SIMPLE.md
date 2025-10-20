# YieldFabric API - Simple CURL Examples

## Base URLs

- **Auth Service**: `http://localhost:3000` (Production: `https://auth.yieldfabric.com`)
- **Payments/GraphQL Service**: `http://localhost:3002` (Production: `https://pay.yieldfabric.com`)
- **GraphQL Endpoint**: `http://localhost:3002/graphql`

---

## 1. Authentication with Services

Login to YieldFabric and request specific service access:

```bash
curl -X POST http://localhost:3000/auth/login/with-services \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password",
    "services": ["vault", "payments"]
  }'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "User",
    "account_address": "0x1234..."
  }
}
```

**Save the token** for subsequent requests:
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 2. Delegate Authentication

Create a delegation JWT for group operations:

```bash
curl -X POST http://localhost:3000/auth/delegation/jwt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "550e8400-e29b-41d4-a716-446655440000",
    "delegation_scope": ["read", "write", "manage"],
    "expiry_seconds": 3600
  }'
```

**Response:**
```json
{
  "delegation_jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "delegation_scope": ["read", "write", "manage"],
  "expiry_seconds": 3600,
  "group_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### List Delegation Tokens

```bash
curl -X GET http://localhost:3000/auth/delegation-tokens \
  -H "Authorization: Bearer $TOKEN"
```

### Revoke Delegation Token

```bash
curl -X DELETE http://localhost:3000/auth/delegation-tokens/{token_id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## 3. Get Balance

Get balance for a specific denomination and obligor:

```bash
curl -X GET "http://localhost:3002/balance?denomination=USD&obligor=null" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**With specific obligor:**
```bash
curl -X GET "http://localhost:3002/balance?denomination=aud-token-asset&obligor=0x0000000000000000000000000000000000000000" \
  -H "Authorization: Bearer $TOKEN"
```

**With wallet address:**
```bash
curl -X GET "http://localhost:3002/balance?denomination=USD&wallet_address=0x1234..." \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "timestamp": "2025-10-19T12:00:00.000Z",
  "balance": {
    "private_balance": "100",
    "public_balance": "50",
    "decimals": "100",
    "locked_out": [],
    "locked_in": [],
    "denomination": "USD",
    "obligor": "null",
    "beneficial_balance": "0",
    "beneficial_transaction_ids": [],
    "outstanding": "0"
  },
  "error": null
}
```

---

## 4. Get Contracts

Fetch all contracts using GraphQL:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { contractFlow { coreContracts { all { id name description status contractType manager { id name } currency startDate expiryDate createdAt parties { id entity { id name } role } payments { id amount status dueDate } } } } }"
  }'
```

**Response:**
```json
{
  "data": {
    "contractFlow": {
      "coreContracts": {
        "all": [
          {
            "id": "contract-123",
            "name": "Service Agreement",
            "description": "Monthly service contract",
            "status": "Active",
            "contractType": "ServiceAgreement",
            "manager": {
              "id": "entity-1",
              "name": "Manager Corp"
            },
            "currency": "USD",
            "startDate": "2025-01-01",
            "expiryDate": "2025-12-31",
            "createdAt": "2025-01-01T00:00:00Z",
            "parties": [...],
            "payments": [...]
          }
        ]
      }
    }
  }
}
```

---

## 5. Get Contracts by Entity

Get contracts for a specific entity:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetEntityContracts($entityId: ID!) { contractFlow { coreContracts { byEntityId(entityId: $entityId) { id name description status contractType currency startDate expiryDate parties { id entity { id name } role } } } } }",
    "variables": {
      "entityId": "your-entity-id"
    }
  }'
```

---

## 6. Get Payments

Fetch all payments for an entity:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetTransactions($currentEntityId: ID) { paymentsByEntity(currentEntityId: $currentEntityId) { id amount assetId status dueDate description payee { entity { id name } wallet { id name } } payer { entity { id name } wallet { id name } } createdAt } }",
    "variables": {
      "currentEntityId": "your-entity-id"
    }
  }'
```

**Response:**
```json
{
  "data": {
    "paymentsByEntity": [
      {
        "id": "payment-123",
        "amount": "1000",
        "assetId": "aud-token-asset",
        "status": "Pending",
        "dueDate": "2025-11-01",
        "description": "Monthly payment",
        "payee": {
          "entity": { "id": "entity-1", "name": "Recipient" },
          "wallet": { "id": "wallet-1", "name": "Main Wallet" }
        },
        "payer": {
          "entity": { "id": "entity-2", "name": "Payer" },
          "wallet": { "id": "wallet-2", "name": "Payment Wallet" }
        },
        "createdAt": "2025-10-01T00:00:00Z"
      }
    ]
  }
}
```

---

## 7. Create Contract

Create a new contract/obligation:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation CreateContract($input: CreateObligationInput!) { createObligation(input: $input) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }",
    "variables": {
      "input": {
        "chainId": "153",
        "obligationAddress": "0x9EB71DE5c8e0079493a6703bFD07845925387a7F",
        "denomination": "aud-token-asset",
        "obligor": "0x0000000000000000000000000000000000000000",
        "amount": "100",
        "unlockSender": "2025-12-31",
        "unlockReceiver": "2025-12-31",
        "idempotencyKey": "unique-key-123"
      }
    }
  }'
```

**Response:**
```json
{
  "data": {
    "createObligation": {
      "success": true,
      "message": "Obligation created successfully",
      "accountAddress": "0x1234...",
      "obligationResult": "...",
      "messageId": "msg-123",
      "contractId": "contract-456",
      "transactionId": "tx-789",
      "signature": "0xabcd...",
      "timestamp": "2025-10-19T12:00:00Z",
      "idHash": "hash-abc"
    }
  }
}
```

---

## 8. Get Contract by ID

**Using GraphQL query with variables** (recommended):

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetContract($id: ID!) { contractFlow { coreContracts { all { id name description status contractType currency startDate expiryDate parties { id entity { id name } role } payments { id amount status } } } } }"
  }'
```

Then filter by ID in your application, or use the full contracts list above.

---

## 9. Create Instant Payment

Send an instant payment to another entity:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation InstantPayment($input: InstantSendInput!) { instant(input: $input) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }",
    "variables": {
      "input": {
        "chainId": "153",
        "walletAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
        "assetId": "aud-token-asset",
        "amount": "10",
        "destinationId": "counterpart@yieldfabric.com",
        "idempotencyKey": "instant-payment-001"
      }
    }
  }'
```

**Alternative with destination wallet ID:**
```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation InstantPayment($input: InstantSendInput!) { instant(input: $input) { success message paymentId messageId timestamp } }",
    "variables": {
      "input": {
        "chainId": "153",
        "walletAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
        "assetId": "aud-token-asset",
        "amount": "10",
        "destinationWalletId": "wallet-id-here",
        "idempotencyKey": "instant-payment-002"
      }
    }
  }'
```

**Response:**
```json
{
  "data": {
    "instant": {
      "success": true,
      "message": "Send message submitted successfully",
      "accountAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
      "destinationId": "counterpart@yieldfabric.com",
      "idHash": "0xabc...",
      "messageId": "95e7ef5e-baca-49d7-9917-76f45b644915",
      "paymentId": "PAY-INSTANT-1759048183145",
      "sendResult": "...",
      "timestamp": "2025-10-19T12:00:00Z"
    }
  }
}
```

**Important Notes:**
- `amount` must be an **integer string** (e.g., `"10"`, NOT `"10.00"`)
- Either `destinationId` (entity name/email) OR `destinationWalletId` (wallet ID) is required
- `assetId` options: `"aud-token-asset"`, `"usd-token-asset"`, etc.
- `idempotencyKey` ensures duplicate prevention

---

## 10. Accept Payment

Accept a pending payment:

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation AcceptPayment($input: AcceptInput!) { accept(input: $input) { success message accountAddress idHash acceptResult messageId transactionId signature timestamp } }",
    "variables": {
      "input": {
        "chainId": "153",
        "walletAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
        "idHash": "0xabc123...",
        "idempotencyKey": "accept-payment-001"
      }
    }
  }'
```

**Response:**
```json
{
  "data": {
    "accept": {
      "success": true,
      "message": "Accept message submitted successfully",
      "accountAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
      "idHash": "0xabc123...",
      "acceptResult": "...",
      "messageId": "msg-456",
      "transactionId": "tx-789",
      "signature": "0xdef...",
      "timestamp": "2025-10-19T12:00:00Z"
    }
  }
}
```

**Required Input:**
- `chainId`: Blockchain chain ID (e.g., `"153"` for Redbelly testnet)
- `walletAddress`: Your wallet address
- `idHash`: The payment ID hash to accept (from locked_in transactions)
- `idempotencyKey`: Unique key to prevent duplicate accepts

---

## Common Headers

All authenticated requests require:

```bash
-H "Authorization: Bearer $TOKEN"
-H "Content-Type: application/json"
```

---

## Quick Reference

### Auth Service (Port 3000)
- `POST /auth/login/with-services` - Login with service selection
- `POST /auth/refresh` - Refresh access token
- `GET /auth/users/me` - Get user profile
- `POST /auth/logout` - Logout current device
- `POST /auth/logout-all` - Logout all devices
- `POST /auth/delegation/jwt` - Create delegation token
- `GET /auth/delegation-tokens` - List delegation tokens
- `DELETE /auth/delegation-tokens/{id}` - Revoke delegation token

### Payments/GraphQL Service (Port 3002)
- `GET /balance?denomination={asset}&obligor={obligor}` - Get balance
- `POST /graphql` - GraphQL endpoint for:
  - Queries: `contracts`, `payments`, `entities`, `wallets`
  - Mutations: `instant`, `accept`, `createObligation`, `createPayment`

---

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "error": "Invalid or expired token"
}
```

**403 Forbidden:**
```json
{
  "error": "Insufficient permissions"
}
```

**422 Validation Error:**
```json
{
  "error": "Invalid input: amount must be integer string"
}
```

**500 Server Error:**
```json
{
  "error": "Internal server error",
  "details": "..."
}
```

---

## JWT Token Structure

Your JWT token includes:

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "role": "User",
  "aud": ["vault", "payments"],
  "permissions": [
    "CryptoOperations",
    "ViewSignatureKeys",
    "ManageSignatureKeys"
  ],
  "exp": 1697712000,
  "iat": 1697625600
}
```

---

## Testing Tips

### 1. Save your token
```bash
export TOKEN=$(curl -s -X POST http://localhost:3000/auth/login/with-services \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password","services":["vault","payments"]}' \
  | jq -r '.token')
```

### 2. Check token validity
```bash
curl -X GET http://localhost:3000/auth/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Pretty print JSON responses
Add `| jq` to the end of your curl commands:
```bash
curl ... | jq
```

---

## Advanced Examples

### Create Contract with Full Payment Details

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation CreateContract($input: CreateObligationInput!) { createObligation(input: $input) { success message contractId messageId } }",
    "variables": {
      "input": {
        "chainId": "153",
        "obligationAddress": "0x9EB71DE5c8e0079493a6703bFD07845925387a7F",
        "denomination": "aud-token-asset",
        "obligor": "0x0000000000000000000000000000000000000000",
        "amount": "1000",
        "unlockSender": "2025-12-31",
        "unlockReceiver": "2025-12-31",
        "oracleAddress": "0x26A20Bfb4A70be4c86D260daA64cE9a8fc6e6eF1",
        "oracleOwner": "0x1234...",
        "oracleKeySender": "contract_signed",
        "oracleValueSender": "true",
        "oracleKeyRecipient": "goods_delivered",
        "oracleValueRecipient": "true",
        "idempotencyKey": "contract-create-001"
      }
    }
  }'
```

### Batch Query Multiple Resources

```bash
curl -X POST http://localhost:3002/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { entities { all { id name } } wallets(entityId: \"entity-id\") { id name address balance } paymentsByEntity(currentEntityId: \"entity-id\") { id amount status } }"
  }'
```

---

## Production URLs

When deploying to production, replace `localhost` with your domain:

```bash
# Auth Service
export AUTH_URL="https://auth.yieldfabric.com"

# Payments/GraphQL Service  
export PAY_URL="https://pay.yieldfabric.com"
export GRAPHQL_URL="https://pay.yieldfabric.com/graphql"

# Example: Production login
curl -X POST $AUTH_URL/auth/login/with-services \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password",
    "services": ["vault", "payments"]
  }'
```

---

## Asset IDs Reference

Common asset identifiers:

- `aud-token-asset` - Australian Dollars
- `usd-token-asset` - US Dollars  
- `usdc-token-asset` - USD Coin
- `usdt-token-asset` - Tether USD
- `eth-token-asset` - Ethereum
- `btc-token-asset` - Bitcoin
- `dai-token-asset` - DAI Stablecoin

---

## Chain IDs Reference

- `153` - Redbelly Testnet (Governors)
- `31337` - Local Hardhat Network
- `1` - Ethereum Mainnet
- `11155111` - Sepolia Testnet

---

## Next Steps

1. **Authenticate**: Get your JWT token
2. **Get Balance**: Check your current balance
3. **Get Contracts**: View existing contracts
4. **Create Payment**: Send instant payment
5. **Accept Payment**: Accept incoming payment

For more detailed documentation, see:
- `/mcp_server/API_SPECIFICATION.md` - Full API reference
- `/mcp_server/INSTANT_PAYMENTS.md` - Instant payments guide
- `/mcp_server/BALANCE_API_GUIDE.md` - Balance API guide

