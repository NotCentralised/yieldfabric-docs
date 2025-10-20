"""
Response models
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CommandResponse:
    """Base response model for command execution."""
    
    success: bool
    command_name: str
    command_type: str
    message: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post initialization validation."""
        if not self.command_name:
            raise ValueError("Command name is required")
        if not self.command_type:
            raise ValueError("Command type is required")
    
    @classmethod
    def success_response(cls, command_name: str, command_type: str, 
                         data: Dict[str, Any], message: Optional[str] = None) -> 'CommandResponse':
        """Create a success response."""
        return cls(
            success=True,
            command_name=command_name,
            command_type=command_type,
            message=message or "Command executed successfully",
            data=data
        )
    
    @classmethod
    def error_response(cls, command_name: str, command_type: str, 
                      errors: List[str], message: Optional[str] = None) -> 'CommandResponse':
        """Create an error response."""
        return cls(
            success=False,
            command_name=command_name,
            command_type=command_type,
            message=message or "Command execution failed",
            errors=errors
        )
    
    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            'success': self.success,
            'command_name': self.command_name,
            'command_type': self.command_type,
            'message': self.message,
            'data': self.data,
            'errors': self.errors
        }


@dataclass
class GraphQLResponse:
    """GraphQL response model."""
    
    success: bool
    data: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_response(cls, response_data: dict) -> 'GraphQLResponse':
        """Create GraphQLResponse from raw response."""
        has_errors = 'errors' in response_data and response_data['errors']
        return cls(
            success=not has_errors,
            data=response_data.get('data'),
            errors=response_data.get('errors', []),
            raw_response=response_data
        )
    
    def get_data(self, path: str, default: Any = None) -> Any:
        """Get data from response using dot notation path."""
        if not self.data:
            return default
        
        keys = path.split('.')
        current = self.data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_error_message(self) -> Optional[str]:
        """Get first error message if any."""
        if self.errors:
            return self.errors[0].get('message', 'Unknown error')
        return None


@dataclass
class RESTResponse:
    """REST API response model."""
    
    success: bool
    status_code: int
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_response(cls, status_code: int, response_data: dict) -> 'RESTResponse':
        """Create RESTResponse from raw response."""
        # Determine success based on status code and response structure
        is_success = (
            200 <= status_code < 300 and 
            (response_data.get('status') == 'success' or 'error' not in response_data)
        )
        
        errors = []
        if not is_success:
            error_msg = response_data.get('error') or response_data.get('message', 'Unknown error')
            errors.append(error_msg)
        
        return cls(
            success=is_success,
            status_code=status_code,
            data=response_data,
            errors=errors,
            raw_response=response_data
        )
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data value by key."""
        return self.data.get(key, default)
    
    def get_error_message(self) -> Optional[str]:
        """Get first error message if any."""
        if self.errors:
            return self.errors[0]
        return None

