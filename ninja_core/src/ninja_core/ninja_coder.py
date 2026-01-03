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
        if not self.api_key:
            log.warning("Gemini API key missing. NinjaCoderAgent disabled.")
            self.model = None
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
    - `robot`: The HardwareAbstractionLayer instance.
    - `time`: Standard time module.
    - `math`: Standard math module.
    - `print`: Redirected to the user's log.
- **Unavailable**: `os`, `sys`, `subprocess` are BLOCKED. Do NOT import them.

## The Robot API (`robot` object)
The `robot` object has the following attributes (drivers):
1.  `robot.servos`:
    - `move_angle_sync(chan, angle)`: Move single servo.
    - `move_sequence(sequence_dict)`: Complex sequences.
2.  `robot.buzzer`:
    - `play_sound(name)`: Play buffer sound ("startup", "jump").
    - `play_tone(freq, duration)`: Play raw tone.
3.  `robot.display`:
    - `show_image(path)`: (Use carefully, paths are restricted).
    - `clear()`: Clear screen.

## Instructions
1.  **Generate Code**: When asked to write code, output ONLY valid Python code inside a markdown code block (```python ... ```).
2.  **No Explanations**: Unless explicitly asked, just provide the code.
3.  **Safety**: Never attempt to access the file system or run shell commands.
4.  **Loops**: If you write an infinite loop (`while True`), YOU MUST call `check_stop()` inside the loop to allow the user to stop execution.
    Example:
    ```python
    while True:
        robot.servos.move_angle_sync(0, 90)
        time.sleep(1)
        check_stop() # CRITICAL!
    ```
"""

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
