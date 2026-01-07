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
| `robot.servo[n].angle = x` | Set servo n to angle x (0-180) |
| `robot.servos.move_all(angles)` | Move all 8 servos at once: `robot.servos.move_all([90, 0, ...])` |
| `robot.servos.center()` | Reset all servos to 90° |

### `robot.buzzer`
| Usage | Description |
|-------|-------------|
| `robot.buzzer.play(name)` | Play emotion (happy, sad, etc) |
| `robot.buzzer.tone(f, d)` | Play frequency f for d seconds |

### `robot.display` / `robot.distance`
- `robot.display.clear()`
- `robot.expression(name)` (Show face)
- `robot.distance.read()` (Returns mm)

## OPTIMIZATION & PIPELINING RULES (High Priority)
1. **Batch Movements**: If you see sequential servo commands like:
   ```python
   robot.servo[0].angle = 90
   robot.servo[1].angle = 0
   ...
   ```
   **REWRAP** them into a single call:
   ```python
   robot.servos.move_all([90, 0, ...])
   ```
   This makes movement smoother.

2. **Sequential Timing**: If discrete movements are required logic logic implies one after another (e.g. wave), you MUST inject `time.sleep(0.5)` (or appropriate duration) after each non-blocking command.

3. **Fix Loops**: Ensure `range()` arguments are integers (e.g., `range(int(x))`).

4. **Context**: If the code is just a standalone expression or variable assignment, ensure it does something visible (e.g., add a print or a sound).

**Example:**
```python
robot.servo[0].angle = 90   # Set servo 1 to 90 degrees
robot.servo[7].angle = 45   # Set servo 8 to 45 degrees
```
**Optimized:**
```python
robot.servos.move_all([90, -1, -1, -1, -1, -1, -1, 45]) # Use -1 to keep others same
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

## OUTPUT FORMAT (STRICT)
You must return a **single JSON object** (no markdown formatting outside the JSON).
Structure:
{
  "explanation": "A concise, natural language summary of what the code does (e.g., 'Moving servo 5 to 45 degrees and playing a tone'). Do not mention 'optimization' technically, just describe the action.",
  "code": "The full, valid, optimized Python code string. Use \\n for newlines."
}
"""

    async def translate_code(self, code: str) -> dict:
        """
        Translates/Optimizes user code into V5-compatible Python code with explanation.
        
        Returns:
            dict: {"explanation": str, "code": str}
        """
        if not self.model:
            return {"explanation": "AI Agent disabled.", "code": code}

        prompt = f"""Validate and optimize this code for NinjaRobot V5.
User Code:
```python
{code}
```
Remember the JSON output format.
"""
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean up potential markdown code blocks around the JSON
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()
                else:
                    text = text[start:].strip()
            elif "```" in text:
                 # Generic code block
                start = text.find("```") + 3
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()

            # Parse JSON
            import json
            try:
                data = json.loads(text)
                # Fallback if keys missing
                if "code" not in data:
                    data["code"] = code
                if "explanation" not in data:
                    data["explanation"] = "Code optimized for execution."
                return data
            except json.JSONDecodeError:
                log.warning(f"Failed to parse JSON from agent: {text[:100]}...")
                # Attempt to salvage if it looks like just code
                return {"explanation": "Optimized code (Auto-recovered)", "code": text}

        except Exception as e:
            log.error(f"Code generation error: {e}")
            return {"explanation": f"Optimization failed: {e}", "code": code}

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
