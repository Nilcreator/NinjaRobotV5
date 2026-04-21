import logging
import math
import threading
import time
import traceback
import types
from typing import Dict, Any, Optional, Callable

from .api_wrappers import RobotWrapper

log = logging.getLogger(__name__)


class SafeTimeProxy:
    """Expose the standard time module with a cooperative sleep override."""

    def __init__(self, sleep_impl: Callable[[float], None]):
        self.sleep = sleep_impl

    def __getattr__(self, name):
        return getattr(time, name)

class SafeExecutor:
    """
    A safe execution environment for user-provided Python code.
    """
    
    def __init__(self, hal: Any, on_print: Optional[Callable[[str], None]] = None):
        self.hal = hal
        self.on_print = on_print
        self._lock = threading.Lock()
        self._current_thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._execution_log = []
        self._last_result = None
        self._safe_time = SafeTimeProxy(self.sleep)
        self.robot_wrapper = RobotWrapper(
            hal,
            cooperative_sleep=self.sleep,
        )
        
    def _safe_print(self, *args, sep=' ', end='\n'):
        msg = sep.join(map(str, args)) + end
        self._execution_log.append(msg)
        log.info(f"[USER CODE]: {msg.strip()}")
        if self.on_print:
            try:
                self.on_print(msg)
            except Exception as e:
                log.error(f"Error in on_print callback: {e}")

    def _safe_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        allowed_modules = ["time", "math", "random", "ninja_core"]
        
        # Determine base module name
        base_name = name.split(".")[0]
        
        if base_name == "time":
            return self._safe_time

        if base_name == "ninja_core":
            # Mock ninja_core module to allow 'from ninja_core import robot'
            mock_module = types.ModuleType("ninja_core")
            mock_module.robot = self.robot_wrapper
            return mock_module

        if base_name in allowed_modules:
            return __import__(name, globals, locals, fromlist, level)
        
        raise ImportError(f"Import of module '{name}' is not allowed in SafeExecutor.")

    def _create_globals(self) -> Dict[str, Any]:
        safe_builtins = {
            'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
            'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
            'filter': filter, 'float': float, 'format': format, 'frozenset': frozenset,
            'hex': hex, 'int': int, 'isinstance': isinstance, 'len': len,
            'list': list, 'map': map, 'max': max, 'min': min, 'oct': oct,
            'ord': ord, 'pow': pow, 'range': range, 'repr': repr, 'reversed': reversed,
            'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
            'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
            'True': True, 'False': False, 'None': None,
            'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
            '__import__': self._safe_import
        }

        return {
            '__builtins__': safe_builtins,
            'robot': self.robot_wrapper,
            'time': self._safe_time,
            'math': math,
            'print': self._safe_print,
            'check_stop': self.check_stop,
            'sleep': self.sleep,
        }

    def check_stop(self):
        if self._stop_flag:
            raise KeyboardInterrupt()

    def sleep(self, duration: float, interval: float = 0.05):
        end_time = time.monotonic() + max(0.0, float(duration))
        while True:
            self.check_stop()
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(interval, remaining))

    def _build_syntax_error_result(self, code: str, exc: SyntaxError) -> Dict[str, Any]:
        line = exc.lineno or 0
        message = f"Syntax error on line {line}: {exc.msg}" if line else f"Syntax error: {exc.msg}"
        return {
            "status": "error",
            "error_code": "syntax_error",
            "message": message,
            "syntax_error": {
                "line": exc.lineno,
                "offset": exc.offset,
                "text": exc.text.strip() if exc.text else None,
                "message": exc.msg,
            },
            "traceback": "",
            "code": code,
        }

    def execute(self, code: str, on_complete: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Starts execution in a thread. returns status immediately."""
        with self._lock:
            if self._current_thread and self._current_thread.is_alive():
                return {"status": "error", "message": "Code already running"}

            try:
                compiled_code = compile(code, "<user_code>", "exec")
            except SyntaxError as exc:
                result = self._build_syntax_error_result(code, exc)
                self._last_result = result
                log.info("[USER CODE]: %s", result["message"])
                return result
            
            self._stop_flag = False
            self._execution_log = []
            self._last_result = {"status": "pending"}
            
            def target():
                result = {"code": code} # Copy code for analysis reference
                try:
                    exec(compiled_code, self._create_globals())
                    self._last_result["status"] = "success"
                    result.update(self._last_result)
                except Exception as e:
                    self._last_result["status"] = "error"
                    self._last_result["message"] = str(e)
                    self._last_result["traceback"] = traceback.format_exc()
                    result.update(self._last_result)
                    
                    # Log error visibly
                    msg = f"Runtime Error: {e}"
                    self._safe_print(msg) 
                    
                except KeyboardInterrupt:
                    self._last_result["status"] = "stopped"
                    self._last_result["message"] = "Execution stopped by user"
                    result.update(self._last_result)
                except SystemExit:
                     self._last_result["status"] = "stopped"
                     result.update(self._last_result)
                finally:
                    if result.get("status") in {"error", "stopped"}:
                        try:
                            self.robot_wrapper.request_stop()
                        except Exception as exc:
                            log.warning("Runtime cleanup failed after %s: %s", result.get("status"), exc)

                    with self._lock:
                        self._current_thread = None
                        self._stop_flag = False

                    if on_complete:
                        try:
                            on_complete(result)
                        except Exception as ex:
                            log.error(f"Error in on_complete callback: {ex}")

            self._current_thread = threading.Thread(target=target, daemon=True)
            self._current_thread.start()
            
            return {"status": "started", "message": "Code execution started"}

    def stop(self):
        self._stop_flag = True
        try:
            self.robot_wrapper.request_stop()
        except Exception as exc:
            log.warning("Robot stop hook failed: %s", exc)
        log.info("Stop signal sent to SafeExecutor")

    def get_log(self) -> str:
        return "".join(self._execution_log)
        
    def get_result(self) -> Optional[Dict[str, Any]]:
        return self._last_result
    
    def is_running(self) -> bool:
        return self._current_thread is not None and self._current_thread.is_alive()
