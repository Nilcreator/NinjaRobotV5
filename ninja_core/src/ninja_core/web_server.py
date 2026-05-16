import asyncio
import os
import signal
import sys
import socket
import subprocess
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import qrcode
import uvicorn
import shutil
import tempfile
from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from pyngrok import ngrok

from .config import build_robot_profile, load_config, set_api_key
from .ngrok_config import has_ngrok_auth_token, set_ngrok_auth_token
from .action_library import ActionLibrary
from .hal import HardwareAbstractionLayer
from .ninja_agent import NinjaAgent, MissingAPIKeyError
from .facial_expressions import AnimatedFaces
from .robot_sound import RobotSoundPlayer
from .movement_controller import MovementController, EmergencyStop
from .perception import DistanceMonitor
from .runtime_pipeline import RuntimePipeline


# --- Configuration ---
base_dir = Path(__file__).parent

# Module-level reference for signal handler cleanup
_app_state: Optional["AppState"] = None

# React SPA dist path (built from ninja_webapp)
WEBAPP_DIST = base_dir.parents[2] / "ninja_webapp" / "dist"

# --- Pydantic Models ---
class SetApiKeyRequest(BaseModel):
    api_key: str

class AgentChatRequest(BaseModel):
    message: str

class CodeExecuteRequest(BaseModel):
    code: str

class CodeAnalyzeRequest(BaseModel):
    code: str

# --- Global State Wrapper ---
class AppState:
    def __init__(self):
        self.hal: Optional[HardwareAbstractionLayer] = None
        self.agent: Optional[NinjaAgent] = None
        self.faces: Optional[AnimatedFaces] = None
        self.sound: Optional[RobotSoundPlayer] = None
        self.movement: Optional[MovementController] = None
        self.action_library: Optional[ActionLibrary] = None
        self.distance_monitor: Optional[DistanceMonitor] = None
        self.runtime_pipeline: Optional[RuntimePipeline] = None
        self.first_interaction: bool = True
        self.has_greeted: bool = False
        self.last_reaction_time: float = 0.0
        self.connection_manager = ConnectionManager()
        self.tasks = set() # Track background tasks
        self.shutdown_event = asyncio.Event()  # Signal for graceful shutdown
        self.action_plan_lock: Optional[asyncio.Lock] = None

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Handle disconnected clients gracefully if not caught elsewhere
                pass

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app_state
    
    # --- Startup ---
    print("Initializing NinjaRobot V4 Web Server...")

    # Configure logging to ensure INFO logs (including BLE data) are visible
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Load Config & HAL
    config = load_config()
    app.state.ninja = AppState()
    app.state.ninja.hal = HardwareAbstractionLayer(config)
    app.state.ninja.hal.initialize()
    app.state.ninja.runtime_pipeline = RuntimePipeline(app.state.ninja.hal)
    app.state.ninja.action_library = ActionLibrary()
    app.state.ninja.action_plan_lock = asyncio.Lock()

    # Initialize Dispatcher
    from .dispatcher import CommandDispatcher
    dispatcher = CommandDispatcher(
        app.state.ninja.hal,
        runtime_pipeline=app.state.ninja.runtime_pipeline,
    )
    app.state.ninja.dispatcher = dispatcher
    dispatcher.attach_action_library(
        app.state.ninja.action_library,
        native_movement_names=config.movements.keys(),
    )
    
    # Bridge Dispatcher -> WebSockets
    # This ensures "chat", "execution_log", "status" events go to the web UI
    dispatcher.register_listener(app.state.ninja.connection_manager.broadcast)

    # Initialize Controllers
    app.state.ninja.faces = AnimatedFaces(app.state.ninja.hal)
    app.state.ninja.sound = RobotSoundPlayer(app.state.ninja.hal)
    app.state.ninja.movement = MovementController(app.state.ninja.hal, config)
    app.state.ninja.runtime_pipeline.attach_faces(app.state.ninja.faces)
    app.state.ninja.runtime_pipeline.attach_sound(app.state.ninja.sound)
    dispatcher.attach_faces(app.state.ninja.faces)

    # Initialize BLE Service (conditionally, could fail on non-Linux)
    try:
        from ninja_ble.service import NinjaBLEService
        app.state.ninja.ble = NinjaBLEService(
            dispatcher,
            service_name=config.bluetooth.name,
            robot_profile=build_robot_profile(config),
        )
        await asyncio.wait_for(app.state.ninja.ble.start(), timeout=30.0)
        if app.state.ninja.ble.is_running:
            print("BLE Service started.")
        else:
            print("BLE Service initialized but is not advertising.")
    except ImportError as e:
        print(f"BLE modules not found, skipping BLE: {e}")
        app.state.ninja.ble = None
    except asyncio.TimeoutError:
        print("Failed to start BLE Service: startup timed out")
        app.state.ninja.ble = None
    except Exception as e:
        print(f"Failed to start BLE Service: {e}")
        app.state.ninja.ble = None
    
    # Prime servos at startup (ensures PWM signals are active)
    if app.state.ninja.hal.servos:
        print("Priming servos at startup...")
        app.state.ninja.hal.servos.center_all()
    
    # Initialize Distance Monitor
    app.state.ninja.distance_monitor = DistanceMonitor(app.state.ninja.hal)
    app.state.ninja.distance_monitor.start_continuous(interval=0.05)

    # Initialize Agent and attach to Dispatcher
    try:
        app.state.ninja.agent = NinjaAgent(
            config,
            action_library=app.state.ninja.action_library,
        )
        dispatcher.attach_agent(app.state.ninja.agent)
        print("Ninja AI Agent initialized and attached to Dispatcher.")
    except MissingAPIKeyError:
        print("WARNING: Gemini API Key not found. AI Agent will be disabled.")
        print("Run 'ninja_core config set-key gemini <KEY>' or use the web interface to set it.")
    except ValueError as e:
        print(f"Ninja AI Agent not initialized: {e}")



    # Network & ngrok
    network_task = asyncio.create_task(setup_network_and_display(app))
    app.state.ninja.tasks.add(network_task)
    network_task.add_done_callback(app.state.ninja.tasks.discard)

    _app_state = app.state.ninja  # Store for signal handler

    yield

    # --- Shutdown ---
    print("Shutting down Web Server...")
    
    try:
        # Signal all WebSocket handlers to exit their loops
        print("Signaling WebSocket handlers to exit...")
        app.state.ninja.shutdown_event.set()
        await asyncio.sleep(0.5)  # Give handlers time to exit
        
        # Stop BLE with timeout to prevent hang
        if hasattr(app.state.ninja, 'ble') and app.state.ninja.ble:
            print("Stopping BLE Service...")
            try:
                await asyncio.wait_for(app.state.ninja.ble.stop(), timeout=2.0)
            except asyncio.TimeoutError:
                print("⚠️ BLE shutdown timed out! Forcing task cancellation...")
            except Exception as e:
                print(f"⚠️ BLE shutdown error: {e}")
        
        # Cancel all background tasks with timeout
        if hasattr(app.state.ninja, 'tasks') and app.state.ninja.tasks:
            print(f"Cancelling {len(app.state.ninja.tasks)} background tasks...")
            for task in list(app.state.ninja.tasks):
                if not task.done():
                    task.cancel()
            
            # Wait with timeout to prevent hang
            _, pending = await asyncio.wait(
                app.state.ninja.tasks,
                timeout=3.0
            )
            if pending:
                print(f"⚠️ {len(pending)} tasks did not finish in time, forcing exit...")

        # Stop Faces
        if app.state.ninja.faces:
            app.state.ninja.faces.stop()

        # Stop Distance Monitor
        if app.state.ninja.distance_monitor:
            app.state.ninja.distance_monitor.stop_continuous()
            
    except Exception as e:
        print(f"Error during shutdown sequence: {e}")
    finally:
        # Stop HAL (Hardware Abstraction Layer) - CRITICAL: Must be last
        if app.state.ninja.hal:
            print("Shutting down HAL...")
            try:
                app.state.ninja.hal.shutdown()
            except Exception as e:
                print(f"HAL shutdown error: {e}")

        # Stop ngrok
        ngrok.kill()
        print("Shutdown complete.")

async def setup_network_and_display(app: FastAPI):
    port = 8000
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception:
        ip_address = "127.0.0.1"

    print(f"Local Access: http://{ip_address}:{port}")

    # ngrok
    public_url = None
    for attempt in range(3):
        try:
            public_url = ngrok.connect(port, "http").public_url
            print(f"Public Access: {public_url}")
            break
        except Exception as e:
            print(f"ngrok attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2)

    # Display QR
    if public_url and app.state.ninja.hal.display:
        try:
            print(f"Displaying QR code on {app.state.ninja.hal.display.width}x{app.state.ninja.hal.display.height} display...")
            qr = qrcode.make(public_url)
            qr = qr.convert('RGB')
            qr = qr.resize((app.state.ninja.hal.display.width, app.state.ninja.hal.display.height))
            app.state.ninja.hal.display.display(qr)
            print("QR code displayed successfully.")
        except Exception as e:
            print(f"Failed to display QR: {e}")
            import traceback
            traceback.print_exc()
    else:
        reason = "no public URL" if not public_url else "no display available"
        print(f"Skipping QR display ({reason}). Starting idle face...")
        # Idle face if no QR or no display
        if app.state.ninja.faces:
            app.state.ninja.faces.play("idle", duration_s=float('inf'))

# --- Helper Functions ---

async def reclaim_native_runtime(app_state: AppState):
    """Let direct web/native actions interrupt Blockly display ownership."""
    pipeline = getattr(app_state, "runtime_pipeline", None)
    if not pipeline or pipeline.mode == "native":
        return

    dispatcher = getattr(app_state, "dispatcher", None)
    if dispatcher and dispatcher.safe_executor.is_running():
        dispatcher.safe_executor.stop()
    pipeline.abort_blockly()


async def interrupt_active_robot_action(
    app_state: AppState,
    *,
    timeout: float = 2.0,
) -> dict:
    """Stop the current robot-owned action before processing a newer agent request."""
    dispatcher = getattr(app_state, "dispatcher", None)
    safe_executor = getattr(dispatcher, "safe_executor", None) if dispatcher else None
    was_running = bool(safe_executor and safe_executor.is_running())
    pipeline = getattr(app_state, "runtime_pipeline", None)
    action_locked = bool(app_state.action_plan_lock and app_state.action_plan_lock.locked())
    should_interrupt = was_running or action_locked or bool(pipeline and pipeline.mode != "native")

    if not should_interrupt:
        return {
            "interrupted": False,
            "stopped": True,
            "still_running": False,
        }

    if safe_executor:
        try:
            safe_executor.stop()
        except Exception as exc:
            print(f"Failed to stop active SafeExecutor action: {exc}")

    servos = getattr(app_state.hal, "servos", None) if app_state.hal else None
    if servos and hasattr(servos, "abort"):
        try:
            servos.abort()
        except Exception as exc:
            print(f"Failed to abort active servo motion: {exc}")

    if app_state.sound and hasattr(app_state.sound, "stop"):
        try:
            app_state.sound.stop(restart_buzzer=True)
        except Exception as exc:
            print(f"Failed to stop active sound: {exc}")

    if app_state.faces:
        try:
            app_state.faces.stop()
        except Exception as exc:
            print(f"Failed to stop active face animation: {exc}")

    if pipeline and pipeline.mode != "native":
        pipeline.abort_blockly()

    deadline = time.monotonic() + timeout
    while safe_executor and safe_executor.is_running() and time.monotonic() < deadline:
        await asyncio.sleep(0.05)

    still_running = bool(safe_executor and safe_executor.is_running())
    return {
        "interrupted": was_running,
        "stopped": not still_running,
        "still_running": still_running,
    }


def _perform_shutdown_animation(app_state: "AppState") -> None:
    """
    Perform graceful shutdown animation: sleepy face + sound → Poweroff pose.
    This function blocks until all animations complete.
    """
    if not app_state:
        return

    print("💤 Starting shutdown animation...")

    # 1. Start face animation (runs in background thread)
    if app_state.faces:
        try:
            app_state.faces.play("sleepy", duration_s=3.0)
        except Exception as e:
            print(f"  ⚠️ Face animation failed: {e}")

    # 2. Play sound (non-blocking, queued in background)
    if app_state.sound:
        try:
            app_state.sound.play("sleepy")
        except Exception as e:
            print(f"  ⚠️ Sound playback failed: {e}")

    # 3. Execute Poweroff movement (blocking - waits for servos)
    if app_state.movement:
        try:
            print("  🤖 Moving to Poweroff pose...")
            app_state.movement.execute_movement("Poweroff")
            print("  ✅ Poweroff pose complete.")
        except Exception as e:
            print(f"  ⚠️ Poweroff movement failed: {e}")

    # 4. Brief delay to ensure face animation completes
    time.sleep(0.5)
    print("✅ Shutdown animation complete.")

async def handle_first_interaction(app_state: AppState):
    await reclaim_native_runtime(app_state)
    if app_state.first_interaction:
        app_state.first_interaction = False
        # Only set to idle if we haven't just greeted (to avoid overriding happy face)
        # But actually, if we are chatting, we probably want to be in a neutral state or the chat state.
        # If has_greeted is True, we might be in "happy" state or "idle" state.
        # Let's just ensure we are in a known state.
        if app_state.faces:
            app_state.faces.play("idle", duration_s=float('inf'))

async def trigger_welcome(app_state: AppState):
    """Plays greeting (happy face + sound) if not already greeted."""
    if not app_state.has_greeted:
        app_state.has_greeted = True
        print("Triggering Welcome Greeting...")
        
        # Wake up servos - center all to 0° position
        if app_state.movement:
            await asyncio.to_thread(app_state.movement.center_all_servos)
        
        # Play Happy Face
        if app_state.faces:
            app_state.faces.play("happy", duration_s=3.0)
        
        # Play Happy Sound (Non-blocking)
        if app_state.sound:
            asyncio.create_task(asyncio.to_thread(app_state.sound.play, "happy"))
        
        # Wait 3s then return to idle
        await asyncio.sleep(3.0)
        if app_state.faces:
            app_state.faces.play("idle", duration_s=float('inf'))

def safety_check(app_state: AppState) -> bool:
    """
    Returns True if obstacle is detected within 50mm AND approaching rapidly.
    Rapid approach threshold: -50 mm/s (moving towards sensor at > 5cm/s).
    """
    if not app_state.distance_monitor:
        return False
    if app_state.distance_monitor.check_emergency_stop(distance_threshold=100):
        import time
        current_time = time.time()
        
        # Throttling to avoid spamming the reaction (e.g., every 5 seconds)
        if current_time - app_state.last_reaction_time > 5.0:
            app_state.last_reaction_time = current_time
            dist = app_state.distance_monitor.get_continuous_distance()
            vel = app_state.distance_monitor.get_velocity()
            print(f"!!! STARTLE RESPONSE !!! Dist: {dist}mm, Vel: {vel:.2f}mm/s")
            
            # Reaction: Scary Face & Sound
            if app_state.faces:
                # Play scary face for 2 seconds (non-blocking call usually, but we want it to interrupt)
                # But we are inside a callback. Just fire and forget.
                app_state.faces.play("scary", duration_s=2.0)
            
            if app_state.sound:
                # Play scary sound (non-blocking via thread, safe for callbacks)
                threading.Thread(target=app_state.sound.play, args=("scary",), daemon=True).start()
            
            # Return False so we DO NOT stop the servos
            return False
            
    return False

async def execute_action_plan(app_state: AppState, action_plan: dict):
    lock = app_state.action_plan_lock
    if lock is None:
        await _execute_action_plan_unlocked(app_state, action_plan)
        return

    async with lock:
        await _execute_action_plan_unlocked(app_state, action_plan)


async def _execute_action_plan_unlocked(app_state: AppState, action_plan: dict):
    tasks = []
    action_chain = action_plan.get("action_chain", [])
    if not action_chain and action_plan.get("action"):
        action_chain = [{"name": action_plan.get("action"), "repetitions": 1}]
    if isinstance(action_chain, dict):
        action_chain = [action_chain]

    # Faces
    if (action_plan.get("face_chain") or action_plan.get("face")) and app_state.faces:
        def run_faces():
             # Support new "face_chain" format
            chain = action_plan.get("face_chain", [])
            
            # Backward compatibility
            if not chain and action_plan.get("face"):
                chain = [{"name": action_plan.get("face"), "duration": 2.0}]

            for item in chain:
                name = item.get("name")
                duration = item.get("duration")
                if duration is None:
                    duration = float('inf')
                
                # If infinity, plays until stopped or replaced (effectively just starts it).
                # But since we are looping, we need to decide if we block.
                # If duration is specific, we block.
                # If infinite, we just start it and move to next? No, infinite usually implies "end state".
                # If infinite is NOT last, maybe assume 2s? No, let's treat infinite as "start and return".
                
                app_state.faces.play(name)
                if duration != float('inf'):
                     time.sleep(duration)
        
        tasks.append(asyncio.to_thread(run_faces))

    # Sound
    if (action_plan.get("sound_chain") or action_plan.get("sound")) and app_state.sound:
        def run_sounds():
            # Support new "sound_chain" format
            chain = action_plan.get("sound_chain", [])
            
            # Backward compatibility
            if not chain and action_plan.get("sound"):
                chain = [action_plan.get("sound")]

            for name in chain:
                app_state.sound.play(name) # play is blocking, so this sequences them naturally
        
        tasks.append(asyncio.to_thread(run_sounds))

    # Movement
    if (action_plan.get("chain") or action_plan.get("movement")) and app_state.movement:
        
        def run_move():
            try:
                # Support new "chain" format
                chain = action_plan.get("chain", [])
                
                # Backward compatibility for old "movement" field
                if not chain and action_plan.get("movement"):
                    chain = [{"name": action_plan.get("movement"), "repetitions": 1}]

                for item in chain:
                    name = item.get("name")
                    repetitions = item.get("repetitions", 1)
                    
                    if name:
                        for _ in range(repetitions):
                            app_state.movement.execute_movement(
                                name, 
                                abort_check=lambda: safety_check(app_state)
                            )
            except EmergencyStop:
                print("Emergency Stop triggered via Web!")
                if app_state.faces:
                    app_state.faces.play("scary")
                if app_state.sound:
                    # Threading used inside safety_check, so just play blocking here?
                    # No, we are in a thread here (run_move is run in thread).
                    # Actually, run_move is executed via to_thread. So it IS a thread.
                    # AppState.sound.play is blocking? Yes.
                    # We can clear the queue to stop previous sounds if we want priority.
                    app_state.sound.play("scary")
        
        tasks.append(asyncio.to_thread(run_move))

    if tasks:
        await asyncio.gather(*tasks)

    if action_chain:
        dispatcher = getattr(app_state, "dispatcher", None)
        if dispatcher:
            await dispatcher.execute_action_chain(action_chain)

    # Post-Task Reset
    # 1. Center Servos
    if app_state.movement:
        await asyncio.to_thread(app_state.movement.center_all_servos)
    
    # 2. Reset Face to Idle (Looping)
    if app_state.faces:
        # play("idle", float('inf')) is non-blocking (starts a background thread)
        app_state.faces.play("idle", float('inf'))

# --- API Router ---
api_router = APIRouter(prefix="/api")

@api_router.get("/agent/status")
async def agent_status(request: Request):
    return {"active": request.app.state.ninja.agent is not None}

@api_router.post("/agent/set_api_key")
async def set_key_endpoint(payload: SetApiKeyRequest, request: Request):
    try:
        # Update .env
        # We need to know the service name, assuming 'gemini' for now based on V3
        set_api_key("gemini", payload.api_key)
        
        # Reload config and agent
        config = load_config()
        request.app.state.ninja.agent = NinjaAgent(
            config,
            action_library=request.app.state.ninja.action_library,
        )
        if request.app.state.ninja.dispatcher:
            request.app.state.ninja.dispatcher.attach_agent(request.app.state.ninja.agent)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/agent/chat")
async def agent_chat(payload: AgentChatRequest, request: Request):
    state = request.app.state.ninja
    await handle_first_interaction(state)
    
    if not state.agent:
        raise HTTPException(status_code=400, detail="Agent not active")

    interruption = await interrupt_active_robot_action(state)
    if interruption["still_running"]:
        message = (
            "I tried to stop the current action, but it is still running. "
            "Please use Stop Robot or restart the server before starting another action."
        )
        await state.connection_manager.broadcast({
            "type": "log",
            "message": "Agent request blocked: previous action did not stop cooperatively.",
        })
        return {
            "response": message,
            "log": "Previous action did not stop within the safe interruption timeout.",
            "interrupted": interruption,
        }

    result = await state.agent.process_command(payload.message)
    
    if result.get("action_plan"):
        # Log the plan to WS
        await request.app.state.ninja.connection_manager.broadcast({
            "type": "log", 
            "message": f"Agent Plan: {result['action_plan']}"
        })
        await execute_action_plan(state, result["action_plan"])
        
    return {"response": result.get("response"), "log": result.get("log")}

@api_router.post("/code/execute")
async def execute_code(payload: CodeExecuteRequest, request: Request):
    dispatcher = request.app.state.ninja.dispatcher
    if not dispatcher:
        raise HTTPException(status_code=500, detail="Dispatcher not ready")
        
    # Route through dispatcher to ensure consistent logging/broadcasting
    result = await dispatcher.handle_command("web", {"type": "execute", "code": payload.code})
    return result

@api_router.post("/code/stop")
async def stop_execution(request: Request):
    dispatcher = request.app.state.ninja.dispatcher
    if not dispatcher:
         raise HTTPException(status_code=500, detail="Dispatcher not ready")
         
    result = await dispatcher.handle_command("web", {"type": "stop"})
    return result

@api_router.post("/agent/code/analyze")
async def analyze_code(payload: CodeAnalyzeRequest, request: Request):
    agent = request.app.state.ninja.coder_agent
    if not agent:
        raise HTTPException(status_code=503, detail="Coder Agent not available (Check API Key)")
        
    analysis = await agent.analyze_code(payload.code)
    return {"analysis": analysis}

# Note: Voice chat requires saving file and passing to agent.
@api_router.post("/agent/voice")
async def agent_voice(request: Request, file: UploadFile = File(...)):
    state = request.app.state.ninja
    await handle_first_interaction(state)

    if not state.agent:
        raise HTTPException(status_code=400, detail="Agent not active")

    interruption = await interrupt_active_robot_action(state)
    if interruption["still_running"]:
        return {
            "response": (
                "I tried to stop the current action, but it is still running. "
                "Please use Stop Robot or restart the server before starting another action."
            ),
            "transcription": "Voice Processed",
            "log": "Previous action did not stop within the safe interruption timeout.",
            "interrupted": interruption,
        }

    # Save to temp file
    try:
        suffix = Path(file.filename).suffix
        if not suffix:
            suffix = ".webm" # Default to webm if unknown
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Process
        result = await state.agent.process_audio_command(tmp_path)
        
        # Cleanup
        os.unlink(tmp_path)
        
        if result.get("action_plan"):
             await execute_action_plan(state, result["action_plan"])
             
        return {"response": result.get("response"), "transcription": "Voice Processed", "log": result.get("log")}

    except Exception as e:
        print(f"Voice processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/servos/movements")
def get_movements(request: Request):
    # MovementController doesn't expose list directly? 
    # It loads from config. Let's check MovementController.
    # It has `self.movements`.
    if request.app.state.ninja.movement:
        return {"movements": list(request.app.state.ninja.movement.movements.keys())}
    return {"movements": []}

@api_router.post("/servos/movements/{name}/execute")
async def execute_movement(name: str, request: Request):
    state = request.app.state.ninja
    await reclaim_native_runtime(state)
    if not state.movement:
        raise HTTPException(status_code=500, detail="Movement controller not ready")
    
    if name not in state.movement.movements:
        raise HTTPException(status_code=404, detail="Movement not found")

    def run():
        try:
            state.movement.execute_movement(name, abort_check=lambda: safety_check(state))
            return "executed"
        except EmergencyStop:
            print("Emergency Stop triggered via Web!")
            if state.faces:
                state.faces.play("scary")
            if state.sound:
                state.sound.play("scary")
            raise HTTPException(status_code=409, detail="Emergency Stop: Obstacle Detected")

    await asyncio.to_thread(run)
    # Broadcast after successful execution (outside the thread)
    await request.app.state.ninja.connection_manager.broadcast({
        "type": "log", "message": f"Executed Movement: {name}"
    })
    return {"status": "executed"}

@api_router.get("/display/expressions")
def get_expressions(request: Request):
    if request.app.state.ninja.faces:
        return {"expressions": list(request.app.state.ninja.faces.animations.keys())}
    return {"expressions": []}

@api_router.post("/display/expressions/{name}")
async def show_expression(name: str, request: Request):
    await reclaim_native_runtime(request.app.state.ninja)
    if request.app.state.ninja.faces:
        request.app.state.ninja.faces.play(name, duration_s=3.0)
        await request.app.state.ninja.connection_manager.broadcast({
            "type": "log", "message": f"Displaying Expression: {name}"
        })
    return {"status": "displayed"}

@api_router.get("/sound/emotions")
def get_sounds(request: Request):
    if request.app.state.ninja.sound:
        return {"emotions": list(request.app.state.ninja.sound.SOUNDS.keys())}
    return {"emotions": []}

@api_router.post("/sound/emotions/{name}")
async def play_sound(name: str, request: Request):
    await reclaim_native_runtime(request.app.state.ninja)
    if request.app.state.ninja.sound:
        await asyncio.to_thread(request.app.state.ninja.sound.play, name)
        await request.app.state.ninja.connection_manager.broadcast({
            "type": "log", "message": f"Playing Sound: {name}"
        })
    return {"status": "played"}

@api_router.get("/sensor/distance")
def get_distance_api(request: Request):
    if request.app.state.ninja.distance_monitor:
        return {"distance_mm": request.app.state.ninja.distance_monitor.get_continuous_distance()}
    return {"distance_mm": -1}


@api_router.get("/ble/status")
def get_ble_status(request: Request):
    """Returns BLE service advertising status for frontend indicator."""
    ble = getattr(request.app.state.ninja, 'ble', None)
    if ble and ble.is_running:
        return {"advertising": True, "service_name": ble.service_name}
    return {"advertising": False, "service_name": getattr(ble, "service_name", None)}

@api_router.post("/system/shutdown")
async def system_shutdown(request: Request):
    """Safely shuts down the Raspberry Pi with graceful animation."""
    print("Received shutdown request via Web UI.")
    try:
        # Run shutdown sequence in a separate thread to avoid blocking the response
        def shutdown_with_animation():
            app_state = request.app.state.ninja

            # 1. Perform shutdown animation (blocks until complete)
            _perform_shutdown_animation(app_state)

            # 2. Stop high-level threads
            if app_state.faces:
                try:
                    app_state.faces.stop()
                except Exception:
                    pass
            if app_state.distance_monitor:
                try:
                    app_state.distance_monitor.stop_continuous()
                except Exception:
                    pass

            # 3. Clear display to black
            if app_state.hal and app_state.hal.display:
                try:
                    from PIL import Image
                    width = app_state.hal.display.width
                    height = app_state.hal.display.height
                    black_screen = Image.new("RGB", (width, height), (0, 0, 0))
                    app_state.hal.display.display(black_screen)
                except Exception as e:
                    print(f"Failed to clear display: {e}")

            # 4. Shutdown HAL
            if app_state.hal:
                app_state.hal.shutdown()

            time.sleep(1)
            print("Executing shutdown command...")
            subprocess.run(["sudo", "shutdown", "-h", "now"])

        threading.Thread(target=shutdown_with_animation, daemon=True).start()
        return {"status": "shutting_down", "message": "Shutdown animation started..."}
    except Exception as e:
        print(f"Shutdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- App ---
app = FastAPI(lifespan=lifespan)

# Locate built webapp
# Assumed Structure:
# NinjaRobotV5/
#   ninja_webapp/dist/
#   ninja_core/src/ninja_core/web_server.py
WEBAPP_DIST = base_dir.parents[2] / "ninja_webapp" / "dist"

print(f"DEBUG: Looking for React SPA at: {WEBAPP_DIST}")
# Serve React SPA if built, otherwise fall back to legacy templates
if WEBAPP_DIST.exists() and (WEBAPP_DIST / "index.html").exists():
    print("✅ React SPA found. Mounting assets...")
    app.mount("/assets", StaticFiles(directory=WEBAPP_DIST / "assets"))
    
    # Keep legacy static mount for backward compatibility (images etc maybe used by API?)
    legacy_static = base_dir / "static"
    if legacy_static.exists():
        app.mount("/static", StaticFiles(directory=str(legacy_static)), name="static")
else:
    print("⚠️ React SPA not found at:", WEBAPP_DIST)
    print("   👉 ACTION REQUIRED: Build ninja_webapp first!")
    print("   cd ninja_webapp && npm run build")

app.include_router(api_router)

# Root route - serves SPA or legacy template
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):

    
    # Serve React SPA if available
    if WEBAPP_DIST.exists() and (WEBAPP_DIST / "index.html").exists():
        return FileResponse(WEBAPP_DIST / "index.html")
    
    # SPA not available - return error
    return HTMLResponse(
        content="<html><body><h1>NinjaRobot Web Interface</h1>"
                "<p>React SPA not built. Run: <code>cd ninja_webapp && npm run build</code></p></body></html>",
        status_code=503
    )

# SPA catch-all route for client-side routing (must be after API routes)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    # Skip API and WebSocket routes (handled by router and specific endpoints)
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Check if a static file exists in dist (e.g., logo.png, manifest.json)
    potential_file = WEBAPP_DIST / full_path
    if WEBAPP_DIST.exists() and potential_file.exists() and potential_file.is_file():
        return FileResponse(potential_file)

    # Serve React SPA for all other routes
    if WEBAPP_DIST.exists() and (WEBAPP_DIST / "index.html").exists():
        return FileResponse(WEBAPP_DIST / "index.html")
    
    # SPA not available
    return HTMLResponse(
        content="<html><body><h1>404 - Page Not Found</h1><p>SPA not built.</p></body></html>",
        status_code=404
    )

@app.websocket("/ws/distance")
async def websocket_distance(websocket: WebSocket):
    await websocket.accept()
    try:
        while not websocket.app.state.ninja.shutdown_event.is_set():
            if websocket.app.state.ninja.distance_monitor:
                dist = websocket.app.state.ninja.distance_monitor.get_continuous_distance()
                await websocket.send_json({"distance_mm": dist})
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    manager = websocket.app.state.ninja.connection_manager
    await manager.connect(websocket)
    
    # Broadcast welcome on connection (tracked for clean shutdown)
    welcome_task = asyncio.create_task(trigger_welcome(websocket.app.state.ninja))
    websocket.app.state.ninja.tasks.add(welcome_task)
    welcome_task.add_done_callback(websocket.app.state.ninja.tasks.discard)
    
    try:
        while not websocket.app.state.ninja.shutdown_event.is_set():
            # Keep connection alive - broadcasts are pushed via manager.broadcast()
            # Using sleep instead of receive to allow async broadcasts to work
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def check_port_available(host: str, port: int) -> bool:
    """Checks if the port is available."""
    print(f"Checking port availability on {host}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # If connect succeeds (result 0), something is listening -> Port Busy
        result = s.connect_ex((host, port))
        if result == 0:
            return False
    return True

def run_server(autostart: bool = False):
    print("--- NinjaRobot Web Server Setup ---")
    
    # Pre-check port 8000
    host = "0.0.0.0"
    port = 8000
    
    # Use 127.0.0.1 for checking availability as 0.0.0.0 can be quirky with connect_ex
    if not check_port_available("127.0.0.1", port):
        print(f"\n❌ ERROR: Port {port} is already in use!")
        print("Possible causes:")
        print("1. Another instance of 'ninja_core' is already running.")
        print("2. The 'ninjarobot.service' background service is active.")
        print("3. Another application is using port 8000.")
        print("\nFix suggestions:")
        print(" - Stop the background service: 'sudo systemctl stop ninjarobot'")
        print(" - Kill zombie processes: 'sudo pkill -f ninja_core'")
        print(" - Check running processes: 'ps aux | grep ninja'")
        sys.exit(1)
    
    # Check for existing token
    token_exists = has_ngrok_auth_token()

    print("Checking ngrok configuration...")
    
    if autostart:
        if token_exists:
            print("✅ Ngrok authtoken found. Starting server...")
        else:
            print("❌ ERROR: Ngrok authtoken not found.")
            print("Autostart aborted to prevent service hang.")
            print("Please run 'uv run ninja_core server' manually to configure ngrok.")
            sys.exit(1)
    else:
        # Interactive Mode
        if token_exists:
            try:
                token = input("Proceed with existing ngrok account by pressing ENTER or input new ngrok authtoken to proceed: ").strip()
            except EOFError:
                # Handle non-interactive input gracefully
                token = ""
        else:
            try:
                token = input("Please input your ngrok authtoken to proceed: ").strip()
            except EOFError:
                print("Error: Input required for ngrok token but no input stream available.")
                sys.exit(1)

        if token:
            print("Setting ngrok authtoken...")
            set_ngrok_auth_token(token)
    
    # --- Set up emergency cleanup signal handler ---
    def emergency_cleanup():
        """Emergency cleanup when SIGINT is received."""
        global _app_state
        print("🧹 Running emergency cleanup...")

        # Perform shutdown animation first (blocks until complete)
        _perform_shutdown_animation(_app_state)

        if _app_state:
            _app_state.shutdown_event.set()
            # Stop faces animation
            if _app_state.faces:
                try:
                    _app_state.faces.stop()
                except Exception:
                    pass
            # Stop distance monitor
            if _app_state.distance_monitor:
                try:
                    _app_state.distance_monitor.stop_continuous()
                except Exception:
                    pass
            # Shutdown HAL (turns off display)
            if _app_state.hal:
                try:
                    _app_state.hal.shutdown()
                except Exception:
                    pass
        # Kill ngrok
        try:
            ngrok.kill()
        except Exception:
            pass
    
    # Capture and wrap original signal handler
    original_sigint = signal.getsignal(signal.SIGINT)
    
    def sigint_handler(signum, frame):
        print("\n🛑 Ctrl+C received. Shutting down...")
        emergency_cleanup()
        # Restore and call original handler to let uvicorn proceed
        signal.signal(signal.SIGINT, original_sigint)
        if callable(original_sigint) and original_sigint not in (signal.SIG_IGN, signal.SIG_DFL):
            original_sigint(signum, frame)
        else:
            sys.exit(0)  # Clean exit without uvloop error traceback
    
    signal.signal(signal.SIGINT, sigint_handler)
    
    print(f"Starting uvicorn on {host}:{port}...")
    try:
        uvicorn.run("ninja_core.web_server:app", host=host, port=port, reload=False)
    except SystemExit:
        pass
    except Exception as e:
        print(f"Server crashed: {e}")
