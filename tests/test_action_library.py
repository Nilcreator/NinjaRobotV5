from __future__ import annotations

import json

import pytest

from ninja_core.action_library import (
    ActionLibrary,
    ActionNameConflictError,
    ActionNotFoundError,
    ActionValidationError,
)


def test_action_library_saves_complete_blockly_action(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")
    code = "\n".join(
        [
            "import time",
            "from ninja_core import robot",
            'robot.expression("happy")',
            'robot.display.text("Hello", scroll=True, duration=1)',
            'robot.buzzer.play_song("jingle_bells")',
            "if robot.distance.read() < 100:",
            '    robot.expression("scary")',
        ]
    )

    record = library.save_action(
        name="Happy Greeting",
        code=code,
        workspace_state={"blocks": {"blocks": []}},
        manifest={"generator_version": "test-generator"},
    )

    assert record["name"] == "Happy Greeting"
    assert record["slug"] == "happy-greeting"
    assert record["workspace_state"] == {"blocks": {"blocks": []}}
    assert record["manifest"]["generator_version"] == "test-generator"

    saved_path = tmp_path / "ninja_actions" / "happy-greeting.json"
    assert saved_path.exists()
    with open(saved_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["code"] == code


def test_action_library_rejects_duplicate_and_native_movement_conflicts(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")
    library.save_action(name="Wave", code='print("ok")')

    with pytest.raises(ActionNameConflictError) as saved_conflict:
        library.save_action(name="wave", code='print("again")')
    assert saved_conflict.value.can_overwrite is True
    assert saved_conflict.value.conflict_type == "saved_action"

    with pytest.raises(ActionNameConflictError) as native_conflict:
        library.save_action(
            name="Poweroff",
            code='print("native conflict")',
            native_movement_names=["Poweroff"],
        )
    assert native_conflict.value.can_overwrite is False
    assert native_conflict.value.conflict_type == "native_movement"


def test_action_library_overwrites_saved_action_but_not_native_movement(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")
    original = library.save_action(name="Wave", code='print("old")')
    updated = library.save_action(name="wave", code='print("new")', overwrite=True)

    assert updated["overwritten"] is True
    assert updated["created_at"] == original["created_at"]
    assert library.get_action("Wave")["code"] == 'print("new")'

    with pytest.raises(ActionNameConflictError) as native_conflict:
        library.save_action(
            name="Poweroff",
            code='print("native conflict")',
            native_movement_names=["Poweroff"],
            overwrite=True,
        )
    assert native_conflict.value.can_overwrite is False


def test_action_library_rejects_disallowed_imports(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")

    with pytest.raises(ActionValidationError, match="not allowed"):
        library.save_action(name="Bad", code="import os\nprint(os.getcwd())")


def test_action_library_builds_replay_code(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")
    library.save_action(
        name="Blink",
        code='from ninja_core import robot\nrobot.display.clear()\n',
    )

    replay_code = library.build_replay_code(
        [
            {
                "name": "Blink",
                "repetitions": 2,
            }
        ]
    )

    assert "for _ninja_action_repeat_0 in range(2):" in replay_code
    assert "    robot.display.clear()" in replay_code
    compile(replay_code, "<replay>", "exec")


def test_action_library_missing_action_raises(tmp_path):
    library = ActionLibrary(tmp_path / "ninja_actions")

    with pytest.raises(ActionNotFoundError):
        library.build_replay_code([{"name": "Missing"}])
