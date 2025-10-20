# YieldFabric Python SDK

A clean, production-ready Python SDK for executing YieldFabric blockchain operations via GraphQL and REST APIs. Built with enterprise-grade architecture, complete type safety, and comprehensive operation support.

## 🚀 Features

- **Complete Operation Support**: All payment, obligation, swap, and treasury operations
- **Clean Architecture**: Modular design with clear separation of concerns
- **Type Safety**: Comprehensive data models with validation
- **Variable Substitution**: Chain commands with dynamic variable references
- **Group Delegation**: Full support for group-based authentication
- **Service Health Checks**: Automatic service availability validation
- **Enhanced Logging**: Structured, colored output with debug mode
- **Production Ready**: Enterprise-grade error handling and resource management

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Access to YieldFabric services (Auth Service and Payments Service)

### Install from Source

```bash
cd yieldfabric-docs/python
pip install -e .
```

### Install Dependencies Only

```bash
pip install -r requirements.txt
```

## 🎯 Quick Start

### Command Line Usage

```bash
# Execute commands from YAML file
yieldfabric execute commands.yaml

# Check service status
yieldfabric status commands.yaml

# Validate YAML structure
yieldfabric validate commands.yaml

# Show version
yieldfabric version

# Enable debug mode
yieldfabric --debug execute commands.yaml
```

### Programmatic Usage

```python
from yieldfabric import YieldFabricConfig, YieldFabricRunner

# Create configuration
config = YieldFabricConfig(
    pay_service_url="https://pay.yieldfabric.io",
    auth_service_url="https://auth.yieldfabric.io",
    debug=True
)

# Execute commands
with YieldFabricRunner(config) as runner:
    success = runner.execute_file("commands.yaml")
    if success:
        print("✅ All commands executed successfully!")
```

## 📝 YAML Configuration

### Basic Command Structure

```yaml
commands:
  - name: "deposit_1"
    type: "deposit"
    user:
      id: "user@example.com"
      password: "password123"
      group: "Admin Group"  # Optional: for group delegation
    parameters:
      denomination: "USD"
      amount: "100.00"
      idempotency_key: "deposit_$(date +%s)"
```

### Variable Substitution

Chain commands by referencing previous outputs:

```yaml
commands:
  - name: "deposit_1"
    type: "deposit"
    # ... parameters

  - name: "balance_1"
    type: "balance"
    parameters:
      denomination: "USD"
      obligor: "$deposit_1.account_address"  # Reference previous output
      group_id: "$deposit_1.group_id"
```

### Shell Command Substitution

```yaml
parameters:
  idempotency_key: "deposit_$(date +%s)"  # Evaluates shell command
```

## 🎨 Supported Operations

### Payment Operations
- `deposit` - Deposit funds to an account
- `withdraw` - Withdraw funds from an account
- `instant` - Send instant payments
- `accept` - Accept incoming payments

### Obligation Operations
- `create_obligation` - Create financial obligations
- `accept_obligation` - Accept obligations
- `transfer_obligation` - Transfer obligations to another party
- `cancel_obligation` - Cancel existing obligations

### Query Operations
- `balance` - Query account balances
- `obligations` - List obligations
- `list_groups` - List user groups

### Swap Operations
- `create_swap` - Create unified swaps
- `create_obligation_swap` - Create obligation-specific swaps
- `create_payment_swap` - Create payment-specific swaps
- `complete_swap` - Complete pending swaps
- `cancel_swap` - Cancel pending swaps

### Treasury Operations
- `mint` - Mint new tokens (requires policy secret)
- `burn` - Burn existing tokens (requires policy secret)
- `total_supply` - Query total token supply

## 🏗️ Architecture

### Clean, Modular Structure

```
yieldfabric/
├── config.py                # Configuration management
├── cli.py                   # CLI interface
├── core/                    # Core business logic
│   ├── runner.py            # Main orchestrator
│   ├── output_store.py      # Variable substitution
│   └── yaml_parser.py       # YAML parsing
├── services/                # Service clients
│   ├── auth_service.py      # Authentication
│   └── payments_service.py  # Payments API
├── executors/               # Command executors
│   ├── payment_executor.py
│   ├── obligation_executor.py
│   ├── query_executor.py
│   ├── swap_executor.py
│   └── treasury_executor.py
├── models/                  # Data models
│   ├── command.py
│   ├── user.py
│   └── response.py
├── validation/              # Validators
│   ├── yaml_validator.py
│   └── service_validator.py
└── utils/                   # Utilities
    ├── logger.py
    ├── graphql.py
    └── shell.py
```

### Key Design Patterns

- **Service Layer Pattern**: Abstracted HTTP clients
- **Strategy Pattern**: Specialized executors per operation type
- **Builder Pattern**: Flexible configuration
- **Context Manager**: Proper resource cleanup
- **Dependency Injection**: Testable components

## ⚙️ Configuration

### Environment Variables

```bash
# Service URLs
export PAY_SERVICE_URL="https://pay.yieldfabric.io"
export AUTH_SERVICE_URL="https://auth.yieldfabric.io"

# Execution settings
export COMMAND_DELAY="3"          # Delay between commands (seconds)
export DEBUG="true"               # Enable debug logging
export REQUEST_TIMEOUT="10"       # HTTP request timeout (seconds)
```

### Configuration File

```python
from yieldfabric import YieldFabricConfig

config = YieldFabricConfig(
    pay_service_url="https://pay.yieldfabric.io",
    auth_service_url="https://auth.yieldfabric.io",
    command_delay=3,
    debug=True,
    request_timeout=10
)
```

## 📚 Examples

### Example 1: Deposit and Balance Check

```yaml
commands:
  - name: "deposit_usd"
    type: "deposit"
    user:
      id: "user@example.com"
      password: "password123"
      group: "Trading Group"
    parameters:
      denomination: "USD"
      amount: "1000.00"
      idempotency_key: "deposit_$(date +%s)"

  - name: "check_balance"
    type: "balance"
    user:
      id: "user@example.com"
      password: "password123"
      group: "Trading Group"
    parameters:
      denomination: "USD"
```

### Example 2: Create and Accept Obligation

```yaml
commands:
  - name: "create_obligation"
    type: "create_obligation"
    user:
      id: "lender@example.com"
      password: "password123"
    parameters:
      counterpart: "borrower@example.com"
      denomination: "USD"
      notional: "10000.00"
      expiry: "2025-12-31"

  - name: "accept_obligation"
    type: "accept_obligation"
    user:
      id: "borrower@example.com"
      password: "password123"
    parameters:
      contract_id: "$create_obligation.contract_id"
```

### Example 3: Swap Operations

```yaml
commands:
  - name: "create_swap"
    type: "create_payment_swap"
    user:
      id: "trader1@example.com"
      password: "password123"
    parameters:
      counterparty: "trader2@example.com"
      initiator:
        expected_payments:
          amount: "100.00"
      counterparty:
        expected_payments:
          amount: "95.00"

  - name: "complete_swap"
    type: "complete_swap"
    user:
      id: "trader2@example.com"
      password: "password123"
    parameters:
      swap_id: "$create_swap.swap_id"
```

## 🔧 Advanced Features

### Custom Service Clients

```python
from yieldfabric.services.base import BaseServiceClient

class CustomService(BaseServiceClient):
    def custom_operation(self, params, token):
        response = self._post("/custom-endpoint", params, token)
        return response.json()
```

### Custom Executors

```python
from yieldfabric.executors.base import BaseExecutor
from yieldfabric.models import Command, CommandResponse

class CustomExecutor(BaseExecutor):
    def execute(self, command: Command) -> CommandResponse:
        # Your custom logic
        pass
```

## 🐛 Debugging

### Enable Debug Mode

```bash
# Via command line
yieldfabric --debug execute commands.yaml

# Via environment
export DEBUG=true
yieldfabric execute commands.yaml
```

### Show Stored Variables

```bash
# View all stored variables for debugging
yieldfabric variables
```

### Validate Configuration

```bash
# Check services and YAML structure
yieldfabric status commands.yaml
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=yieldfabric --cov-report=html

# Run specific test file
pytest tests/test_executors/test_payment_executor.py
```

## 🚢 Production Deployment

### Docker Support

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

CMD ["yieldfabric", "execute", "commands.yaml"]
```

### Best Practices

1. **Use environment variables** for service URLs and secrets
2. **Enable health checks** before executing commands
3. **Set appropriate timeouts** for network operations
4. **Use idempotency keys** for all mutations
5. **Implement retry logic** for production systems
6. **Monitor and log** all operations

## 📊 Performance

- **Service Reuse**: HTTP sessions are reused across requests
- **Connection Pooling**: Efficient connection management
- **Context Managers**: Proper resource cleanup
- **Lazy Initialization**: Components created only when needed

## 🔒 Security

- **No Password Logging**: Credentials never logged
- **HTTPS Only**: All API calls use HTTPS
- **Token Expiry**: JWT tokens with configurable expiry
- **Timeout Protection**: All requests have timeouts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`pytest`)
5. Format code (`black yieldfabric/`)
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yieldfabric/yieldfabric-docs/issues)
- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory

## 📈 Changelog

### Version 2.0.0 (Current)

- ✅ Complete architectural refactoring
- ✅ All 19 operations fully implemented
- ✅ Clean, modular architecture
- ✅ Type-safe data models
- ✅ Enhanced logging and debugging
- ✅ Production-ready error handling
- ✅ Comprehensive documentation

### Version 1.0.0

- Initial Python port from bash scripts
- Basic GraphQL and REST API support
- Variable substitution
- Group delegation

---

**Built with ❤️ by the YieldFabric team**

**Status**: ✅ Production Ready | **Version**: 2.0.0 | **Python**: 3.8+
