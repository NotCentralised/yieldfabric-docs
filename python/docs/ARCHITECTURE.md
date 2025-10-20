# YieldFabric v2.0 Architecture

## Overview

YieldFabric v2.0 follows clean architecture principles with clear separation of concerns, dependency injection, and modular design.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Layer                            │
│                    (cli.py)                              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Core Layer                              │
│           (runner.py, output_store.py,                   │
│             yaml_parser.py)                              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                Executor Layer                            │
│        (payment, obligation, query, swap,                │
│              treasury executors)                         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                Service Layer                             │
│         (auth_service, payments_service)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              External Services                           │
│         (Auth Service, Payments Service)                 │
└──────────────────────────────────────────────────────────┘
```

## Component Details

### 1. CLI Layer (`cli.py`)

**Responsibility**: Command-line interface and argument parsing

**Key Functions**:
- Parse command-line arguments
- Create configuration from arguments and environment
- Invoke runner with appropriate commands

**Dependencies**: Core layer (Runner)

### 2. Core Layer

#### Runner (`core/runner.py`)

**Responsibility**: Main orchestrator for command execution

**Key Functions**:
- Parse YAML files
- Validate services and YAML
- Route commands to appropriate executors
- Manage command execution flow
- Handle variable substitution
- Coordinate between all components

**Dependencies**: Executors, Services, Validators, Output Store, YAML Parser

#### Output Store (`core/output_store.py`)

**Responsibility**: Variable storage and substitution

**Key Functions**:
- Store command outputs
- Retrieve stored values
- Substitute variables in parameters
- Handle shell command evaluation
- Support JSON array/object substitution

**Dependencies**: Logger, Shell utilities

#### YAML Parser (`core/yaml_parser.py`)

**Responsibility**: YAML file parsing and querying

**Key Functions**:
- Parse YAML files into Command objects
- Query YAML data structures
- Validate YAML structure
- Support yq-like query syntax

**Dependencies**: Models, Logger

### 3. Executor Layer

#### Base Executor (`executors/base.py`)

**Responsibility**: Base class for all executors

**Key Functions**:
- Get JWT tokens (with delegation)
- Store command outputs
- Log command execution
- Provide common executor functionality

**Dependencies**: Services, Output Store, Config, Logger

#### Specialized Executors

**Payment Executor** (`payment_executor.py`)
- Handles: deposit, withdraw, instant, accept
- GraphQL mutations for payment operations

**Obligation Executor** (`obligation_executor.py`)
- Handles: create_obligation, accept_obligation, transfer_obligation, cancel_obligation
- GraphQL mutations for obligation operations

**Query Executor** (`query_executor.py`)
- Handles: balance, obligations, list_groups
- REST API queries for read operations

**Swap Executor** (`swap_executor.py`)
- Handles: create_swap, complete_swap, cancel_swap
- GraphQL mutations for swap operations

**Treasury Executor** (`treasury_executor.py`)
- Handles: mint, burn, total_supply
- GraphQL mutations for treasury operations

### 4. Service Layer

#### Base Service Client (`services/base.py`)

**Responsibility**: HTTP client abstraction

**Key Functions**:
- POST requests
- GET requests
- Header management
- Health checks
- Session management

**Dependencies**: Config, Logger

#### Auth Service (`services/auth_service.py`)

**Responsibility**: Authentication and authorization

**Key Functions**:
- User login
- Get user groups
- Create delegation tokens
- Login with group delegation

**Dependencies**: Base Service Client

#### Payments Service (`services/payments_service.py`)

**Responsibility**: Payment operations

**Key Functions**:
- Execute GraphQL mutations
- Query balances
- Query obligations
- Query total supply

**Dependencies**: Base Service Client, GraphQL utilities

### 5. Model Layer

**Command Models** (`models/command.py`)
- Command: Represents a command
- CommandParameters: Command parameters
- Validation and serialization

**User Models** (`models/user.py`)
- User: User authentication information
- Validation

**Response Models** (`models/response.py`)
- CommandResponse: Command execution result
- GraphQLResponse: GraphQL API response
- RESTResponse: REST API response

### 6. Validation Layer

**YAML Validator** (`validation/yaml_validator.py`)
- Validates YAML structure
- Validates commands

**Service Validator** (`validation/service_validator.py`)
- Checks service health
- Validates service availability

**Command Validator** (`validation/command_validator.py`)
- Validates command parameters
- Extensible validation rules

### 7. Utility Layer

**Logger** (`utils/logger.py`)
- Colored terminal output
- Debug mode support
- Structured logging
- Global logger instance

**GraphQL** (`utils/graphql.py`)
- GraphQL mutation templates
- Payload builders
- Query helpers

**Shell** (`utils/shell.py`)
- Shell command evaluation
- Command detection
- Command extraction

## Data Flow

### Command Execution Flow

```
1. CLI
   ↓
2. Runner.execute_file()
   ↓
3. YAML Parser → Parse commands
   ↓
4. Service Validator → Check services
   ↓
5. For each command:
   a. Output Store → Substitute variables
   b. Router → Select executor
   c. Executor.execute()
      ↓
   d. Auth Service → Get token
      ↓
   e. Payments Service → Execute operation
      ↓
   f. Output Store → Store results
      ↓
   g. Logger → Log results
   ↓
6. Return summary
```

### Variable Substitution Flow

```
1. Command parameters
   ↓
2. Output Store.substitute_params()
   ↓
3. For each parameter value:
   a. Check if shell command → Evaluate
   b. Check if variable reference → Substitute
   c. Check if JSON → Recursive substitution
   ↓
4. Return substituted parameters
```

## Design Principles

### 1. Separation of Concerns
- Each layer has a single, well-defined responsibility
- No business logic in CLI or utilities
- No HTTP calls in executors (delegated to services)

### 2. Dependency Injection
- Dependencies passed via constructor
- Easy to test with mocks
- Flexible configuration

### 3. Open/Closed Principle
- Open for extension (new executors)
- Closed for modification (base classes stable)

### 4. Dependency Inversion
- High-level modules don't depend on low-level modules
- Both depend on abstractions (base classes)

### 5. Single Responsibility
- Each class has one reason to change
- Small, focused classes

### 6. Interface Segregation
- Executors only implement what they need
- Base classes provide common functionality

## Extension Points

### Adding a New Command Type

1. Create executor in `executors/`
2. Inherit from `BaseExecutor`
3. Implement `execute()` method
4. Register in `Runner.execute_command()`

```python
class CustomExecutor(BaseExecutor):
    def execute(self, command: Command) -> CommandResponse:
        # Implementation
        pass
```

### Adding a New Service

1. Create service in `services/`
2. Inherit from `BaseServiceClient`
3. Implement service-specific methods
4. Inject into executors

```python
class CustomService(BaseServiceClient):
    def custom_method(self, params, token):
        return self._post("/endpoint", params, token)
```

### Adding Validation

1. Add validator in `validation/`
2. Implement validation logic
3. Call from runner or executor

```python
class CustomValidator:
    def validate(self, data):
        # Validation logic
        pass
```

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock dependencies
- Test edge cases

### Integration Tests
- Test component interactions
- Use test doubles for external services
- Test complete flows

### End-to-End Tests
- Test with real services (or test doubles)
- Test complete command execution
- Verify outputs

## Performance Considerations

1. **Session Reuse**: HTTP sessions are reused across requests
2. **Lazy Initialization**: Components created only when needed
3. **Context Managers**: Proper resource cleanup
4. **Caching**: Consider caching tokens, group IDs

## Security Considerations

1. **Token Handling**: Tokens not logged in production
2. **Password Security**: Passwords not stored, only used for auth
3. **HTTPS**: All API calls use HTTPS
4. **Timeout**: Requests have timeouts to prevent hanging

## Future Enhancements

1. **Async Support**: Add async/await for concurrent operations
2. **Retry Logic**: Automatic retry with exponential backoff
3. **Rate Limiting**: Respect API rate limits
4. **Caching**: Cache tokens, group IDs, etc.
5. **Metrics**: Track execution metrics
6. **Tracing**: Distributed tracing support
7. **Plugin System**: Dynamic executor loading

## Conclusion

The v2.0 architecture provides a solid foundation for:
- Maintainability
- Testability
- Extensibility
- Scalability

The clean separation of concerns and modular design make it easy to understand, modify, and extend.
