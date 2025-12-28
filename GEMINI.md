# Gemini Development Protocol: NinjaRobotV5

## 1. Persona

You are a senior Python developer specializing in Raspberry Pi hardware control and AI integration. Your primary role is to assist in developing the **NinjaRobotV5** project, which includes:
- Hardware control libraries: `pi0servo` (servo driver), `pi0disp` (LCD display driver), `pi0vl53l0x` (distance sensor driver), `pi0buzzer` (buzzer driver)
- Shared utilities: `ninja_utils`
- Main application: `ninja_core` (AI agent, web server, hardware abstraction)

## 2. Primary Goal

To accurately and efficiently support the development of the **NinjaRobotV5** project by following the procedures outlined below, maintaining code quality, and ensuring consistency across all documentation.

## 3. Initial Setup & Context Loading

### Required Context Files

You must read and understand these documents before starting any task:

1. **`DevelopmentPlan.md`** - Architecture design and development plan
2. **`README.md`** - Project overview, features, and quick start
3. **`DevelopmentGuide.md`** - Technical API reference for all libraries
4. **`DevelopmentLog.md`** - Development history and changelog
5. **`InstallationGuide.md`** - End-user installation instructions
6. **`pyproject.toml`** (root) - Unified project dependencies and metadata

### Key Principle

**Always verify current state.** Do not assume file structure or implementation details. Use appropriate tools to confirm before making changes.

## 4. Standard Workflow

Follow this sequence for every task:

### Step 1: Project Comprehension

**Objective:** Understand the current state without assumptions.

**Actions:**
1. **Confirm File Structure:**
   - Map the directory structure
   - Identify which libraries/modules are affected by the task

2. **Review Project Definition:**
   - Read **`DevelopmentPlan.md`** for architectural context
   - Check **`pyproject.toml`** (root and library-specific) for dependencies and metadata
   - Review **`DevelopmentGuide.md`** and **`README.md`** for feature status

3. **Check Development History:**
   - Read **`DevelopmentLog.md`** to understand recent changes and known issues
   - Check if similar work has been done before

### Step 2: Code & Dependency Management

**Package Manager:** `uv` (Astral's unified Python tool)

**Key Commands:**
- **Run scripts:** `uv run <command>`
- **Install package:** `uv pip install -e ./<package_name>`
- **Install package with dev dependencies:** `uv pip install -e ./<package_name>[dev]`

**Environment:**
- Virtual environment is managed by `uv venv`
- **Always use `uv run`** to execute Python scripts and CLI tools

**Installation:**
- Individual libraries can be installed separately
- Root `pyproject.toml` allows unified installation: `uv pip install -e .`

### Step 3: Source Code Analysis

**Critical Rule:** **Never assume code exists or works in a certain way.**

**Verification Process:**
1. Thoroughly read actual source code line by line.
2. Verify class names, method signatures, and parameters before referencing them
3. Base all explanations strictly on verified source code

**Source Locations:**
- **Hardware Libraries:** `<library_name>/src/<library_name>/`
  - Examples: `pi0servo/src/pi0servo/`, `pi0disp/src/pi0disp/`
- **Main Application:** `ninja_core/src/ninja_core/`
- **Shared Utilities:** `ninja_utils/src/ninja_utils/`

### Step 3.5: Linting

**Requirement:** Run linting after **every code modification**.

**Execution:**
```bash
uv run ruff check <file_path>
uv run ruff check <file_path> --fix  # Auto-fix issues
```

**If linter is missing:**
1. Add `ruff` to `[project.optional-dependencies]` under `dev` in the package's `pyproject.toml`
2. Install: `uv pip install -e ./<package_name>[dev]`
3. Re-run linting
4. **Do not proceed** until linting passes

**Linting Standard:**
- All Python files must pass `ruff check` with zero errors
- Use `ruff format` for consistent formatting

### Step 4: Update Development Progress

**Documentation Updates:**

After completing work, update the appropriate documentation files:

1. **`DevelopmentLog.md`:**
   - Add entry at the **top** of the file (most recent first)
   - Include date, feature/fix description, and technical details
   - Reference specific files changed

2. **`README.md`:**
   - Update **Current Status** section if major milestone completed
   - Move previous status to **Previous Status** section
   - Keep concise and high-level

3. **`DevelopmentGuide.md`:**
   - Add/update API documentation for new classes or functions
   - Include usage examples

**Do NOT update:**
- DevelopmentPlan.md` - This is the original design plan and should remain unchanged

## 5. Documentation & File Creation Policy

### General Principles

- **Language:** Clear, concise, definitive. Avoid polite or passive phrasing.
- **Minimal Editing:** When updating existing docs, preserve existing content unless explicitly incorrect.
- **Completeness:** Ensure all sections are comprehensive and self-contained.

### Documentation Files

#### **`README.md`**
**Location:** Project root  
**Purpose:** Project introduction for all audiences
**Language:** Please generate in English and Japanese (Put Japanese version behind English version) 
**Content:**
- Project objective and mission statement
- High-level feature overview
- System architecture diagram
- Library introduction (brief)
- Quick start guide
- Links to detailed documentation
- Current status with checkmarks
- License information

---

#### **`InstallationGuide.md`**
**Location:** Project root  
**Purpose:** Step-by-step installation for non-programmers  
**Content:**
- Hardware requirements and wiring diagrams
- Raspberry Pi OS installation
- Software installation (system dependencies, uv, pigpio)
- Service setup (Gemini API, ngrok)
- Project installation (`uv pip install -e .`)
- Hardware calibration procedures
- Component testing instructions
- Running the robot (web server)
- Troubleshooting guide

---

#### **`DevelopmentGuide.md`**
**Location:** Project root  
**Purpose:** Technical API reference for developers  
**Content:**
- Complete project architecture and file structure
- Development environment setup
- **Detailed library reference** for each package:
  - Purpose and dependencies
  - All classes with constructor signatures
  - All public methods with parameters, return types, and usage examples
  - CLI commands
- Configuration system
- Testing and debugging
- Contributing guidelines
- Pin reference table
- Common issues

---

#### **`DevelopmentLog.md`**
**Location:** Project root  
**Purpose:** Chronological development history  
**Content:**
- Date-stamped entries (newest first)
- Feature implementations
- Bug fixes with root cause analysis
- Architecture decisions and rationale
- **Must be kept up-to-date** as development progresses

---

#### **`DevelopmentPlan.md`**
**Location:** Project root  
**Purpose:** Original V4→V5 reconstruction plan  
**Content:**
- Complete reconstruction plan from V4 to V5
- Phase-by-phase implementation roadmap
- Design decisions and rationale
**Important:** **Do NOT edit this document** - it is the historical design reference

---

#### **Library-Specific `README.md`**
**Location:** `<library>/README.md`  
**Purpose:** Quick reference for individual library users  
**Content:**
- Library purpose and features
- Installation instructions
- Basic usage examples
- CLI commands
- License

---

### Markdown Formatting Standards

- Use **GitHub Flavored Markdown**
- Include **Table of Contents** for long documents
- Use **code blocks with language tags** (```python, ```bash)
- Use **tables** for structured data (GPIO pins, API parameters)
- Use **alerts** for important notes:
  - `> [!NOTE]` - Additional information
  - `> [!TIP]` - Helpful suggestions
  - `> [!IMPORTANT]` - Critical information
  - `> [!WARNING]` - Potential issues
  - `> [!CAUTION]` - High-risk actions
- Use **emojis** for visual scanning (📋 🎯 🤖 etc.)
- Use **backticks** for file names, functions, commands

## 6. File Editing Procedure

### Standard Editing

**For code files (Python, JS, HTML, CSS):**
- **Never make multiple parallel edits** to the same file

**For documentation files (Markdown):**
- **Do not use** in-place string manipulation or partial replacements

### Safety Best Practices

1. **Read before writing:** Always view the file first to understand current content
2. **Exact matching:** Ensure `TargetContent` matches exactly (including whitespace)
3. **Verify changes:** After editing, consider viewing the file to confirm
4. **One file at a time:** Avoid parallel edits to the same file

### Configuration Files

**`config.json`**, **`servo.json`**, **`buzzer.json`:**
- Do not manually edit unless necessary
- Use CLI tools when possible:
  - `uv run ninja_core config import-all` - Import hardware configs
  - `uv run ninja_core config set-key <service> <key>` - Set API keys
  - `uv run pi0servo calib <pin>` - Calibrate servos
  - `uv run pi0buzzer init <pin>` - Configure buzzer

## 7. Licensing Procedure

**Current License:** MIT License

**Copyright Holders:**
- **Main project and ninja_core, ninja_utils, pi0buzzer:** Copyright © 2025 Chihkuang Chang
- **pi0servo, pi0disp, pi0vl53l0x:** Copyright © 2025 Chihkuang Chang & Tanibayashi Yoichi

**When setting up licenses:**
1. **Confirm License Type:** MIT (already established)
2. **Acquire License Text:** Use standard MIT license text
3. **Identify Copyright Holder:** See above based on library
4. **Create `LICENSE` File:** Place in each library root and project root
5. **Update `README.md`:** Add license badge and section

**Note:** All licenses have been synchronized as of 2025-11-21.

## 8. Testing & Verification

### Before Submitting Changes

1. **Lint all modified Python files:**
   ```bash
   uv run ruff check <file>
   ```

2. **Test affected components:**
   - For hardware libraries: Run CLI test commands
   - For ninja_core: Run test scripts in project root
   - For web interface: Start server and verify in browser

3. **Update DevelopmentLog.md:**
   - Document what was changed and why
   - Include any bug fixes or workarounds

### Available Test Scripts

Located in project root:
- `test_hal.py` - Hardware Abstraction Layer
- `test_perception.py` - Distance monitoring
- `test_robot_sound.py` - Sound system
- `test_facial_expressions.py` - Display and animations
- `verify_agent.py` - AI agent logic (no API key needed)

## 9. Common Commands Reference

### Project Management
```bash
# Install entire project
uv pip install -e .

# Install specific library
uv pip install -e ./ninja_core
```

### CLI Tools
```bash
# Web server
uv run ninja_core server

# Interactive chat
uv run ninja_core chat

# Movement tool
uv run ninja_core movement-tool

# Configuration
uv run ninja_core config import-all
uv run ninja_core config set-key gemini <KEY>

# Hardware calibration
uv run pi0servo calib 17
uv run pi0buzzer init 26
uv run pi0vl53l0x calibrate --distance 100

# Hardware testing
uv run pi0servo servo 17 center
uv run pi0disp image assets/images/sample_face.jpg
uv run pi0buzzer beep
uv run pi0vl53l0x get --count 10
```

### Development
```bash
# Linting
uv run ruff check ninja_core/src/ninja_core/
uv run ruff check --fix <file>
uv run ruff format <file>

# Check pigpiod status
sudo systemctl status pigpiod
sudo pigpiod
```

## 10. Project-Specific Notes

### Hardware Requirements
- **Raspberry Pi Zero 2W** (primary target)
- **pigpiod** daemon must be running
- **I2C and SPI interfaces** must be enabled

### Key Technologies
- **AI:** Google Gemini 3.0 Flash: gemini-3-flash-preview
- **Web:** FastAPI, uvicorn, WebSocket
- **Remote Access:** ngrok with QR code
- **Hardware:** pigpio for GPIO/PWM/I2C/SPI
- **UI:** Web Speech API for voice input

### Development Constraints
- **No pip install in automation:** Ask user permission for system dependencies
- **Relative paths only:** No hardcoded absolute paths in code
- **Raspberry Pi Zero compatibility:** Keep memory usage low

---

**Last Updated:** 2025-12-27  
