# Documentation Navigation Guide

Choose your path based on your needs and experience level.

---

## For First-Time Users

**Recommended Reading Order:**

1. **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
   - Basic authentication
   - Send your first payment
   - Accept a payment
   
2. **[01-OVERVIEW.md](./01-OVERVIEW.md)** - Understand the platform
   - What are intelligent accounts?
   - Personal vs group accounts
   - How delegation works
   - Basic payment flow

3. **[05-PAYMENTS.md](./05-PAYMENTS.md)** - Master payments
   - Query payment history
   - Send instant payments
   - Accept incoming payments

4. **[04-CONTRACTS.md](./04-CONTRACTS.md)** - Create obligations
   - Invoices and payment commitments
   - Scheduled payments
   - Self-referential structures

5. **[07-WORKFLOWS.md](./07-WORKFLOWS.md)** - See complete examples
   - Annuity securitization
   - Invoice payment
   - Escrow transactions

---

## For Experienced Developers

**Quick Reference Path:**

1. **[02-AUTHENTICATION.md](./02-AUTHENTICATION.md)** - JWT structure and delegation
2. **[08-REFERENCE.md](./08-REFERENCE.md)** - All endpoints and error codes
3. **[SIMPLE.md](./SIMPLE.md)** - Complete API reference in one file

---

## By Use Case

### I Want to Send/Receive Payments

1. [QUICKSTART.md](./QUICKSTART.md) - Basic payment flow
2. [05-PAYMENTS.md](./05-PAYMENTS.md) - Detailed payment guide
3. [03-BALANCES.md](./03-BALANCES.md) - Understanding balance queries

### I Want to Create Invoices or Loans

1. [04-CONTRACTS.md](./04-CONTRACTS.md) - Creating obligations
2. [07-WORKFLOWS.md](./07-WORKFLOWS.md) - Invoice and loan examples
3. [08-REFERENCE.md](./08-REFERENCE.md) - Input parameter reference

### I Want to Build Structured Finance Products

1. [01-OVERVIEW.md](./01-OVERVIEW.md) - Platform capabilities
2. [04-CONTRACTS.md](./04-CONTRACTS.md) - Building obligation structures
3. [06-SWAPS.md](./06-SWAPS.md) - Atomic swaps for trading
4. [07-WORKFLOWS.md](./07-WORKFLOWS.md) - Annuity securitization example

### I Need to Implement Group Operations

1. [01-OVERVIEW.md](./01-OVERVIEW.md#how-delegation-works) - Delegation overview
2. [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) - Delegation JWT creation
3. [03-BALANCES.md](./03-BALANCES.md) - Group balance queries

---

## By Topic

### Authentication
- [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) - Complete auth guide
- [QUICKSTART.md](./QUICKSTART.md#step-1-login-and-save-token) - Quick start

### Balances
- [03-BALANCES.md](./03-BALANCES.md) - Detailed balance guide
- [QUICKSTART.md](./QUICKSTART.md#step-2-check-your-balance) - Quick example

### Contracts/Obligations
- [04-CONTRACTS.md](./04-CONTRACTS.md) - Contract operations
- [07-WORKFLOWS.md](./07-WORKFLOWS.md#annuity-settlement-workflow) - Complete workflow

### Payments
- [05-PAYMENTS.md](./05-PAYMENTS.md) - Payment guide
- [QUICKSTART.md](./QUICKSTART.md#step-3-send-an-instant-payment) - Quick example

### Swaps
- [06-SWAPS.md](./06-SWAPS.md) - Swap operations
- [07-WORKFLOWS.md](./07-WORKFLOWS.md#annuity-settlement-workflow) - Swap in context

### Cryptographic Operations
- [09-CRYPTOGRAPHIC-OPERATIONS.md](./09-CRYPTOGRAPHIC-OPERATIONS.md) - Key management, encryption, signatures
- [02-AUTHENTICATION.md](./02-AUTHENTICATION.md) - JWT structure and delegation

### Reference
- [08-REFERENCE.md](./08-REFERENCE.md) - Error codes, assets, endpoints
- [SIMPLE.md](./SIMPLE.md) - All examples in one file

---

## Documentation Files Overview

| File | Purpose | Audience |
|------|---------|----------|
| **README.md** | Project overview and navigation | Everyone |
| **NAVIGATION.md** | This file - reading guide | Everyone |
| **QUICKSTART.md** | 5-minute getting started | Beginners |
| **01-OVERVIEW.md** | Platform concepts and architecture | New users |
| **02-AUTHENTICATION.md** | Login, delegation, JWT tokens | Developers |
| **03-BALANCES.md** | Balance queries and locked transactions | Developers |
| **04-CONTRACTS.md** | Creating and querying obligations | Developers |
| **05-PAYMENTS.md** | Sending and accepting payments | Developers |
| **06-SWAPS.md** | Atomic swaps | Advanced users |
| **07-WORKFLOWS.md** | End-to-end examples | All users |
| **08-REFERENCE.md** | Quick reference (errors, assets, endpoints) | Developers |
| **09-CRYPTOGRAPHIC-OPERATIONS.md** | Key management, encryption, signatures | Developers |
| **SIMPLE.md** | All API examples in one file | Reference |

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
01-OVERVIEW.md → 04-CONTRACTS.md → 06-SWAPS.md → 07-WORKFLOWS.md
```

### Quick Reference (Experienced Developers)
```
SIMPLE.md or 08-REFERENCE.md
```

---

## Need Help?

- **Can't find something?** Check [SIMPLE.md](./SIMPLE.md) - it has everything
- **Need examples?** See [07-WORKFLOWS.md](./07-WORKFLOWS.md)
- **Error codes?** Check [08-REFERENCE.md](./08-REFERENCE.md#error-handling)
- **JWT issues?** See [02-AUTHENTICATION.md](./02-AUTHENTICATION.md#jwt-token-structure)

