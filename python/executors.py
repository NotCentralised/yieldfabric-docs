"""
YieldFabric Command Executors Module
Contains functions for executing different types of commands.
"""

import json
import requests
from typing import Any, Dict, List, Optional
from .utils import Colors, echo_with_color, command_output_store
from .auth import auth_service


class CommandExecutor:
    """Execute various YieldFabric commands via GraphQL and REST APIs."""
    
    def __init__(self, pay_service_url: str = "https://pay.yieldfabric.io"):
        self.pay_service_url = pay_service_url
    
    def execute_deposit(self, command_name: str, user_email: str, user_password: str, 
                       denomination: str, amount: str, idempotency_key: Optional[str] = None,
                       group_name: Optional[str] = None) -> bool:
        """Execute deposit command using GraphQL."""
        echo_with_color(Colors.CYAN, f"🏦 Executing deposit command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        echo_with_color(Colors.BLUE, f"  🔑 JWT token obtained (first 50 chars): {jwt_token[:50]}...")
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare GraphQL mutation
        if idempotency_key:
            mutation = f"""
                mutation {{
                    deposit(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}",
                        idempotencyKey: "{idempotency_key}"
                    }}) {{
                        success
                        message
                        accountAddress
                        depositResult
                        messageId
                        timestamp
                    }}
                }}
            """
        else:
            mutation = f"""
                mutation {{
                    deposit(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}"
                    }}) {{
                        success
                        message
                        accountAddress
                        depositResult
                        messageId
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
                if data.get('data', {}).get('deposit', {}).get('success'):
                    deposit_data = data['data']['deposit']
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "account_address", deposit_data.get('accountAddress', ''))
                    command_output_store.store_command_output(command_name, "message", deposit_data.get('message', ''))
                    command_output_store.store_command_output(command_name, "message_id", deposit_data.get('messageId', ''))
                    command_output_store.store_command_output(command_name, "deposit_result", deposit_data.get('depositResult', ''))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Deposit successful!")
                    echo_with_color(Colors.BLUE, f"      Account: {deposit_data.get('accountAddress', '')}")
                    echo_with_color(Colors.BLUE, f"      Message: {deposit_data.get('message', '')}")
                    echo_with_color(Colors.BLUE, f"      Message ID: {deposit_data.get('messageId', '')}")
                    echo_with_color(Colors.BLUE, f"      Deposit Result: {deposit_data.get('depositResult', '')}")
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_account_address, {command_name}_message, {command_name}_message_id, {command_name}_deposit_result")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Deposit failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_withdraw(self, command_name: str, user_email: str, user_password: str,
                        denomination: str, amount: str, idempotency_key: Optional[str] = None,
                        group_name: Optional[str] = None) -> bool:
        """Execute withdraw command using GraphQL."""
        echo_with_color(Colors.CYAN, f"💸 Executing withdraw command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        echo_with_color(Colors.BLUE, f"  🔑 JWT token obtained (first 50 chars): {jwt_token[:50]}...")
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare GraphQL mutation
        if idempotency_key:
            mutation = f"""
                mutation {{
                    withdraw(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}",
                        idempotencyKey: "{idempotency_key}"
                    }}) {{
                        success
                        message
                        accountAddress
                        withdrawResult
                        messageId
                        timestamp
                    }}
                }}
            """
        else:
            mutation = f"""
                mutation {{
                    withdraw(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}"
                    }}) {{
                        success
                        message
                        accountAddress
                        withdrawResult
                        messageId
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
            
            echo_with_color(Colors.BLUE, f"  📥 Response received:")
            echo_with_color(Colors.BLUE, f"    {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('withdraw', {}).get('success'):
                    withdraw_data = data['data']['withdraw']
                    
                    # Store command output for variable substitution
                    command_output_store.store_command_output(command_name, "response", response.text)
                    
                    echo_with_color(Colors.GREEN, "    ✅ Withdraw successful!")
                    echo_with_color(Colors.GREEN, f"      Message ID: {withdraw_data.get('messageId', 'N/A')}")
                    echo_with_color(Colors.GREEN, f"      Account Address: {withdraw_data.get('accountAddress', 'N/A')}")
                    echo_with_color(Colors.GREEN, f"      Withdraw Result: {withdraw_data.get('withdrawResult', 'N/A')}")
                    echo_with_color(Colors.GREEN, f"      Timestamp: {withdraw_data.get('timestamp', 'N/A')}")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Withdraw failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_instant(self, command_name: str, user_email: str, user_password: str,
                       denomination: str, amount: str, destination_id: str, 
                       idempotency_key: Optional[str] = None, group_name: Optional[str] = None) -> bool:
        """Execute instant command using GraphQL."""
        echo_with_color(Colors.CYAN, f"⚡ Executing instant command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare GraphQL mutation
        if idempotency_key:
            mutation = f"""
                mutation {{
                    instant(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}",
                        destinationId: "{destination_id}",
                        idempotencyKey: "{idempotency_key}"
                    }}) {{
                        success
                        message
                        accountAddress
                        destinationId
                        idHash
                        messageId
                        paymentId
                        sendResult
                        timestamp
                    }}
                }}
            """
        else:
            mutation = f"""
                mutation {{
                    instant(input: {{
                        assetId: "{denomination}",
                        amount: "{amount}",
                        destinationId: "{destination_id}"
                    }}) {{
                        success
                        message
                        accountAddress
                        destinationId
                        idHash
                        messageId
                        paymentId
                        sendResult
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
                if data.get('data', {}).get('instant', {}).get('success'):
                    instant_data = data['data']['instant']
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "account_address", instant_data.get('accountAddress', ''))
                    command_output_store.store_command_output(command_name, "destination_id", instant_data.get('destinationId', ''))
                    command_output_store.store_command_output(command_name, "message", instant_data.get('message', ''))
                    command_output_store.store_command_output(command_name, "id_hash", instant_data.get('idHash', ''))
                    command_output_store.store_command_output(command_name, "message_id", instant_data.get('messageId', ''))
                    command_output_store.store_command_output(command_name, "payment_id", instant_data.get('paymentId', ''))
                    command_output_store.store_command_output(command_name, "send_result", instant_data.get('sendResult', ''))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Instant payment successful!")
                    echo_with_color(Colors.BLUE, f"      From Account: {instant_data.get('accountAddress', '')}")
                    echo_with_color(Colors.BLUE, f"      To Address: {instant_data.get('destinationId', '')}")
                    echo_with_color(Colors.BLUE, f"      Message: {instant_data.get('message', '')}")
                    echo_with_color(Colors.BLUE, f"      Message ID: {instant_data.get('messageId', '')}")
                    echo_with_color(Colors.BLUE, f"      Payment ID: {instant_data.get('paymentId', '')}")
                    echo_with_color(Colors.BLUE, f"      Send Result: {instant_data.get('sendResult', '')}")
                    if instant_data.get('idHash'):
                        echo_with_color(Colors.CYAN, f"      ID Hash: {instant_data.get('idHash')}")
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_account_address, {command_name}_destination_id, {command_name}_message, {command_name}_id_hash, {command_name}_message_id, {command_name}_payment_id, {command_name}_send_result")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Instant payment failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_balance(self, command_name: str, user_email: str, user_password: str,
                       denomination: str, obligor: str, group_id: str, 
                       group_name: Optional[str] = None) -> bool:
        """Execute balance command using REST API."""
        echo_with_color(Colors.CYAN, f"💰 Executing balance command via REST API: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        echo_with_color(Colors.BLUE, f"  🔑 JWT token obtained (first 50 chars): {jwt_token[:50]}...")
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare query parameters
        params = {
            "denomination": denomination,
            "obligor": obligor,
            "group_id": group_id
        }
        
        echo_with_color(Colors.BLUE, "  📋 Query parameters:")
        echo_with_color(Colors.BLUE, f"    denomination: {denomination}")
        echo_with_color(Colors.BLUE, f"    obligor: {obligor}")
        echo_with_color(Colors.BLUE, f"    group_id: {group_id}")
        
        # Send REST API request
        try:
            response = requests.get(
                f"{self.pay_service_url}/balance",
                headers={"Authorization": f"Bearer {jwt_token}"},
                params=params,
                timeout=30
            )
            
            echo_with_color(Colors.BLUE, f"  📡 Raw REST API response: '{response.text}'")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    balance_data = data.get('balance', {})
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "private_balance", str(balance_data.get('private_balance', '')))
                    command_output_store.store_command_output(command_name, "public_balance", str(balance_data.get('public_balance', '')))
                    command_output_store.store_command_output(command_name, "decimals", str(balance_data.get('decimals', '')))
                    command_output_store.store_command_output(command_name, "beneficial_balance", str(balance_data.get('beneficial_balance', '')))
                    command_output_store.store_command_output(command_name, "outstanding", str(balance_data.get('outstanding', '')))
                    command_output_store.store_command_output(command_name, "locked_out_count", str(len(balance_data.get('locked_out', []))))
                    command_output_store.store_command_output(command_name, "locked_in_count", str(len(balance_data.get('locked_in', []))))
                    command_output_store.store_command_output(command_name, "denomination", denomination)
                    command_output_store.store_command_output(command_name, "obligor", obligor)
                    command_output_store.store_command_output(command_name, "group_id", group_id)
                    command_output_store.store_command_output(command_name, "timestamp", str(data.get('timestamp', '')))
                    
                    # Store locked transactions as JSON strings
                    command_output_store.store_command_output(command_name, "locked_out", json.dumps(balance_data.get('locked_out', [])))
                    command_output_store.store_command_output(command_name, "locked_in", json.dumps(balance_data.get('locked_in', [])))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Balance retrieved successfully!")
                    
                    echo_with_color(Colors.BLUE, "  📋 Balance Information:")
                    echo_with_color(Colors.BLUE, f"      Private Balance: {balance_data.get('private_balance', '')}")
                    echo_with_color(Colors.BLUE, f"      Public Balance: {balance_data.get('public_balance', '')}")
                    echo_with_color(Colors.BLUE, f"      Decimals: {balance_data.get('decimals', '')}")
                    echo_with_color(Colors.GREEN, f"      Beneficial Balance: {balance_data.get('beneficial_balance', '')}")
                    echo_with_color(Colors.YELLOW, f"      Outstanding: {balance_data.get('outstanding', '')}")
                    echo_with_color(Colors.BLUE, f"      Locked Out Count: {len(balance_data.get('locked_out', []))}")
                    echo_with_color(Colors.BLUE, f"      Locked In Count: {len(balance_data.get('locked_in', []))}")
                    echo_with_color(Colors.BLUE, f"      Denomination: {denomination}")
                    echo_with_color(Colors.BLUE, f"      Obligor: {obligor}")
                    echo_with_color(Colors.BLUE, f"      Group ID: {group_id}")
                    echo_with_color(Colors.BLUE, f"      Timestamp: {data.get('timestamp', '')}")
                    
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_private_balance, {command_name}_public_balance, {command_name}_decimals, {command_name}_beneficial_balance, {command_name}_outstanding, {command_name}_locked_out_count, {command_name}_locked_in_count, {command_name}_locked_out, {command_name}_locked_in, {command_name}_denomination, {command_name}_obligor, {command_name}_group_id, {command_name}_timestamp")
                    return True
                else:
                    error_msg = data.get('error', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Balance retrieval failed: {error_msg}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False
    
    def execute_accept(self, command_name: str, user_email: str, user_password: str,
                      payment_id: str, idempotency_key: Optional[str] = None,
                      group_name: Optional[str] = None) -> bool:
        """Execute accept command using GraphQL."""
        echo_with_color(Colors.CYAN, f"✅ Executing accept command via GraphQL: {command_name}")
        
        # Login to get JWT token
        jwt_token = auth_service.login_user(user_email, user_password, group_name)
        if not jwt_token:
            echo_with_color(Colors.RED, f"❌ Failed to get JWT token for user: {user_email}")
            return False
        
        if group_name:
            echo_with_color(Colors.CYAN, f"  🏢 Using delegation JWT for group: {group_name}")
        
        # Prepare GraphQL mutation
        input_params = f'paymentId: "{payment_id}"'
        if idempotency_key:
            input_params += f', idempotencyKey: "{idempotency_key}"'
        
        mutation = f"""
            mutation {{
                accept(input: {{ {input_params} }}) {{
                    success
                    message
                    accountAddress
                    idHash
                    acceptResult
                    messageId
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
                if data.get('data', {}).get('accept', {}).get('success'):
                    accept_data = data['data']['accept']
                    
                    # Store outputs for variable substitution
                    command_output_store.store_command_output(command_name, "account_address", accept_data.get('accountAddress', ''))
                    command_output_store.store_command_output(command_name, "message", accept_data.get('message', ''))
                    command_output_store.store_command_output(command_name, "id_hash", accept_data.get('idHash', ''))
                    command_output_store.store_command_output(command_name, "message_id", accept_data.get('messageId', ''))
                    command_output_store.store_command_output(command_name, "accept_result", accept_data.get('acceptResult', ''))
                    
                    echo_with_color(Colors.GREEN, "    ✅ Accept successful!")
                    echo_with_color(Colors.BLUE, f"      Account: {accept_data.get('accountAddress', '')}")
                    echo_with_color(Colors.BLUE, f"      ID Hash: {accept_data.get('idHash', '')}")
                    echo_with_color(Colors.BLUE, f"      Message: {accept_data.get('message', '')}")
                    echo_with_color(Colors.BLUE, f"      Message ID: {accept_data.get('messageId', '')}")
                    echo_with_color(Colors.BLUE, f"      Accept Result: {accept_data.get('acceptResult', '')}")
                    echo_with_color(Colors.CYAN, "      📝 Stored outputs for variable substitution:")
                    echo_with_color(Colors.CYAN, f"        {command_name}_account_address, {command_name}_message, {command_name}_id_hash, {command_name}_message_id, {command_name}_accept_result")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error')
                    echo_with_color(Colors.RED, f"    ❌ Accept failed: {error_msg}")
                    echo_with_color(Colors.BLUE, f"      Full response: {response.text}")
                    return False
            else:
                echo_with_color(Colors.RED, f"    ❌ HTTP error: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            echo_with_color(Colors.RED, f"    ❌ Request failed: {e}")
            return False


# Global command executor instance
command_executor = CommandExecutor()
