# YieldFabric API Documentation

Complete API documentation and examples for YieldFabric - a platform for programmable financial operations with zero-knowledge privacy.

## Table of Contents

- [Quick Links](#documentation-structure)
- [Getting Started](#getting-started)
- [Core Capabilities](#core-capabilities)
- [Example Workflows](#example-workflows)
- [GraphQL Schema](#graphql-schema)
- [Authentication & Authorization](#authentication--authorization)
- [Support & Resources](#support--resources)

---

## Overview

YieldFabric provides **intelligent accounts** that enable sophisticated financial operations with confidential transactions protected by zero-knowledge proof technology. Create, program, and trade payment obligations with atomic settlement guarantees.

## Key Features

- 🔐 **Zero-Knowledge Privacy**: Confidential transactions using ZK-proof technology
- 💰 **Intelligent Accounts**: Programmable accounts for users and groups
- 📅 **Payment Obligations**: Create invoices, loans, annuities, and structured payments
- ⚡ **Instant Payments**: Send and receive payments with atomic settlement
- 🔄 **Atomic Swaps**: Exchange payment obligations with guaranteed execution
- ⏰ **Programmable Triggers**: Timelocks and oracle-based conditional execution
- 👥 **Group Accounts**: Collaborative operations with fine-grained access control
- 🔍 **Full Audit Trail**: Complete transaction history and delegation tracking

## Documentation Structure

> **Not sure where to start?** See [NAVIGATION.md](./NAVIGATION.md) for guided reading paths based on your experience level and use case.

### Quick Start
- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes ⚡
- **[01-OVERVIEW.md](./01-OVERVIEW.md)** - How the platform works 📖

### Core Guides (Step-by-Step)
- **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** - Login, delegation, JWT tokens 🔐
- **[03-BALANCES.md](./03-BALANCES.md)** - Balance queries and locked transactions 💰
- **[04-CONTRACTS.md](./04-CONTRACTS.md)** - Creating and querying obligations 📄
- **[05-PAYMENTS.md](./05-PAYMENTS.md)** - Sending and accepting payments 💸
- **[06-SWAPS.md](./06-SWAPS.md)** - Atomic swaps and bilateral trading 🔄
- **[07-WORKFLOWS.md](./07-WORKFLOWS.md)** - Complete end-to-end examples 🎯
- **[08-REFERENCE.md](./08-REFERENCE.md)** - Error codes, assets, quick reference 📚
- **[09-CRYPTOGRAPHIC-OPERATIONS.md](./09-CRYPTOGRAPHIC-OPERATIONS.md)** - Key management, encryption, signatures 🔑

### Complete Reference
- **[SIMPLE.md](./SIMPLE.md)** - All API examples in one comprehensive file
- **[NAVIGATION.md](./NAVIGATION.md)** - Reading guide based on your needs


### Service URLs
- **Production Auth**: `https://auth.yieldfabric.com`
- **Production API**: `https://pay.yieldfabric.com`
- **GraphQL Endpoint**: `https://pay.yieldfabric.com/graphql`

## Getting Started

### New to YieldFabric?

Start here: **[QUICKSTART.md](./QUICKSTART.md)** - Complete beginner's guide with step-by-step examples.

### For Developers

1. **[01-OVERVIEW.md](./01-OVERVIEW.md)** - Understand the platform architecture
2. **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** - Get authenticated
3. **[03-BALANCES.md](./03-BALANCES.md)** - Query your balances
4. **[05-PAYMENTS.md](./05-PAYMENTS.md)** - Send your first payment

### Quick Example

```bash
# Login
export TOKEN=$(curl -s -X POST https://auth.yieldfabric.com/auth/login/with-services \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password","services":["vault","payments"]}' \
  | jq -r '.token')

# Check balance
curl -X GET "https://pay.yieldfabric.com/balance?denomination=aud-token-asset&obligor=null" \
  -H "Authorization: Bearer $TOKEN" | jq

# Send payment
curl -X POST https://pay.yieldfabric.com/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { instant(input: { assetId: \"aud-token-asset\", amount: \"10\", destinationId: \"recipient@yieldfabric.com\" }) { success paymentId } }"
  }' | jq
```

## Core Capabilities

### Intelligent Accounts

**Personal Accounts**
- Owned by individual users
- Full control over funds and operations
- Deployed on-chain with zero-knowledge privacy

**Group Accounts**
- Shared accounts managed by multiple users
- Policy-based access control
- Delegation with audit trail
- Same features as personal accounts (balances, payments, obligations, swaps)

### Payment Operations

**Instant Payments**
- Send funds to other users immediately
- Locked until counterpart accepts or sender cancels
- Atomic settlement guarantees

**Payment Obligations**
- Create structured payment commitments (invoices, loans, annuities)
- **Fully Funded (Escrow)**: Funds locked upfront
- **Unfunded (Credit)**: Payment commitment without immediate funding
- Programmable with timelocks and oracle triggers

**Atomic Swaps**
- Exchange payment obligations bilaterally
- Both parties exchange simultaneously or transaction fails
- Enables securitization and structured finance

## API Sections

The complete API documentation in [SIMPLE.md](./SIMPLE.md) includes:

1. **Authentication** - Login and delegation
2. **Balance Queries** - Check balances and locked transactions
3. **Contracts** - View and create payment obligations
4. **Payments** - Query payment history
5. **Instant Payments** - Send and accept payments
6. **Swaps** - Create and execute atomic swaps
7. **Annuity Workflows** - Complete securitization examples

## Key Concepts

### Self-Referential Obligations

Create obligation structures with yourself as both obligor and counterpart:
- Build complex payment schedules without counterparty risk
- Lock the structure by accepting your own obligations
- Atomically transfer to actual counterparty via swap
- Ensures secure construction and settlement

### Atomic Settlement

All bilateral operations use atomic execution:
- Payment and obligation transfer happen simultaneously
- Transaction succeeds completely or fails entirely
- No partial execution or settlement risk

### Zero-Knowledge Privacy

All account balances and transactions use ZK-proofs:
- Confidential balances (encrypted amounts)
- Public balances (transparent amounts)
- Privacy-preserving transfers
- On-chain verification without revealing details

## Example Workflows

### Simple Payment Flow
1. Deposit funds into intelligent account
2. Send instant payment to recipient
3. Recipient accepts payment
4. Recipient withdraws funds

### Annuity Securitization
1. Create annuity stream obligation (self-referential)
2. Create redemption obligation (self-referential)
3. Accept both obligations (lock structure)
4. Create atomic swap offering obligations for upfront payment
5. Counterparty completes swap (pays upfront, receives obligation rights)
6. Issuer receives liquidity, counterparty receives yield-bearing asset

See [Section 13 in SIMPLE.md](./SIMPLE.md#13-annuity-settlement-workflow) for complete example.

## GraphQL Schema

The API uses GraphQL for most operations:

**Queries:**
- `contractFlow.coreContracts.byEntityId` - Get contracts for entity
- `paymentsByEntity` - Get payments for entity
- `swapFlow.coreSwaps.byEntityId` - Get swaps for entity
- `entities.all` - List entities
- `wallets` - Query wallets

**Mutations:**
- `instant` - Send instant payment
- `accept` - Accept incoming payment
- `createObligation` - Create payment obligation
- `acceptObligation` - Accept obligation
- `createSwap` - Create atomic swap
- `completeSwap` - Execute swap
- `deposit` - Deposit funds
- `withdraw` - Withdraw funds

## Authentication & Authorization

### User Roles
- **SuperAdmin** - Full system access
- **Admin** - Administrative operations
- **Manager** - Manage entities and groups
- **Operator** - Execute operations
- **Viewer** - Read-only access
- **ApiClient** - API integration access

### Permissions
- `CryptoOperations` - Cryptographic operations
- `ViewSignatureKeys` - View signing keys
- `ManageSignatureKeys` - Manage signing keys
- `CreateGroup` - Create groups
- `ManageGroupPermissions` - Manage group access
- `CreateDelegationToken` - Create delegation tokens

### Delegation Scope
When acting on behalf of groups:
- `CryptoOperations` - Perform crypto operations for group
- `ReadGroup` - Read group information
- `UpdateGroup` - Update group settings
- `ManageGroupMembers` - Manage group membership

## Supported Assets

- `aud-token-asset` - Australian Dollars
- `usd-token-asset` - US Dollars

## Blockchain Networks

- **Chain 151** - Redbelly Mainnet (Governors)
- **Chain 153** - Redbelly Testnet (Governors)

## Security Notes

- Always use HTTPS in production
- Store JWT tokens securely
- Implement token refresh before expiration
- Use delegation for group operations (maintains audit trail)
- Revoke delegation tokens when access should be removed
- Monitor audit logs for unauthorized access attempts

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    YieldFabric Platform                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌───────────────────┐          │
│  │  Auth Service    │────────▶│  Payments Service │          │
│  │                  │  JWT    │                   │          │
│  │                  │         │                   │          │
│  │  • Authentication│         │  • GraphQL API    │          │
│  │  • Authorization │         │  • Balance Queries│          │
│  │  • Delegation    │         │  • Payments       │          │
│  │  • Groups        │         │  • Obligations    │          │
│  │  • Permissions   │         │  • Atomic Swaps   │          │
│  └──────────────────┘         └───────────────────┘          │
│           │                            │                     │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌───────────────────────────────────────────────┐           │
│  │     Intelligent Accounts (On-Chain)           │           │
│  │                                               │           │
│  │  • Zero-Knowledge Privacy                     │           │
│  │  • Programmable Payments                      │           │
│  │  • Timelocks & Oracles                        │           │
│  │  • Atomic Swaps                               │           │
│  └───────────────────────────────────────────────┘           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## License

See main YieldFabric repository for license information.

