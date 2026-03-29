---
name: pi0driver-development
description: Use for substantial NinjaRobotV5 driver-library work on pi0buzzer, pi0servo, pi0disp, and pi0vl53l0x. Covers standalone-first Raspberry Pi Zero 2W development, code-backed repository audit, phased planning with approval before risky coding, quality gates, Pi validation, and required documentation updates.
---

# NinjaRobot Pi0 Library Workflow

Use this skill for substantial work on the existing NinjaRobotV5 Pi Zero 2W driver libraries:

- `pi0buzzer`
- `pi0servo`
- `pi0disp`
- `pi0vl53l0x`

This skill is the development guide for these libraries as standalone packages and as `ninja_core` integration points.

## Core policy

- Treat each `pi0*` package as a standalone library first.
- Do not make `ninja_core` a runtime requirement for the libraries standalone.
- Preserve optional future integration hooks where cheap and sensible:
  - `driver.py` compatibility re-export entries
  - config-manager entry points
  - stable callable class surfaces
  - compatibility aliases such as `MultiServo`
- Trust code and tests over documentation when they disagree.
- Do not begin substantial or risky coding until the user has approved a phased implementation plan.
- Do not move to the next phase until the current phase passes the quality gate.
- After each hardware-facing phase, produce a manual Raspberry Pi Zero 2W validation gate.
- If the task is a small documentation-only or metadata-only cleanup with no behavior change, a brief inline plan is enough and a formal approval gate is not required.

## Required context to load first

Before planning substantial work, review:

- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/AGENT.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/DevelopmentGuide.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/README.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/DevelopmentLog.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/InstallationGuide.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/pyproject.toml`
- `README.md` in the developing pi0* package folder, for example `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/pi0servo/README.md`

## Required tool order

Follow this order unless the task is trivial.

1. Serena first for repository understanding.
2. Context7 for third-party library behavior and current package docs.
3. OpenAI docs MCP for OpenAI or Codex related behavior only when relevant to the task.
4. GitHub MCP if branch, issue, PR, or remote repo state matters.
5. Web research using primary sources only when Pi Zero 2W compatibility or library support may have changed, or when Context7 is insufficient.

For Serena-based repository review, use:

- `activate_project`
- `check_onboarding_performed`
- `initial_instructions`

Then prefer:

- `list_dir`
- `find_file`
- `get_symbols_overview`
- `find_symbol`
- `search_for_pattern`

Use line-based file reads only when symbolic review is not enough or when reading Markdown, JSON, TOML, YAML, logs, or other non-code files.

## Required development workflow

### Step 0: Build a verified baseline

Before trusting the docs, confirm the current package behavior from the code.

At minimum, capture:

- package root exports
- CLI entry points and subcommands
- compatibility shims such as `driver.py`
- config file names, paths, and defaults
- integration call sites in `ninja_core`
- current tests and validation commands
- any documentation drift you discover

If documentation and code disagree, follow the code and note the discrepancy in the plan or task summary.

### Step 1: Understand the request

Extract and state:

- target library or libraries
- requested outcome
- target hardware on Raspberry Pi zero 2w
- standalone vs optional future integration scope
- safety risks
- expected output files

If the request is ambiguous and a wrong assumption would be risky, clarify before planning.

### Step 2: Audit the target library before planning

Always audit the current source contract before proposing changes.

Required source locations:

- `NinjaRobotV5/pi0buzzer`
- `NinjaRobotV5/pi0servo`
- `NinjaRobotV5/pi0disp`
- `NinjaRobotV5/pi0vl53l0x`

For the selected library, inspect at minimum:

- package `pyproject.toml`
- package `README.md`
- `src/<package>/__init__.py`
- `src/<package>/__main__.py`
- `src/<package>/driver.py` if present
- core driver modules
- config manager
- CLI modules
- tests
- package-local `pyproject.toml`

If future integration matters, also inspect the integration references in:

- `NinjaRobotV5/ninja_core/src/ninja_core/hal.py`
- `NinjaRobotV5/ninja_core/src/ninja_core/config.py`
- `NinjaRobotV5/ninja_core/src/ninja_core/dispatcher.py`
- `NinjaRobotV5/ninja_core/src/ninja_core/robot_sound.py`
- `NinjaRobotV5/ninja_core/src/ninja_core/movement_cli.py`
- `NinjaRobotV5/ninja_core/src/ninja_core/movement_controller.py`

Capture:

- public exports
- required classes and methods
- config file names and schemas
- CLI commands
- hardware-facing APIs
- compatibility surfaces that must remain available
- relevant integration assumptions

### Step 3: Produce a phased plan and wait for approval

The plan must be explicit and library-by-library in plain English that even non-developers can understand. If any professional terminology or abbreviations are necessary, explain them.

For each phase include:

- objective
- exact files and modules likely to change
- required classes or functions to preserve
- backend choice or backend options
- lint and test commands
- manual Raspberry Pi Zero 2W validation required
- hardware risk level
- documentation files to update
- known documentation drift to fix as part of the task

Do not code until the user approves the plan.

### Step 4: Implement phase by phase

During implementation:

- keep diffs small and reviewable
- prefer modifying existing code over inventing unrelated new files
- mirror the audited package structure unless there is a deliberate, approved reason to change it
- keep public behavior stable unless the user approved a change
- isolate transport and hardware access behind backend helpers or adapters
- when touching compatibility surfaces, update all affected call sites or explicitly preserve old behavior

Expected target structure:

- `pi0buzzer/`
- `pi0servo/`
- `pi0disp/`
- `pi0vl53l0x/`

Typical required package files:

- `pyproject.toml`
- `README.md`
- `src/<package>/__init__.py`
- `src/<package>/__main__.py`
- `src/<package>/driver.py` where legacy compatibility expects it
- `src/<package>/core/*`
- `src/<package>/config/*`
- `src/<package>/cli/*`
- `tests/*`
- `LICENSE`

## Required library contracts

Preserve these audited surfaces unless the user explicitly approves a change.

### `pi0buzzer`

Required behavior:

- exports `Buzzer`, `MusicBuzzer`
- keep note and emotion behavior compatible
- preserve queue-based non-blocking playback
- preserve `play_sound`, `queue_pause`, `play_note`, `play_song`, `play_emotion`, `play_demo`, `play_music`
- preserve config with `pin` and `volume`
- preserve CLI workflows

### `pi0servo`

Required behavior:

- exports `Servo`, `ServoCalibration`, `ServoGroup`, `ConfigManager`
- keep `MultiServo = ServoGroup`
- preserve `angle_to_pulse`, `pulse_to_angle`, `get_pulse`, `get_angle`, `set_pulse`, `set_angle`
- preserve `move_all_sync`, `move_all_async`, abort behavior, refresh behavior, and legacy helper methods
- preserve config schema in `servo.json`
- preserve CLI calibration and command workflows
- preserve `ninja_core` compatibility expectations around the current movement-tool string command path unless a coordinated integration change is approved

### `pi0disp`

Required behavior:

- export `ST7789V`, `ConfigManager` at package root
- preserve `display`, `display_region`, `clear`, `set_brightness`, `set_rotation`, `sleep`, `wake`, `health_check`, `initialize`, `execute`, `off`
- preserve config wizard and `display.json` style behavior
- preserve fonts, ticker, and CLI workflows
- preserve actual runtime behavior over stale README claims; note that current `display()` behavior is full-frame by default for reliability and `TextTicker` currently lives outside the package root export surface

### `pi0vl53l0x`

Required behavior:

- export `VL53L0X` at package root
- preserve `driver.py` compatibility re-export path
- preserve initialize and retry semantics
- preserve `get_range`, `get_data`, `get_ranges`, `get_range_async`, `set_offset`, `calibrate`, `health_check`, `reinitialize`, `close`
- preserve config and CLI workflows

## Required quality gate after every implementation phase

Do not continue to the next phase until the current phase passes the quality gate.

Prefer repo-defined commands if they exist for the target package.

Default gate:

```bash
python -m compileall src tests
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

If the package or repo already uses typing checks, also run:

```bash
uv run mypy .
```

Preferred execution pattern:

- run package-local tests while porting a single library
- run broader repo checks only when the current task affects shared files
- if a package-local environment does not expose `pytest`, use an explicit command such as `uv run --with pytest pytest -q`

If the gate fails:

- stop
- fix the issue
- rerun the failing checks
- only continue after the phase is clean

## Required Raspberry Pi zero 2w manual validation after each library

Every hardware-facing phase must end with a manual Pi Zero 2W validation checklist.

Each checklist must contain:

- safe smoke tests
- device communication tests
- actuator-moving tests if relevant
- power-risk tests if relevant
- expected outcomes
- rollback steps

### Extra rule for `pi0servo`

For `pi0servo`, signal accuracy is mandatory.

The agent must:

- treat pulse generation as hardware-backed, not Python-timed
- keep motion planning in microseconds
- require direct signal measurement with a logic analyser or oscilloscope when validating accuracy
- test center, min, max, small corrections around center, idle, and CPU-load conditions
- reject software-timed servo output as the default production backend

## Required documentation updates

If implementation changes code, the task is not complete until documentation is reviewed and updated.

Required files:

- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/DevelopmentGuide.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/README.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/DevelopmentLog.md`
- `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/InstallationGuide.md`
- `AGENT.md` if the workflow itself changed
- `README.md` in the developing pi0* package folder, for example `/Users/nilcreator/Desktop/0_Projects/Nilcreation/NinjaRobot/CodePlatform/NinjaRobotV5/pi0servo/README.md`

Update expectations:

- `README.md`: project purpose, driver overview, setup, usage examples
- `DevelopmentGuide.md`: workflow, module layout, backend notes, lint and test commands, Pi validation flow, current exports, and real current behavior
- `DevelopmentLog.md`: dated summary, files changed, reason, checks run, Pi validation status, follow-up work
- `InstallationGuide.md`: setup, import/export, calibration, and first-run flow whenever user setup is affected
- package README: root exports, CLI commands, config defaults, setup steps, examples, troubleshooting

### Required documentation fact-check

Before declaring docs updated, verify:

- package exports match `__init__.py`
- CLI commands match `__main__.py` and CLI modules
- config defaults and file paths match the config manager implementation
- reported runtime behavior matches the current code, not historical rebuild notes
- test counts or validation claims match what you actually ran
- multilingual docs are kept in sync where the same information is repeated

## Final response requirements

At handoff, summarize in plain English that even non-developers can understand:

- what changed
- which files were changed
- lint and test outcomes
- what was manually validated on Raspberry Pi zero 2w and what is still pending
- what docs were updated
- remaining risk
- recommended next step
