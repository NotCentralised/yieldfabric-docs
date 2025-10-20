# API Reference

Quick reference guide for common values, error codes, and endpoints.

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

## Asset IDs Reference

Common asset identifiers:

- `aud-token-asset` - Australian Dollars
- `usd-token-asset` - US Dollars

---

## Chain IDs Reference

- `151` - Redbelly Mainnet (Governors)
- `153` - Redbelly Testnet (Governors)

---

## Quick Reference

### Auth Service Endpoints

- `POST /auth/login/with-services` - Login with service selection
- `POST /auth/refresh` - Refresh access token
- `GET /auth/users/me` - Get user profile
- `POST /auth/logout` - Logout current device
- `POST /auth/logout-all` - Logout all devices
- `POST /auth/delegation/jwt` - Create delegation token
- `GET /auth/delegation-tokens` - List delegation tokens
- `DELETE /auth/delegation-tokens/{id}` - Revoke delegation token

### Payments/GraphQL Service Endpoints

**REST Endpoints:**
- `GET /balance?denomination={asset}&obligor={obligor}&group_id={group_id}` - Get balance

**GraphQL Endpoint:** `POST /graphql`

**Queries:**
- `contractFlow.coreContracts.byEntityId` - Get contracts by entity
- `paymentsByEntity` - Get payments by entity
- `swapFlow.coreSwaps.byEntityId` - Get swaps by entity
- `entities.all` - List entities
- `wallets` - Query wallets

**Mutations:**
- `instant` - Send instant payment
- `accept` - Accept incoming payment
- `createObligation` - Create payment obligation
- `acceptObligation` - Accept obligation
- `createSwap` - Create atomic swap
- `completeSwap` - Execute swap
- `deposit` - Deposit funds into intelligent account
- `withdraw` - Withdraw funds from intelligent account

---

## Common Headers

All authenticated requests require:

```bash
-H "Authorization: Bearer $TOKEN"
-H "Content-Type: application/json"
```

---

## Query Parameters

### Balance Endpoint

- `denomination` (required): Asset ID (e.g., `aud-token-asset`)
- `obligor` (optional): Obligor entity name/address or `null` for general balance
- `group_id` (optional): Group ID for delegation queries
- `wallet_address` (optional): Specific wallet address to query

---

## GraphQL Variables

### Common Input Types

**InstantSendInput:**
- `assetId` (string, required)
- `amount` (string, required) - Integer string
- `destinationId` (string, optional) - Entity name/email
- `destinationWalletId` (string, optional) - Wallet ID
- `idempotencyKey` (string, optional)

**AcceptInput:**
- `paymentId` (string, required)
- `idempotencyKey` (string, optional)

**CreateObligationInput:**
- `denomination` (string, required)
- `counterpart` (string, optional) - Entity name/email
- `counterpartWalletId` (string, optional) - Wallet ID
- `obligor` (string, optional) - Entity name/email
- `obligorWalletId` (string, optional) - Wallet ID
- `obligationAddress` (string, optional)
- `notional` (string, optional)
- `expiry` (string, optional) - ISO 8601 date
- `data` (JSON, optional) - Custom contract data
- `initialPayments` (InitialPaymentsInput, optional)
- `idempotencyKey` (string, optional)

**InitialPaymentsInput:**
- `amount` (string, required) - Total amount across all payments
- `denomination` (string, optional)
- `obligor` (string, optional)
- `payments` (array, required) - VaultPaymentInput objects

**VaultPaymentInput:**
- `oracleAddress` (string, nullable)
- `oracleOwner` (string, nullable)
- `oracleKeySender` (string)
- `oracleValueSenderSecret` (string)
- `oracleKeyRecipient` (string)
- `oracleValueRecipientSecret` (string)
- `unlockSender` (string, nullable) - ISO 8601 timestamp
- `unlockReceiver` (string, nullable) - ISO 8601 timestamp

**CreateSwapInput:**
- `swapId` (string, required)
- `counterparty` (string, optional) - Entity name/email
- `counterpartyWalletId` (string, optional) - Wallet ID
- `deadline` (string, required) - ISO 8601 date
- `initiatorObligationIds` (array, optional) - Contract IDs
- `counterpartyExpectedPayments` (InitialPaymentsInput, optional)
- `idempotencyKey` (string, optional)

**CompleteSwapInput:**
- `swapId` (string, required)
- `idempotencyKey` (string, optional)

---

## Status Values

### Contract Status
- `ACTIVE` - Contract is active
- `COMPLETED` - All obligations fulfilled
- `PENDING` - Awaiting acceptance
- `CANCELLED` - Contract cancelled
- `EXPIRED` - Contract past expiry date

### Payment Status
- `COMPLETED` - Payment finalized on-chain
- `PROCESSING` - Payment scheduled/being executed
- `PENDING` - Payment awaiting action
- `FAILED` - Payment execution failed

### Swap Status
- `COMPLETED` - Swap executed successfully
- `PENDING` - Awaiting counterparty action
- `ACTIVE` - Swap created, not yet completed
- `CANCELLED` - Swap cancelled
- `EXPIRED` - Swap past deadline

---

## Payment Types

- `PAYABLE` - Outgoing payment (you are the payer)
- `RECEIVABLE` - Incoming payment (you are the payee)

---

## Party Roles

### Contract Parties
- `ISSUER` - Entity that issued/created the obligation
- `COUNTERPARTY` - Other party to the contract
- `PAYER` - Entity making the payment
- `PAYEE` - Entity receiving the payment

### Swap Parties
- `INITIATOR` - Entity that created the swap
- `COUNTERPARTY` - Entity completing the swap

---

## Best Practices

### Idempotency Keys

Always use idempotency keys for mutations to prevent duplicate operations:
```bash
idempotencyKey: "unique-operation-$(date +%s)"
```

### Amount Format

Always use integer strings for amounts (no decimals):
- ✅ Correct: `"100"`, `"10"`, `"1000"`
- ❌ Incorrect: `"100.00"`, `10` (number), `"10.50"`

### Timestamp Format

Use ISO 8601 format for dates and timestamps:
- `"2025-11-01T00:00:00+00:00"` - Full timestamp
- `"2025-11-01"` - Simple date (system adds time)

### Entity vs Wallet ID

For destination/counterparty/obligor, you can use:
- Entity name/email: `"user@yieldfabric.com"`
- Direct wallet ID: `"WLT-USER-550e8400-e29b-41d4-a716-446655440000"`

Use entity names for simplicity, wallet IDs for precision.

### Null vs Empty

For obligor field:
- `"null"` (string) or omit for no specific obligor
- `"0x0000000000000000000000000000000000000000"` for zero address
- Entity name for specific obligor

---

## Rate Limits

(To be defined based on production deployment)

---

## Versioning

API versioning follows semantic versioning. Current version information included in response headers.

