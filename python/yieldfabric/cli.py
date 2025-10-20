"""
CLI interface for YieldFabric
"""

import argparse
import sys

from .config import YieldFabricConfig
from .core.runner import YieldFabricRunner
from .utils.logger import get_logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='YieldFabric GraphQL Commands Execution - Refactored Version 2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s execute commands.yaml
  %(prog)s status commands.yaml
  %(prog)s --debug execute commands.yaml
  
Environment Variables:
  PAY_SERVICE_URL      Payments service URL (default: https://pay.yieldfabric.io)
  AUTH_SERVICE_URL     Auth service URL (default: https://auth.yieldfabric.io)
  COMMAND_DELAY        Delay between commands in seconds (default: 3)
  DEBUG                Enable debug logging (default: false)
        """
    )
    
    parser.add_argument(
        'command',
        choices=['execute', 'status', 'validate', 'version'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'yaml_file',
        nargs='?',
        default='commands.yaml',
        help='YAML file containing commands (default: commands.yaml)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--pay-service-url',
        help='Override payments service URL'
    )
    
    parser.add_argument(
        '--auth-service-url',
        help='Override auth service URL'
    )
    
    parser.add_argument(
        '--command-delay',
        type=int,
        help='Override command delay in seconds'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = YieldFabricConfig.from_env()
    
    # Override with command line arguments
    if args.debug:
        config.debug = True
    if args.pay_service_url:
        config.pay_service_url = args.pay_service_url
    if args.auth_service_url:
        config.auth_service_url = args.auth_service_url
    if args.command_delay:
        config.command_delay = args.command_delay
    
    logger = get_logger(debug=config.debug)
    
    # Handle version command
    if args.command == 'version':
        from . import __version__
        logger.info(f"YieldFabric Python Port v{__version__}")
        logger.info(f"Pay Service: {config.pay_service_url}")
        logger.info(f"Auth Service: {config.auth_service_url}")
        return 0
    
    # For other commands, check if file exists
    import os
    if not os.path.exists(args.yaml_file):
        logger.error(f"❌ YAML file not found: {args.yaml_file}")
        return 1
    
    # Create runner
    with YieldFabricRunner(config) as runner:
        if args.command == 'execute':
            success = runner.execute_file(args.yaml_file)
            return 0 if success else 1
        
        elif args.command == 'status':
            success = runner.show_status(args.yaml_file)
            return 0 if success else 1
        
        elif args.command == 'validate':
            is_valid, errors = runner.yaml_validator.validate(args.yaml_file)
            if is_valid:
                logger.success("✅ YAML file is valid")
                return 0
            else:
                logger.error("❌ YAML validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                return 1
        
        else:
            logger.error(f"❌ Unknown command: {args.command}")
            return 1


if __name__ == '__main__':
    sys.exit(main())

