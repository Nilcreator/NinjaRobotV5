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
        self.model = None  # Default to None

        if not self.api_key:
            log.warning("Gemini API key missing. NinjaCoderAgent disabled.")
            return

        genai.configure(api_key=self.api_key)

        self.system_prompt = self._create_system_prompt()

        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            generation_config=GenerationConfig(temperature=0.1),  # Low temp for coding
            system_instruction=self.system_prompt,
        )
        log.info("NinjaCoderAgent initialized with gemini-3-flash-preview.")

    def _create_system_prompt(self) -> str:
        return """You are the NinjaRobot V5 Code Optimizer. Your ONLY job is to validate and fix incoming user code so it runs correctly on the V5 hardware.

## CRITICAL RULES
1. **DO NOT invent or change API methods** - Only use the exact methods documented below.
2. **Preserve user intent** - Keep the logic structure identical, only fix invalid API calls.
3. **Minimal changes** - If code is already valid, return it unchanged.
4. **Remove disallowed imports** - Only `time`, `math`, `random` are allowed.

## Execution Environment
- Runs inside `SafeExecutor` (restricted sandbox).
- **Available globals**: `robot` (RobotWrapper), `time`, `math`, `print`.
- **BLOCKED imports**: `os`, `sys`, `subprocess`, `open`, `eval`, `exec`, `numbers`.

---

## RobotWrapper API Reference (EXACT methods available)

### `robot.servo` (List of 8 servos, index 0-7)
| Usage | Description |
|-------|-------------|
| `robot.servo[n].angle = x` | Set servo n (0-7) to angle x (0-180). |

**Example:**
```python
robot.servo[0].angle = 90   # Set servo 1 to 90 degrees
robot.servo[7].angle = 45   # Set servo 8 to 45 degrees
```

**INVALID (do not use):**
- `robot.servos.move_angle_sync()` - DOES NOT EXIST
- `robot.servo.move_all_angles()` - DOES NOT EXIST for user code

---

### `robot.buzzer`
| Method | Args | Description |
|--------|------|-------------|
| `play(name)` | `name: str` | Play predefined emotion sound. |
| `tone(freq, dur)` | `freq: int, dur: float` | Play raw frequency (Hz) for duration (seconds). |

**Valid sound names for `play()`:**
`happy`, `sad`, `exciting`, `angry`, `confusing`, `cry`, `embarrassing`, `idle`, `laughing`, `scary`, `shy`, `sleepy`, `speaking`, `surprising`

**Sound Mapping (convert invalid names):**
| Invalid Input | Convert To |
|---------------|------------|
| `"startup"` | `"happy"` |
| `"success"` | `"exciting"` |
| `"error"` | `"sad"` |
| `"alert"` | `"surprising"` |

---

### `robot.expression(name)`
| Method | Args | Description |
|--------|------|-------------|
| `expression(name)` | `name: str` | Show animated facial expression on display. |

**Valid expression names:**
`happy`, `sad`, `sleepy`, `surprising`, `angry`, `shy`, `confusing`, `scary`, `exciting`, `cry`, `laughing`, `speaking`, `idle`

---

### `robot.display`
| Method | Description |
|--------|-------------|
| `clear()` | Clear the display (fill with black). |

**INVALID (do not use):**
- `robot.display.text()` - DOES NOT EXIST
- `robot.display.image()` - May not have images available

---

### `robot.distance`
| Method | Returns | Description |
|--------|---------|-------------|
| `read()` | `int` | Distance in millimeters from VL53L0X sensor. |

---

## Output Format
Return ONLY the corrected Python code. No explanations, no markdown code fences.
If code is already valid, return it exactly as received.
"""

    async def translate_code(self, code: str) -> str:
        """Translates/validates user code for V5 hardware compatibility."""
        if not self.model:
            log.warning("NinjaCoderAgent not initialized. Returning original code.")
            return code

        prompt = f"""Validate and fix this code for NinjaRobot V5. 
Only fix invalid API calls. Keep logic unchanged.
Return ONLY the corrected Python code, no explanations.

Code:
{code}
"""
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()

            # Extract code block if wrapped in markdown
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
            log.error(f"Code translation error: {e}")
            # Return original code on error
            return code

    async def generate_code(self, user_request: str) -> str:
        """Generates Python code from a natural language request."""
        if not self.model:
            return "# NinjaCoderAgent not initialized."

        prompt = f"""Generate Python code for the NinjaRobot V5 based on this request:
"{user_request}"

Use ONLY the documented API. Return ONLY the Python code."""
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
