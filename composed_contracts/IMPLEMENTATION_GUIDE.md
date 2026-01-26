# YAML DSL Implementation Guide

## Overview

This guide explains how to implement the YAML DSL for structured legal contracts in YieldFabric. The DSL allows users to define complex financial contracts (bonds, loans, mortgages, structured products) in a human-readable format that maps directly to YieldFabric's composed contract system.

## Architecture

### Current System Flow

1. **GraphQL API** (`contract_flow.rs`) - Handles `createObligation` mutations
2. **Workflow API** (`composed_contract_issue`) - Handles composed contract creation
3. **Composed Flow** (`composed_flow.rs`) - Executes multiple operations atomically
4. **MQ System** - Processes messages asynchronously

### Proposed YAML DSL Flow

```
YAML Contract File
    ↓
[Parser & Validator]
    ↓
[Contract Generator]
    ↓
GraphQL Mutations / Workflow API
    ↓
Composed Contract Created
```

## Implementation Steps

### Phase 1: Parser & Validator

Create a Rust crate `yieldfabric-contract-dsl`:

```rust
// yieldfabric-contract-dsl/src/lib.rs

use serde::{Deserialize, Serialize};
use serde_yaml;
use jsonschema::JSONSchema;

pub struct ContractDSL;

impl ContractDSL {
    /// Parse YAML file into Contract structure
    pub fn parse_yaml(yaml_content: &str) -> Result<Contract, Error> {
        let contract: Contract = serde_yaml::from_str(yaml_content)?;
        Ok(contract)
    }
    
    /// Validate contract against JSON schema
    pub fn validate(contract: &Contract) -> Result<(), ValidationError> {
        let schema = include_str!("../schemas/contract_schema.json");
        let json_schema: serde_json::Value = serde_json::from_str(schema)?;
        let compiled = JSONSchema::compile(&json_schema)?;
        
        let contract_json = serde_json::to_value(contract)?;
        compiled.validate(&contract_json)?;
        Ok(())
    }
    
    /// Convert to GraphQL input format
    pub fn to_graphql_input(&self, contract: &Contract) -> Vec<CreateObligationInput> {
        // Convert each obligation to CreateObligationInput
    }
    
    /// Convert to workflow API format
    pub fn to_workflow_input(&self, contract: &Contract) -> WorkflowInput {
        // Convert to workflow API format
    }
}
```

### Phase 2: Contract Types

Define Rust types matching the YAML schema:

```rust
// yieldfabric-contract-dsl/src/types.rs

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contract {
    pub contract: ContractDefinition,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractDefinition {
    pub metadata: ContractMetadata,
    pub parties: Parties,
    pub obligations: Vec<Obligation>,
    pub composed_contract: ComposedContractInfo,
    #[serde(default)]
    pub loan_terms: Option<LoanTerms>,
    #[serde(default)]
    pub mortgage_terms: Option<MortgageTerms>,
    #[serde(default)]
    pub structured_product_terms: Option<StructuredProductTerms>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractMetadata {
    pub name: String,
    pub description: String,
    #[serde(rename = "type")]
    pub contract_type: ContractType,
    pub version: String,
    #[serde(default)]
    pub effective_date: Option<String>,
    #[serde(default)]
    pub expiry_date: Option<String>,
    #[serde(default)]
    pub legal_document_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ContractType {
    Bond,
    Loan,
    Mortgage,
    StructuredProduct,
    Annuity,
    Swap,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Obligation {
    pub name: String,
    pub description: String,
    #[serde(default)]
    #[serde(rename = "type")]
    pub obligation_type: Option<ObligationType>,
    pub denomination: String,
    #[serde(default)]
    pub notional: Option<String>,
    pub expiry: String,
    #[serde(default)]
    pub counterpart: Option<String>,
    #[serde(default)]
    pub counterpart_wallet_id: Option<String>,
    #[serde(default)]
    pub obligor: Option<String>,
    #[serde(default)]
    pub obligor_wallet_id: Option<String>,
    #[serde(default)]
    pub obligation_address: Option<String>,
    pub payment_schedule: PaymentSchedule,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaymentSchedule {
    #[serde(default)]
    pub amount: Option<String>,
    #[serde(default)]
    pub frequency: Option<PaymentFrequency>,
    #[serde(default)]
    pub start_date: Option<String>,
    #[serde(default)]
    pub end_date: Option<String>,
    pub payments: Vec<Payment>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Payment {
    pub date: String,
    pub unlock_sender: String,
    pub unlock_receiver: String,
    #[serde(default)]
    pub oracle_conditions: Option<OracleConditions>,
    #[serde(default)]
    pub linear_vesting: Option<bool>,
    #[serde(default)]
    pub vesting_start: Option<String>,
    #[serde(default)]
    pub vesting_end: Option<String>,
}
```

### Phase 3: GraphQL Conversion

Convert YAML obligations to GraphQL `CreateObligationInput`:

```rust
// yieldfabric-contract-dsl/src/converter.rs

use yieldfabric_payments::graphql::types::contract_types::{
    CreateObligationInput, InitialPaymentsInput, VaultPaymentInput
};

impl ContractDSL {
    pub fn to_create_obligation_inputs(
        &self,
        contract: &Contract,
        obligation: &Obligation,
    ) -> CreateObligationInput {
        // Resolve counterpart from parties or obligation
        let counterpart = obligation.counterpart.clone()
            .or_else(|| contract.contract.parties.counterpart.entity_id.clone());
        
        // Resolve obligor from parties or obligation
        let obligor = obligation.obligor.clone()
            .or_else(|| contract.contract.parties.obligor.as_ref()
                .map(|p| p.entity_id.clone()));
        
        // Convert payment schedule to InitialPaymentsInput
        let initial_payments = if !obligation.payment_schedule.payments.is_empty() {
            Some(self.convert_payment_schedule(&obligation.payment_schedule))
        } else {
            None
        };
        
        CreateObligationInput {
            counterpart,
            counterpart_wallet_id: obligation.counterpart_wallet_id.clone(),
            obligation_address: obligation.obligation_address.clone(),
            denomination: Some(obligation.denomination.clone()),
            obligor,
            obligor_wallet_id: obligation.obligor_wallet_id.clone(),
            notional: obligation.notional.clone(),
            expiry: Some(obligation.expiry.clone()),
            data: Some(serde_json::json!({
                "name": obligation.name,
                "description": obligation.description,
                "type": obligation.obligation_type,
            })),
            initial_payments,
            idempotency_key: None,
            contract_id: None,
        }
    }
    
    fn convert_payment_schedule(
        &self,
        schedule: &PaymentSchedule,
    ) -> InitialPaymentsInput {
        let payments: Vec<VaultPaymentInput> = schedule
            .payments
            .iter()
            .map(|p| self.convert_payment(p))
            .collect();
        
        InitialPaymentsInput {
            amount: schedule.amount.clone()
                .unwrap_or_else(|| "0".to_string()),
            denomination: None, // Will use obligation denomination
            obligor: None, // Will use obligation obligor
            payments,
        }
    }
    
    fn convert_payment(&self, payment: &Payment) -> VaultPaymentInput {
        let oracle = payment.oracle_conditions.as_ref();
        
        VaultPaymentInput {
            oracle_address: oracle.and_then(|o| o.oracle_address.clone()),
            oracle_owner: oracle.and_then(|o| o.oracle_owner.clone()),
            oracle_key_sender: oracle.and_then(|o| o.oracle_key_sender.clone()),
            oracle_value_sender: oracle.and_then(|o| o.oracle_value_sender.clone()),
            oracle_value_sender_secret: oracle.and_then(|o| o.oracle_value_sender_secret.clone()),
            oracle_key_recipient: oracle.and_then(|o| o.oracle_key_recipient.clone()),
            oracle_value_recipient: oracle.and_then(|o| o.oracle_value_recipient.clone()),
            oracle_value_recipient_secret: oracle.and_then(|o| o.oracle_value_recipient_secret.clone()),
            unlock_sender: Some(payment.unlock_sender.clone()),
            unlock_receiver: Some(payment.unlock_receiver.clone()),
            linear_vesting: payment.linear_vesting,
        }
    }
}
```

### Phase 4: Workflow API Integration

Convert to workflow API format:

```rust
// yieldfabric-contract-dsl/src/workflow_converter.rs

use yieldfabric_payments::workflows::composed_contract_issue::types::{
    ComposedContractIssuanceInput, ObligationInput
};

impl ContractDSL {
    pub fn to_workflow_input(&self, contract: &Contract) -> ComposedContractIssuanceInput {
        let obligations: Vec<ObligationInput> = contract
            .contract
            .obligations
            .iter()
            .map(|o| self.convert_obligation_to_workflow(o, &contract.contract.parties))
            .collect();
        
        ComposedContractIssuanceInput {
            name: contract.contract.composed_contract.name.clone(),
            description: Some(contract.contract.composed_contract.description.clone()),
            obligations,
        }
    }
    
    fn convert_obligation_to_workflow(
        &self,
        obligation: &Obligation,
        parties: &Parties,
    ) -> ObligationInput {
        // Convert obligation to workflow format
        // Similar to to_create_obligation_inputs but for workflow API
    }
}
```

### Phase 5: CLI Tool

Create a CLI tool for contract management:

```rust
// yieldfabric-contract-dsl/src/cli.rs

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "yf-contract")]
#[command(about = "YieldFabric Contract DSL Tool")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Validate a contract YAML file
    Validate {
        /// Path to contract YAML file
        #[arg(short, long)]
        file: String,
    },
    
    /// Generate GraphQL mutations from contract
    Generate {
        /// Path to contract YAML file
        #[arg(short, long)]
        file: String,
        /// Output format (graphql, workflow, json)
        #[arg(short, long, default_value = "graphql")]
        format: String,
    },
    
    /// Create contract from YAML file
    Create {
        /// Path to contract YAML file
        #[arg(short, long)]
        file: String,
        /// JWT token for authentication
        #[arg(short, long)]
        token: String,
        /// Use workflow API instead of GraphQL
        #[arg(short, long)]
        workflow: bool,
    },
    
    /// Generate contract template
    Template {
        /// Contract type (bond, loan, mortgage, structured_product)
        #[arg(short, long)]
        contract_type: String,
        /// Output file path
        #[arg(short, long)]
        output: Option<String>,
    },
}
```

## Usage Examples

### 1. Validate Contract

```bash
yf-contract validate --file examples/bond_example.yaml
```

### 2. Generate GraphQL Mutations

```bash
yf-contract generate --file examples/bond_example.yaml --format graphql
```

### 3. Create Contract via Workflow API

```bash
yf-contract create --file examples/bond_example.yaml --token $JWT_TOKEN --workflow
```

### 4. Generate Template

```bash
yf-contract template --contract-type bond --output my_bond.yaml
```

## Integration with Existing System

### Option 1: Direct GraphQL Integration

Use the DSL parser to generate GraphQL mutations and call them directly:

```rust
// In yieldfabric-payments/src/handlers/custom/contract_dsl.rs

pub async fn create_contract_from_yaml(
    yaml_content: &str,
    ctx: &Context<'_>,
) -> Result<CreateObligationResponse> {
    let contract = ContractDSL::parse_yaml(yaml_content)?;
    ContractDSL::validate(&contract)?;
    
    let obligations = contract.contract.obligations;
    let mut contract_ids = Vec::new();
    
    for obligation in obligations {
        let input = ContractDSL::to_create_obligation_inputs(&contract, &obligation);
        let response = contract_flow_mutation.create_obligation(ctx, input).await?;
        contract_ids.push(response.contract_id);
    }
    
    // Create composed contract
    // ...
}
```

### Option 2: Workflow API Integration

Use the existing workflow API:

```rust
// In yieldfabric-payments/src/handlers/rest/composed_contract.rs

pub async fn create_from_yaml(
    yaml_content: &str,
    auth_claims: &AuthClaims,
    jwt_token: &str,
    state: &GraphQLState,
) -> Result<WorkflowResponse> {
    let contract = ContractDSL::parse_yaml(yaml_content)?;
    ContractDSL::validate(&contract)?;
    
    let workflow_input = ContractDSL::to_workflow_input(&contract);
    
    // Use existing workflow processor
    // ...
}
```

## Payment Schedule Generation

For contracts with `frequency` specified, generate payment dates automatically:

```rust
// yieldfabric-contract-dsl/src/payment_generator.rs

pub fn generate_payment_schedule(
    frequency: PaymentFrequency,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    amount: String,
) -> Vec<Payment> {
    let mut payments = Vec::new();
    let mut current_date = start_date;
    
    while current_date <= end_date {
        payments.push(Payment {
            date: current_date.to_rfc3339(),
            unlock_sender: current_date.to_rfc3339(),
            unlock_receiver: current_date.to_rfc3339(),
            oracle_conditions: None,
            linear_vesting: None,
            vesting_start: None,
            vesting_end: None,
        });
        
        current_date = match frequency {
            PaymentFrequency::Daily => current_date + Duration::days(1),
            PaymentFrequency::Weekly => current_date + Duration::weeks(1),
            PaymentFrequency::Biweekly => current_date + Duration::weeks(2),
            PaymentFrequency::Monthly => {
                // Handle month boundaries correctly
                current_date + Duration::days(30)
            },
            PaymentFrequency::Quarterly => current_date + Duration::days(90),
            PaymentFrequency::Semiannually => current_date + Duration::days(180),
            PaymentFrequency::Annually => current_date + Duration::days(365),
        };
    }
    
    payments
}
```

## Testing Strategy

1. **Unit Tests**: Test parser, validator, and converters
2. **Integration Tests**: Test with actual GraphQL API
3. **Contract Examples**: Validate all example contracts
4. **Schema Validation**: Ensure JSON schema matches Rust types

## Future Enhancements

1. **Template Variables**: Support for variable substitution in templates
2. **Contract Versioning**: Track changes to contracts over time
3. **Legal Document Generation**: Generate PDF contracts from YAML
4. **Contract Marketplace**: Share and discover contract templates
5. **Visual Editor**: GUI for creating contracts
6. **Contract Simulation**: Preview payment schedules and cash flows











