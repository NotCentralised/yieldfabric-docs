# Atomic Swaps Guide

Guide to creating and executing atomic swaps for bilateral obligation trading.

---

## Get Swaps by Entity

Query all swaps for a specific entity:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetSwaps($entityId: ID!) { swapFlow { coreSwaps { byEntityId(entityId: $entityId) { id swapId swapType status deadline createdAt parties { id entity { id name } role } initiatorObligationIds counterpartyObligationIds paymentIds payments { id amount assetId paymentType status dueDate unlockSender unlockReceiver description contractId createdAt asset { id name assetType currency } token { chainId address id } payee { entity { id name } wallet { id name } token { chainId address id } } payer { entity { id name } wallet { id name } token { chainId address id } } } } } } }",
    "variables": {
      "entityId": "2cee226b-f69a-4385-bb2c-22ecc61eedcc"
    }
  }'
```

**Response:**
```json
{
  "data": {
    "swapFlow": {
      "coreSwaps": {
        "byEntityId": [
          {
            "id": "123456789",
            "swapId": "123456789",
            "swapType": "CONFIGURABLE",
            "status": "COMPLETED",
            "deadline": "2025-11-10T23:59:59+00:00",
            "createdAt": "2025-10-20T03:51:25.797693681+00:00",
            "parties": [
              {
                "entity": {
                  "id": "2cee226b-f69a-4385-bb2c-22ecc61eedcc",
                  "name": "issuer@yieldfabric.com"
                },
                "role": "INITIATOR"
              },
              {
                "entity": {
                  "id": "2b5c7a69-5c2c-44f3-b621-6c0438d679be",
                  "name": "counterpart@yieldfabric.com"
                },
                "role": "COUNTERPARTY"
              }
            ],
            "initiatorObligationIds": [
              "CONTRACT-OBLIGATION-1760932171982",
              "CONTRACT-OBLIGATION-1760932212849"
            ],
            "counterpartyObligationIds": [],
            "paymentIds": [
              "PAY-SWAP-123456789-0-1760932285444"
            ],
            "payments": [
              {
                "id": "PAY-SWAP-123456789-0-1760932285444",
                "amount": 100,
                "assetId": "aud-token-asset",
                "paymentType": "RECEIVABLE",
                "status": "COMPLETED",
                "dueDate": "2025-10-20T03:51:25.467436455+00:00",
                "unlockSender": null,
                "unlockReceiver": null,
                "description": "SWAP_PAYMENT of 100 to account 0xfbc4e5c907bc67c7f47393b8082ce05b0111fb19",
                "contractId": "CONTRACT-SWAP_PAYMENT-1760932285124",
                "createdAt": "2025-10-20T03:51:25.486221774+00:00",
                "token": {
                  "chainId": "153",
                  "address": "0xe764F77fbCa499E29Ec2B58506fB21CbE4BC2916",
                  "id": "AUD-token"
                }
              }
            ]
          }
        ]
      }
    }
  }
}
```

**Swap Structure:**
- **`swapType`**: Type of swap (e.g., `CONFIGURABLE`)
- **`status`**: Current swap status (`COMPLETED`, `PENDING`, `ACTIVE`)
- **`deadline`**: Swap expiration date (ISO 8601)
- **`parties`**: Array of participants with roles:
  - `INITIATOR`: Entity that created the swap
  - `COUNTERPARTY`: Entity participating in the swap
- **`initiatorObligationIds`**: Contract IDs the initiator is offering
- **`counterpartyObligationIds`**: Contract IDs the counterparty is offering
- **`paymentIds`**: Payment IDs created during swap settlement
- **`payments`**: Full payment details for swap-related payments

**Example:**
This swap shows the initiator exchanged 2 obligations (worth 105 AUD total) for 100 AUD upfront payment.

---

## Create Atomic Swap

Create a swap to exchange obligations for payment:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation($counterpartyExpectedPayments: InitialPaymentsInput) { createSwap(input: { swapId: \"123456789\", counterparty: \"counterpart@yieldfabric.com\", deadline: \"2025-11-10\", initiatorObligationIds: [\"CONTRACT-OBLIGATION-1760932171982\", \"CONTRACT-OBLIGATION-1760932212849\"], counterpartyExpectedPayments: $counterpartyExpectedPayments }) { success message swapId messageId transactionId signature timestamp } }",
    "variables": {
      "counterpartyExpectedPayments": {
        "denomination": "aud-token-asset",
        "amount": "100",
        "payments": [
          { "oracleAddress": null, "oracleOwner": null, "oracleKeySender": "0", "oracleValueSenderSecret": "0", "oracleKeyRecipient": "0", "oracleValueRecipientSecret": "0", "unlockSender": null, "unlockReceiver": null }
        ]
      }
    }
  }'
```

**Response:**
```json
{
  "data": {
    "createSwap": {
      "success": true,
      "message": "Swap created successfully",
      "swapId": "123456789",
      "messageId": "msg-swap-123",
      "transactionId": "TXN-SWAP-123",
      "signature": "0xabc...",
      "timestamp": "2025-10-20T03:51:25.797693681+00:00"
    }
  }
}
```

**Required Input:**
- `swapId`: Unique identifier for the swap
- `counterparty`: Entity name/email of the counterparty (or use `counterpartyWalletId`)
- `deadline`: Swap expiration date in ISO 8601 format

**Optional Input:**
- `initiatorObligationIds`: Array of contract IDs the initiator is offering
- `counterpartyExpectedPayments`: Payment details expected from counterparty
- `idempotencyKey`: Unique key for duplicate prevention

---

## Complete Swap

Complete a swap by providing the required payment:

```bash
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { completeSwap(input: { swapId: \"123456789\" }) { success message swapId messageId transactionId signature timestamp } }"
  }'
```

**Response:**
```json
{
  "data": {
    "completeSwap": {
      "success": true,
      "message": "Swap completed successfully",
      "swapId": "123456789",
      "messageId": "msg-complete-123",
      "transactionId": "TXN-COMPLETE-123",
      "signature": "0xdef...",
      "timestamp": "2025-10-20T03:51:28.040236966+00:00"
    }
  }
}
```

**Required Input:**
- `swapId`: The swap ID to complete

**Optional Input:**
- `idempotencyKey`: Unique key for duplicate prevention

**Note:** The `completeSwap` mutation retrieves the expected payment details from the stored swap data, so you only need to provide the `swapId`.

---

## Swap Lifecycle

1. **Create Obligations**: Build obligation structures (can be self-referential)
2. **Accept Obligations**: Lock the structures ready for exchange
3. **Create Swap**: Initiator proposes swap with obligation IDs and expected payment
4. **Review**: Counterparty reviews swap terms
5. **Complete**: Counterparty executes swap by providing payment
6. **Atomic Settlement**: 
   - Obligations transfer to counterparty
   - Payment transfers to initiator
   - Both happen simultaneously or not at all

---

## Atomic Settlement Guarantees

**All-or-Nothing Execution:**
- If counterparty's payment succeeds → obligations transfer
- If payment fails → obligations remain with initiator
- No partial execution possible

**Security Features:**
- Smart contract enforced atomicity
- On-chain verification
- Immutable transaction records
- Full audit trail

**Use Cases:**
- Securitization (sell future payment rights)
- Debt trading (transfer loan obligations)
- Structured finance (composite obligation packages)
- Liquidity provision (exchange obligations for cash)

