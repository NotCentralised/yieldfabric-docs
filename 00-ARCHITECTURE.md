# YieldFabric Architecture

Complete technical architecture documentation for the YieldFabric platform, covering system design, components, data flows, and integration patterns.

---

## Executive Summary

YieldFabric is a blockchain-based platform for programmable confidential cashflows, built on a microservices architecture with zero-knowledge proof technology. The system enables creation, management, and trading of financial obligations with privacy, atomicity, and programmability.

**Architecture Flow:**
1. **Client Layer**: Web applications (React), API clients (GraphQL/REST), and AI agents (MCP)
2. **Services Layer**: Three core services (Auth, Agents, Payments) sharing a knowledge base (Fuseki) and service-specific SQL databases
3. **Library Layer**: Shared Rust crates (core, vault, mq, zkp, encryption) embedded in services
4. **Message Queue**: RabbitMQ — per-user sequential processing, relay wallet operations, idempotency
5. **Blockchain Layer**: Smart contracts for confidential payments, obligations, swaps, distributions, and account abstraction

**Core Principles:**
- **Confidentiality**: Zero-knowledge proofs protect transaction amounts and balances
- **Atomicity**: All-or-nothing execution guarantees
- **Programmability**: Time-based and event-based payment conditions
- **Modularity**: Microservices architecture with clear separation of concerns
- **Scalability**: Asynchronous message queue processing

---

## System Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │   Web App    │  │  API Clients │  │  AI Agents    │               │
│  │  (React)     │  │  (GraphQL)   │  │   (MCP)       │               │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘               │
│         │ WebSocket       │ GraphQL/REST     │ MCP                   │
└─────────┼─────────────────┼──────────────────┼───────────────────────┘
          └─────────────────┼──────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Services Layer                                │
│                                                                      │
│  ┌──────────────────┐ ┌──────────────────┐ ┌───────────────────────┐ │
│  │  Auth Service    │ │  Agents Service  │ │   Payments Service    │ │
│  │                  │ │                  │ │                       │ │
│  │ • JWT Auth       │ │ • AI Support     │ │ • GraphQL API         │ │
│  │ • Key Management │ │ • Knowledge      │ │ • REST Balance API    │ │
│  │ • Crypto Ops     │ │   Graph / MCP    │ │ • WebSocket Server    │ │
│  │ • Delegation     │ │ • Chat           │ │ • Contracts/Payments  │ │
│  │ • Groups         │ │ • Contextual     │ │ • Swaps/Distributions │ │
│  │                  │ │   Reasoning      │ │ • Workflows           │ │
│  └────────┬─────────┘ └────────┬─────────┘ └───────────┬───────────┘ │
│           │                    │                       │             │
│           └────────────────────┼───────────────────────┘             │
│                                ▼                                     │
│  ┌──────────────────────────────────────────────┐                    │
│  │    Shared Knowledge Base (Apache Jena Fuseki)│                    │
│  │    • Entities  • Contracts  • Swaps          │                    │
│  │    • Payments  • Knowledge Graph             │                    │
│  │    ⚠️ Permissioned — users see own data only │                    │
│  └──────────────────────────────────────────────┘                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │ Auth SQL     │  │ Agents SQL   │  │ Payments SQL  │               │
│  │ (Encrypted   │  │ (Chat,       │  │ (Encrypted    │               │
│  │  User Keys)  │  │  Sessions)   │  │  Payment Data)│               │
│  └──────────────┘  └──────────────┘  └───────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┤ Payments Service embeds:
            │               │ • yieldfabric-core (types, resolvers, stores)
            │               │ • yieldfabric-vault (ZK, signing, blockchain)
            │               │ • yieldfabric-mq (queue consumers, validation)
            │               │ • yieldfabric-zkp (proof circuits)
            ▼               │
┌───────────────────────────────────────────────────────────────────────┐
│                     Message Queue (RabbitMQ)                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ • Per-user sequential queues  • Concurrent across users        │   │
│  │ • Validation → Execution pipeline  • Idempotency + retry       │   │
│  │ • Automatic execution (user vault key)                         │   │
│  │ • Relay operations (system key): identity, claims, token deploy│   │
│  └────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
                            │
                    Vault library calls
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     Blockchain Layer                                  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Intelligent Accounts (ConfidentialAccount / Factory)         │    │
│  │  • Account abstraction  • Policy-based access control         │    │
│  │  • Multi-signature support  • ConfidentialGroup               │    │
│  └───────────────────────────────────────────────────────────────┘    │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │  Confidential Finance Smart Contracts                         │    │
│  │  • ConfidentialVault (payments, distributions)                │    │
│  │  • ConfidentialObligation (NFT obligations)                   │    │
│  │  • ConfidentialSwap + ConfidentialSwapRoll (swaps, repos)     │    │
│  │  • ConfidentialWallet (balance management)                    │    │
│  │  • ConfidentialOracle (event verification)                    │    │
│  │  • ConfidentialAccessControl (policies, ZK access checks)     │    │
│  │  • ConfidentialTreasury, DAOTreasury, ConfidentialServiceBus  │    │
│  │  • ZK Proof Verification  • State Management                  │    │
│  └───────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Core Services

### Auth Service (`yieldfabric-auth`)

**Purpose:** Manages authentication, authorization, and cryptographic key storage.

**Responsibilities:**
- User authentication (JWT generation and validation)
- Access control for individuals and groups
- Delegation token management
- Key pair generation and management
- Cryptographic operations (sign, verify, encrypt, decrypt)
- Entity and group management

**Data Storage:**
- **Shared Knowledge Base (Fuseki)**: Entity relationships, user/group data (with permissioned access)
- **Service-Specific SQL**: Encrypted user keys stored separately for security isolation

**Technology Stack:**
- Rust, JWT (jsonwebtoken), Argon2, Apache Jena Fuseki, PostgreSQL, `yieldfabric-encryption` (key pair providers: OpenSSL/HSM/Hybrid)

### Agents Service (`yieldfabric-agents`)

**Purpose:** AI-powered user support using the knowledge base.

**Responsibilities:**
- AI-powered user support and assistance
- Knowledge graph querying and reasoning
- Model Context Protocol (MCP) implementation
- Chat and conversational interfaces
- Workflow automation through AI

**Data Storage:**
- **Shared Knowledge Base (Fuseki)**: System-wide knowledge graph, entities, contracts, payments, swaps
- **Service-Specific SQL**: Conversation history, sessions

**Technology Stack:**
- Rust, Apache Jena Fuseki, PostgreSQL, AI/LLM integration libraries

### Payments Service (`yieldfabric-payments`)

**Purpose:** Business logic for contracts, payments, swaps, distributions, and workflows. Uses message queue for policy enforcement and blockchain interaction.

**Responsibilities:**
- Contract (obligation) management
- Payment processing (deposits, instant, obligation, swap payments)
- Distribution processing (one-to-many Merkle-tree-based payments)
- Swap operations (atomic swaps, repo swaps, repo rolling)
- Workflow execution (onramp, composed operations)
- GraphQL resolvers (exposed directly at `/graphql`)
- WebSocket server for real-time payment/balance notifications
- MCP tools for Agents Service
- Market data feeds (equity prices via external APIs)
- Balance endpoint (`/balance`) for REST-based balance queries

**Data Storage:**
- **Shared Knowledge Base (Fuseki)**: Entities, contracts, swaps, payments (permissioned access)
- **Service-Specific SQL**: Encrypted payment data, messages, transactions, positions

**Technology Stack:**
- Rust, async-graphql, Axum, Apache Jena Fuseki, PostgreSQL, RabbitMQ (via Lapin)

### Vault Library (`yieldfabric-vault`)

**Purpose:** Cryptographic operations and blockchain interface. A **Rust library** (not a standalone service) consumed by `yieldfabric-payments` and `yieldfabric-mq`. Message queue consumers call vault functions to execute on-chain operations.

**Responsibilities:**
- Zero-knowledge proof generation
- Transaction signing and blockchain calls (via Alloy)
- Encrypted balance queries and decryption
- Payment, obligation, swap, and distribution operations
- Oracle proof generation
- Relay wallet operations (identity registration, claim issuance)

**Technology Stack:**
- Rust, Alloy (Ethereum interaction), depends on `yieldfabric-zkp`, `yieldfabric-zkp-object`, `yieldfabric-encryption`

### Shared Libraries

Several Rust crates are used as shared libraries across services:

| Crate | Purpose | Used By |
|-------|---------|---------|
| `yieldfabric-core` | GraphQL types, resolvers, data stores (Fuseki), entity/contract/payment models | Payments |
| `yieldfabric-vault` | Blockchain interface, ZK proofs, balance queries, transaction signing | Payments, MQ |
| `yieldfabric-mq` | Message queue consumers, validation, execution, idempotency | Payments |
| `yieldfabric-zkp` | Zero-knowledge proof circuit wrappers (Circom) | Vault, Payments |
| `yieldfabric-zkp-object` | ZK proof data structures and serialization | Vault |
| `yieldfabric-encryption` | Key pair management, AES-256-GCM encryption, provider abstraction (OpenSSL/HSM) | Auth, Vault |
| `yieldfabric-dlt` | DLT integration library (staticlib + rlib) | CLI |
| `yieldfabric-cli` | Command-line tools for administration and testing | — |

### Message Queue System (RabbitMQ)

**Purpose:** Policy enforcement and event-based messaging between Payments Service and blockchain.

**Execution Model:**
- **Sequential per User**: Each user's actions processed sequentially (one at a time)
- **Concurrent across Users**: Many users can execute actions simultaneously

**Responsibilities:**
- Policy enforcement for Payments Service
- Event-based messaging with blockchain (via Vault library)
- User-specific queue processing
- Message validation and execution coordination
- Idempotency management
- **Relay wallet operations**: Identity registration, claim issuance, token deployment, and compliance proxy deployment — executed using a system relay key (not user keys)
- **Automatic vs. manual execution**: Messages can be executed automatically (signed by user's vault key) or queued for manual signature (user signs via UX)

**Technology Stack:**
- RabbitMQ (via Lapin), PostgreSQL (message persistence)

### Shared Knowledge Base (Apache Jena Fuseki)

**Purpose:** Centralized RDF triplestore containing system-wide knowledge graph.

**Data Stored:**
- Entities (users and groups)
- Contracts (obligations)
- Swaps
- Payments
- System-wide knowledge graph relationships

**Access Control:**
- All access permissioned through Auth Service
- Users can only access their own data and authorized groups
- SPARQL queries for complex relationships

**Technology Stack:**
- Apache Jena Fuseki, TDB2 (triplestore database)

### Smart Contracts (`yieldfabric-smart-contracts`)

**Purpose:** On-chain execution of confidential operations.

**Key Contracts:**
- **ConfidentialVault**: Private token transfers with ZK proofs, distributions (Merkle-tree-based one-to-many payments)
- **ConfidentialObligation**: NFT-based payment obligations (mint, accept, transfer, expire)
- **ConfidentialSwap**: Atomic asset exchanges, repo swaps with collateral
- **ConfidentialSwapRoll**: Facet for two-step repo rolling (initiate roll / complete roll) via delegatecall
- **ConfidentialWallet**: Account balance management (encrypted balances, outstanding tracking)
- **ConfidentialOracle**: External event verification (oracle key/value conditions on payments)
- **ConfidentialAccessControl**: Policy management, multi-signature verification, ZK-proof-based access checks
- **ConfidentialAccount / ConfidentialAccountFactory**: Account abstraction — programmable account logic, account deployment
- **ConfidentialGroup**: Group account management on-chain
- **ConfidentialTreasury**: Meta-transaction ERC-20 wrapper with treasurer-only mint/burn
- **ConfidentialServiceBus**: On-chain service bus for event routing
- **DAOTreasury**: Fee collection and revenue management

**Supporting Libraries:**
- `AccessControlLib`, `PolicyVerificationLib`, `SignatureVerificationLib`, `MetaTransactionLib`

**Technology Stack:**
- Solidity, Zero-knowledge proof verifiers (Circom-generated), Hardhat

---

## Data Flow

### Request Flow: Create Obligation

```
1. Client → GraphQL Mutation: createObligation
2. Payments Service (GraphQL Resolver) → Validate JWT & Input
3. Create Message → Store in PostgreSQL → Submit to Message Queue
4. User Queue Manager (sequential per user) → Validation Queue → Execution Queue
5. Execution Queue Consumer → Calls Vault Layer
   → Generate ZK proofs → Sign transaction → Execute on blockchain
6. Graph Processing Queue → Update database → Create contract/payment records
7. Response → Update message status → Return result to client
```

### Request Flow: Accept Payment

```
1. Client → GraphQL Mutation: accept
2. Payments Service → Validate payment status & unlock conditions
3. Create retrieve message → Submit to Message Queue
4. Vault Layer: Retrieve Operation
   → Get payment from contract → Calculate vested amount
   → Generate receiver proof → Sign transaction → Execute on blockchain
5. Retrieve Processor → Update payment status → Update balances → Create positions
6. Response → Return acceptance result
```

### Request Flow: Create Distribution

```
1. Client → GraphQL Mutation: createDistribution (assetId, recipients[], amounts[])
2. Payments Service (GraphQL Resolver) → Validate JWT & Input
3. Create Message → Store in PostgreSQL → Submit to Message Queue
4. User Queue Manager (sequential per user) → Validation Queue → Execution Queue
5. Execution Queue Consumer → Calls Vault Layer
   → Build Merkle tree of (recipient, amount) leaves
   → Generate ZK proof for total amount
   → Sign transaction → Execute createDistribution on ConfidentialVault
6. Distribution Processor → Create DISTRIBUTION contract + one RECEIVABLE payment per recipient
7. Each recipient accepts via standard Accept flow → acceptDistribution on-chain (Merkle proof)
```

---

## Security Architecture

### Authentication & Authorization

- **JWT-Based Authentication**: Tokens issued by Auth Service, validated on every request
- **Delegation System**: Users can act on behalf of groups with delegation tokens
- **Permissioned Access**: All knowledge base access controlled by Auth Service

### Cryptographic Security

- **Zero-Knowledge Proofs**: Amounts and balances encrypted, proofs verify correctness without revealing values
- **Key Management**: Private keys encrypted at rest, stored in Auth Service, signing via Vault Layer
- **Transaction Signing**: All blockchain transactions signed by Vault Layer (called by Payments Service)

### Data Privacy

- **Confidential Transactions**: Payment amounts and balances encrypted, only parties can decrypt
- **Encrypted Payment Data**: Payment information in Payments Service SQL is encrypted, accessible only using user keys from Auth Service
- **Container Security**: Each service runs in separate container with network isolation

---

## Technology Stack

### Backend
- **Language**: Rust
- **Web Framework**: Axum
- **GraphQL**: async-graphql
- **Database**: PostgreSQL (SQLx)
- **Message Queue**: RabbitMQ (Lapin)
- **Blockchain**: Alloy (Ethereum interaction)
- **Cryptography**: Zero-knowledge proofs (Circom)

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **GraphQL Client**: Apollo Client
- **Styling**: Tailwind CSS

### Infrastructure
- **Database**: PostgreSQL
- **Message Broker**: RabbitMQ
- **Knowledge Base**: Apache Jena Fuseki (with Oxigraph fallback)
- **Blockchain**: Ethereum-compatible networks

---

## Summary

YieldFabric's architecture provides:

1. **Modular Design**: Clear separation — services (Auth, Agents, Payments), shared libraries (core, vault, mq, zkp, encryption), and smart contracts
2. **Scalability**: Horizontal scaling with stateless services; per-user sequential MQ ensures correctness while allowing cross-user concurrency
3. **Reliability**: Message queue with persistence, retry logic, and idempotency management
4. **Security**: Zero-knowledge proofs, encrypted balances, secure key management (OpenSSL/HSM), relay wallet isolation
5. **Flexibility**: GraphQL + REST APIs, WebSocket real-time notifications, MCP for AI agent integration, workflow system
6. **Completeness**: Payments, distributions, obligations, atomic swaps, repo swaps with rolling, oracle conditions, linear vesting — all with on-chain enforcement

The architecture supports complex financial operations — from simple payments to multi-tranche structured products — while maintaining security, privacy, and performance requirements.
