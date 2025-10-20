#!/usr/bin/env python3
"""
Test script to verify YieldFabric Python Port installation
This script tests basic functionality without requiring actual services
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing module imports...")
    
    try:
        from yieldfabric import main
        print("  ✅ yieldfabric.main imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.main: {e}")
        return False
    
    try:
        from yieldfabric import utils
        print("  ✅ yieldfabric.utils imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.utils: {e}")
        return False
    
    try:
        from yieldfabric import auth
        print("  ✅ yieldfabric.auth imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.auth: {e}")
        return False
    
    try:
        from yieldfabric import executors
        print("  ✅ yieldfabric.executors imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.executors: {e}")
        return False
    
    try:
        from yieldfabric import executors_additional
        print("  ✅ yieldfabric.executors_additional imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.executors_additional: {e}")
        return False
    
    try:
        from yieldfabric import validation
        print("  ✅ yieldfabric.validation imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import yieldfabric.validation: {e}")
        return False
    
    return True

def test_dependencies():
    """Test that required dependencies are available."""
    print("🔍 Testing dependencies...")
    
    try:
        import requests
        print(f"  ✅ requests {requests.__version__} available")
    except ImportError as e:
        print(f"  ❌ requests not available: {e}")
        return False
    
    try:
        import yaml
        print(f"  ✅ PyYAML available")
    except ImportError as e:
        print(f"  ❌ PyYAML not available: {e}")
        return False
    
    try:
        import json
        print(f"  ✅ json (built-in) available")
    except ImportError as e:
        print(f"  ❌ json not available: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without requiring services."""
    print("🔍 Testing basic functionality...")
    
    try:
        from yieldfabric.utils import echo_with_color, Colors
        echo_with_color(Colors.GREEN, "  ✅ Color output working")
    except Exception as e:
        print(f"  ❌ Color output failed: {e}")
        return False
    
    try:
        from yieldfabric.utils import command_output_store
        command_output_store.store("test", "field", "value")
        stored_value = command_output_store.get("test", "field")
        if stored_value == "value":
            print("  ✅ Variable storage working")
        else:
            print(f"  ❌ Variable storage failed: expected 'value', got '{stored_value}'")
            return False
    except Exception as e:
        print(f"  ❌ Variable storage failed: {e}")
        return False
    
    try:
        from yieldfabric.utils import substitute_variables
        result = substitute_variables("test_$test.field")
        if result == "test_value":
            print("  ✅ Variable substitution working")
        else:
            print(f"  ❌ Variable substitution failed: expected 'test_value', got '{result}'")
            return False
    except Exception as e:
        print(f"  ❌ Variable substitution failed: {e}")
        return False
    
    return True

def test_yaml_parsing():
    """Test YAML parsing functionality."""
    print("🔍 Testing YAML parsing...")
    
    try:
        from yieldfabric.utils import parse_yaml
        import tempfile
        import yaml
        
        # Create a temporary YAML file
        test_data = {
            "commands": [
                {
                    "name": "test_command",
                    "type": "test",
                    "parameters": {
                        "test_param": "test_value"
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Test parsing
            command_name = parse_yaml(temp_file, ".commands[0].name")
            if command_name == "test_command":
                print("  ✅ YAML parsing working")
            else:
                print(f"  ❌ YAML parsing failed: expected 'test_command', got '{command_name}'")
                return False
        finally:
            os.unlink(temp_file)
    
    except Exception as e:
        print(f"  ❌ YAML parsing failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 YieldFabric Python Port - Installation Test")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    print()
    
    # Test dependencies
    if not test_dependencies():
        all_passed = False
    
    print()
    
    # Test basic functionality
    if not test_basic_functionality():
        all_passed = False
    
    print()
    
    # Test YAML parsing
    if not test_yaml_parsing():
        all_passed = False
    
    print()
    print("=" * 50)
    
    if all_passed:
        print("✅ All tests passed! Installation is working correctly.")
        print("You can now use the YieldFabric Python port.")
        print()
        print("Next steps:")
        print("1. Create a commands.yaml file")
        print("2. Run: python -m yieldfabric.main execute commands.yaml")
        print("3. Or run: python example_usage.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the installation.")
        print("Make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == '__main__':
    sys.exit(main())
