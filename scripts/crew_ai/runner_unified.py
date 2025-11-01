#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Unified HFO PREY runner: thin CLI that delegates to the orchestrator
ROOT = Path(__file__).resolve().parents[2]
# Ensure repository root is on sys.path so `scripts.*` absolute imports work when run as a script
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.crew_ai.orchestrator import run as run_orchestrator  # type: ignore  # noqa: E402

DEFAULT_INTENT = ROOT / "hfo_mission_intent/2025-10-31/mission_intent_2025-10-31.v1.yml"


def run(intent_path: Path) -> int:
    """Run the unified PREY orchestrator with the provided mission intent path."""
    return run_orchestrator(intent_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="HFO PREY runner — unified lanes with adapters")
    ap.add_argument("--intent", type=str, default=str(DEFAULT_INTENT), help="Path to mission intent YAML")
    args = ap.parse_args()
    intent_path = Path(args.intent)
    if not intent_path.exists():
        print(f"Intent not found: {intent_path}", file=sys.stderr)
        sys.exit(2)
    code = run(intent_path)
    sys.exit(code)


if __name__ == "__main__":
    main()
