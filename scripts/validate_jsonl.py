#!/usr/bin/env python3
"""
Validate JSON and JSONL files in the repository.

Rules (low-friction):
- .json: must parse as valid JSON
- .jsonl: each non-empty line must parse as a valid JSON object or array
- Special case: hfo_blackboard/*.jsonl — lines must parse as JSON objects; if they
  include mission_id and phase, ensure evidence_refs is an array when present.

Exit non-zero on first failure; print a concise error summary.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # Skip common bulky directories
        parts = {p.lower() for p in path.parts}
        if ".git" in parts or "node_modules" in parts or ".venv" in parts:
            continue
        if path.suffix.lower() in {".json", ".jsonl"}:
            yield path


def validate_json(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        raise SystemExit(f"JSON invalid: {path}\n  error: {e}")


def validate_jsonl(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except Exception as e:
                    raise SystemExit(f"JSONL invalid: {path}:{i}\n  line: {s[:160]}\n  error: {e}")
                # Blackboard lines should be JSON objects
                if "hfo_blackboard" in str(path):
                    if not isinstance(obj, dict):
                        raise SystemExit(f"Blackboard JSONL must be object: {path}:{i}")
                    # Soft validation: if mission_id and phase exist, evidence_refs should be a list when present
                    if "mission_id" in obj and "phase" in obj and "evidence_refs" in obj:
                        if not isinstance(obj["evidence_refs"], list):
                            raise SystemExit(
                                f"Blackboard evidence_refs must be an array: {path}:{i}"
                            )
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"Error reading JSONL: {path}\n  error: {e}")


def main() -> int:
    failures = 0
    for path in iter_files(REPO_ROOT):
        if path.suffix.lower() == ".json":
            try:
                validate_json(path)
            except SystemExit as e:
                print(e, file=sys.stderr)
                failures += 1
        elif path.suffix.lower() == ".jsonl":
            try:
                validate_jsonl(path)
            except SystemExit as e:
                print(e, file=sys.stderr)
                failures += 1
    if failures:
        print(f"Validation failed: {failures} file(s) with errors.", file=sys.stderr)
        return 1
    print("JSON/JSONL validation PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
