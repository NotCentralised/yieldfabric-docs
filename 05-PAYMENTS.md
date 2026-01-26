# Payments Guide

Complete guide to YieldFabric's payment system, covering deposits, instant payments, obligation payments, and payment acceptance.

---

## Overview

YieldFabric's payment system enables confidential, programmable payments with time locks, oracle conditions, and linear vesting. Payments can be cash (obligor = null) or credit (obligor = entity address), supporting both immediate and scheduled transfers.

**Important**: Users primarily interact with payments through the GraphQL API. The system handles all blockchain interactions, cryptographic operations, and state management automatically.

---

## Payment Types

### Payment Categories

Payments are categorized by their source and purpose:

1. **DEPOSIT**: Funds deposited into wallet (cash payment, no obligor)
2. **INSTANT**: Immediate payment sent to another entity (can be cash or credit)
3. **OBLIGATION**: Scheduled payment from a contract/obligation (can be cash or credit)
4. **SWAP_PAYMENT**: Payment created during swap settlement (can be cash or credit)

### Payment Direction

Payments have a direction indicating your role:

- **PAYABLE**: Outgoing payment (you are the payer/sender)
- **RECEIVABLE**: Incoming payment (you are the payee/receiver)

### Cash vs Credit Payments

**Cash Payments** (`obligor = null`):
- No obligor specified (uses zero address internally)
- Direct asset transfer
- No outstanding balance tracking
- Examples: Deposits, instant cash transfers, repurchase payments

**Credit Payments** (`obligor = entity address`):
- Obligor specified (the entity responsible for the debt)
- Tracks outstanding balance for the obligor
- When sender = obligor: Issues new credit (increases outstanding)
- When sender ≠ obligor: Transfers existing credit (no outstanding change)
- Examples: Obligation payments, credit transfers, debt assignments

---

## Payment Status

Payments progress through the following statuses:

1. **PENDING**: Initial state after payment creation
   - Payment created, awaiting processing
   - For instant payments: Waiting for payee to accept
   - For deposits: Waiting for blockchain confirmation
   - Assets are locked and cannot be used for other operations

2. **PROCESSING**: Payment is being processed
   - Blockchain transaction submitted
   - Waiting for confirmation
   - Assets remain locked

3. **COMPLETED**: Payment successfully executed
   - Funds transferred between parties
   - Balance updated
   - Transaction recorded on blockchain
   - Final state - cannot be reversed

4. **FAILED**: Payment processing failed
   - Error during blockchain transaction
   - Insufficient balance
   - Invalid parameters
   - Assets remain with original owner

5. **CANCELLED**: Payment was cancelled or rejected
   - Can occur before acceptance (instant payments)
   - Can occur due to expiry/timeout
   - Assets returned to sender

---

## Payment Operations

### 1. Deposit

Deposit funds into your wallet (cash payment).

**GraphQL Mutation:**
```graphql
mutation Deposit($input: DepositInput!) {
  deposit(input: $input) {
    success
    message
    accountAddress
    depositResult
    messageId
    transactionId
    signature
    timestamp
  }
}
```

**Input Parameters:**
- `assetId`: Asset identifier (e.g., `"aud-token-asset"`) (required)
- `amount`: Amount to deposit as integer string (e.g., `"100"`) (required)
- `idempotencyKey`: Unique key for duplicate prevention (optional)

**Rules:**
1. **Obligor**: Always zero address (cash payment)
2. **Balance**: Increases private balance
3. **Outstanding**: No change (cash payments don't affect outstanding)
4. **Status**: Starts as `PENDING`, becomes `COMPLETED` after blockchain confirmation

**Example:**
```graphql
mutation {
  deposit(input: {
    assetId: "aud-token-asset"
    amount: "100"
    idempotencyKey: "deposit-001"
  }) {
    success
    messageId
    transactionId
  }
}
```

**Response:**
```json
{
  "data": {
    "deposit": {
      "success": true,
      "message": "Deposit message submitted successfully",
      "accountAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
      "depositResult": "Message queued for processing with ID: msg-deposit-123",
      "messageId": "msg-deposit-123",
      "transactionId": "TXN-DEPOSIT-1760931347129",
      "signature": "0xabc...",
      "timestamp": "2025-10-20T03:48:04.756700864+00:00"
    }
  }
}
```

---

### 2. Send Instant Payment

Send an immediate payment to another entity (can be cash or credit).

**GraphQL Mutation:**
```graphql
mutation Instant($input: InstantSendInput!) {
  instant(input: $input) {
    success
    message
    accountAddress
    destinationId
    idHash
    messageId
    paymentId
    sendResult
    transactionId
    signature
    timestamp
  }
}
```

**Input Parameters:**
- `assetId`: Asset identifier (e.g., `"aud-token-asset"`) (required)
- `amount`: Amount to send as integer string (e.g., `"10"`) (required)
- `destinationId`: Entity name/email or wallet address of recipient (optional)
- `destinationWalletId`: Wallet ID of recipient (optional)
- `contractId`: Existing contract ID to use (optional)
- `obligor`: Entity name/email or wallet address of obligor (optional)
  - If provided: Credit payment (obligor responsible for debt)
  - If `null`: Cash payment (no obligor)
- `idempotencyKey`: Unique key for duplicate prevention (optional)

**Rules:**
1. **Destination**: Either `destinationId` OR `destinationWalletId` OR `contractId` required
2. **Obligor**: 
   - If `obligor` provided: Credit payment (tracks outstanding)
   - If `obligor` is `null`: Cash payment (no outstanding tracking)
3. **Balance**: 
   - Sender's balance decreases
   - Payment locked in sender's account until accepted
4. **Outstanding**: 
   - If sender = obligor: Outstanding increases (issuing credit)
   - If sender ≠ obligor: Outstanding unchanged (transferring credit)
   - If obligor = null: Outstanding unchanged (cash payment)
5. **Status**: Starts as `PENDING`, becomes `PROCESSING` after blockchain confirmation, `COMPLETED` after acceptance

**Example - Cash Payment:**
```graphql
mutation {
  instant(input: {
    assetId: "aud-token-asset"
    amount: "10"
    destinationId: "counterpart@yieldfabric.com"
    idempotencyKey: "instant-payment-001"
  }) {
    success
    paymentId
    messageId
  }
}
```

**Example - Credit Payment:**
```graphql
mutation {
  instant(input: {
    assetId: "aud-token-asset"
    amount: "10"
    destinationId: "counterpart@yieldfabric.com"
    obligor: "issuer@yieldfabric.com"
    idempotencyKey: "instant-credit-001"
  }) {
    success
    paymentId
    messageId
  }
}
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
      "sendResult": "Message queued for processing with ID: msg-send-123",
      "transactionId": "TXN-INSTANT-SEND-1759048183145",
      "signature": "0xdef...",
      "timestamp": "2025-10-20T03:49:03.807744427+00:00"
    }
  }
}
```

**Important Notes:**
- `amount` must be an **integer string** (e.g., `"10"`, NOT `"10.00"`)
- Either `destinationId` (entity name/email) OR `destinationWalletId` (wallet ID) OR `contractId` is required
- `obligor` determines if payment is cash (`null`) or credit (entity address)
- `idempotencyKey` ensures duplicate prevention

---

### 3. Accept Payment

Accept a pending payment to receive funds.

**GraphQL Mutation:**
```graphql
mutation Accept($input: AcceptInput!) {
  accept(input: $input) {
    success
    message
    accountAddress
    idHash
    acceptResult
    messageId
    transactionId
    signature
    timestamp
  }
}
```

**Input Parameters:**
- `paymentId`: The payment ID to accept (required)
- `amount`: Partial amount to accept (optional, defaults to full balance)
- `idempotencyKey`: Unique key for duplicate prevention (optional)

**Rules:**
1. **Permission**: Only payee (receiver) can accept payment
2. **Status**: Payment must be `PENDING` or `PROCESSING`
3. **Token**: Payment must have valid token with `id_hash` (address)
4. **Unlock**: Payment must be unlocked for receiver (`unlock_receiver` is `None` or in the past)
5. **Linear Vesting**: If `linear_vesting = true`, can accept partial amount based on vesting schedule
6. **Balance**: 
   - Receiver's balance increases
   - Sender's locked balance decreases
7. **Outstanding**: 
   - If receiver = obligor: Outstanding decreases (obligor receiving own credit reduces debt)
   - If receiver ≠ obligor: Outstanding unchanged
   - If obligor = null: Outstanding unchanged (cash payment)
8. **Status**: Changes from `PENDING`/`PROCESSING` to `COMPLETED` after blockchain confirmation

**Example:**
```graphql
mutation {
  accept(input: {
    paymentId: "PAY-INSTANT-1759048183145"
    idempotencyKey: "accept-payment-001"
  }) {
    success
    messageId
    transactionId
  }
}
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
      "acceptResult": "Payment accept submitted for processing",
      "messageId": "msg-456",
      "transactionId": "TXN-ACCEPT-1759048183145",
      "signature": "0xghi...",
      "timestamp": "2025-10-20T03:49:21.791216299+00:00"
    }
  }
}
```

**Note:** For linear vesting payments, you can accept partial amounts. The system calculates the vested amount based on elapsed time and vesting period.

---

### 4. Accept All Payments

Accept all pending payments matching criteria (denomination and optional obligor filter).

**GraphQL Mutation:**
```graphql
mutation AcceptAll($input: AcceptAllInput!) {
  acceptAll(input: $input) {
    success
    message
    totalPayments
    acceptedCount
    failedCount
    acceptedPayments {
      paymentId
      amount
      messageId
      transactionId
    }
    failedPayments {
      paymentId
      amount
      error
    }
    timestamp
  }
}
```

**Input Parameters:**
- `denomination`: Asset identifier to filter by (e.g., `"aud-token-asset"`) (required)
- `obligor`: Optional obligor filter (entity name/email or wallet address) (optional)
  - If provided: Only accept payments with matching obligor
  - If `null`: Accept payments with any obligor (or no obligor)
- `idempotencyKey`: Unique key for duplicate prevention (optional)

**Rules:**
1. **Filtering**: Only processes `RECEIVABLE` payments (incoming)
2. **Status**: Only processes `PROCESSING` payments
3. **Unlock**: Only processes payments unlocked for receiver
4. **Denomination**: Must match specified `denomination`
5. **Obligor**: If `obligor` provided, must match payment's obligor
6. **Batch Processing**: Accepts each payment individually (some may succeed, others may fail)

**Example:**
```graphql
mutation {
  acceptAll(input: {
    denomination: "aud-token-asset"
    obligor: "issuer@yieldfabric.com"
  }) {
    success
    totalPayments
    acceptedCount
    failedCount
    acceptedPayments {
      paymentId
      amount
    }
  }
}
```

**Response:**
```json
{
  "data": {
    "acceptAll": {
      "success": true,
      "message": "Successfully accepted all 3 payments",
      "totalPayments": 3,
      "acceptedCount": 3,
      "failedCount": 0,
      "acceptedPayments": [
        {
          "paymentId": "PAY-INSTANT-1759048183145",
          "amount": 100,
          "messageId": "msg-456",
          "transactionId": "TXN-ACCEPT-1759048183145"
        }
      ],
      "failedPayments": [],
      "timestamp": "2025-10-20T03:50:00.123456789+00:00"
    }
  }
}
```

---

### 5. Withdraw

Withdraw funds from your wallet (cash payment).

**GraphQL Mutation:**
```graphql
mutation Withdraw($input: WithdrawInput!) {
  withdraw(input: $input) {
    success
    message
    accountAddress
    withdrawResult
    messageId
    transactionId
    signature
    timestamp
  }
}
```

**Input Parameters:**
- `assetId`: Asset identifier (e.g., `"aud-token-asset"`) (required)
- `amount`: Amount to withdraw as integer string (e.g., `"50"`) (required)
- `idempotencyKey`: Unique key for duplicate prevention (optional)

**Rules:**
1. **Obligor**: Always zero address (cash payment)
2. **Balance**: Decreases private balance
3. **Outstanding**: No change (cash payments don't affect outstanding)
4. **Status**: Starts as `PENDING`, becomes `COMPLETED` after blockchain confirmation

**Example:**
```graphql
mutation {
  withdraw(input: {
    assetId: "aud-token-asset"
    amount: "50"
    idempotencyKey: "withdraw-001"
  }) {
    success
    messageId
    transactionId
  }
}
```

**Response:**
```json
{
  "data": {
    "withdraw": {
      "success": true,
      "message": "Withdraw message submitted successfully",
      "accountAddress": "0x0620cFad3f9798FA036a0795e70661a98feDE9D4",
      "withdrawResult": "Withdraw message submitted successfully with ID: msg-withdraw-123",
      "messageId": "msg-withdraw-123",
      "transactionId": "TXN-WITHDRAW-1759048183145",
      "signature": "0xjkl...",
      "timestamp": "2025-10-20T03:51:00.123456789+00:00"
    }
  }
}
```

---

### 6. Hide Payment

Hide a payment from your view (soft delete).

**GraphQL Mutation:**
```graphql
mutation HidePayment($input: HidePaymentInput!) {
  hidePayment(input: $input) {
    success
    message
    paymentId
  }
}
```

**Input Parameters:**
- `paymentId`: The payment ID to hide (required)

**Rules:**
1. **Soft Delete**: Sets `deleted = true` flag (does not remove from database)
2. **Reversible**: Can be undone by updating the flag (if needed)
3. **Visibility**: Hidden payments are filtered from queries by default

**Example:**
```graphql
mutation {
  hidePayment(input: {
    paymentId: "PAY-INSTANT-1759048183145"
  }) {
    success
    message
  }
}
```

**Response:**
```json
{
  "data": {
    "hidePayment": {
      "success": true,
      "message": "Payment PAY-INSTANT-1759048183145 has been hidden",
      "paymentId": "PAY-INSTANT-1759048183145"
    }
  }
}
```

---

## Time Locks & Unlock Conditions

### Unlock Sender (`unlock_sender`)

Time when the sender can cancel/retrieve the payment:

- **Purpose**: Allows sender to reclaim funds after a certain time
- **Format**: ISO 8601 datetime or `null` (no time lock)
- **Effect**: Sender can cancel payment after this time
- **Oracle Integration**: If oracle is present, `unlock_sender` is the oracle expiry time

**Rules:**
1. If `unlock_sender = null`: Sender can cancel immediately
2. If `unlock_sender` in future: Sender must wait until this time
3. If oracle present: `unlock_sender` is oracle expiry (payment locked until oracle value matches or expires)

### Unlock Receiver (`unlock_receiver`)

Time when the receiver can accept the payment:

- **Purpose**: Controls when payment becomes available for acceptance
- **Format**: ISO 8601 datetime or `null` (no time lock)
- **Effect**: Receiver can accept payment after this time
- **Oracle Integration**: If oracle is present, `unlock_receiver` is the oracle expiry time

**Rules:**
1. If `unlock_receiver = null`: Receiver can accept immediately
2. If `unlock_receiver` in future: Receiver must wait until this time
3. If oracle present: `unlock_receiver` is oracle expiry (payment locked until oracle value matches or expires)

### Linear Vesting (`linear_vesting`)

Gradual unlock of payment amount over time:

- **Purpose**: Allows partial acceptance based on elapsed time
- **Calculation**: `vested_amount = total_amount * (block_time - start_time) / (end_time - start_time)`
- **Start Time**: Payment creation time (`created`)
- **End Time**: `unlock_receiver` (vesting completion time)
- **Effect**: Receiver can accept partial amounts proportional to elapsed time

**Rules:**
1. Only applies when `linear_vesting = true` AND receiver is accepting
2. Sender cannot use linear vesting (always full amount for cancellation)
3. Vested amount increases linearly from 0% to 100% over vesting period
4. Can accept multiple times (each time accepts up to current vested amount minus previously accepted)

**Example Timeline:**
```
Payment Created:     2025-10-01
Unlock Receiver:    2025-12-01  (2 months vesting)
                     │          │
                     │          └─ 100% vested (full amount available)
                     └─ 0% vested (no amount available)
                     
Current Time:        2025-11-01  (1 month elapsed)
Vested Amount:       50% of total (1 month / 2 months)
```

---

## Outstanding Balance

Outstanding balance tracks credit/debt for each obligor-denomination pair:

**Purpose:**
- Tracks how much credit an obligor has issued (debt owed to them)
- Used for credit risk management and balance calculations

**Rules:**
1. **Issuing Credit** (sender = obligor):
   - Outstanding increases by payment amount
   - Represents new debt issued by obligor

2. **Transferring Credit** (sender ≠ obligor):
   - Outstanding unchanged
   - Credit transferred between parties, but obligor remains same

3. **Receiving Own Credit** (receiver = obligor):
   - Outstanding decreases by accepted amount
   - Obligor receiving their own credit reduces their debt

4. **Cash Payments** (obligor = null):
   - Outstanding unchanged
   - Cash payments don't affect outstanding balance

**Example:**
```
Initial State:
- Obligor A outstanding: 1000 AUD

Action: Obligor A sends 100 AUD credit to Entity B
- Obligor A outstanding: 1100 AUD (increased by 100)

Action: Entity B accepts 100 AUD credit
- Obligor A outstanding: 1100 AUD (unchanged, B ≠ A)

Action: Obligor A receives 50 AUD of their own credit back
- Obligor A outstanding: 1050 AUD (decreased by 50)
```

---

## Balance Types

When querying balances, you get several balance components:

### Private Balance (`private_balance`)

Your actual spendable balance for a denomination-obligor pair:

- **Cash Balance** (obligor = null): Direct cash holdings
- **Credit Balance** (obligor = entity): Credit received from that obligor
- **Effect**: Increases on deposit/accept, decreases on send/withdraw

### Locked Out (`locked_out`)

Payments you've sent but haven't been accepted yet:

- **Purpose**: Tracks outgoing payments awaiting acceptance
- **Effect**: Reduces available balance (funds are locked)
- **Unlock**: When receiver accepts or you cancel

### Locked In (`locked_in`)

Payments you've received but haven't accepted yet:

- **Purpose**: Tracks incoming payments awaiting acceptance
- **Effect**: Not yet in your balance (funds are locked)
- **Unlock**: When you accept the payment

### Outstanding (`outstanding`)

Total credit issued by an obligor (for credit payments only):

- **Purpose**: Tracks debt/credit for risk management
- **Effect**: Increases when obligor issues credit, decreases when obligor receives own credit
- **Scope**: Only applies to credit payments (obligor ≠ null)

### Beneficial Balance

Calculated balance considering locked amounts:

- **Formula**: `private_balance + locked_in - locked_out`
- **Purpose**: Shows your effective balance including pending transactions

---

## Payment Lifecycle

### Instant Payment Lifecycle

1. **Create** (`PENDING`):
   - Sender creates payment via `instant` mutation
   - Payment locked in sender's account
   - Status: `PENDING`

2. **Process** (`PROCESSING`):
   - Blockchain transaction submitted
   - Payment appears in receiver's `locked_in` array
   - Status: `PROCESSING`

3. **Accept** (`COMPLETED`):
   - Receiver accepts payment via `accept` mutation
   - Funds transfer to receiver's balance
   - Status: `COMPLETED`

4. **Cancel** (`CANCELLED`):
   - Sender cancels payment (if `unlock_sender` passed)
   - Funds returned to sender
   - Status: `CANCELLED`

### Obligation Payment Lifecycle

1. **Create** (`PENDING`):
   - Payment created as part of obligation contract
   - Time locks set (`unlock_sender`, `unlock_receiver`)
   - Status: `PENDING`

2. **Accept** (`PROCESSING`):
   - Receiver accepts payment (after `unlock_receiver`)
   - Payment tokens created
   - Status: `PROCESSING`

3. **Complete** (`COMPLETED`):
   - Payment executed on blockchain
   - Funds transferred
   - Status: `COMPLETED`

### Deposit Lifecycle

1. **Create** (`PENDING`):
   - User creates deposit via `deposit` mutation
   - Status: `PENDING`

2. **Process** (`PROCESSING`):
   - Blockchain transaction submitted
   - Status: `PROCESSING`

3. **Complete** (`COMPLETED`):
   - Deposit confirmed on blockchain
   - Balance updated
   - Status: `COMPLETED`

---

## Querying Payments

### Get Payments by Entity

Query all payments for a specific entity:

```graphql
query GetPayments($currentEntityId: ID!) {
  paymentsByEntity(currentEntityId: $currentEntityId) {
    id
    amount
    assetId
    asset {
      id
      name
      assetType
      currency
    }
    paymentType
    status
    dueDate
    unlockSender
    unlockReceiver
    linearVesting
    description
    contractId
    createdAt
    token {
      chainId
      address
      id
    }
    payee {
      entity {
        id
        name
      }
      wallet {
        id
        name
      }
    }
    payer {
      entity {
        id
        name
      }
      wallet {
        id
        name
      }
    }
    obligorId
  }
}
```

**Response:**
```json
{
  "data": {
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
        "linearVesting": false,
        "description": "DEPOSIT of 225 to account 0x207bbca7acd050e67e311a45175a8cb0cb0b7396",
        "contractId": "CONTRACT-DEPOSIT-1760931346780",
        "createdAt": "2025-10-20T03:48:04.771157268+00:00",
        "token": null,
        "obligorId": null
      },
      {
        "id": "PAY-INSTANT-1760932133588",
        "amount": 100,
        "assetId": "aud-token-asset",
        "paymentType": "PAYABLE",
        "status": "COMPLETED",
        "unlockSender": null,
        "unlockReceiver": null,
        "linearVesting": false,
        "contractId": "CONTRACT-INSTANT-1760932133267",
        "token": {
          "chainId": "153",
          "address": "0x373a54221cc0f483757f527a4f586ff2b804833f8afbecbfc22476a5806dd0dc",
          "id": "PAY-INSTANT-1760932133588-payment-token"
        },
        "obligorId": null
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
        "linearVesting": false,
        "description": "Initial payment 1 for contract CONTRACT-OBLIGATION-1760932171982",
        "contractId": "CONTRACT-OBLIGATION-1760932171982",
        "token": null,
        "obligorId": "2cee226b-f69a-4385-bb2c-22ecc61eedcc"
      }
    ]
  }
}
```

---

## Best Practices

### Payment Creation

1. **Use Idempotency Keys**: Always provide `idempotencyKey` to prevent duplicate payments
2. **Validate Amounts**: Ensure amounts are integer strings (no decimals)
3. **Check Balance**: Verify sufficient balance before sending
4. **Set Time Locks**: Use `unlock_sender` and `unlock_receiver` for scheduled payments
5. **Choose Obligor**: 
   - Use `obligor = null` for cash payments
   - Use `obligor = entity` for credit payments

### Payment Acceptance

1. **Check Unlock Time**: Verify `unlock_receiver` has passed before accepting
2. **Linear Vesting**: For vesting payments, accept partial amounts as they vest
3. **Batch Acceptance**: Use `acceptAll` for multiple payments with same denomination
4. **Monitor Status**: Track payment status to ensure completion

### Error Handling

1. **Insufficient Balance**: Check balance before sending
2. **Locked Payments**: Wait for unlock time before accepting
3. **Invalid Token**: Ensure payment has valid token with `id_hash`
4. **Status Validation**: Only accept `PENDING` or `PROCESSING` payments

---

## Integration with Contracts & Swaps

### Contract Payments

Payments can be created as part of obligation contracts:

- **Initial Payments**: Created when contract is issued
- **Scheduled Payments**: Created based on payment schedule
- **Time Locks**: Inherited from contract expiry dates
- **Obligor**: Inherited from contract parties

### Swap Payments

Payments can be created during swap settlement:

- **Initiator Payments**: Created during `createSwap`
- **Counterparty Payments**: Created during `completeSwap`
- **Collateral Payments**: Created for repo swaps
- **Repurchase Payments**: Always cash payments (obligor = null)

**Note**: Swap payments are locked until swap status is `COMPLETED`. See [Swaps Documentation](./06-SWAPS.md) for details.

---

## Summary

YieldFabric's payment system provides:

- **Multiple Payment Types**: Deposit, Instant, Obligation, Swap
- **Cash & Credit Support**: Payments with or without obligor
- **Time Locks**: Scheduled unlock conditions for sender and receiver
- **Linear Vesting**: Gradual unlock over time
- **Outstanding Tracking**: Credit/debt management per obligor
- **Balance Management**: Private balance, locked amounts, outstanding
- **Lifecycle Management**: Status tracking from creation to completion
- **Security**: Smart contract enforced atomicity and confidentiality

Users primarily interact with payments through the GraphQL API, with the system handling all blockchain interactions, cryptographic operations, and state management automatically.
