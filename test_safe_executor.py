import unittest
import time
import threading
from unittest.mock import MagicMock
import sys
import os

# Ensure we can import ninja_core
sys.path.append("ninja_core/src")

from ninja_core.safe_executor import SafeExecutor

class TestSafeExecutor(unittest.TestCase):
    def setUp(self):
        self.mock_hal = MagicMock()
        self.executor = SafeExecutor(self.mock_hal)

    def test_valid_code_execution(self):
        code = "print('Hello World')\nx = 1 + 1"
        res = self.executor.execute(code)
        self.assertEqual(res["status"], "started")
        
        # Wait for completion
        start = time.time()
        while self.executor.is_running() and time.time() - start < 2:
            time.sleep(0.1)
            
        self.assertFalse(self.executor.is_running())
        self.assertEqual(self.executor.get_result()["status"], "success")
        self.assertIn("Hello World", self.executor.get_log())

    def test_robot_interaction(self):
        code = "robot.test_method()"
        self.executor.execute(code)
        
        start = time.time()
        while self.executor.is_running() and time.time() - start < 2:
            time.sleep(0.1)
            
        self.mock_hal.test_method.assert_called_once()

    def test_blocked_imports(self):
        code = "import os\nos.system('ls')"
        self.executor.execute(code)
        
        start = time.time()
        while self.executor.is_running() and time.time() - start < 2:
            time.sleep(0.1)
            
        res = self.executor.get_result()
        self.assertEqual(res["status"], "error")
        # Should raise ImportError or NameError depending on how exec handles it
        # Since __builtins__ does not include __import__? 
        # Wait, minimal __builtins__ used in SafeExecutor does NOT include __import__!
        # So 'import' statement should fail.
        self.assertIn("ImportError", res["traceback"])

    def test_stop_execution(self):
        # Code that loops
        code = """
while True:
    time.sleep(0.1)
    check_stop()
"""
        self.executor.execute(code)
        time.sleep(0.2)
        self.assertTrue(self.executor.is_running())
        
        self.executor.stop()
        
        start = time.time()
        while self.executor.is_running() and time.time() - start < 2:
            time.sleep(0.1)
            
        self.assertFalse(self.executor.is_running())
        res = self.executor.get_result()
        self.assertEqual(res["status"], "stopped")

if __name__ == '__main__':
    unittest.main()
