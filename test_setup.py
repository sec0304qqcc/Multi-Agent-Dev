#!/usr/bin/env python3
"""
Test setup script for Multi-Agent Development Platform

This script tests the basic functionality of the platform components
without requiring external dependencies like Redis or PostgreSQL.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.config.settings import settings
    from src.agents.developer_agent import DeveloperAgent
    from src.agents.reviewer_agent import ReviewerAgent
    from src.core.base_agent import TaskResult
    print("[OK] Import test passed - all modules can be imported successfully")
except ImportError as e:
    print(f"[FAIL] Import test failed: {e}")
    sys.exit(1)


async def test_agent_initialization():
    """Test agent initialization"""
    print("\n[TEST] Testing Agent Initialization...")
    
    try:
        # Test Developer Agent
        developer = DeveloperAgent(agent_id="test_developer")
        print(f"[OK] Developer Agent initialized: {developer.agent_id}")
        
        # Test Reviewer Agent
        reviewer = ReviewerAgent(agent_id="test_reviewer")
        print(f"[OK] Reviewer Agent initialized: {reviewer.agent_id}")
        
        return developer, reviewer
    
    except Exception as e:
        print(f"[FAIL] Agent initialization failed: {e}")
        return None, None


async def test_agent_health_check():
    """Test agent health checks"""
    print("\n❤️ Testing Agent Health Checks...")
    
    try:
        developer = DeveloperAgent(agent_id="health_test_dev")
        reviewer = ReviewerAgent(agent_id="health_test_rev")
        
        # Test health checks
        dev_health = await developer.health_check()
        rev_health = await reviewer.health_check()
        
        print(f"✅ Developer Agent health: {dev_health['status']}")
        print(f"✅ Reviewer Agent health: {rev_health['status']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_developer_agent_basic_functionality():
    """Test Developer Agent basic functionality"""
    print("\n👨‍💻 Testing Developer Agent Functionality...")
    
    try:
        developer = DeveloperAgent(agent_id="func_test_dev")
        
        # Test task processing
        context = {
            "language": "python",
            "requirements": ["Create a simple function"],
            "task_id": "test_task_001"
        }
        
        result = await developer.process_task(
            task_description="Create a simple Python function that adds two numbers",
            context=context
        )
        
        print(f"✅ Developer Agent task completed: {result.status}")
        print(f"   Task ID: {result.task_id}")
        print(f"   Agent ID: {result.agent_id}")
        
        return True
    
    except Exception as e:
        print(f"❌ Developer Agent test failed: {e}")
        return False


async def test_reviewer_agent_basic_functionality():
    """Test Reviewer Agent basic functionality"""
    print("\n🔍 Testing Reviewer Agent Functionality...")
    
    try:
        reviewer = ReviewerAgent(agent_id="func_test_rev")
        
        # Test code review
        sample_code = """
def add_numbers(a, b):
    return a + b

def main():
    result = add_numbers(5, 3)
    print(result)

if __name__ == "__main__":
    main()
"""
        
        context = {
            "code": sample_code,
            "language": "python",
            "task_id": "test_review_001"
        }
        
        result = await reviewer.process_task(
            task_description="Review this Python code for quality and best practices",
            context=context
        )
        
        print(f"✅ Reviewer Agent task completed: {result.status}")
        print(f"   Task ID: {result.task_id}")
        print(f"   Agent ID: {result.agent_id}")
        
        return True
    
    except Exception as e:
        print(f"❌ Reviewer Agent test failed: {e}")
        return False


async def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ Testing Configuration...")
    
    try:
        print(f"✅ App Name: {settings.app_name}")
        print(f"✅ Version: {settings.app_version}")
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Debug Mode: {settings.debug}")
        print(f"✅ Log Level: {settings.log_level}")
        print(f"✅ Default LLM Model: {settings.default_llm_model}")
        
        return True
    
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_agent_status():
    """Test agent status functionality"""
    print("\n📊 Testing Agent Status...")
    
    try:
        developer = DeveloperAgent(agent_id="status_test_dev")
        reviewer = ReviewerAgent(agent_id="status_test_rev")
        
        dev_status = developer.get_status()
        rev_status = reviewer.get_status()
        
        print(f"✅ Developer Status: {dev_status['status']}")
        print(f"   Current Tasks: {dev_status['current_tasks']}")
        print(f"   Success Rate: {dev_status['metrics'].success_rate}")
        
        print(f"✅ Reviewer Status: {rev_status['status']}")
        print(f"   Current Tasks: {rev_status['current_tasks']}")
        print(f"   Success Rate: {rev_status['metrics'].success_rate}")
        
        return True
    
    except Exception as e:
        print(f"❌ Agent status test failed: {e}")
        return False


def test_file_structure():
    """Test that all required files exist"""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        "src/__init__.py",
        "src/config/settings.py",
        "src/core/base_agent.py",
        "src/core/message_bus.py",
        "src/agents/developer_agent.py",
        "src/agents/reviewer_agent.py",
        "src/orchestration/crew_coordinator.py",
        "src/api/routes.py",
        "src/api/websocket.py",
        "main.py",
        "requirements.txt",
        ".env.example",
        "docker-compose.mvp.yml"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️ Missing files: {len(missing_files)}")
        return False
    else:
        print(f"\n✅ All {len(required_files)} required files present")
        return True


async def run_all_tests():
    """Run all tests"""
    print("🚀 Multi-Agent Development Platform - Setup Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration", test_configuration),
        ("Agent Initialization", test_agent_initialization),
        ("Agent Health Check", test_agent_health_check),
        ("Agent Status", test_agent_status),
        ("Developer Agent", test_developer_agent_basic_functionality),
        ("Reviewer Agent", test_reviewer_agent_basic_functionality),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
                
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The Multi-Agent Development Platform is ready to use.")
        print("\nNext steps:")
        print("1. Set up your .env file with API keys")
        print("2. Start Redis and PostgreSQL (docker-compose up -d redis postgres)")
        print("3. Run the main application (python main.py)")
        return True
    else:
        print(f"\n⚠️ {failed} tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)