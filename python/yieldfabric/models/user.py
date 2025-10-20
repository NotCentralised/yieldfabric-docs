"""
User and authentication models
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User authentication information."""
    
    id: str  # Email address
    password: str
    group: Optional[str] = None  # Group name for delegation
    
    def __post_init__(self):
        """Validate user data."""
        if not self.id:
            raise ValueError("User ID (email) is required")
        if not self.password:
            raise ValueError("User password is required")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from dictionary."""
        return cls(
            id=data.get('id', ''),
            password=data.get('password', ''),
            group=data.get('group')
        )
    
    def to_dict(self) -> dict:
        """Convert User to dictionary."""
        return {
            'id': self.id,
            'password': self.password,
            'group': self.group
        }
    
    def __repr__(self) -> str:
        """String representation (hide password)."""
        return f"User(id={self.id}, group={self.group})"

