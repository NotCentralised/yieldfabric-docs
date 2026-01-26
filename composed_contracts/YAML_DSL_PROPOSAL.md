# YAML DSL for Structured Legal Contracts

## Overview

This document proposes a YAML-based Domain Specific Language (DSL) for defining structured financial contracts that can be created and managed on YieldFabric. The DSL maps to the composed contract system which groups multiple obligations together.

## Core Concepts

### Contract Structure
- **Composed Contract**: A collection of related obligations that are managed together
- **Obligation**: A single contract representing a payment stream or financial commitment
- **Payment Schedule**: A series of payments with specific dates, amounts, and conditions

### Key Components
1. **Parties**: Entities involved (issuer, counterpart, obligor)
2. **Obligations**: Individual payment commitments
3. **Payment Schedules**: Time-based payment structures
4. **Conditions**: Oracle-based unlock conditions, vesting, etc.

## YAML Schema Design

### Base Structure

```yaml
contract:
  metadata:
    name: string
    description: string
    type: bond | loan | mortgage | structured_product
    version: string
    effective_date: ISO8601
    expiry_date: ISO8601
  
  parties:
    issuer:
      entity_id: string
      wallet_id: optional<string>
      role: issuer
    
    counterpart:
      entity_id: string
      wallet_id: optional<string>
      role: counterpart
    
    obligor:
      entity_id: optional<string>
      wallet_id: optional<string>
      role: obligor
  
  obligations:
    - obligation_definition
  
  composed_contract:
    name: string
    description: string
```

## Product-Specific Schemas

### 1. Bond Contract

```yaml
contract:
  metadata:
    name: "Corporate Bond 2026"
    description: "5-year corporate bond with quarterly coupons"
    type: bond
    version: "1.0"
    effective_date: "2026-01-01T00:00:00Z"
    expiry_date: "2031-12-31T23:59:59Z"
  
  parties:
    issuer:
      entity_id: "issuer@yieldfabric.com"
    counterpart:
      entity_id: "investor@yieldfabric.com"
    obligor:
      entity_id: "issuer@yieldfabric.com"
  
  obligations:
    # Coupon stream obligation
    - name: "Coupon Payments"
      description: "Quarterly interest payments"
      type: coupon_stream
      denomination: "usd-token-asset"
      notional: "100000000000000000000000"  # 100,000 tokens
      expiry: "2031-12-31T23:59:59Z"
      payment_schedule:
        amount: "5000000000000000000000"  # 5,000 per payment
        frequency: quarterly
        start_date: "2026-03-31T00:00:00Z"
        end_date: "2031-12-31T23:59:59Z"
        payments:
          - date: "2026-03-31T00:00:00Z"
            unlock_sender: "2026-03-31T00:00:00Z"
            unlock_receiver: "2026-03-31T00:00:00Z"
          - date: "2026-06-30T00:00:00Z"
            unlock_sender: "2026-06-30T00:00:00Z"
            unlock_receiver: "2026-06-30T00:00:00Z"
          # ... more payments
    
    # Redemption obligation
    - name: "Principal Redemption"
      description: "Final principal repayment at maturity"
      type: redemption
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
    name: "Corporate Bond 2026"
    description: "5-year corporate bond with quarterly coupons and principal redemption"
```

### 2. Loan Contract

```yaml
contract:
  metadata:
    name: "Business Loan Agreement"
    description: "3-year term loan with monthly principal and interest"
    type: loan
    version: "1.0"
    effective_date: "2026-01-01T00:00:00Z"
    expiry_date: "2029-01-01T23:59:59Z"
  
  parties:
    issuer:
      entity_id: "lender@yieldfabric.com"
    counterpart:
      entity_id: "borrower@yieldfabric.com"
    obligor:
      entity_id: "borrower@yieldfabric.com"
  
  loan_terms:
    principal: "1000000000000000000000000"  # 1,000,000
    interest_rate: 5.5  # Annual percentage
    term_months: 36
    payment_frequency: monthly
    denomination: "usd-token-asset"
  
  obligations:
    # Principal repayment stream
    - name: "Principal Repayment"
      description: "Monthly principal repayment"
      type: principal_stream
      denomination: "usd-token-asset"
      notional: "1000000000000000000000000"
      expiry: "2029-01-01T23:59:59Z"
      payment_schedule:
        amount: "27777777777777777777778"  # Principal / 36 months
        frequency: monthly
        start_date: "2026-02-01T00:00:00Z"
        end_date: "2029-01-01T23:59:59Z"
        payments:
          - date: "2026-02-01T00:00:00Z"
            unlock_sender: "2026-02-01T00:00:00Z"
            unlock_receiver: "2026-02-01T00:00:00Z"
          # ... 35 more payments
    
    # Interest payment stream
    - name: "Interest Payments"
      description: "Monthly interest payments"
      type: interest_stream
      denomination: "usd-token-asset"
      notional: "1000000000000000000000000"
      expiry: "2029-01-01T23:59:59Z"
      payment_schedule:
        amount: "4583333333333333333333"  # (Principal * Rate / 12)
        frequency: monthly
        start_date: "2026-02-01T00:00:00Z"
        end_date: "2029-01-01T23:59:59Z"
        payments:
          - date: "2026-02-01T00:00:00Z"
            unlock_sender: "2026-02-01T00:00:00Z"
            unlock_receiver: "2026-02-01T00:00:00Z"
          # ... 35 more payments
  
  composed_contract:
    name: "Business Loan Agreement"
    description: "3-year term loan with monthly principal and interest payments"
```

### 3. Mortgage Contract

```yaml
contract:
  metadata:
    name: "Residential Mortgage"
    description: "30-year fixed-rate mortgage"
    type: mortgage
    version: "1.0"
    effective_date: "2026-01-01T00:00:00Z"
    expiry_date: "2056-01-01T23:59:59Z"
  
  parties:
    issuer:
      entity_id: "bank@yieldfabric.com"
    counterpart:
      entity_id: "homeowner@yieldfabric.com"
    obligor:
      entity_id: "homeowner@yieldfabric.com"
  
  mortgage_terms:
    principal: "500000000000000000000000"  # 500,000
    interest_rate: 4.25  # Annual percentage
    term_years: 30
    payment_frequency: monthly
    denomination: "usd-token-asset"
    property_address: "123 Main St, City, State"
    property_value: "600000000000000000000000"
    ltv_ratio: 83.33  # Loan-to-value
  
  obligations:
    # Principal and interest combined (P&I)
    - name: "Mortgage Payments"
      description: "Monthly principal and interest payments"
      type: p_and_i_stream
      denomination: "usd-token-asset"
      notional: "500000000000000000000000"
      expiry: "2056-01-01T23:59:59Z"
      payment_schedule:
        amount: "2460000000000000000000"  # P&I payment
        frequency: monthly
        start_date: "2026-02-01T00:00:00Z"
        end_date: "2056-01-01T23:59:59Z"
        payments:
          - date: "2026-02-01T00:00:00Z"
            unlock_sender: "2026-02-01T00:00:00Z"
            unlock_receiver: "2026-02-01T00:00:00Z"
          # ... 359 more payments
    
    # Property tax escrow (optional)
    - name: "Property Tax Escrow"
      description: "Monthly property tax payments"
      type: escrow_stream
      denomination: "usd-token-asset"
      notional: "12000000000000000000000"  # Annual tax / 12
      expiry: "2056-01-01T23:59:59Z"
      payment_schedule:
        amount: "1000000000000000000000"  # Monthly tax
        frequency: monthly
        start_date: "2026-02-01T00:00:00Z"
        end_date: "2056-01-01T23:59:59Z"
        payments:
          - date: "2026-02-01T00:00:00Z"
            unlock_sender: "2026-02-01T00:00:00Z"
            unlock_receiver: "2026-02-01T00:00:00Z"
          # ... 359 more payments
  
  composed_contract:
    name: "Residential Mortgage"
    description: "30-year fixed-rate mortgage with property tax escrow"
```

### 4. Structured Product Contract

```yaml
contract:
  metadata:
    name: "Capital Protected Note"
    description: "Structured product with capital protection and equity participation"
    type: structured_product
    version: "1.0"
    effective_date: "2026-01-01T00:00:00Z"
    expiry_date: "2028-12-31T23:59:59Z"
  
  parties:
    issuer:
      entity_id: "bank@yieldfabric.com"
    counterpart:
      entity_id: "investor@yieldfabric.com"
    obligor:
      entity_id: "bank@yieldfabric.com"
  
  structured_product_terms:
    principal: "1000000000000000000000000"  # 1,000,000
    denomination: "usd-token-asset"
    capital_protection: 100  # Percentage
    participation_rate: 80  # Percentage of underlying performance
    underlying_asset: "SP500"
    barrier_level: 70  # Percentage
  
  obligations:
    # Capital protection component (zero-coupon bond)
    - name: "Capital Protection"
      description: "Guaranteed return of principal at maturity"
      type: capital_protection
      denomination: "usd-token-asset"
      notional: "1000000000000000000000000"
      expiry: "2028-12-31T23:59:59Z"
      payment_schedule:
        amount: "1000000000000000000000000"
        payments:
          - date: "2028-12-31T23:59:59Z"
            unlock_sender: "2028-12-31T23:59:59Z"
            unlock_receiver: "2028-12-31T23:59:59Z"
            oracle_conditions:
              barrier_check: true
              barrier_level: 70
    
    # Equity participation component
    - name: "Equity Participation"
      description: "Participation in underlying asset performance"
      type: equity_participation
      denomination: "usd-token-asset"
      notional: "1000000000000000000000000"
      expiry: "2028-12-31T23:59:59Z"
      payment_schedule:
        amount: "variable"  # Based on underlying performance
        payments:
          - date: "2028-12-31T23:59:59Z"
            unlock_sender: "2028-12-31T23:59:59Z"
            unlock_receiver: "2028-12-31T23:59:59Z"
            oracle_conditions:
              oracle_address: "0x..."  # Price oracle
              oracle_owner: "oracle@yieldfabric.com"
              oracle_key_recipient: "SP500_PRICE"
              participation_rate: 80
              barrier_level: 70
  
  composed_contract:
    name: "Capital Protected Note"
    description: "Structured product with capital protection and equity participation"
```

## Advanced Features

### Oracle Conditions

```yaml
payment_schedule:
  payments:
    - date: "2026-12-31T23:59:59Z"
      unlock_sender: "2026-12-31T23:59:59Z"
      unlock_receiver: "2026-12-31T23:59:59Z"
      oracle_conditions:
        oracle_address: "0x1234..."
        oracle_owner: "oracle@yieldfabric.com"
        oracle_key_sender: "SENDER_KEY"
        oracle_value_sender_secret: "SECRET_VALUE"
        oracle_key_recipient: "RECIPIENT_KEY"
        oracle_value_recipient_secret: "SECRET_VALUE"
        linear_vesting: false
```

### Vesting Schedules

```yaml
payment_schedule:
  payments:
    - date: "2026-12-31T23:59:59Z"
      unlock_sender: "2026-12-31T23:59:59Z"
      unlock_receiver: "2026-12-31T23:59:59Z"
      linear_vesting: true
      vesting_start: "2026-01-01T00:00:00Z"
      vesting_end: "2026-12-31T23:59:59Z"
```

### Payment Frequency Shortcuts

```yaml
payment_schedule:
  frequency: daily | weekly | biweekly | monthly | quarterly | semiannually | annually
  start_date: ISO8601
  end_date: ISO8601
  amount: string  # Will be automatically distributed across payments
```

## Implementation Ideas

### 1. YAML Parser & Validator

Create a Rust crate `yieldfabric-contract-dsl` that:
- Parses YAML files into structured types
- Validates schema against JSON Schema or custom validators
- Generates GraphQL mutation inputs for `createObligation`
- Generates workflow API calls for composed contract issuance

### 2. Template Library

Create a library of common contract templates:
- `bond_template.yaml` - Standard bond structure
- `loan_template.yaml` - Standard loan structure
- `mortgage_template.yaml` - Standard mortgage structure
- `structured_product_template.yaml` - Standard structured product

### 3. Code Generation

Generate:
- TypeScript types for frontend
- Rust types for backend validation
- GraphQL schema extensions
- API documentation

### 4. Legal Document Integration

- Link YAML contracts to legal document templates
- Generate human-readable contract summaries
- Export to PDF with legal formatting
- Version control for contract changes

### 5. Validation Rules

- Payment schedule consistency checks
- Date range validations
- Amount calculations verification
- Party relationship validations
- Oracle condition validations

## Example: Complete Bond Contract

```yaml
contract:
  metadata:
    name: "5-Year Corporate Bond"
    description: "Quarterly coupon bond with principal redemption"
    type: bond
    version: "1.0"
    effective_date: "2026-01-01T00:00:00Z"
    expiry_date: "2031-12-31T23:59:59Z"
    legal_document_id: "LEGAL-2026-001"
  
  parties:
    issuer:
      entity_id: "corporation@yieldfabric.com"
      wallet_id: null
      role: issuer
    
    counterpart:
      entity_id: "investor@yieldfabric.com"
      wallet_id: null
      role: counterpart
    
    obligor:
      entity_id: "corporation@yieldfabric.com"
      wallet_id: null
      role: obligor
  
  obligations:
    - name: "Quarterly Coupons"
      description: "Quarterly interest payments at 5% annual rate"
      type: coupon_stream
      denomination: "usd-token-asset"
      notional: "100000000000000000000000"
      expiry: "2031-12-31T23:59:59Z"
      counterpart: "investor@yieldfabric.com"
      obligor: "corporation@yieldfabric.com"
      payment_schedule:
        amount: "1250000000000000000000"  # 1.25% quarterly (5% / 4)
        frequency: quarterly
        start_date: "2026-03-31T00:00:00Z"
        end_date: "2031-12-31T23:59:59Z"
        payments:
          - date: "2026-03-31T00:00:00Z"
            unlock_sender: "2026-03-31T00:00:00Z"
            unlock_receiver: "2026-03-31T00:00:00Z"
          - date: "2026-06-30T00:00:00Z"
            unlock_sender: "2026-06-30T00:00:00Z"
            unlock_receiver: "2026-06-30T00:00:00Z"
          - date: "2026-09-30T00:00:00Z"
            unlock_sender: "2026-09-30T00:00:00Z"
            unlock_receiver: "2026-09-30T00:00:00Z"
          - date: "2026-12-31T00:00:00Z"
            unlock_sender: "2026-12-31T00:00:00Z"
            unlock_receiver: "2026-12-31T00:00:00Z"
          # ... continue for all quarters
    
    - name: "Principal Redemption"
      description: "Return of principal at maturity"
      type: redemption
      denomination: "usd-token-asset"
      notional: "100000000000000000000000"
      expiry: "2031-12-31T23:59:59Z"
      counterpart: "investor@yieldfabric.com"
      obligor: "corporation@yieldfabric.com"
      payment_schedule:
        amount: "100000000000000000000000"
        payments:
          - date: "2031-12-31T23:59:59Z"
            unlock_sender: "2031-12-31T23:59:59Z"
            unlock_receiver: "2031-12-31T23:59:59Z"
  
  composed_contract:
    name: "5-Year Corporate Bond"
    description: "Quarterly coupon bond with principal redemption at maturity"
```

## Next Steps

1. **Define JSON Schema** for YAML validation
2. **Create Parser** in Rust to convert YAML to GraphQL inputs
3. **Build Template Library** with common contract types
4. **Implement Validation** rules for contract consistency
5. **Create CLI Tool** for contract generation and validation
6. **Integrate with Workflow API** for automated contract creation
7. **Add Legal Document Generation** from YAML contracts











