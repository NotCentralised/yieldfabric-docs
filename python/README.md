# YieldFabric Python Port v2.0 - Refactored Architecture

A completely refactored Python implementation of YieldFabric GraphQL command execution with clean architecture, separation of concerns, and enterprise-grade design patterns.

## 🎯 What's New in v2.0

### Architecture Improvements
- **Clean Architecture**: Separation of concerns with distinct layers (models, services, executors, core, utils)
- **Service Clients**: Dedicated HTTP client abstraction for Auth and Payments services
- **Executor Pattern**: Specialized executors for different operation types
- **Configuration Management**: Centralized configuration with environment variable support
- **Enhanced Logging**: Structured, colored logging with debug mode
- **Type Safety**: Comprehensive data models with validation
- **Context Managers**: Proper resource management with context manager support

### Code Organization

```
yieldfabric/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── cli.py                   # CLI interface
│
├── core/                    # Core business logic
│   ├── output_store.py      # Variable substitution
│   ├── yaml_parser.py       # YAML parsing
│   └── runner.py            # Main orchestrator
│
├── services/                # Service clients
│   ├── base.py              # Base HTTP client
│   ├── auth_service.py      # Auth service client
│   └── payments_service.py  # Payments service client
│
├── executors/               # Command executors
│   ├── base.py              # Base executor
│   ├── payment_executor.py  # Payment operations
│   ├── obligation_executor.py # Obligation operations
│   ├── query_executor.py    # Query operations
│   ├── swap_executor.py     # Swap operations
│   └── treasury_executor.py # Treasury operations
│
├── models/                  # Data models
│   ├── command.py           # Command models
│   ├── user.py              # User models
│   └── response.py          # Response models
│
├── validation/              # Validators
│   ├── yaml_validator.py    # YAML validation
│   ├── service_validator.py # Service health checks
│   └── command_validator.py # Command validation
│
└── utils/                   # Utilities
    ├── logger.py            # Logging utilities
    ├── graphql.py           # GraphQL helpers
    └── shell.py             # Shell command utilities
```

## 🚀 Quick Start

### Installation

```bash
cd yieldfabric-docs/python
pip install -e .
```

### Deploy assets from a setup.yaml (port of `setup_system.sh`)

The `setup` subcommand bootstraps users, groups (+ on-chain account
deploy), tokens, assets, and fiat accounts from a `setup.yaml` — the same
file shape `scripts/setup_system.sh` uses.

Provide service URLs and an API key via a `.env` file (auto-loaded from
the current directory). Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
# edit .env → AUTH_SERVICE_URL, PAY_SERVICE_URL, API_KEY

yieldfabric setup ./setup.yaml
```

`.env`:

```bash
AUTH_SERVICE_URL=https://auth.yieldfabric.io
PAY_SERVICE_URL=https://pay.yieldfabric.io
API_KEY=yf_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The CLI exchanges `API_KEY` for a short-lived JWT at boot via
`POST /auth/api-key`, then creates everything in `setup.yaml` under that
identity. The key owner needs `SuperAdmin`/`Admin` so the
create-token/asset/fiat mutations are permitted. Issue a key once with a
one-time user JWT:

```bash
curl -X POST "$AUTH_SERVICE_URL/auth/api-key/generate" \
     -H "Authorization: Bearer <one-time user JWT>" \
     -H "Content-Type: application/json" \
     -d '{"service_name":"asset-setup","description":"setup CLI"}'
# → {"api_key":"yf_api_…", ...}  ← store as API_KEY
```

Everything can also be passed as flags (flags > env/.env):

```bash
yieldfabric --auth-service-url https://auth.yieldfabric.io \
            --pay-service-url https://pay.yieldfabric.io \
            --api-key yf_api_… \
            --env-file ./prod.env \
            setup ./setup.yaml
```

If `API_KEY` is unset, `setup` falls back to logging in the **first user**
declared in `setup.yaml` (conventionally a `SuperAdmin`) with
email/password — the original `setup_system.sh` behaviour.

### Usage

```bash
# Bootstrap a system (users/groups/tokens/assets/fiat) from setup.yaml
yieldfabric setup setup.yaml

# Execute commands
yieldfabric execute commands.yaml

# Check status
yieldfabric status commands.yaml

# Validate YAML
yieldfabric validate commands.yaml

# Show version
yieldfabric version

# Enable debug mode
yieldfabric --debug execute commands.yaml

# Override service URLs
yieldfabric --pay-service-url https://custom-pay.example.com execute commands.yaml
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
        print("All commands executed successfully!")
```

## 📚 Key Components

### 1. Configuration (`config.py`)

Centralized configuration management:

```python
@dataclass
class YieldFabricConfig:
    pay_service_url: str
    auth_service_url: str
    command_delay: int = 3
    debug: bool = False
    request_timeout: int = 10
    # ... more settings
```

### 2. Service Clients (`services/`)

Clean HTTP client abstraction:

```python
# Base client with common functionality
class BaseServiceClient:
    def _post(self, endpoint, data, token): ...
    def _get(self, endpoint, params, token): ...
    def check_health(self): ...

# Specialized clients
class AuthService(BaseServiceClient):
    def login(self, email, password): ...
    def login_with_group(self, email, password, group): ...

class PaymentsService(BaseServiceClient):
    def graphql_mutation(self, mutation, variables, token): ...
    def get_balance(self, denomination, obligor, group_id, token): ...
```

### 3. Executors (`executors/`)

Specialized command executors:

```python
class PaymentExecutor(BaseExecutor):
    def execute(self, command): ...
    def _execute_deposit(self, command): ...
    def _execute_withdraw(self, command): ...
    def _execute_instant(self, command): ...
    def _execute_accept(self, command): ...
```

### 4. Output Store (`core/output_store.py`)

Advanced variable substitution:

```python
class OutputStore:
    def store(self, command_name, field_name, value): ...
    def get(self, command_name, field_name): ...
    def substitute(self, value): ...  # Handles $var.field, $(shell), JSON
    def substitute_params(self, params): ...
```

### 5. Runner (`core/runner.py`)

Main orchestrator:

```python
class YieldFabricRunner:
    def execute_file(self, yaml_file): ...
    def execute_command(self, command): ...
    def show_status(self, yaml_file): ...
```

## 🔧 Advanced Features

### Custom Executors

Extend the base executor to add custom operations:

```python
from yieldfabric.executors.base import BaseExecutor
from yieldfabric.models import Command, CommandResponse

class CustomExecutor(BaseExecutor):
    def execute(self, command: Command) -> CommandResponse:
        # Your custom logic here
        pass
```

### Custom Service Clients

Create custom service clients:

```python
from yieldfabric.services.base import BaseServiceClient

class CustomService(BaseServiceClient):
    def custom_operation(self, params, token):
        response = self._post("/custom-endpoint", params, token)
        return response.json()
```

### Configuration from File

Load configuration from a file:

```python
import json
from yieldfabric import YieldFabricConfig

with open('config.json') as f:
    config_dict = json.load(f)

config = YieldFabricConfig.from_dict(config_dict)
```

## 🎨 Design Patterns Used

1. **Service Layer Pattern**: Services encapsulate external API interactions
2. **Strategy Pattern**: Different executors for different command types
3. **Builder Pattern**: Configuration and command builders
4. **Template Method**: Base executor defines execution flow
5. **Factory Pattern**: Executor selection based on command type
6. **Singleton Pattern**: Global output store and logger instances
7. **Context Manager**: Proper resource cleanup

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=yieldfabric --cov-report=html

# Run specific test
pytest tests/test_executors/test_payment_executor.py
```

## 🔍 Debugging

Enable debug mode to see detailed execution logs:

```bash
# Via command line
yieldfabric --debug execute commands.yaml

# Via environment variable
export DEBUG=true
yieldfabric execute commands.yaml

# Programmatically
config = YieldFabricConfig(debug=True)
```

## 📊 Comparison: v1.0 vs v2.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Architecture | Monolithic | Layered/Clean |
| Service Clients | Direct requests | Abstracted clients |
| Executors | Single file | Specialized classes |
| Configuration | Environment only | Centralized config |
| Logging | Basic colored output | Structured logger |
| Models | Dictionaries | Dataclasses |
| Validation | Basic | Multi-level |
| Testing | Limited | Test-ready |
| Extensibility | Difficult | Easy |
| Type Safety | Minimal | Comprehensive |

## 🛠️ Migration from v1.0

### API Changes

```python
# v1.0
from yieldfabric.main import YieldFabricCommandRunner
runner = YieldFabricCommandRunner(pay_url, auth_url)
runner.execute_all_commands("commands.yaml")

# v2.0
from yieldfabric import YieldFabricConfig, YieldFabricRunner
config = YieldFabricConfig(pay_service_url=pay_url, auth_service_url=auth_url)
with YieldFabricRunner(config) as runner:
    runner.execute_file("commands.yaml")
```

### YAML Compatibility

YAML files from v1.0 are fully compatible with v2.0. No changes required!

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

MIT License

## 🙏 Acknowledgments

- Original bash scripts by YieldFabric team
- Python port v1.0 contributors
- Refactoring and v2.0 architecture

## 📮 Support

- GitHub Issues: https://github.com/yieldfabric/yieldfabric-docs/issues
- Documentation: See `docs/` directory
- Examples: See `examples/` directory

---

**YieldFabric Python Port v2.0** - Enterprise-grade architecture for blockchain payment operations
