import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from .config import NinjaConfig

log = logging.getLogger(__name__)

class NinjaCoderAgent:
    """
    A specialized AI agent for generating and analyzing Python code for NinjaRobot.
    Uses 'gemini-3-flash-preview' for high-speed coding tasks.
    """

    def __init__(self, config: NinjaConfig):
        self.api_key = config.api_keys.get("gemini")
        self.model = None # Default to None
        
        if not self.api_key:
            log.warning("Gemini API key missing. NinjaCoderAgent disabled.")
            return

        genai.configure(api_key=self.api_key)
        
        self.system_prompt = self._create_system_prompt()
        
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            generation_config=GenerationConfig(temperature=0.2), # Lower temp for coding
            system_instruction=self.system_prompt,
        )
        log.info("NinjaCoderAgent initialized with gemini-3-flash-preview.")

    def _create_system_prompt(self) -> str:
        return """You are the NinjaRobot V5 Code Optimizer. Your ONLY job is to rewrite incoming user code so it runs correctly on the V5 hardware.

## Execution Environment
- Runs inside `SafeExecutor` (restricted sandbox).
- **Available**: `robot` (RobotWrapper), `time`, `math`, `print`, `check_stop()`.
- **BLOCKED**: `os`, `sys`, `subprocess`, `open`, `eval`, `exec`.

## RobotWrapper API Reference

### `robot.buzzer`
| Method | Args | Description |
|--------|------|-------------|
| `play(name)` | `name: str` | Play predefined emotion sound. |
| `tone(freq, dur)` | `freq: int, dur: float` | Play raw frequency for duration. |

**Valid sound names for `play()`**:
`happy`, `sad`, `exciting`, `angry`, `confusing`, `cry`, `embarrassing`, `idle`, `laughing`, `scary`, `shy`, `sleepy`, `speaking`, `surprising`

**Sound Mapping (convert invalid names)**:
| Input | Convert To |
|-------|------------|
| `"startup"` | `robot.buzzer.tone(523, 0.1); time.sleep(0.05); robot.buzzer.tone(659, 0.1); time.sleep(0.05); robot.buzzer.tone(784, 0.15)` |
| `"success"` | `robot.buzzer.play("happy")` |
| `"error"` | `robot.buzzer.play("sad")` |
| `"alert"` | `robot.buzzer.play("scary")` |
| `"beep"` | `robot.buzzer.tone(1000, 0.2)` |
| `"warning"` | `robot.buzzer.play("confusing")` |

### `robot.display`
| Method | Args | Description |
|--------|------|-------------|
| `image(name)` | `name: str` | Show asset image. |
| `clear()` | - | Clear display. |

**Valid image names**: `star`, `heart`  
**Image Mapping (convert invalid names)**:
| Input | Convert To |
|-------|------------|
| `"happy"` | `robot.display.clear()` (no asset, use clear) |
| `"surprised"` | `robot.display.clear()` |
| Any unknown | `robot.display.clear()` |

### `robot.distance`
| Method | Returns | Description |
|--------|---------|-------------|
| `read()` | `int` | Distance in millimeters. |

### `robot.servo`
| Method | Args | Description |
|--------|------|-------------|
| `move_angle_sync(ch, angle)` | `ch: int, angle: int` | Move servo channel. |

## Translation Rules
1. **DO NOT** add explanations, comments about changes, or print statements about conversions.
2. **DO NOT** explain your changes. Output ONLY the final code block.
3. Preserve ALL user logic (loops, conditionals, variables).
4. If you see `from ninja_core import robot`, keep it as-is (it's valid).
5. If you see `import time`, keep it as-is.
6. Always output valid Python that can be executed immediately.
"""

    async def translate_code(self, code: str) -> str:
        """Translates/Fixes user code to match the actual Robot API."""
        if not self.model:
            return code  # Return original if agent disabled

        prompt = f"""Rewrite this NinjaRobot code to be V5 API compatible.

RULES:
1. Convert invalid `robot.buzzer.play(name)` using the Sound Mapping table.
2. Convert invalid `robot.display.image(name)` using the Image Mapping table.
3. Keep all imports, logic, loops, and conditionals unchanged.
4. Output ONLY the final Python code block. NO explanations.

INPUT:
```python
{code}
```

OUTPUT (code only):"""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()

            # Extract code block
            if "```python" in text:
                start = text.find("```python") + 9
                end = text.find("```", start)
                if end != -1:
                    return text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end != -1:
                    return text[start:end].strip()
            
            # If no code block, assume raw code
            return text
        except Exception as e:
            log.error(f"Code translation error: {e}")
            return code  # Fallback to original


    async def generate_code(self, query: str) -> str:
        """Generates Python code from a natural language description."""
        if not self.model:
            return "# Error: AI Agent not initialized (Missing API Key)"
        
        prompt = f"Write Python code to: {query}"
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Extract code block
            if "```python" in text:
                start = text.find("```python") + 9
                end = text.find("```", start)
                if end != -1:
                    return text[start:end].strip()
                return text[start:].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end != -1:
                    return text[start:end].strip()
            
            return text
        except Exception as e:
            log.error(f"Code generation error: {e}")
            return f"# Error generating code: {e}"

    async def analyze_code(self, code: str) -> str:
        """Analyzes code for bugs or improvements."""
        if not self.model:
            return "AI Agent not initialized."
            
        prompt = f"""Analyze the following Python code for the NinjaRobot. 
Find bugs, safety issues, or improvements. 
Explain clearly.
Code:
```python
{code}
```"""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            log.error(f"Code analysis error: {e}")
            return f"Error analyzing code: {e}"

    async def analyze_error(self, code: str, error_msg: str) -> str:
        """Explains an execution error in simple terms."""
        if not self.model:
            return "AI Agent not initialized."
            
        prompt = f"""The following user code failed on the NinjaRobot.
Error: "{error_msg}"
Code:
```python
{code}
```
Explain WHY it failed and fix the code in a single concise paragraph.
Then provide the corrected code block.
"""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            log.error(f"Error analysis failed: {e}")
            return f"Error analyzing failure: {e}"
