#!/usr/bin/env python3
"""
Basic usage example for YieldFabric v2.0
"""

from yieldfabric import YieldFabricConfig, YieldFabricRunner

def main():
    """Basic usage example."""
    
    # Create configuration
    config = YieldFabricConfig.from_env()
    
    # Or create with custom settings
    config = YieldFabricConfig(
        pay_service_url="https://pay.yieldfabric.io",
        auth_service_url="https://auth.yieldfabric.io",
        command_delay=3,
        debug=True  # Enable debug logging
    )
    
    # Execute commands from YAML file
    with YieldFabricRunner(config) as runner:
        success = runner.execute_file("commands.yaml")
        
        if success:
            print("✅ All commands executed successfully!")
        else:
            print("❌ Some commands failed")

if __name__ == '__main__':
    main()

