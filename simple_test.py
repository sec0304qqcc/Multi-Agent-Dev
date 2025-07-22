#!/usr/bin/env python3
"""
Simple test for Multi-Agent Development Platform setup
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test basic imports"""
    print("\nTesting imports...")
    try:
        from src.config.settings import settings
        print("- Settings imported successfully")
        
        from src.agents.developer_agent import DeveloperAgent
        print("- Developer Agent imported successfully")
        
        from src.agents.reviewer_agent import ReviewerAgent
        print("- Reviewer Agent imported successfully")
        
        from src.core.base_agent import TaskResult
        print("- Base Agent imported successfully")
        
        return True
    except Exception as e:
        print(f"Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality"""
    print("\nTesting basic functionality...")
    try:
        from src.config.settings import settings
        from src.agents.developer_agent import DeveloperAgent
        from src.agents.reviewer_agent import ReviewerAgent
        
        print(f"- App Name: {settings.app_name}")
        print(f"- Version: {settings.app_version}")
        print(f"- Environment: {settings.environment}")
        
        # Test agent creation
        developer = DeveloperAgent(agent_id="test_dev")
        print(f"- Developer Agent created: {developer.agent_id}")
        
        reviewer = ReviewerAgent(agent_id="test_rev")
        print(f"- Reviewer Agent created: {reviewer.agent_id}")
        
        return True
    except Exception as e:
        print(f"Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Multi-Agent Development Platform - Simple Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_imports():
        tests_passed += 1
        print("[PASS] Import test")
    else:
        print("[FAIL] Import test")
    
    if test_basic_functionality():
        tests_passed += 1
        print("[PASS] Basic functionality test")
    else:
        print("[FAIL] Basic functionality test")
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("All tests passed! Setup is working correctly.")
        sys.exit(0)
    else:
        print("Some tests failed. Check the errors above.")
        sys.exit(1)