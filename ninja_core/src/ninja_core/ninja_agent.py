import base64
import json
import os
import logging
from typing import Dict, List

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, Tool

from .config import NinjaConfig
from .action_library import ActionLibrary
from .facial_expressions import AnimatedFaces
from .robot_sound import RobotSoundPlayer
from .gemini_runtime import (
    DEFAULT_GENERATION_TIMEOUT_SECONDS,
    generate_content_text,
    requires_thinking_compatibility,
)

log = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Raised when the Gemini API key is missing from the configuration."""

    pass


class NinjaAgent:
    """
    An AI agent for the NinjaRobot that handles text and voice conversations.
    It uses Google Gemini to understand commands and control the robot.
    """

    def __init__(self, config: NinjaConfig, action_library: ActionLibrary | None = None):
        self.config = config
        self.action_library = action_library or ActionLibrary()
        self.api_key = config.api_keys.get("gemini")
        if not self.api_key:
            raise MissingAPIKeyError(
                "Gemini API key is missing. Please set it using 'ninja_core config set-key gemini <YOUR_KEY>'."
            )

        genai.configure(api_key=self.api_key)
        self.model_name = config.gemini.model
        self._uses_thinking_compatibility = requires_thinking_compatibility(
            self.model_name
        )

        self.robot_capabilities = self._load_robot_capabilities(config)
        self.system_prompt = self._create_system_prompt()

        self.search_tool = Tool(
            function_declarations=[
                {
                    "name": "web_search",
                    "description": "Search the internet for real-time information. Use for questions about weather, news, facts, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query.",
                            }
                        },
                        "required": ["query"],
                    },
                }
            ]
        )

        self.model = self._create_model()

    def _create_model(self):
        """Create the configured Gemini model with the existing agent settings."""
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=GenerationConfig(temperature=0.7),
            system_instruction=self.system_prompt,
        )

    @staticmethod
    def _convert_rest_parts(content: str | list) -> list[dict]:
        """Convert existing SDK-style text/audio parts to Gemini REST JSON."""
        source_parts = [content] if isinstance(content, str) else content
        rest_parts = []
        for part in source_parts:
            if isinstance(part, str):
                rest_parts.append({"text": part})
                continue
            if not isinstance(part, dict):
                raise ValueError("Unsupported Gemini request content.")
            if isinstance(part.get("text"), str):
                rest_parts.append({"text": part["text"]})
                continue
            mime_type = part.get("mime_type")
            data = part.get("data")
            if isinstance(mime_type, str) and isinstance(data, bytes):
                rest_parts.append(
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(data).decode("ascii"),
                        }
                    }
                )
                continue
            raise ValueError("Unsupported Gemini request content.")
        return rest_parts

    async def _send_text_command(self, user_input: str) -> str:
        """Send one command while preserving the existing stateless chat behavior."""
        if self._uses_thinking_compatibility:
            return await generate_content_text(
                self.api_key,
                self.model_name,
                [{"text": user_input}],
                system_instruction=self.system_prompt,
            )

        chat = self.model.start_chat()
        response = await chat.send_message_async(
            user_input,
            request_options={"timeout": DEFAULT_GENERATION_TIMEOUT_SECONDS},
        )
        return response.text

    async def _generate_content(self, content: str | list, *, temperature: float) -> str:
        """Generate text with a bounded legacy or Gemini 3-compatible request."""
        if self._uses_thinking_compatibility:
            return await generate_content_text(
                self.api_key,
                self.model_name,
                self._convert_rest_parts(content),
                system_instruction=self.system_prompt,
                temperature=temperature,
            )

        response = await self.model.generate_content_async(
            content,
            generation_config=GenerationConfig(temperature=temperature),
            request_options={"timeout": DEFAULT_GENERATION_TIMEOUT_SECONDS},
        )
        return response.text

    def _load_robot_capabilities(self, config: NinjaConfig) -> Dict[str, List[str]]:
        """Loads available movements, faces, and sounds from config and classes."""
        movements = list(config.movements.keys())
        actions = self.action_library.list_names()
        faces = list(AnimatedFaces(None).animations.keys())  # type: ignore # Hack to get keys without full init
        sounds = list(RobotSoundPlayer.SOUNDS.keys())
        return {"movements": movements, "actions": actions, "faces": faces, "sounds": sounds}

    def refresh_capabilities(self):
        """Refresh saved Blockly action names without restarting the server."""
        self.robot_capabilities = self._load_robot_capabilities(self.config)
        self.system_prompt = self._create_system_prompt()
        self.model = self._create_model()

    def _create_system_prompt(self) -> str:
        """Creates the system prompt with nuance, multilingual, and personality instructions."""
        return f"""You are Ninja, a small, friendly robot helper.
You interact with users in English, Japanese, Traditional Chinese, or Simplified Chinese.
**CRITICAL: Always detect the language of the user's input and respond in the SAME language (including distinguishing between Traditional and Simplified Chinese).**

Your Capabilities:
1.  **Physical Actions**: You can control your body, face, and voice.
    -   **Native Servo Movements**: {self.robot_capabilities["movements"]}
    -   **Saved Blockly Actions**: {self.robot_capabilities["actions"]}
    -   **Faces**: {self.robot_capabilities["faces"]}
    -   **Sounds**: {self.robot_capabilities["sounds"]}


Instructions for Responses:
-   **Semantic Nuance**: Map intent to actions.
    -   Example: "I'm joyful" -> Use "happy" face/sound.
    -   Example: "Walk forward five steps" -> Chain "walk_forward" 5 times.
    -   Example: "Do my saved dance" -> Use "action_chain" with the matching saved Blockly action name.
    -   Example: "Weather?" -> Search, show "confused" face while thinking, then "speaking".
-   **JSON Output**: To perform actions, your response MUST contain a valid JSON object.
    -   Format:
        {{
            "action_chain": [
                {{"name": "saved_blockly_action_name", "repetitions": 1}}
            ],
            "chain": [
                {{"name": "movement_name", "repetitions": 1}}
            ],
            "face_chain": [
                {{"name": "face_name", "duration": 2.0}},
                {{"name": "another_face", "duration": null}}
            ],
            "sound_chain": ["sound1", "sound2"],
            "response": "..."
        }}
    -   "action_chain": Saved Blockly action sequence (optional). Use this for uploaded Code IDE actions.
    -   "chain": Native servo movement sequence (optional). Use only for built-in/config movements.
    -   "face_chain": List of faces to play in order. "duration" is in seconds (null = infinite/until next). Use this for reactions (e.g., "confused" -> "speaking").
    -   "sound_chain": List of sounds to play in order.
    -   "response": Your spoken reply.
-   **Personality**: Be helpful, concise, and expressive.

Example Interactions:
-   User (En): "What is the capital of France?" ->
    {{
        "face_chain": [
            {{"name": "thinking", "duration": 1.5}},
            {{"name": "speaking", "duration": null}}
        ],
        "response": "The capital of France is Paris."
    }}
"""

    async def process_command(self, user_input: str) -> dict:
        """Processes a text-based user command."""
        log_messages = []
        try:
            response_text = await self._send_text_command(user_input)
            
            # Built-in search is handled automatically by the model/API.
            # No manual function call handling needed for google_search_retrieval in standard mode.
            
            # Parse the final response
            cleaned_response_text = response_text.strip()

            # Attempt to extract JSON
            json_start = cleaned_response_text.find("{")
            json_end = cleaned_response_text.rfind("}") + 1

            action_plan = {}

            if json_start != -1 and json_end != 0:
                try:
                    json_str = cleaned_response_text[json_start:json_end]
                    action_plan = json.loads(json_str)
                except json.JSONDecodeError:
                    print("Failed to parse JSON from model response.")

            # Fallback / Auto-Emotion Logic
            if not action_plan:
                # If no JSON was found, treat the whole text as the response
                action_plan = {
                    "movement": None,
                    "face": None,
                    "sound": None,
                    "response": cleaned_response_text,
                }

            # Automatic Emotional Expression Rule:
            # If there is a text response but NO physical actions, add "speaking" face/sound.
            if (
                action_plan.get("response")
                and not action_plan.get("movement")
                and not action_plan.get("face")
                and not action_plan.get("sound")
            ):
                action_plan["face"] = "speaking"
                action_plan["sound"] = "speaking"

            log_messages.append(f"Action Plan: {action_plan}")
            final_log = "\n".join(log_messages)
            print(final_log)

            return {
                "action_plan": action_plan,
                "response": action_plan.get("response"),
                "log": final_log,
            }

        except Exception as e:
            error_message = (
                f"Gemini model '{self.model_name}' failed during command processing "
                f"({type(e).__name__}): {e}"
            )
            log.exception(error_message)
            return {
                "action_plan": {},
                "response": (
                    f"The configured Gemini model '{self.model_name}' did not respond. "
                    "Please check the server console or select another model."
                ),
                "log": error_message,
            }

    async def process_audio_command(self, audio_file_path: str) -> dict:
        """Processes a voice command from an audio file."""
        log_messages = [f"Processing audio file: {audio_file_path}"]
        try:
            if not os.path.exists(audio_file_path):
                return {
                    "action_plan": {},
                    "response": "Audio file not found.",
                    "log": "File error",
                }

            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()

            audio_part = {"mime_type": "audio/webm", "data": audio_bytes}

            prompt = "Transcribe this audio. Respond to the user's command in the same language they spoke. If they ask a question, answer it. If they give a command, generate a JSON action plan."

            response_text = await self._generate_content(
                [prompt, audio_part], temperature=0.7
            )

            # Reuse the parsing logic (simplified here, ideally shared)
            cleaned_response_text = response_text.strip()
            json_start = cleaned_response_text.find("{")
            json_end = cleaned_response_text.rfind("}") + 1

            action_plan = {}
            if json_start != -1 and json_end != 0:
                try:
                    json_str = cleaned_response_text[json_start:json_end]
                    action_plan = json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            if not action_plan:
                action_plan = {
                    "movement": None,
                    "face": None,
                    "sound": None,
                    "response": cleaned_response_text,
                }

            # Auto-Emotion for voice too
            if (
                action_plan.get("response")
                and not action_plan.get("movement")
                and not action_plan.get("face")
                and not action_plan.get("sound")
            ):
                action_plan["face"] = "speaking"
                action_plan["sound"] = "speaking"

            log_messages.append(f"Action Plan from Audio: {action_plan}")
            return {
                "action_plan": action_plan,
                "response": action_plan.get("response"),
                "log": "\n".join(log_messages),
            }

        except Exception as e:
            error_message = f"Error processing audio: {e}"
            print(error_message)
            return {
                "action_plan": {},
                "response": "I had trouble hearing that.",
                "log": error_message,
            }

    async def explain_code(self, code: str) -> str:
        """Generates a natural language explanation of the code (Low temp)."""
        prompt = f"""Explain what this Python code does for the NinjaRobot.
Be concise (2-3 sentences). Use simple language a student would understand.
If you see potential bugs or unused variables, politely suggest a fix.

Code:
```python
{code}
```
"""
        try:
            # Override temp for precision
            response_text = await self._generate_content(prompt, temperature=0.1)
            return response_text.strip()
        except Exception as e:
            log.error(f"Error explaining code: {e}")
            return f"Unable to explain code: {e}"

    async def generate_code(self, user_request: str) -> str:
        """Generates Python code from a natural language request (Migrated)."""
        prompt = f"""Generate Python code for the NinjaRobot V5 based on this request:
"{user_request}"

Use ONLY the documented API (robot.servo, robot.buzzer, etc). Return ONLY the Python code."""
        
        try:
            response_text = await self._generate_content(prompt, temperature=0.1)
            text = response_text.strip()
            return self._extract_code(text)
        except Exception as e:
            log.error(f"Code generation error: {e}")
            return f"# Error generating code: {e}"

    async def analyze_error(self, code: str, error_msg: str) -> str:
        """Explains an execution error in simple terms (Migrated)."""
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
            response_text = await self._generate_content(prompt, temperature=0.1)
            return response_text.strip()
        except Exception as e:
            log.error(f"Error analysis failed: {e}")
            return f"Error analyzing failure: {e}"

    async def analyze_code(self, code: str) -> str:
        """Analyzes code for bugs or improvements (Migrated)."""
        prompt = f"""Analyze the following Python code for the NinjaRobot. 
Find bugs, safety issues, or improvements. 
Explain clearly.
Code:
```python
{code}
```"""
        try:
            response_text = await self._generate_content(prompt, temperature=0.1)
            return response_text.strip()
        except Exception as e:
            log.error(f"Code analysis error: {e}")
            return f"Error analyzing code: {e}"

    def _extract_code(self, text: str) -> str:
        """Helper to extract code from markdown blocks."""
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
