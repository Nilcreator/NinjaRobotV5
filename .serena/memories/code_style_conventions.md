# NinjaRobotV5 - Code Style & Conventions

## General Rules
- **Python 3.11+** with type hints everywhere
- **Asyncio-first**: All I/O must be non-blocking (async/await or threaded)
- **Relative paths only**: Use `os.path.join(os.path.dirname(__file__), ...)` - never absolute paths
- **No automatic pip install**: Always ask user permission before installing packages
- **Defensive coding**: Handle hardware exceptions gracefully, never crash the main loop

## Naming Conventions
- **Files/modules:** `snake_case.py`
- **Classes:** `PascalCase` (e.g., `ServoGroup`, `MovementController`, `VL53L0X`)
- **Functions/methods:** `snake_case` (e.g., `move_all_sync`, `get_range_async`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `PHYSICAL_MAX_VELOCITY`, `DRIVER_REGISTRY`)
- **Private:** Leading underscore `_private_method`

## Design Patterns
1. **ABC Interfaces:** All hardware drivers MUST implement `Sensor` or `Actuator` from `ninja_utils.interfaces`
   - `Sensor`: `initialize()`, `get_data()`, `close()`
   - `Actuator`: `initialize()`, `execute(command: dict)`, `off()`
2. **HAL Dynamic Loading:** Drivers loaded via `importlib` from `DRIVER_REGISTRY`
3. **Config Synchronization:** Each driver has its own JSON config, synced with `ninja_core/config.json`
4. **Command Pattern:** JSON command dicts passed to `execute()` methods

## Linting
- **Tool:** `ruff` (via `uv run ruff check`)
- Always lint after modifications

## Documentation Policy
- **DevelopmentLog.md:** Update IMMEDIATELY after every significant change
  - Format: `YYYY-MM-DD: <Title>` → `Action`, `Details`, `Related Files`
- **DevelopmentGuide.md:** Keep API reference in sync
- **README.md:** Keep "Current Status" accurate
- **Languages:** English for code/main docs, Japanese required for README.md and InstallationGuide.md translations

## Project Structure Pattern (per library)
```
library_name/
├── src/library_name/
│   ├── __init__.py       # Public exports
│   ├── __main__.py       # CLI entry point
│   ├── core/             # Core classes
│   ├── config/           # Config management
│   └── cli/              # CLI commands
├── tests/                # pytest tests
├── pyproject.toml
├── README.md
└── LICENSE
```

## Task Completion Checklist
1. ✅ Code changes complete
2. ✅ Run `uv run ruff check <modified_files>`
3. ✅ Run relevant tests if they exist
4. ✅ Update `DevelopmentLog.md` with the change
5. ✅ Update `DevelopmentGuide.md` if API changed
6. ✅ Update library `README.md` if behavior changed
7. ✅ Update `DevelopmentPlan.md` checkmarks if applicable
