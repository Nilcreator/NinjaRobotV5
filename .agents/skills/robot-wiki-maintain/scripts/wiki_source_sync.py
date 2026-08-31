#!/usr/bin/env python3
"""Check or synchronize project-owned documents mirrored into the local wiki."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tomllib


DEFAULT_MANIFEST = Path("Wiki/NinjaRobotPi0_Wiki/project-sources.toml")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_path(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes its allowed root: {relative}") from exc
    return candidate


def load_mappings(project_root: Path, manifest_relative: Path) -> list[dict[str, str]]:
    manifest_path = contained_path(project_root, str(manifest_relative), "manifest")
    with manifest_path.open("rb") as handle:
        data = tomllib.load(handle)
    mappings = data.get("sources")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError(f"No [[sources]] mappings found in {manifest_path}")

    required = {"id", "project_path", "wiki_path"}
    seen_ids: set[str] = set()
    for mapping in mappings:
        if not isinstance(mapping, dict) or not required.issubset(mapping):
            raise ValueError(f"Invalid source mapping in {manifest_path}: {mapping!r}")
        source_id = str(mapping["id"])
        if source_id in seen_ids:
            raise ValueError(f"Duplicate source id in {manifest_path}: {source_id}")
        seen_ids.add(source_id)
    return mappings


def atomic_copy(source: Path, target: Path) -> None:
    payload = source.read_bytes()
    mode = target.stat().st_mode if target.exists() else source.stat().st_mode
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="report drift without writing (default)")
    action.add_argument("--sync", action="store_true", help="copy reviewed project docs to raw snapshots")
    parser.add_argument("--only", action="append", default=[], metavar="SOURCE_ID")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = (
        args.project_root.resolve()
        if args.project_root
        else Path(__file__).resolve().parents[4]
    )

    try:
        mappings = load_mappings(project_root, args.manifest)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR {exc}")
        return 2

    requested = set(args.only)
    known = {str(item["id"]) for item in mappings}
    unknown = requested - known
    if unknown:
        print(f"ERROR unknown source id(s): {', '.join(sorted(unknown))}")
        return 2

    wiki_root = contained_path(project_root, "Wiki/NinjaRobotPi0_Wiki", "wiki root")
    results: list[dict[str, str]] = []
    failures = False
    drift = False

    for mapping in mappings:
        source_id = str(mapping["id"])
        if requested and source_id not in requested:
            continue
        try:
            project_path = contained_path(project_root, str(mapping["project_path"]), "project path")
            wiki_path = contained_path(wiki_root, str(mapping["wiki_path"]), "wiki path")
            if not project_path.is_file():
                raise FileNotFoundError(f"project document is missing: {project_path}")
            if not wiki_path.is_file():
                raise FileNotFoundError(f"wiki snapshot is missing: {wiki_path}")
            project_hash = file_hash(project_path)
            wiki_hash = file_hash(wiki_path)
            status = "match" if project_hash == wiki_hash else "drift"
            if status == "drift":
                drift = True
                if args.sync:
                    atomic_copy(project_path, wiki_path)
                    wiki_hash = file_hash(wiki_path)
                    status = "synced"
            results.append(
                {
                    "id": source_id,
                    "status": status,
                    "project_path": str(project_path.relative_to(project_root)),
                    "wiki_path": str(wiki_path.relative_to(wiki_root)),
                    "project_sha256": project_hash,
                    "wiki_sha256": wiki_hash,
                }
            )
        except (OSError, ValueError) as exc:
            failures = True
            results.append({"id": source_id, "status": "error", "message": str(exc)})

    if args.json_output:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for item in results:
            if item["status"] == "error":
                print(f"ERROR {item['id']}: {item['message']}")
            else:
                print(
                    f"{item['status'].upper():6} {item['id']} "
                    f"{item['project_path']} -> {item['wiki_path']}"
                )

    if failures:
        return 2
    if drift and not args.sync:
        print("Project/wiki source drift found. Review both sides before using --sync.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
