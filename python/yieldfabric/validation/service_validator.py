"""
Service health validator
"""

from ..services import AuthService, PaymentsService
from ..utils.logger import get_logger


class ServiceValidator:
    """Validator for service health checks."""
    
    def __init__(self, auth_service: AuthService, payments_service: PaymentsService, debug: bool = False):
        """
        Initialize validator.
        
        Args:
            auth_service: Auth service client
            payments_service: Payments service client
            debug: Enable debug logging
        """
        self.auth_service = auth_service
        self.payments_service = payments_service
        self.logger = get_logger(debug=debug)
    
    def validate_services(self) -> bool:
        """
        Validate that required services are available.
        
        Returns:
            True if all services are healthy
        """
        auth_healthy = self.auth_service.check_health()
        payments_healthy = self.payments_service.check_health()
        
        if not auth_healthy:
            self.logger.error(f"❌ Auth service is not reachable at {self.auth_service.base_url}")
            self.logger.warning("Please check your connection or start the auth service")
        else:
            self.logger.success(f"✅ Auth service is healthy at {self.auth_service.base_url}")
        
        if not payments_healthy:
            self.logger.error(f"❌ Payments service is not reachable at {self.payments_service.base_url}")
            self.logger.warning("Please check your connection or start the payments service")
        else:
            self.logger.success(f"✅ Payments service is healthy at {self.payments_service.base_url}")
        
        return auth_healthy and payments_healthy

