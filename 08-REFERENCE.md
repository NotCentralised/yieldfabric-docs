# API Reference

Quick reference guide for common values, error codes, endpoints, and input types.

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

- `aud-token-asset` — Australian Dollars
- `usd-token-asset` — US Dollars

Asset IDs are deployment-specific. Contact your administrator for the full list of configured denominations.

---

## Chain IDs Reference

- `151` — Redbelly Mainnet (Governors)
- `153` — Redbelly Testnet (Governors)

---

## Common Headers

All authenticated requests require:

```bash
-H "Authorization: Bearer $TOKEN"
-H "Content-Type: application/json"
```

---

## Auth Service Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Login |
| `POST` | `/auth/login/with-services` | Login with service selection |
| `POST` | `/auth/refresh` | Refresh access token |
| `GET`  | `/auth/users/me` | Get user profile |
| `POST` | `/auth/logout` | Logout current device |
| `POST` | `/auth/logout-all` | Logout all devices |
| `POST` | `/auth/users` | Create user |

### Account Deployment

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/users/:user_id/deploy-account` | Deploy user account |
| `POST` | `/auth/deploy-account` | Deploy entity account (parameterised) |

### User Permissions

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/auth/users/:user_id/permissions` | List permissions |
| `POST` | `/auth/users/:user_id/permissions` | Grant permissions |
| `PUT`  | `/auth/users/:user_id/permissions` | Replace permissions |
| `DELETE` | `/auth/users/:user_id/permissions` | Revoke permissions |
| `GET`  | `/auth/users/:user_id/permissions/:permission` | Check permission |
| `POST` | `/auth/users/:user_id/permissions/:permission` | Grant single permission |
| `DELETE` | `/auth/users/:user_id/permissions/:permission` | Revoke single permission |

### Groups

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/groups` | Create group |
| `GET`  | `/auth/groups` | List groups |
| `GET`  | `/auth/groups/user` | List user's groups |
| `GET`  | `/auth/groups/:id` | Get group |
| `PUT`  | `/auth/groups/:id` | Update group |
| `DELETE` | `/auth/groups/:id` | Delete group |
| `POST` | `/auth/groups/:id/members` | Add member |
| `GET`  | `/auth/groups/:id/members` | List members |
| `PUT`  | `/auth/groups/:id/members/:user_id` | Update member role |
| `DELETE` | `/auth/groups/:id/members/:user_id` | Remove member |
| `POST` | `/auth/groups/:id/entity-scope` | Add entity scope |
| `GET`  | `/auth/groups/:id/entity-scope` | List entity scope |
| `GET`  | `/auth/groups/:id/audit-logs` | Audit logs |
| `POST` | `/auth/groups/:id/keypairs` | Create group keypair |

### Delegation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/delegation/jwt` | Create delegation JWT |
| `POST` | `/auth/delegation/tokens` | Create delegation token |
| `GET`  | `/auth/delegation/tokens` | List user delegations |
| `DELETE` | `/auth/delegation/tokens/:id` | Revoke delegation token |

### API Key & Signature Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/api-key` | Authenticate with API key |
| `POST` | `/auth/api-key/generate` | Generate API key |
| `GET`  | `/auth/api-keys` | List API keys |
| `GET`  | `/auth/api-keys/:key_id` | Get API key |
| `POST` | `/auth/api-keys/:key_id/revoke` | Revoke API key |
| `POST` | `/auth/signature` | Authenticate with signature |
| `POST` | `/auth/signature/register` | Register signature key |
| `GET`  | `/auth/signature/keys` | List signature keys |
| `GET`  | `/auth/signature/keys/:key_id` | Get signature key |
| `DELETE` | `/auth/signature/keys/:key_id` | Delete signature key |

### MCP Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/mcp/login` | MCP login |
| `POST` | `/auth/mcp/generate-token` | Generate MCP token |
| `GET`  | `/mcp/login` | MCP login form |

### Key Management (`/keys/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/keys/` | Create key pair |
| `POST` | `/keys/external` | Register external key |
| `POST` | `/keys/external/verify-ownership` | Verify external key ownership |
| `GET`  | `/keys/:key_id` | Get key pair |
| `PUT`  | `/keys/:key_id` | Update key pair |
| `DELETE` | `/keys/:key_id` | Delete key pair |
| `POST` | `/keys/:key_id/rotate` | Rotate key pair |
| `GET`  | `/keys/:key_id/wallet-status` | Check wallet registration |
| `POST` | `/keys/register-with-wallet` | Register key with wallet |
| `POST` | `/keys/register-with-specific-wallet` | Register key with specific wallet |
| `GET`  | `/keys/users/:user_id/keys` | Get user key pairs |
| `GET`  | `/keys/users/:user_id/default-key` | Get default key pair |
| `GET`  | `/keys/logs` | Key operation logs |
| `GET`  | `/keys/providers/health` | Provider health check |

### Cryptographic Operations (`/api/v1/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/encrypt` | Encrypt data |
| `POST` | `/api/v1/decrypt` | Decrypt data |
| `POST` | `/api/v1/sign` | Sign data |
| `POST` | `/api/v1/verify` | Verify signature |
| `GET`  | `/api/v1/keys/:key_id/info` | Get key info |
| `GET`  | `/api/v1/public-key/:contact_id` | Get contact public key |
| `POST` | `/api/v1/generate-keypair` | Generate keypair for contact |
| `POST` | `/api/v1/vault/decrypt` | Vault decrypt (internal) |
| `POST` | `/api/v1/vault/sign` | Vault sign (internal) |

### Connections (`/auth/connections/*`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/connections/request` | Create connection request |
| `GET`  | `/auth/connections/requests` | List connection requests |
| `GET`  | `/auth/connections/requests/:id` | Get connection request |
| `POST` | `/auth/connections/requests/:id/accept` | Accept request |
| `POST` | `/auth/connections/requests/:id/reject` | Reject request |
| `POST` | `/auth/connections/requests/:id/block` | Block request |
| `POST` | `/auth/connections/requests/:id/preferences` | Set sharing preferences |
| `GET`  | `/auth/connections/requests/:id/preferences` | Get sharing preferences |
| `POST` | `/auth/connections/invite` | Create invitation |
| `GET`  | `/auth/connections/invitations` | List sent invitations |
| `GET`  | `/auth/connections/invitations/received` | List received invitations |
| `GET`  | `/auth/connections/invitations/:token` | Get invitation |
| `POST` | `/auth/connections/invitations/:token/accept` | Accept invitation |
| `DELETE` | `/auth/connections/invitations/:id/cancel` | Cancel invitation |

---

## Payments Service Endpoints

### REST

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/balance?denomination={asset}&obligor={obligor}&group_id={group_id}` | Get balance |

### Balance Query Parameters

- `denomination` (required): Asset ID (e.g., `aud-token-asset`)
- `obligor` (optional): Obligor entity name/address or `null` for general balance
- `group_id` (optional): Group ID for delegation queries
- `wallet_address` (optional): Specific wallet address to query

### GraphQL Endpoint

`POST /graphql`

---

## GraphQL Queries

Queries are organized into flow-based namespaces:

| Namespace | Description |
|-----------|-------------|
| `paymentFlow` | Payment queries |
| `contractFlow` | Contract/obligation queries |
| `swapFlow` | Swap queries |
| `swapIntentFlow` | Swap intent queries |
| `loanFlow` | Loan queries |
| `tokenFlow` | Token queries |
| `assetFlow` | Asset queries |
| `composedFlow` | Composed operation queries |
| `walletFlow` | Wallet queries |
| `fiatAccountFlow` | Fiat account queries |

**Direct queries** (top-level shortcuts):

| Query | Description |
|-------|-------------|
| `entities(queryType)` | List entities |
| `tokens` | Token queries |
| `wallets` | Wallet queries |
| `payments` | Payment queries |
| `contractsCore` | Contract queries |
| `loansCore` | Loan queries |
| `assets` | Asset queries |
| `transactions` | Transaction queries |
| `contracts` | All contracts for current entity |
| `paymentsByEntity` | All payments for current entity |
| `paymentsByEntityDashboard` | Dashboard payment view |
| `walletsByIds(ids)` | Wallets by ID list |
| `entityWallets` | All wallets for current entity |
| `wallet(id)` | Single wallet by ID |
| `loans` | All loans for current entity |
| `health` | Health check |

### Flow-Based Query Examples

```graphql
query {
  contractFlow {
    coreContracts {
      byEntityId { id status denomination }
    }
  }
}
```

```graphql
query {
  swapFlow {
    coreSwaps {
      byEntityId { swapId status deadline }
    }
  }
}
```

---

## GraphQL Mutations

Mutations are organized into flow namespaces and also exposed as top-level shortcuts:

### Payment Mutations

| Mutation | Description |
|----------|-------------|
| `deposit(input)` | Deposit funds into intelligent account |
| `instant(input)` | Send instant payment (cash or credit) |
| `accept(input)` | Accept incoming payment (or cancel/retrieve) |
| `acceptAll(input)` | Batch-accept all pending payables for a denomination |
| `withdraw(input)` | Withdraw funds from intelligent account |
| `createDistribution(input)` | Create one-to-many distribution |
| `hidePayment(input)` | Hide a payment from view (soft delete) |

### Contract Mutations

| Mutation | Description |
|----------|-------------|
| `createObligation(input)` | Create payment obligation |
| `acceptObligation(input)` | Accept obligation |
| `transferObligation(input)` | Transfer obligation to new holder |
| `cancelObligation(input)` | Cancel obligation |
| `hideContract(input)` | Hide a contract from view |

### Swap Mutations

| Mutation | Description |
|----------|-------------|
| `createSwap(input)` | Create swap (atomic or repo) |
| `completeSwap(input)` | Complete/execute swap |
| `cancelSwap(input)` | Cancel swap |
| `repurchaseSwap(input)` | Repurchase collateral from repo swap |
| `swapObligorPayment(input)` | Swap obligor payment for non-obligor |
| `expireCollateral(input)` | Forfeit collateral after expiry |

### Repo Rolling Mutations

| Mutation | Description |
|----------|-------------|
| `initiateRoll(input)` | Initiate two-step roll (creates new swap) |
| `completeRoll(input)` | Complete a pending roll |

### Loan Mutations

| Mutation | Description |
|----------|-------------|
| `createLoan(input)` | Create a loan |
| `updateLoan(input)` | Update loan terms |
| `acceptLoan(input)` | Accept a loan |
| `processLoan(input)` | Process loan payment |

### Composed Mutations

| Mutation | Description |
|----------|-------------|
| `executeComposedOperations(input)` | Execute multiple operations atomically |

### Flow Namespaces (Nested)

Mutations can also be accessed via their flow namespace:

```graphql
mutation {
  paymentFlow { deposit(input: { ... }) { success message } }
}
```

```graphql
mutation {
  swapFlow { createSwap(input: { ... }) { success swapId } }
}
```

---

## GraphQL Input Types

### DepositInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assetId` | String | Yes | Asset/denomination ID |
| `amount` | String | Yes | Integer string |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet to deposit into |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### WithdrawInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assetId` | String | Yes | Asset/denomination ID |
| `amount` | String | Yes | Integer string |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet to withdraw from |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### InstantSendInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assetId` | String | Yes | Asset/denomination ID |
| `amount` | String | Yes | Integer string |
| `destinationId` | String | No | Entity name/email (one of `destinationId`, `destinationWalletId`, or `contractId` required) |
| `destinationWalletId` | String | No | Direct wallet ID |
| `contractId` | String | No | Existing contract ID — sends to this contract |
| `obligor` | String | No | Obligor entity name/ID (defaults to sender) |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Sender wallet to use |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### AcceptInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `paymentId` | String | Yes | Payment hash/ID |
| `amount` | String | No | Partial retrieval amount (omit for full) |
| `walletId` | String | No | Wallet to accept with |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### AcceptAllInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `denomination` | String | Yes | Asset ID filter |
| `obligor` | String | No | Obligor entity filter |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet scope — only accept payables for this wallet |

### CreateDistributionInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assetId` | String | Yes | Asset/denomination ID |
| `obligor` | String | No | Obligor entity (defaults to sender) |
| `recipients` | [CreateDistributionRecipientInput] | Yes | List of recipients |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Sender wallet to use |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

**CreateDistributionRecipientInput:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | String | Yes | Recipient wallet address |
| `obligationId` | String | No | NFT token ID (`"0"` or omit for wallet; non-zero = NFT claimant via `ownerOf`) |
| `amount` | String | Yes | Raw amount (integer string) |

### HidePaymentInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `paymentId` | String | Yes | Payment ID to hide |

### CreateObligationInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `counterpart` | String | No | Entity name/email (or use `counterpartWalletId`) |
| `counterpartWalletId` | String | No | Direct wallet ID |
| `obligationAddress` | String | No | On-chain obligation address |
| `denomination` | String | No | Required when `initialPayments` present |
| `obligor` | String | No | Entity name/email (or use `obligorWalletId`) |
| `obligorWalletId` | String | No | Direct wallet ID |
| `notional` | String | No | Notional value |
| `expiry` | String | No | ISO 8601 date |
| `data` | JSON | No | Custom contract metadata |
| `initialPayments` | InitialPaymentsInput | No | Scheduled payments |
| `contractId` | String | No | Custom ID (auto-generated if omitted) |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### TransferObligationInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contractId` | String | No | Legacy — contract ID |
| `contractReference` | ContractReference | No | Unified reference (single or composed) |
| `destinationId` | String | No | Entity name/email |
| `destinationWalletId` | String | No | Direct wallet ID |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### CancelObligationInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contractId` | String | No | Legacy — contract ID |
| `contractReference` | ContractReference | No | Unified reference (single or composed) |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### ContractReference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `contractId` | String | No | Single contract ID (mutually exclusive with `composedContractId`) |
| `composedContractId` | String | No | Composed contract ID |

### InitialPaymentsInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | String | Yes | Total amount across all payments |
| `denomination` | String | No | Asset ID |
| `obligor` | String | No | Obligor entity |
| `payments` | [VaultPaymentInput] | Yes | Individual payment conditions |

### VaultPaymentInput

Defines conditions for a single payment within an obligation or swap:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `oracleAddress` | String | No | Oracle contract address |
| `oracleOwner` | String | No | Oracle owner address |
| `oracleKeySender` | String | No | Oracle key for sender condition |
| `oracleValueSender` | String | No | Oracle value for sender condition |
| `oracleValueSenderSecret` | String | No | Secret for sender oracle value |
| `oracleKeyRecipient` | String | No | Oracle key for recipient condition |
| `oracleValueRecipient` | String | No | Oracle value for recipient condition |
| `oracleValueRecipientSecret` | String | No | Secret for recipient oracle value |
| `unlockSender` | String | No | ISO 8601 — earliest sender can retrieve |
| `unlockReceiver` | String | No | ISO 8601 — earliest recipient can accept |
| `linearVesting` | Boolean | No | Enable linear vesting over the lock period |

### CreateSwapInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `swapId` | String | Yes | Unique swap identifier |
| `counterparty` | String | Yes | Counterparty entity name/email |
| `counterpartyWalletId` | String | No | Direct wallet ID |
| `deadline` | String | Yes | ISO 8601 deadline |
| `initiatorObligationIds` | [String] | No | Legacy — contract IDs from initiator |
| `initiatorContractReferences` | [ContractReference] | No | Unified contract references for initiator |
| `initiatorExpectedPayments` | InitialPaymentsInput | No | Expected payments from initiator |
| `counterpartyObligationIds` | [String] | No | Legacy — contract IDs from counterparty |
| `counterpartyContractReferences` | [ContractReference] | No | Unified contract references for counterparty |
| `counterpartyExpectedPayments` | InitialPaymentsInput | No | Expected payments from counterparty |
| `initiatorCollateralObligationIds` | [String] | No | Legacy — collateral contract IDs |
| `initiatorCollateralContractReferences` | [ContractReference] | No | Unified collateral references |
| `initiatorCollateralPayments` | InitialPaymentsInput | No | Collateral payment conditions |
| `idempotencyKey` | String | No | Prevents duplicate operations |

### CompleteSwapInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `swapId` | String | Yes | Swap to complete |
| `counterpartyCollateralObligationIds` | [String] | No | Counterparty collateral contract IDs |
| `counterpartyCollateralPayments` | InitialPaymentsInput | No | Counterparty collateral conditions |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet to use |
| `counterpartyWalletId` | String | No | Override counterparty wallet |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### CancelSwapInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `swapId` | String | Yes | Swap to cancel |
| `key` | String | Yes | Oracle key |
| `value` | String | Yes | Oracle value |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet to use |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### RepurchaseSwapInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `swapId` | String | Yes | Repo swap to repurchase |
| `repurchaseObligationIds` | [String] | No | Legacy — repurchase contract IDs |
| `repurchaseContractReferences` | [ContractReference] | No | Unified repurchase references |
| `repurchasePaymentIds` | [String] | No | Payment IDs for repurchase |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### SwapObligorPaymentInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `denomination` | String | Yes | Asset ID |
| `amount` | String | Yes | Integer string |
| `obligor` | String | Yes | Entity name or ID |
| `deadline` | String | No | ISO 8601 (defaults to 30 days) |
| `idempotencyKey` | String | No | Prevents duplicate operations |

### ExpireCollateralInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `swapId` | String | Yes | Swap with expired collateral |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

### RollRepoInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `oldSwapId` | String | Yes | Existing repo swap to roll |
| `newSwapId` | String | Yes | ID for the new swap |
| `newCounterparty` | String | Yes | New counterparty entity |
| `newCounterpartyWalletId` | String | No | Direct wallet ID |
| `newDeadline` | String | Yes | ISO 8601 deadline for new swap |
| `newExpiry` | String | No | Collateral expiry |
| `newCounterpartyExpectedPayments` | InitialPaymentsInput | No | New counterparty payments |
| `newInitiatorExpectedPayments` | InitialPaymentsInput | No | Upfront initiator payments |
| `newInitiatorRepurchasePayments` | InitialPaymentsInput | No | New repurchase terms (initiator) |
| `newCounterpartyRepurchasePayments` | InitialPaymentsInput | No | New repurchase terms (counterparty) |
| `repurchaseObligationIds` | [String] | No | Legacy — repurchase contract IDs |
| `repurchaseContractReferences` | [ContractReference] | No | Unified repurchase references |
| `repurchasePaymentIds` | [String] | No | Payment IDs for repurchase |
| `idempotencyKey` | String | No | Prevents duplicate operations |

### CompleteRollInput

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `newSwapId` | String | Yes | Pending roll swap to complete |
| `idempotencyKey` | String | No | Prevents duplicate operations |
| `walletId` | String | No | Wallet to use |
| `requireManualSignature` | Boolean | No | Route to manual signing UX |

---

## Status Values

### Contract Status

| Status | Description |
|--------|-------------|
| `DRAFT` | Contract drafted, not yet submitted |
| `PENDING` | Awaiting counterparty acceptance |
| `ACTIVE` | Contract is active |
| `COMPLETED` | All obligations fulfilled |
| `SUSPENDED` | Temporarily suspended |
| `TERMINATED` | Terminated early |
| `EXPIRED` | Contract past expiry date |
| `CANCELLED` | Contract cancelled |
| `OVERDUE` | Payment overdue |

### Contract Party Status

| Status | Description |
|--------|-------------|
| `PENDING` | Party awaiting action |
| `ACTIVE` | Party is active |
| `SUSPENDED` | Party suspended |
| `COMPLETED` | Party completed obligations |
| `TERMINATED` | Party terminated |
| `EXPIRED` | Party expired |
| `CANCELLED` | Party cancelled |
| `OVERDUE` | Party overdue |

### Payment Status

| Status | Description |
|--------|-------------|
| `PENDING` | Payment awaiting action |
| `SCHEDULED` | Payment scheduled for future execution |
| `PROCESSING` | Payment being executed |
| `COMPLETED` | Payment finalized on-chain |
| `PAID` | Payment confirmed paid |
| `OVERDUE` | Payment past due date |
| `FAILED` | Payment execution failed |
| `CANCELLED` | Payment cancelled |

### Swap Status

| Status | Description |
|--------|-------------|
| `PENDING` | Awaiting counterparty action |
| `ACTIVE` | Swap created, not yet completed |
| `COMPLETED` | Swap executed successfully |
| `CANCELLED` | Swap cancelled |
| `EXPIRED` | Swap past deadline |
| `FORFEITED` | Collateral forfeited after expiry |
| `REPURCHASED` | Collateral repurchased by initiator |

---

## Payment Direction

Payments have a direction relative to the current user:

| Direction | Description |
|-----------|-------------|
| `PAYABLE` | Outgoing payment (you are the payer) |
| `RECEIVABLE` | Incoming payment (you are the payee) |

---

## Party Roles

### Contract Parties

| Role | Description |
|------|-------------|
| `HOLDER` | Entity that holds/created the obligation |
| `COUNTERPARTY` | Other party to the contract |
| `RECIPIENT` | Designated recipient |
| `GUARANTOR` | Guarantor of the obligation |
| `BENEFICIARY` | Beneficiary of the contract |
| `PAYER` | Entity making the payment |
| `PAYEE` | Entity receiving the payment |
| `INITIATOR` | Entity that initiated the contract |

### Swap Parties

| Role | Description |
|------|-------------|
| `INITIATOR` | Entity that created the swap |
| `COUNTERPARTY` | Entity completing the swap |

---

## Best Practices

### Idempotency Keys

Always use idempotency keys for mutations to prevent duplicate operations:
```bash
idempotencyKey: "unique-operation-$(date +%s)"
```

### Amount Format

Always use integer strings for amounts (no decimals):
- Correct: `"100"`, `"10"`, `"1000"`
- Incorrect: `"100.00"`, `10` (number), `"10.50"`

### Timestamp Format

Use ISO 8601 format for dates and timestamps:
- `"2025-11-01T00:00:00+00:00"` — Full timestamp
- `"2025-11-01"` — Simple date (system adds time)

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

### Manual Signature

Set `requireManualSignature: true` to route the transaction through the manual signing UX instead of automatic execution. This is useful when the user needs to review and approve a transaction before it is submitted.

---

## Rate Limits

(To be defined based on production deployment)

---

## Versioning

API versioning follows semantic versioning. Current version information included in response headers.
