# YieldFabric Contract YAML DSL

## Overview

This directory contains the specification, examples, and implementation guide for a YAML-based Domain Specific Language (DSL) for defining structured financial contracts in YieldFabric.

## What is the YAML DSL?

The YAML DSL allows you to define complex financial contracts (bonds, loans, mortgages, structured products) in a human-readable format that maps directly to YieldFabric's composed contract system. Instead of writing GraphQL mutations or API calls, you can define contracts in YAML and have them automatically converted to the appropriate system calls.

## Key Features

- **Human-Readable**: Define contracts in YAML instead of JSON/GraphQL
- **Type-Safe**: JSON Schema validation ensures contract correctness
- **Product-Specific**: Specialized schemas for bonds, loans, mortgages, structured products
- **Payment Scheduling**: Automatic generation of payment schedules from frequency specifications
- **Oracle Support**: Define oracle-based unlock conditions for payments
- **Legal Integration**: Link contracts to legal documents and generate summaries

## Quick Start

### Example: Creating a Bond

```yaml
contract:
  metadata:
    name: "5-Year Corporate Bond"
    type: bond
    version: "1.0"
  
  parties:
    issuer:
      entity_id: "corporation@yieldfabric.com"
    counterpart:
      entity_id: "investor@yieldfabric.com"
  
  obligations:
    - name: "Quarterly Coupons"
      denomination: "usd-token-asset"
      notional: "100000000000000000000000"
      expiry: "2031-12-31T23:59:59Z"
      payment_schedule:
        amount: "1250000000000000000000"
        frequency: quarterly
        start_date: "2026-03-31T00:00:00Z"
        end_date: "2031-12-31T23:59:59Z"
    
    - name: "Principal Redemption"
      denomination: "usd-token-asset"
      notional: "100000000000000000000000"
      expiry: "2031-12-31T23:59:59Z"
      payment_schedule:
        amount: "100000000000000000000000"
        payments:
          - date: "2031-12-31T23:59:59Z"
            unlock_sender: "2031-12-31T23:59:59Z"
            unlock_receiver: "2031-12-31T23:59:59Z"
  
  composed_contract:
    name: "5-Year Corporate Bond"
    description: "Quarterly coupon bond with principal redemption"
```

## Files in This Directory

### Specification Documents

- **`YAML_DSL_PROPOSAL.md`** - Complete specification of the YAML DSL with examples for all contract types
- **`contract_schema.json`** - JSON Schema for validating YAML contract files
- **`IMPLEMENTATION_GUIDE.md`** - Detailed implementation guide with code examples

### Example Contracts

- **`examples/bond_example.yaml`** - Complete bond contract example
- **`examples/loan_example.yaml`** - Complete loan contract example
- **`examples/mortgage_example.yaml`** - Complete mortgage contract example
- **`examples/structured_product_example.yaml`** - Complete structured product example

## Supported Contract Types

### 1. Bonds
- Coupon payment streams
- Principal redemption
- Zero-coupon bonds
- Callable/puttable bonds

### 2. Loans
- Principal repayment streams
- Interest payment streams
- Amortization schedules
- Balloon payments

### 3. Mortgages
- Principal and Interest (P&I) payments
- Property tax escrow
- Insurance escrow
- Adjustable rate mortgages

### 4. Structured Products
- Capital protection components
- Equity participation
- Barrier conditions
- Oracle-based payouts

## How It Works

### Current System Architecture

```
User → GraphQL API → createObligation → MQ → Contract Created
                    ↓
              Workflow API → Composed Contract Created
```

### With YAML DSL

```
User → YAML File → Parser → Validator → Converter → GraphQL/Workflow API → Contract Created
```

## Implementation Status

### Phase 1: Specification ✅
- [x] YAML schema design
- [x] JSON Schema validation
- [x] Example contracts for all types
- [x] Implementation guide

### Phase 2: Parser & Validator (Planned)
- [ ] Rust crate `yieldfabric-contract-dsl`
- [ ] YAML parser
- [ ] JSON Schema validator
- [ ] Type definitions

### Phase 3: GraphQL Converter (Planned)
- [ ] Convert YAML to `CreateObligationInput`
- [ ] Convert to workflow API format
- [ ] Payment schedule generator

### Phase 4: CLI Tool (Planned)
- [ ] `yf-contract validate` command
- [ ] `yf-contract generate` command
- [ ] `yf-contract create` command
- [ ] `yf-contract template` command

### Phase 5: Integration (Planned)
- [ ] REST API endpoint for YAML upload
- [ ] GraphQL mutation for YAML input
- [ ] Frontend integration

## Usage Examples

### Validate a Contract

```bash
yf-contract validate --file examples/bond_example.yaml
```

### Generate GraphQL Mutations

```bash
yf-contract generate --file examples/bond_example.yaml --format graphql
```

### Create Contract via API

```bash
yf-contract create --file examples/bond_example.yaml --token $JWT_TOKEN --workflow
```

### Generate Template

```bash
yf-contract template --contract-type bond --output my_bond.yaml
```

## Mapping to YieldFabric System

### YAML Obligation → GraphQL CreateObligationInput

| YAML Field | GraphQL Field | Notes |
|------------|----------------|-------|
| `name` | `data.name` | Stored in contract metadata |
| `denomination` | `denomination` | Asset ID for payments |
| `notional` | `notional` | Principal amount |
| `expiry` | `expiry` | Contract expiration date |
| `counterpart` | `counterpart` | Entity name or wallet ID |
| `obligor` | `obligor` | Entity name or wallet ID |
| `payment_schedule.payments` | `initial_payments.payments` | Array of VaultPaymentInput |

### YAML Payment → VaultPaymentInput

| YAML Field | GraphQL Field | Notes |
|------------|----------------|-------|
| `unlock_sender` | `unlock_sender` | Date when sender can unlock |
| `unlock_receiver` | `unlock_receiver` | Date when receiver can unlock |
| `oracle_conditions.*` | `oracle_*` | Oracle configuration |
| `linear_vesting` | `linear_vesting` | Vesting schedule flag |

## Advanced Features

### Oracle Conditions

Define conditional payments based on external data:

```yaml
payments:
  - date: "2026-12-31T23:59:59Z"
    unlock_sender: "2026-12-31T23:59:59Z"
    unlock_receiver: "2026-12-31T23:59:59Z"
    oracle_conditions:
      oracle_address: "0x1234..."
      oracle_owner: "oracle@yieldfabric.com"
      oracle_key_recipient: "SP500_PRICE"
      barrier_level: 70
```

### Payment Frequency Shortcuts

Automatically generate payment schedules:

```yaml
payment_schedule:
  frequency: quarterly
  start_date: "2026-01-01T00:00:00Z"
  end_date: "2031-12-31T23:59:59Z"
  amount: "1250000000000000000000"
```

### Vesting Schedules

Define linear vesting for payments:

```yaml
payments:
  - date: "2026-12-31T23:59:59Z"
    unlock_sender: "2026-12-31T23:59:59Z"
    unlock_receiver: "2026-12-31T23:59:59Z"
    linear_vesting: true
    vesting_start: "2026-01-01T00:00:00Z"
    vesting_end: "2026-12-31T23:59:59Z"
```

## Related Documentation

- **Composed Contracts**: See `yieldfabric-payments/src/graphql/resolvers/contract_flow.rs`
- **Workflow API**: See `yieldfabric-payments/src/workflows/composed_contract_issue/`
- **GraphQL Types**: See `yieldfabric-payments/src/graphql/types/contract_types.rs`
- **Example Script**: See `yieldfabric-docs/composed_contracts/issue_workflow.sh`

## Contributing

When adding new contract types or features:

1. Update `contract_schema.json` with new fields
2. Add example contract in `examples/`
3. Update `YAML_DSL_PROPOSAL.md` with documentation
4. Update this README with usage examples

## Questions?

For questions or suggestions, please refer to:
- Implementation guide: `IMPLEMENTATION_GUIDE.md`
- Full specification: `YAML_DSL_PROPOSAL.md`
- Example contracts: `examples/`











