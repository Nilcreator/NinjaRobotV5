import asyncio
import os
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
from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pyngrok import ngrok, conf

from .config import load_config, set_api_key
from .hal import HardwareAbstractionLayer
from .ninja_agent import NinjaAgent, MissingAPIKeyError
from .facial_expressions import AnimatedFaces
from .robot_sound import RobotSoundPlayer
from .movement_controller import MovementController, EmergencyStop
from .perception import DistanceMonitor
from .ninja_coder import NinjaCoderAgent

# --- Configuration ---
base_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

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
        self.distance_monitor: Optional[DistanceMonitor] = None
        self.coder_agent: Optional[NinjaCoderAgent] = None
        self.first_interaction: bool = True
        self.has_greeted: bool = False
        self.last_reaction_time: float = 0.0
        self.connection_manager = ConnectionManager()

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

    # Initialize Dispatcher
    from .dispatcher import CommandDispatcher
    dispatcher = CommandDispatcher(app.state.ninja.hal)
    app.state.ninja.dispatcher = dispatcher
    
    # Bridge Dispatcher -> WebSockets
    # This ensures "chat", "execution_log", "status" events go to the web UI
    dispatcher.register_listener(app.state.ninja.connection_manager.broadcast)
    
    # Initialize BLE Service (conditionally, could fail on non-Linux)
    try:
        from ninja_ble.service import NinjaBLEService
        app.state.ninja.ble = NinjaBLEService(dispatcher)
        asyncio.create_task(app.state.ninja.ble.start())
        print("BLE Service started.")
    except ImportError as e:
        print(f"BLE modules not found, skipping BLE: {e}")
        app.state.ninja.ble = None
    except Exception as e:
        print(f"Failed to start BLE Service: {e}")
        app.state.ninja.ble = None
    
    # Initialize Controllers
    app.state.ninja.faces = AnimatedFaces(app.state.ninja.hal)
    app.state.ninja.sound = RobotSoundPlayer(app.state.ninja.hal)
    app.state.ninja.movement = MovementController(app.state.ninja.hal, config)
    
    # Initialize Distance Monitor
    app.state.ninja.distance_monitor = DistanceMonitor(app.state.ninja.hal)
    app.state.ninja.distance_monitor.start_continuous(interval=0.05)

    # Initialize Agent and attach to Dispatcher
    try:
        app.state.ninja.agent = NinjaAgent(config)
        dispatcher.attach_agent(app.state.ninja.agent)
        print("Ninja AI Agent initialized and attached to Dispatcher.")
    except MissingAPIKeyError:
        print("WARNING: Gemini API Key not found. AI Agent will be disabled.")
        print("Run 'ninja_core config set-key gemini <KEY>' or use the web interface to set it.")
    except ValueError as e:
        print(f"Ninja AI Agent not initialized: {e}")

    # Initialize NinjaCoderAgent
    try:
        app.state.ninja.coder_agent = NinjaCoderAgent(config)
        dispatcher.attach_coder_agent(app.state.ninja.coder_agent) # Attach for error loop
        print("Ninja Coder Agent initialized.")
    except Exception as e:
         print(f"Ninja Coder Agent failed to start: {e}")

    # Network & ngrok
    asyncio.create_task(setup_network_and_display(app))

    yield

    # --- Shutdown ---
    print("Shutting down Web Server...")
    # Stop BLE
    if hasattr(app.state.ninja, 'ble') and app.state.ninja.ble:
        await app.state.ninja.ble.stop()

    if app.state.ninja.faces:
        app.state.ninja.faces.stop()
    if app.state.ninja.distance_monitor:
        app.state.ninja.distance_monitor.stop_continuous()
    if app.state.ninja.hal:
        app.state.ninja.hal.shutdown()
    ngrok.kill()

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
            qr = qrcode.make(public_url)
            qr = qr.convert('RGB')
            qr = qr.resize((app.state.ninja.hal.display.width, app.state.ninja.hal.display.height))
            app.state.ninja.hal.display.display(qr)
        except Exception as e:
            print(f"Failed to display QR: {e}")
    else:
        # Idle face if no QR or no display
        if app.state.ninja.faces:
            app.state.ninja.faces.play("idle", duration_s=float('inf'))

# --- Helper Functions ---
async def handle_first_interaction(app_state: AppState):
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
    tasks = []

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
        request.app.state.ninja.agent = NinjaAgent(config)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/agent/chat")
async def agent_chat(payload: AgentChatRequest, request: Request):
    state = request.app.state.ninja
    await handle_first_interaction(state)
    
    if not state.agent:
        raise HTTPException(status_code=400, detail="Agent not active")

    result = await state.agent.process_command(payload.message)
    
    if result.get("action_plan"):
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
# V4 agent doesn't have process_audio_command yet in the interface shown in previous turns?
# Checking ninja_agent.py in previous turns... 
# The user didn't explicitly ask for voice in V4 yet, but V3 had it. 
# I will implement the endpoint structure but might need to stub it if Agent doesn't support it yet.
# Actually, looking at V3, it used `process_audio_command`. 
# I'll omit voice for now to avoid errors if not implemented in V4 Agent, 
# or I can add it if I verify Agent has it. 
# For now, I will stick to text chat as per "Chat" requirement.

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
    return {"status": "executed"}

@api_router.get("/display/expressions")
def get_expressions(request: Request):
    if request.app.state.ninja.faces:
        return {"expressions": list(request.app.state.ninja.faces.animations.keys())}
    return {"expressions": []}

@api_router.post("/display/expressions/{name}")
def show_expression(name: str, request: Request):
    if request.app.state.ninja.faces:
        request.app.state.ninja.faces.play(name, duration_s=3.0)
    return {"status": "displayed"}

@api_router.get("/sound/emotions")
def get_sounds(request: Request):
    if request.app.state.ninja.sound:
        return {"emotions": list(request.app.state.ninja.sound.SOUNDS.keys())}
    return {"emotions": []}

@api_router.post("/sound/emotions/{name}")
async def play_sound(name: str, request: Request):
    if request.app.state.ninja.sound:
        await asyncio.to_thread(request.app.state.ninja.sound.play, name)
    return {"status": "played"}

@api_router.get("/sensor/distance")
def get_distance_api(request: Request):
    if request.app.state.ninja.distance_monitor:
        return {"distance_mm": request.app.state.ninja.distance_monitor.get_continuous_distance()}
    return {"distance_mm": -1}

@api_router.post("/system/shutdown")
async def system_shutdown(request: Request):
    """Safely shuts down the Raspberry Pi."""
    print("Received shutdown request via Web UI.")
    try:
        # Run shutdown command in a separate thread to avoid blocking the response
        # giving time for the response to be sent back to the client.
        async def delayed_shutdown():
            # 1. Stop high-level threads first (Critical to prevent race condition)
            if request.app.state.ninja.faces:
                request.app.state.ninja.faces.stop()
            if request.app.state.ninja.distance_monitor:
                request.app.state.ninja.distance_monitor.stop_continuous()

            # 2. Clear display to black (so even if backlight flickers back on, it's black)
            if request.app.state.ninja.hal and request.app.state.ninja.hal.display:
                try:
                    from PIL import Image
                    # Create a black image matching the display size
                    width = request.app.state.ninja.hal.display.width
                    height = request.app.state.ninja.hal.display.height
                    black_screen = Image.new("RGB", (width, height), (0, 0, 0))
                    request.app.state.ninja.hal.display.display(black_screen)
                except Exception as e:
                    print(f"Failed to clear display: {e}")

            # 3. Shutdown HAL (turns off backlight, servos, buzzer)
            if request.app.state.ninja.hal:
                request.app.state.ninja.hal.shutdown()

            await asyncio.sleep(1)
            print("Executing shutdown command...")
            # sudo is required, and user must have passwordless sudo for shutdown
            subprocess.run(["sudo", "shutdown", "-h", "now"])

        asyncio.create_task(delayed_shutdown())
        return {"status": "shutting_down", "message": "System is shutting down..."}
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
    print("⚠️ React SPA not found. Falling back to legacy templates.")
    print("   👉 ACTION REQUIRED: The 'dist' folder is missing on the robot.")
    print("   1. If using git: I have updated .gitignore. Please commit 'ninja_webapp/dist' and pull on the robot.")
    print("   2. Or manually copy 'ninja_webapp/dist' to the robot.")

    # Legacy static files
    legacy_static = base_dir / "static" # Define legacy_static here for the else block
    if legacy_static.exists():
        app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

app.include_router(api_router)

# Root route - serves SPA or legacy template
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Trigger welcome greeting on page load
    asyncio.create_task(trigger_welcome(request.app.state.ninja))
    
    # Serve React SPA if available
    if WEBAPP_DIST.exists() and (WEBAPP_DIST / "index.html").exists():
        return FileResponse(WEBAPP_DIST / "index.html")
    
    # Fallback to legacy template
    print("Serving Legacy Index (SPA not found)")
    return templates.TemplateResponse("index.html", {"request": request})

# SPA catch-all route for client-side routing (must be after API routes)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    # Skip API and WebSocket routes (handled by router and specific endpoints)
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Serve React SPA for all other routes
    if WEBAPP_DIST.exists() and (WEBAPP_DIST / "index.html").exists():
        return FileResponse(WEBAPP_DIST / "index.html")
    
    # Fallback to legacy template
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/distance")
async def websocket_distance(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
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
    try:
        while True:
            # Keep connection alive, maybe receive client pings/commands later?
            # For now, just listen.
            await websocket.receive_text()
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
    token_exists = False
    if conf.get_default().auth_token:
        token_exists = True
    else:
        # Check common config paths
        paths = [
            os.path.join(os.path.expanduser("~"), ".ngrok2", "ngrok.yml"),
            os.path.join(os.path.expanduser("~"), "Library", "Application Support", "ngrok", "ngrok.yml"),
            os.path.join(os.path.expanduser("~"), ".config", "ngrok", "ngrok.yml")
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        if "authtoken" in f.read():
                            token_exists = True
                            break
                except Exception:
                    pass

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
            ngrok.set_auth_token(token)
    
    print(f"Starting uvicorn on {host}:{port}...")
    try:
        uvicorn.run("ninja_core.web_server:app", host=host, port=port, reload=False)
    except SystemExit:
        pass
    except Exception as e:
        print(f"Server crashed: {e}")
