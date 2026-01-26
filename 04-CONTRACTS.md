# Contracts & Obligations

Complete guide to YieldFabric's contract system, covering both individual contracts/obligations and composed contracts.

---

## Overview

YieldFabric's contract system enables sophisticated payment obligations with programmable unlock conditions, time-based schedules, and oracle-driven payments. The system has two main layers:

1. **Contracts/Obligations**: Individual payment obligation contracts (building blocks)
2. **Composed Contracts**: Collections of multiple contracts managed atomically

**Important**: Users primarily interact with **Composed Contracts** through the API. Individual contracts are building blocks that compose into more complex financial instruments.

---

## Contract Types

### Individual Contracts (Obligations)

Individual contracts represent single payment obligations with:
- **Counterparty**: The party obligated to make payments (payer)
- **Owner/Holder**: The party entitled to receive payments (payee)
- **Obligor**: Optional third party responsible for payments (if different from counterparty)
- **Initial Payments**: Optional scheduled payments that unlock based on time/oracle conditions
- **Status**: ACTIVE, COMPLETED, CANCELLED, PENDING

### Composed Contracts

Composed contracts are collections of multiple individual contracts that are:
- **Managed Atomically**: All sub-contracts are created, accepted, transferred, or cancelled together
- **Unified View**: Presented as a single entity in the API (though composed of multiple contracts)
- **Atomic Operations**: Operations on composed contracts affect all sub-contracts simultaneously
- **ID Format**: Start with `COMPOSED-CONTRACT-` prefix

---

## Contract Lifecycle & Operations

### 1. Issue (Create Contract/Obligation)

Creates a new payment obligation contract.

**GraphQL Mutation:**
```graphql
mutation {
  createObligation(input: {
    counterpart: "counterpart@yieldfabric.com"
    denomination: "aud-token-asset"
    obligor: "issuer@yieldfabric.com"
    notional: "100"
    expiry: "2025-11-01T23:59:59+00:00"
    data: { "name": "Payment Agreement", "description": "..." }
    initialPayments: {
      amount: "100"
      payments: [
        {
          oracleAddress: null
          unlockSender: "2025-11-01T00:00:00+00:00"
          unlockReceiver: "2025-11-01T00:00:00+00:00"
        }
      ]
    }
    idempotencyKey: "unique-key-123"
  }) {
    success
    contractId
    messageId
    transactionId
    signature
  }
}
```

**What Happens:**
1. Creates obligation NFT on blockchain via `safe_mint`
2. Generates unique `token_id` (obligation_id) for the obligation
3. Creates contract record in database with status `ACTIVE`
4. If `initialPayments` provided:
   - Creates payment records in database (status `PENDING`)
   - Generates payment hashes for blockchain commitment
   - Payment records are linked to contract but not yet executed
5. Stores obligation metadata (counterpart, obligor, denomination, expiry)

**Key Fields:**
- `counterpart` (required): Entity name or wallet ID of the payer
- `counterpart_wallet_id` (optional): Direct wallet ID lookup (takes precedence over counterpart)
- `denomination` (required if initialPayments): Asset ID for payments
- `obligor` (optional): Entity name of third-party obligor
- `obligor_wallet_id` (optional): Direct wallet ID for obligor
- `expiry` (optional): Expiry date defining acceptance window (default: 30 days from creation)
- `initialPayments` (optional): Scheduled payments with unlock conditions
- `contract_id` (optional): Custom contract ID (auto-generated if not provided)

**Status After Creation:** `ACTIVE` (pending acceptance)

**Permissions:** Any authenticated user with `CryptoOperations` permission

---

### 2. Accept (Accept Contract/Obligation)

Counterparty accepts the payment obligation, committing to the payment schedule.

**GraphQL Mutation:**
```graphql
mutation {
  acceptObligation(input: {
    contractId: "CONTRACT-OBLIGATION-1760932171982"
  }) {
    success
    obligationId
    messageId
    contractIds
  }
}
```

**What Happens:**
1. Validates obligation exists and hasn't expired
2. Validates caller is the designated counterparty
3. Calls `accept` function on blockchain
4. If `initialPayments` exist:
   - Creates send requests (payment transactions) on blockchain
   - Links payment records to blockchain send requests
   - Updates payment status from `PENDING` to `PROCESSING`
5. Updates contract status from `ACTIVE` to `COMPLETED`
6. Creates position records for payments
7. Notifies dependent workflows (composed contracts, swaps)

**Status After Acceptance:** `COMPLETED`

**Permissions:** Must be the designated counterparty (payer)

**Important:** 
- Acceptance must occur within the **acceptance window** (before expiry date)
- After acceptance, payments execute according to their individual schedules
- Acceptance cannot be reversed

---

### 3. Acceptance Window & Expiry Rules

Every contract has an **acceptance window** defined by the `expiry` date.

#### Acceptance Window

**Definition:** Time period from contract creation until the `expiry` date during which the counterparty can accept the obligation.

**Start:** Contract creation timestamp  
**End:** `expiry` date (default: 30 days from creation if not specified)

#### Rules:

1. **During Acceptance Window:**
   - Counterparty can accept the contract
   - Creator can cancel the contract
   - Contract status: `ACTIVE`

2. **If Accepted Within Window:**
   - Contract status changes to `COMPLETED`
   - Acceptance window is no longer relevant
   - Payments execute according to their individual schedules
   - Original expiry date has no further impact

3. **If Not Accepted Before Expiry:**
   - Contract can no longer be accepted
   - Contract can be expired via `expireObligation` on blockchain
   - Status should be set to `EXPIRED` or `CANCELLED`
   - Assets are returned/released
   - The obligation offer is invalidated

4. **After Expiry (Not Accepted):**
   - `expireObligation` function can be called on blockchain
   - Sets `obligationStatus = Expired`
   - Emits `ObligationExpired` event
   - Acceptance is permanently disabled

**Key Points:**
- The expiry date defines the **acceptance deadline**, not the payment deadline
- Individual payments have their own unlock schedules (independent of acceptance window)
- Once accepted, payments continue regardless of original expiry date
- Unaccepted contracts after expiry should be marked as expired/cancelled

**Example Timeline:**
```
Day 1:    Contract created with expiry = Day 8 (7-day acceptance window)
Day 1-7:  Counterparty can accept
Day 5:    Counterparty accepts → Contract becomes COMPLETED
          Payments now execute on their own schedules (e.g., unlock on Day 10)
          Original expiry (Day 8) is no longer relevant

OR

Day 1:    Contract created with expiry = Day 8
Day 1-7:  Counterparty can accept
Day 8+:   Contract expires → Cannot be accepted anymore
          Must be explicitly expired via expireObligation
          Status should be EXPIRED/CANCELLED
```

---

### 4. Transfer (Transfer Contract/Obligation)

Transfers ownership of an obligation to a new holder, enabling payment rights to be sold or assigned.

**GraphQL Mutation:**
```graphql
mutation {
  transferObligation(input: {
    contractId: "CONTRACT-OBLIGATION-1760932171982"
    destinationId: "newholder@yieldfabric.com"
    # OR destinationWalletId: "wallet-id-123"
  }) {
    success
    obligationId
    destinationAddress
    messageId
  }
}
```

**What Happens:**
1. Validates contract exists and is transferable
2. Validates caller is current owner/holder
3. Calls `safe_transfer_from` on blockchain to transfer obligation NFT
4. Creates new contract record with updated parties:
   - **COUNTERPARTY** (payer): Remains unchanged
   - **HOLDER**: Updated to new owner (replaces old holder)
5. Transfers all associated payments to new payee:
   - Updates `payee_wallet_id` to new holder's wallet
   - Updates `due_date` to use `unlock_receiver` for correct fallback
   - Preserves all payment details (amount, unlock dates, oracle fields)
6. Creates transaction record for audit trail

**Key Concepts:**
- **Payer (COUNTERPARTY)** never changes - original payer remains responsible
- **Payee (HOLDER)** changes - new holder receives all payments
- **Parties are replaced** - old holder is removed, new holder is added
- **Payment rights transfer** - all pending and future payments go to new holder

**Status After Transfer:** Remains `COMPLETED` (transfer doesn't change contract status)

**Permissions:** Must be the current owner/holder of the obligation

**Important:**
- Transfer creates a new contract record (immutable pattern)
- Original payment obligations remain unchanged
- Only the recipient of payments changes
- Transfer is one-way (cannot reverse)

---

### 5. Cancel (Cancel Contract/Obligation)

Cancels a contract, terminating all payment obligations.

**GraphQL Mutation:**
```graphql
mutation {
  cancelObligation(input: {
    contractId: "CONTRACT-OBLIGATION-1760932171982"
  }) {
    success
    obligationId
    messageId
  }
}
```

**What Happens:**
1. Validates contract exists
2. Validates caller has permission (owner, counterpart, or minter)
3. Validates contract hasn't expired (if before acceptance)
4. Calls `cancel` function on blockchain
5. Updates contract status to `CANCELLED`
6. Releases locked assets back to parties
7. Invalidates payment obligations

**When Cancellation is Allowed:**
- **Before Acceptance:** Creator (owner) can cancel freely
- **Before Acceptance:** Counterparty can cancel (if not yet accepted)
- **After Acceptance:** Requires specific contract conditions or mutual consent
- **Expired Contracts:** Can be cancelled if not accepted

**Status After Cancellation:** `CANCELLED`

**Permissions:** 
- Owner (creator), counterparty, or minter can cancel
- Before acceptance: Either party can cancel
- After acceptance: Cancellation may be restricted

**Important:**
- Cancellation is permanent (cannot be reversed)
- All locked assets are released
- No further payments can be executed

---

## Composed Contracts

Composed contracts enable atomic operations across multiple individual contracts.

### Creating Composed Contracts

Composed contracts are typically created through workflows that coordinate multiple obligation creations:

```graphql
mutation {
  executeComposedOperations(input: {
    operations: [
      {
        operationType: CREATE_OBLIGATION
        operationData: {
          counterpart: "counterpart1@yieldfabric.com"
          denomination: "aud-token-asset"
          notional: "100"
        }
      },
      {
        operationType: CREATE_OBLIGATION
        operationData: {
          counterpart: "counterpart2@yieldfabric.com"
          denomination: "aud-token-asset"
          notional: "200"
        }
      }
    ]
  }) {
    success
    composedId
    contractIds
  }
}
```

### Operations on Composed Contracts

All operations (accept, transfer, cancel) work on composed contracts atomically:

**Accept Composed Contract:**
```graphql
mutation {
  acceptObligation(input: {
    contractReference: {
      composedContractId: "COMPOSED-CONTRACT-123"
    }
  }) {
    success
    composedContractId
    composedId
    contractIds
  }
}
```

**Transfer Composed Contract:**
```graphql
mutation {
  transferObligation(input: {
    contractReference: {
      composedContractId: "COMPOSED-CONTRACT-123"
    }
    destinationId: "newholder@yieldfabric.com"
  }) {
    success
    composedContractId
    contractIds
  }
}
```

**Cancel Composed Contract:**
```graphql
mutation {
  cancelObligation(input: {
    contractReference: {
      composedContractId: "COMPOSED-CONTRACT-123"
    }
  }) {
    success
    composedContractId
    contractIds
  }
}
```

**Key Points:**
- Operations on composed contracts affect **all sub-contracts** simultaneously
- Atomic execution ensures all contracts are processed together
- If any sub-contract operation fails, the entire composed operation fails
- Individual contracts can still be queried separately if needed

---

## Contract Statuses

### Individual Contract Statuses

- **ACTIVE**: Contract created, pending acceptance
- **COMPLETED**: Contract accepted, payments active
- **CANCELLED**: Contract cancelled by party or system
- **PENDING**: Intermediate state during processing
- **EXPIRED**: Acceptance window expired without acceptance

### Composed Contract Statuses

Composed contracts inherit status from their sub-contracts:
- All sub-contracts must have consistent status for the composed contract to show that status
- Mixed statuses may show as `PENDING` or transition state

---

## Contract Parties & Roles

### Roles in Individual Contracts

- **MANAGER**: Entity that created the contract
- **COUNTERPARTY**: Party obligated to make payments (payer)
- **HOLDER/ISSUER**: Party entitled to receive payments (payee/holder)
- **TRANSFEROR**: Original holder (before transfer)
- **TRANSFEREE**: New holder (after transfer)

### Party Relationships

**Initial State (Creation):**
- Manager = Creator
- Counterparty = Payer (remains fixed)
- Holder = Initial payee (can change via transfer)

**After Transfer:**
- Manager = Creator (unchanged)
- Counterparty = Original payer (unchanged)
- Holder = New payee (updated)

---

## Querying Contracts

### Get Contracts by Entity

```graphql
query {
  contractFlow {
    contracts(currentEntityId: "entity-id-123") {
      id
      name
      status
      contractType
      parties {
        entity { id name }
        role
      }
      payments {
        id
        amount
        status
        dueDate
      }
    }
  }
}
```

### Get Unified Contract (Single or Composed)

```graphql
query {
  contractFlow {
    unifiedById(id: "CONTRACT-OBLIGATION-123") {
      ... on Contract {
        id
        name
        status
      }
      ... on ComposedContract {
        id
        name
        contracts {
          id
          name
          status
        }
      }
    }
  }
}
```

### Get All Contracts (Single and Composed)

```graphql
query {
  contractFlow {
    unifiedByEntityId(entityId: "entity-id-123") {
      ... on Contract {
        id
        name
        status
      }
      ... on ComposedContract {
        id
        name
        contracts {
          id
          name
        }
      }
    }
  }
}
```

---

## Payment Integration

### Initial Payments

When creating a contract with `initialPayments`:

1. **At Creation:**
   - Payment records created in database (status: `PENDING`)
   - Payment hashes committed to blockchain
   - No actual funds transferred yet

2. **At Acceptance:**
   - Send requests (payment transactions) created on blockchain
   - Payment records linked to send requests via `token_id`
   - Payment status updates to `PROCESSING`
   - Position records created

3. **Payment Execution:**
   - Payments unlock based on `unlockSender`/`unlockReceiver` dates
   - Oracle conditions (if specified) must be met
   - Payments execute automatically when conditions satisfied
   - Payment status updates to `COMPLETED`

### Payment Schedule Independence

**Important:** Payment unlock schedules are **independent** of the acceptance window:
- Acceptance window expiry does not affect payment schedules
- Individual payments have their own unlock dates (`unlockSender`, `unlockReceiver`)
- Payments continue executing after acceptance regardless of original expiry date
- Only the acceptance deadline is affected by the expiry date

---

## Best Practices

### For Contract Creation

1. **Set Appropriate Expiry:** Provide realistic acceptance window (e.g., 7-30 days)
2. **Use Composed Contracts:** For multi-party or multi-contract scenarios, use composed contracts
3. **Initial Payments:** Define clear unlock schedules with time-based and/or oracle conditions
4. **Clear Documentation:** Use `data` field to store contract metadata and descriptions

### For Contract Acceptance

1. **Review Before Accepting:** Ensure payment terms are acceptable
2. **Accept Within Window:** Accept before expiry date to avoid expiration
3. **Monitor Payments:** Track payment execution status after acceptance

### For Contract Transfer

1. **Verify Recipient:** Ensure new holder is correct entity
2. **Understand Rights:** Transferred contracts give payment rights, not payment obligations
3. **Audit Trail:** Transfer creates immutable records for compliance

### For Composed Contracts

1. **Atomic Operations:** Use composed contracts for operations that must succeed or fail together
2. **Status Monitoring:** Monitor both composed contract and individual sub-contract statuses
3. **Error Handling:** Understand that partial failures affect entire composed operation

---

## Example Use Cases

### Annuity Stream

Create a contract with scheduled payments unlocking daily:

```graphql
mutation($initialPayments: InitialPaymentsInput) {
  createObligation(input: {
    counterpart: "payer@yieldfabric.com"
    denomination: "aud-token-asset"
    notional: "5"
    expiry: "2025-11-01"
    initialPayments: $initialPayments
  }) {
    contractId
  }
}

# Variables:
# {
#   "initialPayments": {
#     "amount": "5",
#     "payments": [
#       { "unlockSender": "2025-11-01", "unlockReceiver": "2025-11-01" },
#       { "unlockSender": "2025-11-02", "unlockReceiver": "2025-11-02" },
#       { "unlockSender": "2025-11-03", "unlockReceiver": "2025-11-03" }
#     ]
#   }
# }
```

### Self-Referential Obligations

Create obligations where you are both obligor and counterparty:

```graphql
mutation {
  createObligation(input: {
    counterpart: "issuer@yieldfabric.com"
    obligor: "issuer@yieldfabric.com"
    denomination: "aud-token-asset"
    notional: "100"
    expiry: "2025-11-01"
  }) {
    contractId
  }
}
```

**Why Self-Referential?**
- Build complex structures without counterparty risk
- Lock the structure by accepting your own obligation
- Atomically transfer to actual counterparty via swap
- Ensures secure construction and settlement

### Multi-Contract Swap (Composed)

Create multiple contracts atomically for a swap operation:

```graphql
mutation {
  executeComposedOperations(input: {
    operations: [
      {
        operationType: CREATE_OBLIGATION
        operationData: { counterpart: "party1", denomination: "asset1", notional: "100" }
      },
      {
        operationType: CREATE_OBLIGATION
        operationData: { counterpart: "party2", denomination: "asset2", notional: "200" }
      }
    ]
  }) {
    composedId
    contractIds
  }
}
```

---

## API Reference Summary

### Mutations

- `createObligation`: Create new payment obligation
- `acceptObligation`: Accept pending obligation (can use `contractReference` for composed)
- `transferObligation`: Transfer obligation to new holder (can use `contractReference` for composed)
- `cancelObligation`: Cancel obligation (can use `contractReference` for composed)
- `executeComposedOperations`: Create and manage composed contracts atomically
- `hideContract`: Soft-delete contract (hide from view)

### Queries

- `contracts`: Get contracts for entity (legacy)
- `coreContracts`: Access core contract query resolver
- `unifiedById`: Get single contract or composed contract by ID
- `unifiedByEntityId`: Get all contracts (single and composed) for entity

### Input Types

- `CreateObligationInput`: Contract creation parameters
- `AcceptObligationInput`: Acceptance parameters (supports `contractReference`)
- `TransferObligationInput`: Transfer parameters (supports `contractReference`)
- `CancelObligationInput`: Cancellation parameters (supports `contractReference`)
- `ContractReference`: Reference to single contract (`contractId`) or composed contract (`composedContractId`)
- `InitialPaymentsInput`: Scheduled payment structure
- `ComposedOperationInput`: Operations for composed contracts

---

## Troubleshooting

### Contract Not Found
- Verify contract ID is correct
- Check if contract was deleted (soft-deleted contracts may be hidden)
- Ensure you have permission to view the contract

### Cannot Accept Contract
- Verify you are the designated counterparty
- Check if acceptance window has expired (expiry date)
- Ensure contract status is `ACTIVE`
- Verify contract hasn't been cancelled

### Payment Not Executing
- Check payment unlock dates (`unlockSender`, `unlockReceiver`)
- Verify oracle conditions (if specified) are met
- Ensure contract has been accepted (status: `COMPLETED`)
- Check payment status in database (`PENDING`, `PROCESSING`, `COMPLETED`)

### Transfer Failed
- Verify you are the current holder/owner
- Ensure contract has been accepted
- Check destination entity/wallet exists
- Verify contract hasn't been cancelled

---

## Additional Resources

- [Payment Flow Documentation](./05-PAYMENTS.md): Detailed payment execution flow
- [Composed Contracts Guide](../composed_contracts/): Advanced composed contract patterns
- [Smart Contract Documentation](../../yieldfabric-smart-contracts/docs/Obligations.md): Blockchain contract details
