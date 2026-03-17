# Documentation Navigation Guide

Choose your path based on your needs and experience level.

---

## For First-Time Users

**Recommended Reading Order:**

1. **[QUICKSTART.md](./QUICKSTART.md)** — Get started in 5 minutes
   - Basic authentication
   - Deposit funds
   - Send your first payment
   - Accept a payment

2. **[01-OVERVIEW.md](./01-OVERVIEW.md)** — Understand the platform
   - What are intelligent accounts?
   - Personal vs group accounts
   - How delegation works
   - Payment flow, distributions, repo swaps

3. **[05-PAYMENTS.md](./05-PAYMENTS.md)** — Master payments
   - Query payment history
   - Send instant payments
   - Accept incoming payments
   - Create distributions (one-to-many)

4. **[04-CONTRACTS.md](./04-CONTRACTS.md)** — Create obligations
   - Invoices and payment commitments
   - Scheduled payments with time locks
   - Self-referential structures

5. **[07-WORKFLOWS.md](./07-WORKFLOWS.md)** — See complete examples
   - Annuity securitization
   - Invoice payment
   - Escrow transactions
   - Distribution workflow
   - Repo rolling workflow

---

## For Experienced Developers

**Quick Reference Path:**

1. **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** — JWT structure and delegation
2. **[08-REFERENCE.md](./08-REFERENCE.md)** — All endpoints, input types, status values
3. **[SIMPLE.md](./SIMPLE.md)** — Complete curl examples in one file

---

## By Use Case

### I Want to Send/Receive Payments

1. [QUICKSTART.md](./QUICKSTART.md) — Basic payment flow
2. [05-PAYMENTS.md](./05-PAYMENTS.md) — Detailed payment guide
3. [03-BALANCES.md](./03-BALANCES.md) — Understanding balance queries

### I Want to Distribute to Multiple Recipients

1. [05-PAYMENTS.md](./05-PAYMENTS.md) — Distribution creation and acceptance
2. [07-WORKFLOWS.md](./07-WORKFLOWS.md) — Distribution workflow example
3. [04-CONTRACTS.md](./04-CONTRACTS.md) — Distribution contracts

### I Want to Create Invoices or Loans

1. [04-CONTRACTS.md](./04-CONTRACTS.md) — Creating obligations
2. [07-WORKFLOWS.md](./07-WORKFLOWS.md) — Invoice and loan examples
3. [08-REFERENCE.md](./08-REFERENCE.md) — Input parameter reference

### I Want to Build Structured Finance Products

1. [01-OVERVIEW.md](./01-OVERVIEW.md) — Platform capabilities
2. [04-CONTRACTS.md](./04-CONTRACTS.md) — Building obligation structures
3. [06-SWAPS.md](./06-SWAPS.md) — Atomic swaps, repo swaps, collateral, rolling
4. [07-WORKFLOWS.md](./07-WORKFLOWS.md) — Annuity securitization, repo rolling
5. [10_STRUCTURING.md](./10_STRUCTURING.md) — Financial structuring patterns
6. [11_ABS.md](./11_ABS.md) — Asset-backed securitization

### I Need to Implement Group Operations

1. [01-OVERVIEW.md](./01-OVERVIEW.md#how-delegation-works) — Delegation overview
2. [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) — Delegation JWT creation
3. [03-BALANCES.md](./03-BALANCES.md) — Group balance queries

### I Need Key Management & Encryption

1. [09-CRYPTOGRAPHIC-OPERATIONS.md](./09-CRYPTOGRAPHIC-OPERATIONS.md) — Key pairs, encryption, signing
2. [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) — JWT structure and key providers

### I Want to Understand the Architecture

1. [00-ARCHITECTURE.md](./00-ARCHITECTURE.md) — Services, libraries, smart contracts, data flows
2. [01-OVERVIEW.md](./01-OVERVIEW.md) — Platform concepts

---

## By Topic

### Architecture
- [00-ARCHITECTURE.md](./00-ARCHITECTURE.md) — Services, shared libraries, smart contracts, message queue
- [01-OVERVIEW.md](./01-OVERVIEW.md) — Platform overview and concepts

### Authentication
- [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) — Complete auth guide (JWT, delegation, groups, API keys)
- [QUICKSTART.md](./QUICKSTART.md#step-1-login-and-save-token) — Quick start

### Balances
- [03-BALANCES.md](./03-BALANCES.md) — Detailed balance guide
- [QUICKSTART.md](./QUICKSTART.md#step-2-check-your-balance) — Quick example

### Contracts/Obligations
- [04-CONTRACTS.md](./04-CONTRACTS.md) — Contract operations (single, composed, distribution)
- [07-WORKFLOWS.md](./07-WORKFLOWS.md#annuity-settlement-workflow) — Complete workflow

### Payments
- [05-PAYMENTS.md](./05-PAYMENTS.md) — Payments guide (instant, obligations, distributions)
- [QUICKSTART.md](./QUICKSTART.md#step-3-send-an-instant-payment) — Quick example

### Swaps & Repos
- [06-SWAPS.md](./06-SWAPS.md) — Atomic swaps, repo swaps, collateral, rolling
- [07-WORKFLOWS.md](./07-WORKFLOWS.md) — Swap and repo rolling in context

### Cryptographic Operations
- [09-CRYPTOGRAPHIC-OPERATIONS.md](./09-CRYPTOGRAPHIC-OPERATIONS.md) — Key management, encryption, signatures
- [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) — JWT structure and delegation

### Structuring & Securitization
- [10_STRUCTURING.md](./10_STRUCTURING.md) — Financial structuring patterns and building blocks
- [11_ABS.md](./11_ABS.md) — Asset-backed securitization guide

### Reference
- [08-REFERENCE.md](./08-REFERENCE.md) — Endpoints, input types, status values, error codes
- [SIMPLE.md](./SIMPLE.md) — All curl examples in one file

---

## Documentation Files Overview

| File | Purpose | Audience |
|------|---------|----------|
| **README.md** | Project overview and navigation | Everyone |
| **NAVIGATION.md** | This file — reading guide | Everyone |
| **QUICKSTART.md** | 5-minute getting started | Beginners |
| **00-ARCHITECTURE.md** | Technical architecture (services, libraries, contracts) | Architects / Advanced |
| **01-OVERVIEW.md** | Platform concepts and features | New users |
| **02-AUTHENTICATION.md** | Login, delegation, JWT, API keys, groups | Developers |
| **03-BALANCES.md** | Balance queries and locked transactions | Developers |
| **04-CONTRACTS.md** | Creating and querying obligations | Developers |
| **05-PAYMENTS.md** | Payments (instant, obligations, distributions) | Developers |
| **06-SWAPS.md** | Atomic swaps, repo swaps, collateral, rolling | Developers / Advanced |
| **07-WORKFLOWS.md** | End-to-end examples (annuities, distributions, repos) | All users |
| **08-REFERENCE.md** | All endpoints, input types, status values, error codes | Developers |
| **09-CRYPTOGRAPHIC-OPERATIONS.md** | Key management, encryption, signatures | Developers |
| **10_STRUCTURING.md** | Financial structuring patterns and building blocks | Structuring specialists |
| **11_ABS.md** | Asset-backed securitization guide | Finance / Advanced |
| **SIMPLE.md** | All API curl examples in one file | Reference |

---

## Recommended Learning Path

### Beginner (New to YieldFabric)
```
QUICKSTART.md → 01-OVERVIEW.md → 05-PAYMENTS.md
```

### Intermediate (Building Applications)
```
02-AUTHENTICATION.md → 03-BALANCES.md → 05-PAYMENTS.md → 04-CONTRACTS.md → 09-CRYPTOGRAPHIC-OPERATIONS.md → 08-REFERENCE.md
```

### Advanced (Structured Finance)
```
01-OVERVIEW.md → 04-CONTRACTS.md → 06-SWAPS.md → 07-WORKFLOWS.md → 10_STRUCTURING.md → 11_ABS.md
```

### Architecture Deep-Dive
```
00-ARCHITECTURE.md → 09-CRYPTOGRAPHIC-OPERATIONS.md → 08-REFERENCE.md
```

### Quick Reference (Experienced Developers)
```
SIMPLE.md or 08-REFERENCE.md
```

---

## Need Help?

- **Can't find something?** Check [SIMPLE.md](./SIMPLE.md) — it has all the curl examples
- **Need examples?** See [07-WORKFLOWS.md](./07-WORKFLOWS.md)
- **Error codes?** Check [08-REFERENCE.md](./08-REFERENCE.md#error-handling)
- **JWT issues?** See [02-AUTHENTICATION.md](./02-AUTHENTICATION.md#jwt-token-structure)
- **Input types?** Check [08-REFERENCE.md](./08-REFERENCE.md#graphql-input-types)
- **Architecture?** See [00-ARCHITECTURE.md](./00-ARCHITECTURE.md)
