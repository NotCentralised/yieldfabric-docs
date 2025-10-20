#!/usr/bin/env python3
"""
Example usage of YieldFabric Python Port
Demonstrates how to use the Python port programmatically
"""

import os
import sys
from yieldfabric.main import YieldFabricCommandRunner
from yieldfabric.utils import echo_with_color, Colors

def main():
    """Example usage of the YieldFabric Python port."""
    
    echo_with_color(Colors.CYAN, "🚀 YieldFabric Python Port - Example Usage")
    echo_with_color(Colors.CYAN, "=" * 50)
    
    # Set up service URLs (can be overridden by environment variables)
    pay_service_url = os.environ.get('PAY_SERVICE_URL', 'https://pay.yieldfabric.io')
    auth_service_url = os.environ.get('AUTH_SERVICE_URL', 'https://auth.yieldfabric.io')
    
    echo_with_color(Colors.BLUE, f"Pay Service URL: {pay_service_url}")
    echo_with_color(Colors.BLUE, f"Auth Service URL: {auth_service_url}")
    echo_with_color(Colors.CYAN, "")
    
    # Create command runner
    runner = YieldFabricCommandRunner(pay_service_url, auth_service_url)
    
    # Example 1: Show help
    echo_with_color(Colors.GREEN, "📖 Example 1: Show help")
    runner.show_help()
    echo_with_color(Colors.CYAN, "")
    
    # Example 2: Check if commands.yaml exists and show status
    commands_file = "commands.yaml"
    if os.path.exists(commands_file):
        echo_with_color(Colors.GREEN, f"📋 Example 2: Check status of {commands_file}")
        runner.show_commands_status(commands_file)
        echo_with_color(Colors.CYAN, "")
        
        # Example 3: Execute commands (if file exists)
        echo_with_color(Colors.GREEN, f"🚀 Example 3: Execute commands from {commands_file}")
        echo_with_color(Colors.YELLOW, "Note: This will actually execute the commands!")
        response = input("Do you want to proceed? (y/N): ")
        if response.lower() in ['y', 'yes']:
            success = runner.execute_all_commands(commands_file)
            if success:
                echo_with_color(Colors.GREEN, "✅ All commands executed successfully!")
            else:
                echo_with_color(Colors.RED, "❌ Some commands failed")
        else:
            echo_with_color(Colors.YELLOW, "Skipping command execution")
    else:
        echo_with_color(Colors.YELLOW, f"📋 Example 2: {commands_file} not found")
        echo_with_color(Colors.BLUE, "Create a commands.yaml file to see more examples")
        echo_with_color(Colors.CYAN, "")
        
        # Show example YAML structure
        echo_with_color(Colors.GREEN, "📝 Example YAML structure:")
        echo_with_color(Colors.BLUE, """
commands:
  - name: "deposit_1"
    type: "deposit"
    user:
      id: "user@example.com"
      password: "password123"
      group: "Admin Group"
    parameters:
      denomination: "USD"
      amount: "100.00"
      idempotency_key: "deposit_$(date +%s)"

  - name: "balance_1"
    type: "balance"
    user:
      id: "user@example.com"
      password: "password123"
      group: "Admin Group"
    parameters:
      denomination: "USD"
      obligor: "user@example.com"
      group_id: "$deposit_1.group_id"
        """)
    
    # Example 4: Show stored variables (for debugging)
    echo_with_color(Colors.GREEN, "🔍 Example 4: Show stored variables")
    runner.show_stored_variables()
    echo_with_color(Colors.CYAN, "")
    
    # Example 5: Environment variables
    echo_with_color(Colors.GREEN, "🌍 Example 5: Environment variables")
    echo_with_color(Colors.BLUE, "Current environment variables:")
    echo_with_color(Colors.BLUE, f"  COMMAND_DELAY: {os.environ.get('COMMAND_DELAY', '3')}")
    echo_with_color(Colors.BLUE, f"  PAY_SERVICE_URL: {pay_service_url}")
    echo_with_color(Colors.BLUE, f"  AUTH_SERVICE_URL: {auth_service_url}")
    echo_with_color(Colors.CYAN, "")
    
    echo_with_color(Colors.GREEN, "✅ Example usage completed!")
    echo_with_color(Colors.CYAN, "For more information, see README.md")

if __name__ == '__main__':
    main()
