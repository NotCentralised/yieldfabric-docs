# YieldFabric Architecture

Complete technical architecture documentation for the YieldFabric platform, covering system design, components, data flows, and integration patterns.

---

## Executive Summary

YieldFabric is a blockchain-based platform for programmable confidential cashflows, built on a microservices architecture with zero-knowledge proof technology. The system enables creation, management, and trading of financial obligations with privacy, atomicity, and programmability.

**Architecture Flow:**
1. **Client Layer**: Web applications, API clients, and AI agents
2. **API Gateway**: Request routing, authentication, and rate limiting
3. **Services Layer**: Three core services (Auth, Agents, Payments) sharing a knowledge base
4. **Message Queue**: Policy enforcement and event-based messaging (Payments → Blockchain)
5. **Blockchain & Vault**: On-chain execution and cryptographic operations

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
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Web App    │  │  API Clients │  │  AI Agents   │           │
│  │  (React)     │  │  (GraphQL)   │  │   (MCP)      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              API Gateway (GraphQL + REST)                 │  │
│  │  • Request Routing  • Authentication  • Rate Limiting     │  │
│  │  • Request Validation  • Response Formatting              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Services Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │  Auth Service    │  │  Agents Service  │  │ Payments Service││
│  │  [Container]     │  │  [Container]     │  │  [Container]    ││
│  │                  │  │                  │  │                 ││
│  │ • Access         │  │ • AI Support     │  │ • Contracts     ││
│  │   Management     │  │ • Knowledge      │  │ • Payments      ││
│  │ • JWT Auth       │  │   Graph          │  │ • Swaps         ││
│  │ • Key Mgmt       │  │ • MCP            │  │ • Workflows     ││
│  │ • Delegation     │  │ • Chat           │  │ • GraphQL       ││
│  │                  │  │ • Advanced       │  │ • MCP Tools     ││
│  │                  │  │   Contextual     │  │   (for Agents)  ││
│  │                  │  │   Reasoning      │  │                 ││
│  │ 🔒 Security      │  │ 🔒 Security      │  │ 🔒 Security     ││
│  │   Isolation      │  │   Isolation      │  │   Isolation     ││
│  └──────────────────┘  └──────────────────┘  └─────────────────┘│
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                           ▼                                     │
│         ┌──────────────────────────────────────┐                │
│         │   Shared Knowledge Base (Fuseki)     │                │
│         │   • Entities (Users & Groups)        │                │
│         │   • Contracts (Obligations)          │                │
│         │   • Swaps                            │                │
│         │   • Payments                         │                │
│         │   • System-wide Knowledge Graph      │                │
│         │                                      │                │
│         │   ⚠️ Permissioned Access             │                │
│         │   • Access controlled by Auth        │                │
│         │   • Users can only access their      │                │
│         │     own data and authorized groups   │                │
│         └──────────────────────────────────────┘                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │ Auth SQL     │  │ Agents SQL   │  │ Payments SQL  │          │
│  │ (Service-    │  │ (Service-    │  │ (Service-     │          │
│  │  Specific)   │  │  Specific)   │  │  Specific)    │          │
│  │              │  │              │  │               │          │
│  │ • User Keys  │  │ • Chat       │  │ • Encrypted   │          │
│  │   (Encrypted)│  │   History    │  │   Payment     │          │
│  │ • Key Mgmt   │  │ • Sessions   │  │   Data        │          │
│  │              │  │              │  │               │          │
│  │ ⚠️ Keys      │  │              │  │ ⚠️ Encrypted  │          │
│  │   Stored     │  │              │  │   & Accessible│          │
│  │   Separately │  │              │  │   Only by     │          │
│  │   by Auth    │  │              │  │   User Keys   │          │
│  └──────────────┘  └──────────────┘  └───────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Vault Layer (Middle Layer)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Cryptographic Operations & Blockchain Interface          │  │
│  │  • ZK Proof Generation  • Transaction Signing             │  │
│  │  • Balance Queries  • Crypto Operations                   │  │
│  │  • Called by Payments Service via Message Queue           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Queue Layer                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              RabbitMQ Message Broker                      │  │
│  │  • Policy Enforcement  • Event-based Messaging            │  │
│  │  • User Queues  • Validation  • Execution                 │  │
│  │  • Message Persistence  • Retry Logic  • Idempotency      │  │
│  │                                                           │  │
│  │  ⚠️ Execution Model:                                      │  │
│  │  • Sequential per user (one action at a time per user)    │  │
│  │  • Concurrent across users (many users simultaneously)    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Gas Station / Relay Wallet Sub-Layer               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  • Gas Fee Management  • Transaction Relaying             │  │
│  │  • Relay Wallet Operations  • Fee Estimation              │  │
│  │  • Batch Transaction Processing  • Gas Optimization       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Blockchain Layer                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │    Intelligent Account Smart Contract                     │  │
│  │    (Abstract Account)                                     │  │
│  │    • Account abstraction layer                            │  │
│  │    • Programmable account logic                           │  │
│  │    • Multi-signature support                              │  │
│  │    • Custom execution rules                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │    Confidential Finance Smart Contracts                   │  │
│  │    • ConfidentialVault  • ConfidentialObligation          │  │
│  │    • ConfidentialSwap   • ConfidentialWallet              │  │
│  │    • ConfidentialOracle • DAOTreasury                     │  │
│  │    • ZK Proof Verification  • State Management            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
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
- Rust, JWT (jsonwebtoken), Argon2, Apache Jena Fuseki, PostgreSQL

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

**Purpose:** Business logic for contracts, payments, swaps, and workflows. Uses message queue for policy enforcement and blockchain interaction.

**Responsibilities:**
- Contract (obligation) management
- Payment processing
- Swap operations
- Workflow execution
- GraphQL resolvers (exposed directly at `/graphql`)
- MCP tools for Agents Service

**Data Storage:**
- **Shared Knowledge Base (Fuseki)**: Entities, contracts, swaps, payments (permissioned access)
- **Service-Specific SQL**: Encrypted payment data, messages, transactions, positions

**Technology Stack:**
- Rust, async-graphql, Axum, Apache Jena Fuseki, PostgreSQL, RabbitMQ (via Lapin)

### Vault Layer (`yieldfabric-vault`)

**Purpose:** Cryptographic operations and blockchain interface. Library/component called by Payments Service message queue consumers.

**Responsibilities:**
- Zero-knowledge proof generation
- Transaction signing
- Balance queries
- Payment, obligation, and swap operations
- Oracle proof generation

**Technology Stack:**
- Rust, Zero-knowledge proof circuits (Circom), Alloy (Ethereum interaction)

### Message Queue System (RabbitMQ)

**Purpose:** Policy enforcement and event-based messaging between Payments Service and blockchain.

**Execution Model:**
- **Sequential per User**: Each user's actions processed sequentially (one at a time)
- **Concurrent across Users**: Many users can execute actions simultaneously

**Responsibilities:**
- Policy enforcement for Payments Service
- Event-based messaging with blockchain
- User-specific queue processing
- Message validation and execution coordination
- Idempotency management

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
- **ConfidentialVault**: Private token transfers with ZK proofs
- **ConfidentialObligation**: NFT-based payment obligations
- **ConfidentialSwap**: Atomic asset exchanges
- **ConfidentialWallet**: Account balance management
- **ConfidentialOracle**: External event verification
- **DAOTreasury**: Fee collection and revenue management

**Technology Stack:**
- Solidity, Zero-knowledge proof verifiers, Hardhat

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

1. **Modular Design**: Clear separation of concerns across services
2. **Scalability**: Horizontal scaling with stateless services
3. **Reliability**: Message queue with persistence and retry logic
4. **Security**: Zero-knowledge proofs, encrypted data, secure key management
5. **Flexibility**: GraphQL API, workflow system, extensible design
6. **Performance**: Async processing, connection pooling, caching

The architecture supports complex financial operations while maintaining security, privacy, and performance requirements.
