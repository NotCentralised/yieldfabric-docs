# Contracts & Obligations

Guide to creating and querying payment obligations and contracts.

---

## Get Contracts by Entity

Get all contracts for a specific entity:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetEntityContracts($entityId: ID!) { contractFlow { coreContracts { byEntityId(entityId: $entityId) { id name description status contractType manager { id name } currency startDate expiryDate createdAt parties { id entity { id name } role } payments { id amount assetId paymentType status dueDate token { chainId address id } payee { entity { id name } wallet { id name } token { chainId address id } } payer { entity { id name } wallet { id name } token { chainId address id } } description } } } } }",
    "variables": {
      "entityId": "2cee226b-f69a-4385-bb2c-22ecc61eedcc"
    }
  }'
```

**Response (showing 2 contracts):**
```json
{
  "data": {
    "contractFlow": {
      "coreContracts": {
        "byEntityId": [
          {
            "id": "CONTRACT-DEPOSIT-1760931346780",
            "name": "DEPOSIT Contract - 2025-10-20 03:35:46",
            "description": "DEPOSIT contract for 225 tokens to account 0x207bbca7acd050e67e311a45175a8cb0cb0b7396",
            "status": "COMPLETED",
            "contractType": "OTHER",
            "manager": {
              "id": "2cee226b-f69a-4385-bb2c-22ecc61eedcc",
              "name": "issuer@yieldfabric.com"
            },
            "currency": "aud-token-asset",
            "startDate": "2025-10-20T03:35:46.791638611+00:00",
            "expiryDate": "2025-10-21T03:35:46.791638667+00:00",
            "createdAt": "2025-10-20T03:48:05.002844319+00:00",
            "parties": [
              {
                "id": "CONTRACT-DEPOSIT-1760931346780-2cee226b-f69a-4385-bb2c-22ecc61eedcc",
                "entity": {
                  "id": "2cee226b-f69a-4385-bb2c-22ecc61eedcc",
                  "name": "issuer@yieldfabric.com"
                },
                "role": "ISSUER"
              }
            ],
            "payments": [
              {
                "id": "PAY-DEPOSIT-1760931347129",
                "amount": 225,
                "assetId": "aud-token-asset",
                "paymentType": "PAYABLE",
                "status": "COMPLETED",
                "dueDate": "2025-10-20T03:48:04.756700864+00:00",
                "description": "DEPOSIT of 225 to account 0x207bbca7acd050e67e311a45175a8cb0cb0b7396"
              }
            ]
          },
          {
            "id": "CONTRACT-OBLIGATION-1760932171982",
            "name": "Annuity Stream",
            "description": "Annuity Stream Obligation",
            "status": "ACTIVE",
            "contractType": "OTHER",
            "manager": {
              "id": "2cee226b-f69a-4385-bb2c-22ecc61eedcc",
              "name": "issuer@yieldfabric.com"
            },
            "currency": "aud-token-asset",
            "startDate": "2025-10-20T03:49:31.982912978+00:00",
            "expiryDate": "2025-11-01T23:59:59+00:00",
            "createdAt": "2025-10-20T03:51:21.338337113+00:00",
            "parties": [
              {
                "entity": {
                  "id": "2cee226b-f69a-4385-bb2c-22ecc61eedcc",
                  "name": "issuer@yieldfabric.com"
                },
                "role": "COUNTERPARTY"
              },
              {
                "entity": {
                  "id": "2b5c7a69-5c2c-44f3-b621-6c0438d679be",
                  "name": "counterpart@yieldfabric.com"
                },
                "role": "ISSUER"
              }
            ],
            "payments": [
              {
                "id": "PAY-INITIAL-CONTRACT-OBLIGATION-1760932171982-0",
                "amount": 5,
                "assetId": "aud-token-asset",
                "paymentType": "PAYABLE",
                "status": "PROCESSING",
                "dueDate": "2025-11-01T00:00:00+00:00",
                "description": "Initial payment 1 for contract CONTRACT-OBLIGATION-1760932171982"
              }
            ]
          }
        ]
      }
    }
  }
}
```

**Contract Types:**
- **DEPOSIT**: Completed deposit contract
- **OBLIGATION**: Active annuity stream with scheduled payments
- **INSTANT**: Instant payment contracts
- **SWAP_PAYMENT**: Swap-related payment contracts

**Key Fields:**
- **`status`**: `COMPLETED`, `ACTIVE`, `PENDING`
- **`contractType`**: Type classification
- **`manager`**: Entity managing the contract
- **`parties`**: Entities involved with roles (`ISSUER`, `COUNTERPARTY`, `PAYER`, `PAYEE`)
- **`payments`**: Associated payments with:
  - `paymentType`: `PAYABLE` (outgoing) or `RECEIVABLE` (incoming)
  - `status`: `COMPLETED`, `PROCESSING`, `PENDING`
  - `token`: On-chain data when completed, `null` when pending

---

## Create Contract/Obligation

Create a new payment obligation:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { createObligation(input: { counterpart: \"counterpart@yieldfabric.com\", denomination: \"aud-token-asset\", obligor: \"issuer@yieldfabric.com\", notional: \"100\", expiry: \"2025-11-01T23:59:59+00:00\", idempotencyKey: \"unique-key-123\" }) { success message accountAddress obligationResult messageId contractId transactionId signature timestamp idHash } }"
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

**Required Input:**
- `denomination`: Asset ID (e.g., `"aud-token-asset"`)
- `counterpart`: Entity name/email of the counterparty (or use `counterpartWalletId` for direct wallet ID)

**Optional Input:**
- `obligor`: Entity name/email of the obligor (or use `obligorWalletId` for direct wallet ID)
- `obligationAddress`: Specific obligation address (if not provided, uses your account address)
- `notional`: Total notional value of the obligation
- `expiry`: Expiry date in ISO 8601 format
- `data`: Custom JSON data for the contract
- `initialPayments`: Initial payment structure with amount and payment details
- `idempotencyKey`: Unique key for duplicate prevention

---

## Create Obligation with Initial Payments

Create an obligation with scheduled payments (annuity stream):

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($initialPayments: InitialPaymentsInput, $data: JSON) { createObligation(input: { counterpart: \"issuer@yieldfabric.com\", denomination: \"aud-token-asset\", obligor: \"issuer@yieldfabric.com\", notional: \"5\", expiry: \"2025-11-01\", data: $data, initialPayments: $initialPayments }) { success contractId messageId } }",
    "variables": {
      "data": { "name": "Annuity Stream", "description": "Annuity Stream Obligation" },
      "initialPayments": {
        "amount": "5",
        "payments": [
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-01T00:00:00+00:00", "unlockReceiver": "2025-11-01T00:00:00+00:00" },
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-02T00:00:00+00:00", "unlockReceiver": "2025-11-02T00:00:00+00:00" },
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-03T00:00:00+00:00", "unlockReceiver": "2025-11-03T00:00:00+00:00" },
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-04T00:00:00+00:00", "unlockReceiver": "2025-11-04T00:00:00+00:00" },
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-05T00:00:00+00:00", "unlockReceiver": "2025-11-05T00:00:00+00:00" }
        ]
      }
    }
  }'
```

This creates a 5-day annuity stream with payments unlocking on Nov 1-5, 2025.

**InitialPayments Structure:**
- `amount`: Total amount to be paid across all payments
- `payments`: Array of payment schedules, each with:
  - `unlockSender`/`unlockReceiver`: ISO 8601 timestamp for time locks
  - Oracle fields for conditional release (set to "0" or null for unconditional)

---

## Accept Obligation

Accept a pending obligation (commits you to the payment schedule):

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { acceptObligation(input: { contractId: \"CONTRACT-OBLIGATION-1760932171982\" }) { success message obligationId messageId } }"
  }'
```

---

## Self-Referential Obligations

Create obligations with yourself as both obligor and counterparty:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($initialPayments: InitialPaymentsInput, $data: JSON) { createObligation(input: { counterpart: \"issuer@yieldfabric.com\", denomination: \"aud-token-asset\", obligor: \"issuer@yieldfabric.com\", notional: \"100\", expiry: \"2025-11-01\", data: $data, initialPayments: $initialPayments }) { success contractId } }",
    "variables": {
      "data": { "name": "Redemption", "description": "Redemption Obligation" },
      "initialPayments": {
        "amount": "100",
        "payments": [
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": "2025-11-06T00:00:00+00:00", "unlockReceiver": "2025-11-06T00:00:00+00:00" }
        ]
      }
    }
  }'
```

**Why Self-Referential?**
- Build complex structures without counterparty risk
- Lock the structure by accepting your own obligation
- Atomically transfer to actual counterparty via swap
- Ensures secure construction and settlement

---

## Contract Lifecycle

1. **Create**: Define obligation with counterpart, obligor, and payment schedule
2. **Accept**: Counterpart (or self) accepts the obligation
3. **Execute**: Payments unlock based on time locks or oracle triggers
4. **Transfer**: Ownership can be transferred via atomic swaps
5. **Settle**: Complete when all payments are fulfilled

