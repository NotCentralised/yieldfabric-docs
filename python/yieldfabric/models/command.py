"""
Command models
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .user import User


@dataclass
class CommandParameters:
    """Command parameters."""
    
    # Common parameters
    denomination: Optional[str] = None
    asset_id: Optional[str] = None  # Alias for denomination
    amount: Optional[str] = None
    destination_id: Optional[str] = None
    payment_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    obligor: Optional[str] = None
    group_id: Optional[str] = None
    
    # Obligation parameters
    counterpart: Optional[str] = None
    obligation_address: Optional[str] = None
    obligation_group_id: Optional[str] = None
    notional: Optional[str] = None
    expiry: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    initial_payments: Optional[Dict[str, Any]] = None
    contract_id: Optional[str] = None
    
    # Swap parameters
    initiator: Optional[Dict[str, Any]] = None
    counterparty: Optional[Dict[str, Any]] = None
    swap_id: Optional[str] = None
    
    # Treasury parameters
    policy_secret: Optional[str] = None
    
    # Additional raw parameters
    raw_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CommandParameters':
        """Create CommandParameters from dictionary."""
        # Extract known parameters
        known_params = {
            'denomination': data.get('denomination'),
            'asset_id': data.get('asset_id'),
            'amount': data.get('amount'),
            'destination_id': data.get('destination_id'),
            'payment_id': data.get('payment_id'),
            'idempotency_key': data.get('idempotency_key'),
            'obligor': data.get('obligor'),
            'group_id': data.get('group_id'),
            'counterpart': data.get('counterpart'),
            'obligation_address': data.get('obligation_address'),
            'obligation_group_id': data.get('obligation_group_id'),
            'notional': data.get('notional'),
            'expiry': data.get('expiry'),
            'data': data.get('data'),
            'initial_payments': data.get('initial_payments'),
            'contract_id': data.get('contract_id'),
            'initiator': data.get('initiator'),
            'counterparty': data.get('counterparty'),
            'swap_id': data.get('swap_id'),
            'policy_secret': data.get('policy_secret'),
        }
        
        # Store all unknown parameters in raw_params
        raw_params = {k: v for k, v in data.items() if k not in known_params}
        
        return cls(**known_params, raw_params=raw_params)
    
    def to_dict(self) -> dict:
        """Convert CommandParameters to dictionary."""
        result = {}
        
        # Add non-None known parameters
        if self.denomination:
            result['denomination'] = self.denomination
        if self.asset_id:
            result['asset_id'] = self.asset_id
        if self.amount:
            result['amount'] = self.amount
        if self.destination_id:
            result['destination_id'] = self.destination_id
        if self.payment_id:
            result['payment_id'] = self.payment_id
        if self.idempotency_key:
            result['idempotency_key'] = self.idempotency_key
        if self.obligor:
            result['obligor'] = self.obligor
        if self.group_id:
            result['group_id'] = self.group_id
        if self.counterpart:
            result['counterpart'] = self.counterpart
        if self.obligation_address:
            result['obligation_address'] = self.obligation_address
        if self.obligation_group_id:
            result['obligation_group_id'] = self.obligation_group_id
        if self.notional:
            result['notional'] = self.notional
        if self.expiry:
            result['expiry'] = self.expiry
        if self.data:
            result['data'] = self.data
        if self.initial_payments:
            result['initial_payments'] = self.initial_payments
        if self.contract_id:
            result['contract_id'] = self.contract_id
        if self.initiator:
            result['initiator'] = self.initiator
        if self.counterparty:
            result['counterparty'] = self.counterparty
        if self.swap_id:
            result['swap_id'] = self.swap_id
        if self.policy_secret:
            result['policy_secret'] = self.policy_secret
        
        # Add raw parameters
        result.update(self.raw_params)
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter value by key."""
        value = getattr(self, key, None)
        if value is not None:
            return value
        return self.raw_params.get(key, default)


@dataclass
class Command:
    """Command model."""
    
    name: str
    type: str
    user: User
    parameters: CommandParameters
    
    def __post_init__(self):
        """Validate command data."""
        if not self.name:
            raise ValueError("Command name is required")
        if not self.type:
            raise ValueError("Command type is required")
        if not isinstance(self.user, User):
            raise ValueError("User must be a User instance")
        if not isinstance(self.parameters, CommandParameters):
            raise ValueError("Parameters must be a CommandParameters instance")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Command':
        """Create Command from dictionary."""
        return cls(
            name=data.get('name', ''),
            type=data.get('type', ''),
            user=User.from_dict(data.get('user', {})),
            parameters=CommandParameters.from_dict(data.get('parameters', {}))
        )
    
    def to_dict(self) -> dict:
        """Convert Command to dictionary."""
        return {
            'name': self.name,
            'type': self.type,
            'user': self.user.to_dict(),
            'parameters': self.parameters.to_dict()
        }

