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
        return """You are an expert Python developer for the NinjaRobot V5 platform.
Your goal is to write clean, efficient, and safe Python code based on user requests.

## The Environment
- You are running inside a restricted `SafeExecutor` environment.
- **Available Globals**:
    - `robot`: The `RobotWrapper` instance (High-Level API).
    - `time`, `math`: Standard modules.
    - `print`: Redirected to user log.
- **Unavailable**: `os`, `sys`, `subprocess` are BLOCKED.

## The Robot API (`robot` object)
The `robot` object supports a High-Level API:

1.  **`robot.servos`** (MultiServo):
    - `move_angle_sync(chan, angle)`: Move single servo.
    - `move_sequence(sequence_dict)`: Complex sequences.
    
2.  **`robot.buzzer`** (BuzzerWrapper):
    - `play(name)`: Play emotion sound.
      - **Valid Sounds**: 'happy', 'sad', 'exciting', 'angry', 'confusing', 'cry', 'embarrassing', 'idle', 'laughing', 'scary', 'shy', 'sleepy', 'speaking', 'surprising'.
      - *Note*: If a requested sound is NOT in this list, you MUST generate raw tones using `tone()` or map it to a similar sound.
    - `tone(frequency, duration)`: Play frequency (Hz) for duration (s).

3.  **`robot.display`** (DisplayWrapper):
    - `image(name)`: Display asset image (e.g., 'star', 'heart').
      - *Note*: If image likely doesn't exist, ignore or use `clear()`.
    - `clear()`: Clear screen.

4.  **`robot.distance`** (DistanceWrapper):
    - `read()`: Returns distance in **millimeters** (int).

## Instructions
1.  **Translate/Fix**: When processing code, checking for API validity (especially valid sound names). if a sound name like "startup" is missing, replace it with a sequence of `tone()` calls or a similar sound.
2.  **Generate Code**: Output ONLY valid Python code inside a markdown code block.
3.  **Safety**: No infinite loops without `check_stop()`.
"""

    async def translate_code(self, code: str) -> str:
        """Translates/Fixes user code to match the actual Robot API."""
        if not self.model:
            return code # Return original if agent disabled
            
        prompt = f"""Translate and Fix the following NinjaRobot Python code to ensure it works with the V5 API.
        
        Specific Checks:
        1. Check `robot.buzzer.play(name)` calls. Only use VALID sounds (happy, sad, etc.).
           - If user asks for "startup", REPLACE it with: `robot.buzzer.tone(440, 0.1); time.sleep(0.1); robot.buzzer.tone(880, 0.2)` (or similar).
        2. Check `robot.display.image(name)`. Ensure strict asset names.
        
        Input Code:
        ```python
        {code}
        ```
        
        Output ONLY the fixed executable Python code block.
        """
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
            return text
        except Exception as e:
            log.error(f"Code translation error: {e}")
            return code # Fallback to original


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
