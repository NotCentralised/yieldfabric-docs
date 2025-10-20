"""
Payments service client
"""

from typing import Any, Dict, Optional

from .base import BaseServiceClient
from ..config import YieldFabricConfig
from ..models.response import GraphQLResponse, RESTResponse
from ..utils.graphql import GraphQLMutation


class PaymentsService(BaseServiceClient):
    """Client for Payments Service."""
    
    def __init__(self, config: YieldFabricConfig):
        """
        Initialize Payments Service client.
        
        Args:
            config: YieldFabric configuration
        """
        super().__init__(config.pay_service_url, config)
    
    def graphql_mutation(self, mutation: str, variables: Dict[str, Any], token: str) -> GraphQLResponse:
        """
        Execute GraphQL mutation.
        
        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            token: JWT token
            
        Returns:
            GraphQLResponse object
        """
        payload = GraphQLMutation.build_payload(mutation, variables)
        
        self.logger.debug("  📋 GraphQL mutation (variables omitted for brevity)")
        self.logger.debug(f"  📋 GraphQL variables: {variables}")
        
        try:
            response = self._post("/graphql", payload, token=token)
            data = response.json()
            
            self.logger.debug(f"  📡 Raw GraphQL response: {data}")
            
            return GraphQLResponse.from_response(data)
        
        except Exception as e:
            self.logger.error(f"    ❌ GraphQL mutation failed: {e}")
            return GraphQLResponse(
                success=False,
                errors=[{"message": str(e)}]
            )
    
    def get_balance(self, denomination: str, obligor: Optional[str], group_id: Optional[str], 
                    token: str) -> RESTResponse:
        """
        Get account balance.
        
        Args:
            denomination: Asset denomination
            obligor: Optional obligor address
            group_id: Optional group ID
            token: JWT token
            
        Returns:
            RESTResponse object
        """
        params = {"denomination": denomination}
        
        if obligor and obligor != "null":
            params["obligor"] = obligor
        if group_id and group_id != "null":
            params["group_id"] = group_id
        
        self.logger.debug("  📋 Query parameters:")
        for k, v in params.items():
            self.logger.debug(f"    {k}: {v}")
        
        try:
            response = self._get("/balance", params=params, token=token)
            data = response.json()
            
            self.logger.debug(f"  📡 Raw REST API response: {data}")
            
            return RESTResponse.from_response(response.status_code, data)
        
        except Exception as e:
            self.logger.error(f"    ❌ Balance query failed: {e}")
            return RESTResponse(
                success=False,
                status_code=0,
                errors=[str(e)]
            )
    
    def get_obligations(self, token: str) -> RESTResponse:
        """
        Get obligations list.
        
        Args:
            token: JWT token
            
        Returns:
            RESTResponse object
        """
        self.logger.debug("  📋 Fetching obligations")
        
        try:
            response = self._get("/obligations", token=token)
            data = response.json()
            
            self.logger.debug(f"  📡 Raw REST API response: {data}")
            
            return RESTResponse.from_response(response.status_code, data)
        
        except Exception as e:
            self.logger.error(f"    ❌ Obligations query failed: {e}")
            return RESTResponse(
                success=False,
                status_code=0,
                errors=[str(e)]
            )
    
    def get_total_supply(self, denomination: str, obligor: Optional[str], token: str) -> RESTResponse:
        """
        Get total supply for a denomination.
        
        Args:
            denomination: Asset denomination
            obligor: Optional obligor address
            token: JWT token
            
        Returns:
            RESTResponse object
        """
        params = {"denomination": denomination}
        
        if obligor and obligor != "null":
            params["obligor"] = obligor
        
        self.logger.debug("  📋 Query parameters:")
        for k, v in params.items():
            self.logger.debug(f"    {k}: {v}")
        
        try:
            response = self._get("/total-supply", params=params, token=token)
            data = response.json()
            
            self.logger.debug(f"  📡 Raw REST API response: {data}")
            
            return RESTResponse.from_response(response.status_code, data)
        
        except Exception as e:
            self.logger.error(f"    ❌ Total supply query failed: {e}")
            return RESTResponse(
                success=False,
                status_code=0,
                errors=[str(e)]
            )

