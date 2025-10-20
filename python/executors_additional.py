"""
YieldFabric Additional Command Executors Module
Contains additional executor functions for complex operations.
"""

import json
import requests
from typing import Any, Dict, List, Optional
from .utils import Colors, echo_with_color, command_output_store
from .auth import auth_service


class AdditionalCommandExecutor:
    """Execute additional YieldFabric commands via GraphQL and REST APIs."""
    
    def __init__(self, pay_service_url: str = "https://pay.yieldfabric.io"):
        self.pay_service_url = pay_service_url
    
    def execute_create_obligation(self, command_name: str, user_email: str, user_password: str,
                                 counterpart: str, denomination: str, notional: Optional[str] = None,
                                 expiry: Optional[str] = None, obligor: Optional[str] = None,
                                 obligation_address: Optional[str] = None, obligation_group_id: Optional[str] = None,
                                 data: Optional[Dict] = None, initial_payments_amount: Optional[str] = None,
                                 initial_payments_json: Optional[List[Dict]] = None,
                                 idempotency_key: Optional[str] = None, group_name: Optional[str] = None) -> bool:
        """Execute create obligation command using GraphQL."""
        echo_with_color(Colors.CYAN, f"🤝 Executing create obligation command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Build input parameters
        input_params = [f'counterpart: "{counterpart}"', f'denomination: "{denomination}"']
        
        if obligation_address and obligation_address != "null":
            input_params.append(f'obligationAddress: "{obligation_address}"')
        if obligation_group_id and obligation_group_id != "null":
            input_params.append(f'obligationGroupId: "{obligation_group_id}"')
        if obligor and obligor != "null":
            input_params.append(f'obligor: "{obligor}"')
        if notional and notional != "null":
            input_params.append(f'notional: "{notional}"')
        if expiry and expiry != "null":
            input_params.append(f'expiry: "{expiry}"')
        if idempotency_key:
            input_params.append(f'idempotencyKey: "{idempotency_key}"')
        
        # Handle data parameter
        variables = {}
        if data and data != {} and data != "null":
            variables["data"] = data
            input_params.append("data: $data")
        
        # Handle initial payments
        if initial_payments_amount and initial_payments_json:
            # Convert user-friendly payments to VaultPaymentInput format
            vault_payments = []
            for payment in initial_payments_json:
                vault_payment = {
                    "oracleAddress": None,
                    "oracleOwner": payment.get("owner", ""),
                    "oracleKeySender": payment.get("payer", {}).get("key", "0"),
                    "oracleValueSenderSecret": payment.get("payer", {}).get("valueSecret", "0"),
                    "oracleKeyRecipient": payment.get("payee", {}).get("key", "0"),
                    "oracleValueRecipientSecret": payment.get("payee", {}).get("valueSecret", "0"),
                    "unlockSender": payment.get("payer", {}).get("unlock", ""),
                    "unlockReceiver": payment.get("payee", {}).get("unlock", "")
                }
                vault_payments.append(vault_payment)
            
            initial_payments_variable = {
                "amount": initial_payments_amount,
                "payments": vault_payments
            }
            variables["initialPayments"] = initial_payments_variable
            input_params.append("initialPayments: $initialPayments")
        
        # Build GraphQL mutation
        mutation_vars = []
        if "data" in variables:
            mutation_vars.append("$data: JSON")
        if "initialPayments" in variables:
            mutation_vars.append("$initialPayments: InitialPaymentsInput")
        
        if mutation_vars:
            mutation = f"""
                mutation({', '.join(mutation_vars)}) {{
                    createObligation(input: {{ {', '.join(input_params)} }}) {{
                        success
                        message
                        accountAddress
                        obligationResult
                        messageId
                        contractId
                        transactionId
                        signature
                        timestamp
                        idHash
                    }}
                }}
            """
        else:
            mutation = f"""
                mutation {{
                    createObligation(input: {{ {', '.join(input_params)} }}) {{
                        success
                        message
                        accountAddress
                        obligationResult
                        messageId
                        contractId
                        transactionId
                        signature
                        timestamp
                        idHash
                    }}
                }}
            """
        
        payload = {"query": mutation}
        if variables:
            payload["variables"] = variables
        
        echo_with_color(Colors.BLUE, "  📋 GraphQL mutation:")
        echo_with_color(Colors.BLUE, f"    {mutation.strip()}")
        
        # Send GraphQL request
        try:
            response = requests.post(
                f"{self.pay_service_url}/graphql",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {jwt_token}"
                },
                json=payload,
                timeout=30
            )
            
            echo_with_color(Colors.BLUE, f"  📡 Raw GraphQL response: '{response.text}'")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('createObligation', {}).get('success'):
                    obligation_data = data['data']['createObligation']
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "account_address", obligation_data.get('accountAddress', ''))
                    command_output_store.store_command_output(command_name, "message", obligation_data.get('message', ''))
                    command_output_store.store_command_output(command_name, "obligation_result", obligation_data.get('obligationResult', ''))
                    command_output_store.store_command_output(command_name, "message_id", obligation_data.get('messageId', ''))
                    command_output_store.store_command_output(command_name, "contract_id", obligation_data.get('contractId', ''))
                    command_output_store.store_command_output(command_name, "transaction_id", obligation_data.get('transactionId', ''))
                    command_output_store.store_command_output(command_name, "signature", obligation_data.get('signature', ''))
                    command_output_store.store_command_output(command_name, "timestamp", obligation_data.get('timestamp', ''))
                    command_output_store.store_command_output(command_name, "id_hash", obligation_data.get('idHash', ''))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Create obligation successful!")
                    echo_with_color(Colors.BLUE, f"      Account: {obligation_data.get('accountAddress', '')}")
                    echo_with_color(Colors.BLUE, f"      Contract ID: {obligation_data.get('contractId', '')}")
                    echo_with_color(Colors.BLUE, f"      Transaction ID: {obligation_data.get('transactionId', '')}")
                    echo_with_color(Colors.BLUE, f"      Message: {obligation_data.get('message', '')}")
                    echo_with_color(Colors.BLUE, f"      Message ID: {obligation_data.get('messageId', '')}")
                    echo_with_color(Colors.BLUE, f"      Obligation Result: {obligation_data.get('obligationResult', '')}")
                    if obligation_data.get('idHash'):
                        echo_with_color(Colors.CYAN, f"      ID Hash: {obligation_data.get('idHash')}")
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_account_address, {command_name}_message, {command_name}_obligation_result, {command_name}_message_id, {command_name}_contract_id, {command_name}_transaction_id, {command_name}_signature, {command_name}_timestamp, {command_name}_id_hash")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Create obligation failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_accept_obligation(self, command_name: str, user_email: str, user_password: str,
                                 contract_id: str, idempotency_key: Optional[str] = None,
                                 group_name: Optional[str] = None) -> bool:
        """Execute accept obligation command using GraphQL."""
        echo_with_color(Colors.CYAN, f"✅ Executing accept obligation command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare GraphQL mutation
        input_params = [f'contractId: "{contract_id}"']
        if idempotency_key:
            input_params.append(f'idempotencyKey: "{idempotency_key}"')
        
        mutation = f"""
            mutation {{
                acceptObligation(input: {{ {', '.join(input_params)} }}) {{
                    success
                    message
                    accountAddress
                    obligationId
                    acceptResult
                    messageId
                    transactionId
                    signature
                    timestamp
                }}
            }}
        """
        
        payload = {"query": mutation}
        
        echo_with_color(Colors.BLUE, "  📋 GraphQL mutation:")
        echo_with_color(Colors.BLUE, f"    {mutation.strip()}")
        
        # Send GraphQL request
        try:
            response = requests.post(
                f"{self.pay_service_url}/graphql",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {jwt_token}"
                },
                json=payload,
                timeout=30
            )
            
            echo_with_color(Colors.BLUE, f"  📡 Raw GraphQL response: '{response.text}'")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('acceptObligation', {}).get('success'):
                    accept_data = data['data']['acceptObligation']
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "account_address", accept_data.get('accountAddress', ''))
                    command_output_store.store_command_output(command_name, "message", accept_data.get('message', ''))
                    command_output_store.store_command_output(command_name, "obligation_id", accept_data.get('obligationId', ''))
                    command_output_store.store_command_output(command_name, "message_id", accept_data.get('messageId', ''))
                    command_output_store.store_command_output(command_name, "transaction_id", accept_data.get('transactionId', ''))
                    command_output_store.store_command_output(command_name, "signature", accept_data.get('signature', ''))
                    command_output_store.store_command_output(command_name, "timestamp", accept_data.get('timestamp', ''))
                    command_output_store.store_command_output(command_name, "accept_result", accept_data.get('acceptResult', ''))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Accept obligation successful!")
                    echo_with_color(Colors.BLUE, f"      Account: {accept_data.get('accountAddress', '')}")
                    echo_with_color(Colors.BLUE, f"      Obligation ID: {accept_data.get('obligationId', '')}")
                    echo_with_color(Colors.BLUE, f"      Message: {accept_data.get('message', '')}")
                    echo_with_color(Colors.BLUE, f"      Message ID: {accept_data.get('messageId', '')}")
                    echo_with_color(Colors.BLUE, f"      Transaction ID: {accept_data.get('transactionId', '')}")
                    echo_with_color(Colors.BLUE, f"      Accept Result: {accept_data.get('acceptResult', '')}")
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_account_address, {command_name}_message, {command_name}_obligation_id, {command_name}_message_id, {command_name}_transaction_id, {command_name}_signature, {command_name}_timestamp, {command_name}_accept_result")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Accept obligation failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_obligations(self, command_name: str, user_email: str, user_password: str,
                           group_name: Optional[str] = None) -> bool:
        """Execute obligations command using REST API."""
        echo_with_color(Colors.CYAN, f"🤝 Executing obligations command via REST API: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        echo_with_color(Colors.BLUE, f"  🔑 JWT token obtained (first 50 chars): {jwt_token[:50]}...")
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Send REST API request
        try:
            response = requests.get(
                f"{self.pay_service_url}/obligations",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=30
            )
            
            echo_with_color(Colors.BLUE, f"  📡 Raw REST API response: '{response.text}'")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    obligations = data.get('obligations', [])
                    obligations_count = len(obligations)
                    timestamp = data.get('timestamp', '')
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "obligations_count", str(obligations_count))
                    command_output_store.store_command_output(command_name, "timestamp", timestamp)
                    command_output_store.store_command_output(command_name, "obligations_json", json.dumps(obligations))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Obligations retrieved successfully!")
                    
                    echo_with_color(Colors.BLUE, "  📋 Obligations Information:")
                    echo_with_color(Colors.BLUE, f"      Total Obligations: {obligations_count}")
                    echo_with_color(Colors.BLUE, f"      Timestamp: {timestamp}")
                    
                    # Display obligations if they exist
                    if obligations_count > 0:
                        echo_with_color(Colors.YELLOW, "  🤝 Obligations Details:")
                        for obligation in obligations:
                            echo_with_color(Colors.BLUE, f"      {json.dumps(obligation, indent=6)}")
                    else:
                        echo_with_color(Colors.YELLOW, "  📭 No obligations found for this user")
                    
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_obligations_count, {command_name}_timestamp, {command_name}_obligations_json")
                    return True
                else:
                    error_msg = data.get('error', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Obligations retrieval failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_list_groups(self, command_name: str, user_email: str, user_password: str,
                           group_name: Optional[str] = None) -> bool:
        """Execute list_groups command using Auth Service."""
        echo_with_color(Colors.CYAN, f"👥 Executing list_groups command via Auth Service: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        echo_with_color(Colors.BLUE, f"  🔑 JWT token obtained (first 50 chars): {jwt_token[:50]}...")
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Make request to auth service
        try:
            response = requests.get(
                f"{auth_service.auth_service_url}/auth/groups/user",
                headers={"Authorization": f"Bearer {jwt_token}"},
                timeout=30
            )
            
            echo_with_color(Colors.BLUE, "  📡 Response received:")
            echo_with_color(Colors.BLUE, f"    {response.text}")
            
            if response.status_code == 200:
                groups = response.json()
                if isinstance(groups, list):
                    group_count = len(groups)
                    echo_with_color(Colors.GREEN, "    ✅ List groups successful!")
                    echo_with_color(Colors.GREEN, f"    📊 Found {group_count} groups for user")
                    
                    # Display groups in a formatted way
                    if group_count > 0:
                        echo_with_color(Colors.CYAN, "    📋 Groups:")
                        for group in groups:
                            echo_with_color(Colors.BLUE, f"      • {group.get('name', 'Unknown')} (ID: {group.get('id', 'Unknown')}, Type: {group.get('group_type', 'Unknown')}, Active: {group.get('is_active', 'Unknown')})")
                    else:
                        echo_with_color(Colors.YELLOW, "    📋 No groups found for this user")
                    
                    # Store command outputs for variable substitution
                    command_output_store.store_command_output(f"{command_name}_groups", "response", response.text)
                    command_output_store.store_command_output(f"{command_name}_group_count", "count", str(group_count))
                    
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_groups, {command_name}_group_count")
                    return True
                else:
                    error_msg = groups.get('message') or groups.get('error') or 'Unknown error'
                    echo_with_color(Colors.RED, f"    ❌ List groups failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False


# Global additional command executor instance
additional_command_executor = AdditionalCommandExecutor()
