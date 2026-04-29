from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import textwrap
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import build_execution_manifest


ACTION_SCHEMA_VERSION = "ninja-action-v1"
ACTION_LIBRARY_PATH = Path("ninja_actions")
MAX_ACTION_CODE_BYTES = 128 * 1024
MAX_ACTION_NAME_BYTES = 80
MAX_ACTION_REPETITIONS = 20
ALLOWED_ACTION_IMPORTS = frozenset({"time", "math", "random", "ninja_core"})


class ActionLibraryError(Exception):
    """Base exception for Blockly action library failures."""


class ActionValidationError(ActionLibraryError):
    """Raised when an action payload is invalid or unsafe to save."""


class ActionNameConflictError(ActionLibraryError):
    """Raised when an action name conflicts with an existing action or movement."""

    def __init__(
        self,
        message: str,
        *,
        conflict_type: str = "saved_action",
        action_name: str | None = None,
        action_slug: str | None = None,
        can_overwrite: bool = False,
    ):
        super().__init__(message)
        self.conflict_type = conflict_type
        self.action_name = action_name
        self.action_slug = action_slug
        self.can_overwrite = can_overwrite


class ActionNotFoundError(ActionLibraryError):
    """Raised when a saved action cannot be found."""


def normalize_action_name(name: str) -> str:
    """Normalize a user-facing action name without losing multilingual text."""
    normalized = unicodedata.normalize("NFKC", str(name or ""))
    normalized = " ".join(normalized.strip().split())
    if not normalized:
        raise ActionValidationError("Action name cannot be empty.")
    if len(normalized.encode("utf-8")) > MAX_ACTION_NAME_BYTES:
        raise ActionValidationError(
            f"Action name must fit within {MAX_ACTION_NAME_BYTES} UTF-8 bytes."
        )
    return normalized


def action_name_key(name: str) -> str:
    """Return a case-insensitive comparison key for user-facing names."""
    return normalize_action_name(name).casefold()


def slugify_action_name(name: str) -> str:
    """Create a stable filesystem-safe slug from an action name."""
    normalized = normalize_action_name(name)
    ascii_name = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_name).strip("-").lower()
    if not slug:
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
        slug = f"action-{digest}"
    return slug[:64].strip("-") or "action"


def validate_action_code(code: str) -> str:
    """Validate saved Blockly Python against the same broad safety envelope."""
    code_value = str(code or "")
    if not code_value.strip():
        raise ActionValidationError("Action code cannot be empty.")
    if len(code_value.encode("utf-8")) > MAX_ACTION_CODE_BYTES:
        raise ActionValidationError(
            f"Action code exceeds {MAX_ACTION_CODE_BYTES} bytes."
        )

    try:
        tree = ast.parse(code_value, filename="<ninja_action>", mode="exec")
        compile(tree, "<ninja_action>", "exec")
    except SyntaxError as exc:
        raise ActionValidationError(f"Action code has a syntax error: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split(".", 1)[0]
                if module_name not in ALLOWED_ACTION_IMPORTS:
                    raise ActionValidationError(
                        f"Import of module '{module_name}' is not allowed."
                    )
        elif isinstance(node, ast.ImportFrom):
            module_name = (node.module or "").split(".", 1)[0]
            if module_name not in ALLOWED_ACTION_IMPORTS:
                raise ActionValidationError(
                    f"Import of module '{module_name}' is not allowed."
                )

    return code_value


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_repetitions(value: Any) -> int:
    try:
        repetitions = int(value)
    except (TypeError, ValueError):
        repetitions = 1
    return max(1, min(MAX_ACTION_REPETITIONS, repetitions))


def _indent_code_block(code: str) -> str:
    return textwrap.indent(code.rstrip() or "pass", "    ")


class ActionLibrary:
    """Persistent library for complete Blockly actions uploaded from Code IDE."""

    def __init__(self, root: Path | str = ACTION_LIBRARY_PATH):
        self.root = Path(root)

    def list_actions(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if not self.root.exists():
            return actions

        for path in sorted(self.root.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    record = json.load(f)
                if record.get("schema_version") == ACTION_SCHEMA_VERSION:
                    actions.append(record)
            except (OSError, json.JSONDecodeError):
                continue
        return actions

    def list_names(self) -> list[str]:
        return [record["name"] for record in self.list_actions() if record.get("name")]

    def find_action(self, name_or_slug: str) -> dict[str, Any] | None:
        try:
            requested_name_key = action_name_key(name_or_slug)
        except ActionValidationError:
            requested_name_key = ""
        requested_slug = slugify_action_name(name_or_slug)

        for record in self.list_actions():
            record_name = record.get("name", "")
            record_slug = record.get("slug", "")
            if record_slug == requested_slug:
                return record
            try:
                if action_name_key(record_name) == requested_name_key:
                    return record
            except ActionValidationError:
                continue
        return None

    def get_action(self, name_or_slug: str) -> dict[str, Any]:
        record = self.find_action(name_or_slug)
        if not record:
            raise ActionNotFoundError(f"Saved action '{name_or_slug}' was not found.")
        return record

    def ensure_name_available(
        self,
        name: str,
        *,
        native_movement_names: Iterable[str] = (),
        allow_existing_action: bool = False,
    ) -> tuple[str, str]:
        normalized_name = normalize_action_name(name)
        slug = slugify_action_name(normalized_name)
        name_key = action_name_key(normalized_name)

        native_keys = {action_name_key(native_name) for native_name in native_movement_names}
        native_slugs = {slugify_action_name(native_name) for native_name in native_movement_names}
        if name_key in native_keys or slug in native_slugs:
            raise ActionNameConflictError(
                f"Action name '{normalized_name}' conflicts with an existing native movement.",
                conflict_type="native_movement",
                action_name=normalized_name,
                action_slug=slug,
                can_overwrite=False,
            )

        for record in self.list_actions():
            record_name = record.get("name", "")
            record_slug = record.get("slug", "")
            if record_slug == slug or action_name_key(record_name) == name_key:
                if allow_existing_action:
                    return normalized_name, slug
                raise ActionNameConflictError(
                    f"Action name '{normalized_name}' already exists.",
                    conflict_type="saved_action",
                    action_name=record_name or normalized_name,
                    action_slug=record_slug or slug,
                    can_overwrite=True,
                )

        return normalized_name, slug

    def save_action(
        self,
        *,
        name: str,
        code: str,
        workspace_state: Mapping[str, Any] | None = None,
        manifest: Mapping[str, Any] | None = None,
        native_movement_names: Iterable[str] = (),
        overwrite: bool = False,
    ) -> dict[str, Any]:
        normalized_name, slug = self.ensure_name_available(
            name,
            native_movement_names=native_movement_names,
            allow_existing_action=overwrite,
        )
        validated_code = validate_action_code(code)
        if workspace_state is not None and not isinstance(workspace_state, Mapping):
            raise ActionValidationError("Blockly workspace state must be a JSON object.")
        workspace_payload = dict(workspace_state) if workspace_state else None
        timestamp = _utc_timestamp()
        existing_record = self.find_action(normalized_name) if overwrite else None
        if existing_record:
            slug = existing_record.get("slug") or slug
        record = {
            "schema_version": ACTION_SCHEMA_VERSION,
            "name": normalized_name,
            "slug": slug,
            "source": "blockly",
            "manifest": build_execution_manifest(manifest),
            "workspace_state": workspace_payload,
            "code": validated_code,
            "created_at": existing_record.get("created_at", timestamp)
            if existing_record
            else timestamp,
            "updated_at": timestamp,
        }

        self.root.mkdir(parents=True, exist_ok=True)
        target_path = self.root / f"{slug}.json"
        tmp_path = target_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, target_path)
        return {**record, "overwritten": bool(existing_record)}

    def build_replay_code(self, action_chain: Iterable[Mapping[str, Any]]) -> str:
        lines = [
            "# NinjaRobot saved Blockly action replay",
            "import time",
            "from ninja_core import robot",
            "",
        ]

        has_actions = False
        for index, item in enumerate(action_chain):
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            record = self.get_action(name)
            repetitions = _normalize_repetitions(item.get("repetitions", 1))
            loop_var = f"_ninja_action_repeat_{index}"
            lines.append(f"# Saved action: {record['name']}")
            lines.append(f"for {loop_var} in range({repetitions}):")
            lines.append("    check_stop()")
            lines.append(_indent_code_block(record["code"]))
            lines.append("")
            has_actions = True

        if not has_actions:
            raise ActionValidationError("No saved Blockly actions were requested.")

        return "\n".join(lines).rstrip() + "\n"
