#!/usr/bin/env python3
"""Quick test to verify context managers are importable and properly structured."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


async def test_imports():
    """Test that all context managers can be imported."""
    try:
        from amplifier.ccsdk_toolkit.context_managers import FileProcessor
        from amplifier.ccsdk_toolkit.context_managers import RetryContext
        from amplifier.ccsdk_toolkit.context_managers import RetryStrategy
        from amplifier.ccsdk_toolkit.context_managers import SessionContext
        from amplifier.ccsdk_toolkit.context_managers import StreamingQuery
        from amplifier.ccsdk_toolkit.context_managers import TimedExecution

        print("✓ All context managers imported successfully")

        # Verify they are classes
        assert isinstance(FileProcessor, type)
        assert isinstance(StreamingQuery, type)
        assert isinstance(SessionContext, type)
        assert isinstance(TimedExecution, type)
        assert isinstance(RetryContext, type)
        print("✓ All context managers are proper classes")

        # Verify RetryStrategy enum
        assert hasattr(RetryStrategy, "LINEAR")
        assert hasattr(RetryStrategy, "EXPONENTIAL")
        print("✓ RetryStrategy enum is properly defined")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"✗ Assertion error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def test_context_manager_protocols():
    """Test that context managers have proper async context manager protocol."""
    from amplifier.ccsdk_toolkit.context_managers import FileProcessor
    from amplifier.ccsdk_toolkit.context_managers import RetryContext
    from amplifier.ccsdk_toolkit.context_managers import SessionContext
    from amplifier.ccsdk_toolkit.context_managers import StreamingQuery
    from amplifier.ccsdk_toolkit.context_managers import TimedExecution

    # Check they have __aenter__ and __aexit__ methods
    for cm_class in [FileProcessor, StreamingQuery, SessionContext, TimedExecution, RetryContext]:
        assert hasattr(cm_class, "__aenter__"), f"{cm_class.__name__} missing __aenter__"
        assert hasattr(cm_class, "__aexit__"), f"{cm_class.__name__} missing __aexit__"
        print(f"✓ {cm_class.__name__} has async context manager protocol")

    return True


async def main():
    """Run all tests."""
    print("Testing Context Managers Module\n" + "=" * 40)

    tests = [
        ("Import Test", test_imports),
        ("Context Manager Protocol Test", test_context_manager_protocols),
    ]

    all_passed = True
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = await test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            all_passed = False

    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
