import unittest
import time
import threading
from unittest.mock import MagicMock
import sys
import os
import math

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

    def test_ninja_core_import(self):
        # Verification for standard generated code
        code = "from ninja_core import robot\nrobot.test_method()"
        self.executor.execute(code)
        
        start = time.time()
        while self.executor.is_running() and time.time() - start < 2:
            time.sleep(0.1)
            
        self.mock_hal.test_method.assert_called()
        self.assertEqual(self.executor.get_result()["status"], "success")

    def test_allowed_imports(self):
        code = "import time\nimport math\nprint(math.pi)"
        result = self.executor.execute(code)
        
        # Wait for thread
        time.sleep(0.1)
        
        self.assertEqual(result["status"], "started")
        
        # Check logs
        logs = self.executor.get_log()
        self.assertIn(str(math.pi), logs) # Should have printed PI
        self.assertEqual(self.executor.get_result()["status"], "success")

    def test_blocked_imports(self):
        code = "import os"
        result = self.executor.execute(code)
        
        time.sleep(0.1)
        
        self.assertEqual(self.executor.get_result()["status"], "error")
        self.assertIn("Import of module 'os' is not allowed", self.executor.get_result()["message"])

    def test_on_complete_callback(self):
        callback_event = threading.Event()
        callback_result = {}

        def on_complete(res):
            callback_result.update(res)
            callback_event.set()

        self.executor.execute("print('Callback test')", on_complete=on_complete)
        
        # Wait for callback
        success = callback_event.wait(timeout=1.0)
        self.assertTrue(success, "Callback was not triggered")
        self.assertEqual(callback_result["status"], "success")
        
    def test_stop_execution(self):
        # Long running code with check_stop
        code = """
import time
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
