#!/usr/bin/env python3
"""
Mission Intent Guard (extended)

Primary checks:
    1) Clarification passes: ≥3 same-date clarification_pass_refs exist and paths resolve.

Lightweight additional checks (non-exhaustive, schema-level):
    2) mission_context block exists with required fields and a min_lines integer.
    3) quorum performed_by is set (explicitly swarmlord for now), and threshold present.
    4) outputs.digest_shape includes BLUF, matrix, diagrams, executive_summary.
    5) LLM per_stage_defaults present for core stages with model and max_tokens.

Usage:
    - Pre-commit: python3 scripts/validators/validate_mission_intents.py <files>
    - CI (changed files only): python3 scripts/validators/validate_mission_intents.py <files>

Notes:
    - This is intentionally lightweight: it validates presence/shape, not semantics.
    - It won’t retroactively enforce historical files unless they’re part of the change set.
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Tuple, Dict, Any

try:
    import yaml  # PyYAML
except Exception as e:
    print("ERROR: PyYAML is required. Please ensure PyYAML is installed.")
    sys.exit(2)


MI_PATTERN = re.compile(r"hfo_mission_intent/.*/mission_intent.*\\.yml$")
DATE_PATTERN = re.compile(r"(20\\d{2}-\\d{2}-\\d{2})")


def is_mission_intent_file(path: str) -> bool:
    if not MI_PATTERN.search(path):
        return False
    base = os.path.basename(path)
    if base == "mission_intent_template.yml":
        return False
    # skip archive folder paths
    if "/archive/" in path or path.endswith("/archive"):
        return False
    return True


def extract_date_from_path(path: str) -> str | None:
    m = DATE_PATTERN.search(path)
    return m.group(1) if m else None


def _validate_mission_context(data: Dict[str, Any], path: str) -> List[str]:
    errs: List[str] = []
    mc = data.get("mission_context")
    if not isinstance(mc, dict):
        errs.append(f"{path}: mission_context block missing or not a mapping")
        return errs
    # Required keys
    required_keys = ["required", "min_lines", "fields"]
    for k in required_keys:
        if k not in mc:
            errs.append(f"{path}: mission_context.{k} missing")
    # min_lines integer
    if "min_lines" in mc and not isinstance(mc.get("min_lines"), int):
        errs.append(f"{path}: mission_context.min_lines must be an integer")
    # fields must include the canonical set
    fields = mc.get("fields", [])
    required_fields = {"overview", "scope", "assumptions", "risks", "evidence_refs"}
    if isinstance(fields, list):
        missing = sorted(list(required_fields - set(fields)))
        if missing:
            errs.append(f"{path}: mission_context.fields missing entries: {', '.join(missing)}")
    else:
        errs.append(f"{path}: mission_context.fields must be a list")
    return errs


def _validate_quorum_and_outputs(data: Dict[str, Any], path: str) -> List[str]:
    errs: List[str] = []
    q = data.get("quorum", {})
    if not isinstance(q, dict):
        errs.append(f"{path}: quorum must be a mapping")
    else:
        if "threshold" not in q:
            errs.append(f"{path}: quorum.threshold missing")
        if q.get("performed_by") is None:
            errs.append(f"{path}: quorum.performed_by not set (expected 'swarmlord' for now)")

    out = data.get("outputs", {})
    if not isinstance(out, dict):
        errs.append(f"{path}: outputs must be a mapping")
    else:
        ds = out.get("digest_shape", [])
        expected = {"BLUF", "matrix", "diagrams", "executive_summary"}
        if not isinstance(ds, list) or not expected.issubset(set(ds)):
            errs.append(
                f"{path}: outputs.digest_shape must include BLUF, matrix, diagrams, executive_summary"
            )
    return errs


def _validate_llm_defaults(data: Dict[str, Any], path: str) -> List[str]:
    errs: List[str] = []
    llm = data.get("llm", {})
    if not isinstance(llm, dict):
        errs.append(f"{path}: llm must be a mapping")
        return errs
    psd = llm.get("per_stage_defaults")
    if not isinstance(psd, dict):
        errs.append(f"{path}: llm.per_stage_defaults missing or not a mapping")
        return errs
    stages = ["orchestrate", "perceive", "react", "engage", "yield", "digest"]
    for st in stages:
        cfg = psd.get(st)
        if not isinstance(cfg, dict):
            errs.append(f"{path}: llm.per_stage_defaults.{st} missing or not a mapping")
            continue
        if "model" not in cfg or "max_tokens" not in cfg:
            errs.append(f"{path}: llm.per_stage_defaults.{st} requires model and max_tokens")
    return errs


def validate_intent(path: str) -> Tuple[bool, List[str]]:
    """Validate a single mission intent file. Returns (ok, errors)."""
    errors: List[str] = []
    if not is_mission_intent_file(path):
        return True, []

    if not os.path.exists(path):
        return True, []  # ignore deleted/missing in diff contexts

    date = extract_date_from_path(path)
    if not date:
        errors.append(f"{path}: could not extract date (expected YYYY-MM-DD in name or path)")
        return False, errors

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        errors.append(f"{path}: YAML load failed: {e}")
        return False, errors

    refs = data.get("clarification_pass_refs")
    if not isinstance(refs, list) or len(refs) < 3:
        errors.append(
            f"{path}: requires clarification_pass_refs with ≥3 entries for same date ({date})"
        )
        return False, errors

    # verify referenced files exist and dates match
    good = 0
    for ref in refs:
        if not isinstance(ref, str):
            errors.append(f"{path}: invalid ref (not a string): {ref}")
            continue
        # require same-date folder or filename
        ref_date = extract_date_from_path(ref)
        if ref_date != date:
            errors.append(
                f"{path}: ref date mismatch: {ref} (expected {date}, got {ref_date})"
            )
            continue
        if not os.path.exists(ref):
            errors.append(f"{path}: referenced clarification not found: {ref}")
            continue
        good += 1

    if good < 3:
        errors.append(
            f"{path}: only {good} valid clarification passes found for {date}; need at least 3"
        )
        return False, errors

    # Additional lightweight schema checks (non-fatal if older schema):
    extra_errs: List[str] = []
    try:
        extra_errs.extend(_validate_mission_context(data, path))
    except Exception as e:
        extra_errs.append(f"{path}: mission_context validation error: {e}")
    try:
        extra_errs.extend(_validate_quorum_and_outputs(data, path))
    except Exception as e:
        extra_errs.append(f"{path}: quorum/outputs validation error: {e}")
    try:
        extra_errs.extend(_validate_llm_defaults(data, path))
    except Exception as e:
        extra_errs.append(f"{path}: llm defaults validation error: {e}")

    if extra_errs:
        return False, extra_errs

    return True, []


def main(argv: List[str]) -> int:
    # Filter to mission intent files among provided args
    files = [p for p in argv if is_mission_intent_file(p)]
    if not files:
        # No mission intent files in this change set; nothing to do
        return 0

    all_ok = True
    all_errors: List[str] = []
    for path in files:
        ok, errs = validate_intent(path)
        if not ok:
            all_ok = False
            all_errors.extend(errs)

    if not all_ok:
        print("Mission Intent Guard: FAIL\n")
        for e in all_errors:
            print(f"- {e}")
        print(
            "\nRemediation: Create at least three same-date clarification passes under hfo_mission_intent/YYYY-MM-DD/ "
            "and reference them in clarification_pass_refs before committing the mission intent."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
