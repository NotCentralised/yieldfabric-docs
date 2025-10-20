# Payments Guide

Guide to querying, sending, and accepting payments.

---

## Get Payments by Entity

Fetch all payments for an entity:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetTransactions($currentEntityId: ID) { paymentsByEntity(currentEntityId: $currentEntityId) { id amount assetId asset { id name assetType currency } paymentType status dueDate unlockSender unlockReceiver description contractId createdAt token { chainId address id } payee { entity { id name } wallet { id name } token { chainId address id } } payer { entity { id name } wallet { id name } token { chainId address id } } } }",
    "variables": {
      "currentEntityId": "2cee226b-f69a-4385-bb2c-22ecc61eedcc"
    }
  }'
```

**Response (showing 3 payment types):**
```json
{
  "paymentsByEntity": [
    {
      "id": "PAY-DEPOSIT-1760931347129",
      "amount": 225,
      "assetId": "aud-token-asset",
      "asset": {
        "id": "aud-token-asset",
        "name": "AUD Token",
        "assetType": "CASH",
        "currency": "AUD"
      },
      "paymentType": "PAYABLE",
      "status": "COMPLETED",
      "dueDate": "2025-10-20T03:48:04.756700864+00:00",
      "unlockSender": null,
      "unlockReceiver": null,
      "description": "DEPOSIT of 225 to account 0x207bbca7acd050e67e311a45175a8cb0cb0b7396",
      "contractId": "CONTRACT-DEPOSIT-1760931346780",
      "createdAt": "2025-10-20T03:48:04.771157268+00:00",
      "token": null
    },
    {
      "id": "PAY-INITIAL-CONTRACT-OBLIGATION-1760932171982-0",
      "amount": 5,
      "assetId": "aud-token-asset",
      "paymentType": "PAYABLE",
      "status": "PROCESSING",
      "dueDate": "2025-11-01T00:00:00+00:00",
      "unlockSender": "2025-11-01T00:00:00+00:00",
      "unlockReceiver": "2025-11-01T00:00:00+00:00",
      "description": "Initial payment 1 for contract CONTRACT-OBLIGATION-1760932171982",
      "contractId": "CONTRACT-OBLIGATION-1760932171982",
      "createdAt": "2025-10-20T03:51:21.985640137+00:00",
      "token": null
    },
    {
      "id": "PAY-INSTANT-1760932133588",
      "amount": 100,
      "assetId": "aud-token-asset",
      "paymentType": "PAYABLE",
      "status": "COMPLETED",
      "dueDate": "2025-10-20T03:49:03.807744427+00:00",
      "unlockSender": null,
      "unlockReceiver": null,
      "description": "Send payment from 0x207bbca7acd050e67e311a45175a8cb0cb0b7396 to 0xfbc4e5c907bc67c7f47393b8082ce05b0111fb19",
      "contractId": "CONTRACT-INSTANT-1760932133267",
      "createdAt": "2025-10-20T03:49:21.791216299+00:00",
      "token": {
        "chainId": "153",
        "address": "0x373a54221cc0f483757f527a4f586ff2b804833f8afbecbfc22476a5806dd0dc",
        "id": "PAY-INSTANT-1760932133588-payment-token"
      }
    }
  ]
}
```

**Payment Types:**
- **DEPOSIT**: Completed deposit payment (no time locks)
- **OBLIGATION**: Scheduled obligation payment with time locks
- **INSTANT**: Instant payment with on-chain token data
- **SWAP_PAYMENT**: Payment created during swap settlement

**Key Fields:**
- **`paymentType`**: 
  - `PAYABLE` = Outgoing payment (you are the payer)
  - `RECEIVABLE` = Incoming payment (you are the payee)
- **`status`**: 
  - `COMPLETED` = Payment finalized on-chain
  - `PROCESSING` = Payment scheduled/pending execution
- **`unlockSender`/`unlockReceiver`**: Time lock dates (ISO 8601), `null` = no time lock
- **`token`**: On-chain token data (populated when `COMPLETED`, `null` when `PROCESSING`)
- **`asset`**: Asset metadata (name, type, currency)
- **`contractId`**: Associated contract for tracking

---

## Create Instant Payment

Send an instant payment to another entity:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { instant(input: { assetId: \"aud-token-asset\", amount: \"10\", destinationId: \"counterpart@yieldfabric.com\", idempotencyKey: \"instant-payment-001\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
  }'
```

**Alternative with destination wallet ID:**
```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { instant(input: { assetId: \"aud-token-asset\", amount: \"10\", destinationWalletId: \"wallet-id-here\", idempotencyKey: \"instant-payment-002\" }) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
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

## Accept Payment

Accept a pending payment:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { accept(input: { paymentId: \"PAY-INSTANT-1759048183145\", idempotencyKey: \"accept-payment-001\" }) { success message accountAddress idHash acceptResult messageId timestamp } }"
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
      "timestamp": "2025-10-19T12:00:00Z"
    }
  }
}
```

**Required Input:**
- `paymentId`: The payment ID to accept (use `id_hash` from balance locked_in transactions)
- `idempotencyKey`: Unique key to prevent duplicate accepts (optional)

---

## Payment Lifecycle

1. **Create**: Sender creates payment (instant or scheduled)
2. **Lock**: Payment locked in sender's account
3. **Notify**: Recipient sees payment in `locked_in` array
4. **Accept**: Recipient accepts payment
5. **Settle**: Funds transfer to recipient's account
6. **Complete**: Payment marked as completed on-chain

