"""
Base service client
"""

import requests
from typing import Any, Dict, Optional

from ..config import YieldFabricConfig
from ..utils.logger import get_logger


class BaseServiceClient:
    """Base class for service clients."""
    
    def __init__(self, base_url: str, config: YieldFabricConfig):
        """
        Initialize service client.
        
        Args:
            base_url: Base URL for the service
            config: YieldFabric configuration
        """
        self.base_url = base_url.rstrip('/')
        self.config = config
        self.logger = get_logger(debug=config.debug)
        self.session = requests.Session()
    
    def _get_headers(self, token: Optional[str] = None, content_type: str = "application/json") -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = {"Content-Type": content_type}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def _post(self, endpoint: str, data: Dict[str, Any], token: Optional[str] = None, 
              timeout: Optional[int] = None) -> requests.Response:
        """
        Make POST request to service.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            data: Request data
            token: Optional JWT token
            timeout: Optional request timeout
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(token)
        timeout = timeout or self.config.request_timeout
        
        self.logger.api_request("POST", url)
        
        try:
            response = self.session.post(
                url,
                json=data,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            self.logger.api_response(response.status_code, True)
            return response
        
        except requests.exceptions.RequestException as e:
            self.logger.api_response(getattr(e.response, 'status_code', 0), False)
            raise
    
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
             token: Optional[str] = None, timeout: Optional[int] = None) -> requests.Response:
        """
        Make GET request to service.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Optional query parameters
            token: Optional JWT token
            timeout: Optional request timeout
            
        Returns:
            Response object
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(token)
        timeout = timeout or self.config.request_timeout
        
        self.logger.api_request("GET", url)
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            self.logger.api_response(response.status_code, True)
            return response
        
        except requests.exceptions.RequestException as e:
            self.logger.api_response(getattr(e.response, 'status_code', 0), False)
            raise
    
    def check_health(self, timeout: Optional[int] = None) -> bool:
        """
        Check if service is healthy.
        
        Args:
            timeout: Optional health check timeout
            
        Returns:
            True if service is healthy
        """
        timeout = timeout or self.config.health_check_timeout
        
        try:
            # Try /health endpoint first
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=timeout
            )
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        try:
            # Fallback to base URL
            response = self.session.get(
                self.base_url,
                timeout=timeout
            )
            return 200 <= response.status_code < 500
        except requests.exceptions.RequestException:
            return False
    
    def close(self):
        """Close session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

