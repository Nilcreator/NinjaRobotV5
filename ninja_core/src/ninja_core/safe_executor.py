import logging
import threading
import time
import math
import traceback
from typing import Dict, Any, Optional, Callable

log = logging.getLogger(__name__)

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
        
    def _safe_print(self, *args, sep=' ', end='\n'):
        msg = sep.join(map(str, args)) + end
        self._execution_log.append(msg)
        log.info(f"[USER CODE]: {msg.strip()}")
        if self.on_print:
            try:
                self.on_print(msg)
            except Exception as e:
                log.error(f"Error in on_print callback: {e}")

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
        }

        return {
            '__builtins__': safe_builtins,
            'robot': self.hal,
            'time': time,
            'math': math,
            'print': self._safe_print,
            'check_stop': self.check_stop 
        }

    def check_stop(self):
        if self._stop_flag:
            raise KeyboardInterrupt()

    def execute(self, code: str) -> Dict[str, Any]:
        """Starts execution in a thread."""
        with self._lock:
            if self._current_thread and self._current_thread.is_alive():
                return {"status": "error", "message": "Code already running"}
            
            self._stop_flag = False
            self._execution_log = []
            self._last_result = {"status": "pending"}
            
            def target():
                try:
                    compiled_code = compile(code, "<user_code>", "exec")
                    exec(compiled_code, self._create_globals())
                    self._last_result["status"] = "success"
                except Exception as e:
                    self._last_result["status"] = "error"
                    self._last_result["message"] = str(e)
                    self._last_result["traceback"] = traceback.format_exc()
                except KeyboardInterrupt:
                    self._last_result["status"] = "stopped"
                    self._last_result["message"] = "Execution stopped by user"
                except SystemExit:
                     self._last_result["status"] = "stopped"

            self._current_thread = threading.Thread(target=target, daemon=True)
            self._current_thread.start()
            
            return {"status": "started", "message": "Code execution started"}

    def stop(self):
        self._stop_flag = True
        log.info("Stop signal sent to SafeExecutor")

    def get_log(self) -> str:
        return "".join(self._execution_log)
        
    def get_result(self) -> Optional[Dict[str, Any]]:
        return self._last_result
    
    def is_running(self) -> bool:
        return self._current_thread is not None and self._current_thread.is_alive()
