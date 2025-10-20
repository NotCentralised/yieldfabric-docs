"""
Configuration management for YieldFabric
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class YieldFabricConfig:
    """Configuration for YieldFabric services and execution."""
    
    # Service URLs
    pay_service_url: str = field(
        default_factory=lambda: os.getenv('PAY_SERVICE_URL', 'https://pay.yieldfabric.io')
    )
    auth_service_url: str = field(
        default_factory=lambda: os.getenv('AUTH_SERVICE_URL', 'https://auth.yieldfabric.io')
    )
    
    # Execution settings
    command_delay: int = field(
        default_factory=lambda: int(os.getenv('COMMAND_DELAY', '3'))
    )
    
    # Debug settings
    debug: bool = field(
        default_factory=lambda: os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
    )
    
    # Timeout settings
    request_timeout: int = field(
        default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT', '10'))
    )
    health_check_timeout: int = field(
        default_factory=lambda: int(os.getenv('HEALTH_CHECK_TIMEOUT', '5'))
    )
    
    # JWT settings
    jwt_expiry_seconds: int = field(
        default_factory=lambda: int(os.getenv('JWT_EXPIRY_SECONDS', '3600'))
    )
    
    # Delegation scopes
    delegation_scopes: list = field(
        default_factory=lambda: [
            "CryptoOperations",
            "ReadGroup",
            "UpdateGroup",
            "ManageGroupMembers"
        ]
    )
    
    @classmethod
    def from_env(cls) -> 'YieldFabricConfig':
        """Create configuration from environment variables."""
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'YieldFabricConfig':
        """Create configuration from dictionary."""
        return cls(
            pay_service_url=config_dict.get('pay_service_url', cls.pay_service_url),
            auth_service_url=config_dict.get('auth_service_url', cls.auth_service_url),
            command_delay=config_dict.get('command_delay', cls.command_delay),
            debug=config_dict.get('debug', cls.debug),
            request_timeout=config_dict.get('request_timeout', cls.request_timeout),
            health_check_timeout=config_dict.get('health_check_timeout', cls.health_check_timeout),
            jwt_expiry_seconds=config_dict.get('jwt_expiry_seconds', cls.jwt_expiry_seconds),
            delegation_scopes=config_dict.get('delegation_scopes', cls.delegation_scopes),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'pay_service_url': self.pay_service_url,
            'auth_service_url': self.auth_service_url,
            'command_delay': self.command_delay,
            'debug': self.debug,
            'request_timeout': self.request_timeout,
            'health_check_timeout': self.health_check_timeout,
            'jwt_expiry_seconds': self.jwt_expiry_seconds,
            'delegation_scopes': self.delegation_scopes,
        }
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if not self.pay_service_url:
            raise ValueError("pay_service_url is required")
        if not self.auth_service_url:
            raise ValueError("auth_service_url is required")
        if self.command_delay < 0:
            raise ValueError("command_delay must be non-negative")
        if self.request_timeout < 1:
            raise ValueError("request_timeout must be at least 1 second")
        if self.health_check_timeout < 1:
            raise ValueError("health_check_timeout must be at least 1 second")
        if self.jwt_expiry_seconds < 60:
            raise ValueError("jwt_expiry_seconds must be at least 60 seconds")
        return True

