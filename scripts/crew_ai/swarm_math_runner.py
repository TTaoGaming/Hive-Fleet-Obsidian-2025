#!/usr/bin/env python3
"""
Swarm math runner: executes lane-parallel math tasks, writes per-lane yield artifacts,
verifies each lane, retries failures per mission policy, and generates a final digest MD.

Outputs are written to hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/ ...

Default behavior is deterministic (no LLM) so you can validate the end-to-end pipeline
without external dependencies. Pass --use-llm to benchmark LLM answers instead.

Usage examples:
  # Deterministic demo (10 lanes from intent)
  python scripts/crew_ai/swarm_math_runner.py \
    --intent hfo_mission_intent/2025-10-30/mission_intent_parallel_10lanes_2025-10-30.v1.yml

  # LLM mode with allowlisted model hint
  OPENROUTER_MODEL_HINT=openai/gpt-oss-120b \
  python scripts/crew_ai/swarm_math_runner.py --use-llm \
    --intent hfo_mission_intent/2025-10-30/mission_intent_parallel_10lanes_2025-10-30.v1.yml
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from dotenv import load_dotenv

# Local imports (works both as module and script)
try:
    from .llm_client import call_openrouter
except Exception:  # pragma: no cover
    from llm_client import call_openrouter  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "hfo_crew_ai_swarm_results"
ISO = "%Y-%m-%dT%H:%M:%SZ"

# Small set of math problems with known integer answers
PROBLEMS: List[Tuple[str, int]] = [
    ("12 + 7 = ?", 19),
    ("8 * 9 = ?", 72),
    ("144 / 12 = ?", 12),
    ("(3 + 5) * 2 = ?", 16),
    ("2^5 = ?", 32),
    ("100 - 77 = ?", 23),
    ("15 * 0 = ?", 0),
    ("7 * 13 = ?", 91),
    ("81^(1/2) = ?", 9),
    ("(10 + 2) / 4 = ? (integer)", 3),
]


def now_z() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


@dataclass
class LanePolicy:
    auto_retries_max: int = 2
    shrink_scope_on_retry: bool = True


@dataclass
class VerifyCfg:
    accuracy_threshold: float = 0.8  # fraction correct required


@dataclass
class RunCfg:
    mission_id: str
    lane_names: List[str]
    lane_policy: LanePolicy
    verify_cfg: VerifyCfg
    use_llm: bool
    problems_per_lane: int


@dataclass
class LaneAttemptResult:
    lane: str
    attempt: int
    total: int
    correct: int
    accuracy: float
    passed: bool
    details: List[Dict[str, object]]
    model: Optional[str]


def extract_int(s: str) -> Optional[int]:
    m = re.search(r"-?\d+", s or "")
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def ask_llm(q: str, model_hint: Optional[str]) -> Tuple[bool, Optional[int], str, Optional[str]]:
    res = call_openrouter(
        f"Answer with just the integer. {q}",
        model_hint=model_hint,
        max_tokens=12,
        temperature=0.0,
    )
    ok = bool(res.get("ok"))
    content = res.get("content") or ""
    got = extract_int(content) if ok else None
    return ok, got, (res.get("model") or ""), res.get("error")


def solve_locally(q: str, expected: int) -> Tuple[bool, int, str, Optional[str]]:
    # Deterministic: return expected directly as if computed.
    return True, expected, "local/deterministic", None


def run_lane_once(cfg: RunCfg, lane: str, attempt: int, out_dir: Path) -> LaneAttemptResult:
    model_hint = os.environ.get("OPENROUTER_MODEL_HINT")
    # Choose subset for this attempt (shrink if retries)
    subset = PROBLEMS[: cfg.problems_per_lane]

    details: List[Dict[str, object]] = []
    correct = 0
    for q, ans in subset:
        if cfg.use_llm:
            ok, got, model, err = ask_llm(q, model_hint)
        else:
            ok, got, model, err = solve_locally(q, ans)
        is_correct = (got == ans)
        correct += 1 if is_correct else 0
        details.append({
            "q": q,
            "expected": ans,
            "got": got,
            "ok": ok,
            "correct": is_correct,
            "error": err,
        })
    total = len(subset)
    accuracy = (correct / total) if total else 0.0
    passed = accuracy >= cfg.verify_cfg.accuracy_threshold

    # Write yield artifact (JSON) and yield.md
    lane_dir = out_dir / lane / f"attempt_{attempt}"
    lane_dir.mkdir(parents=True, exist_ok=True)
    yield_json = {
        "mission_id": cfg.mission_id,
        "lane": lane,
        "attempt": attempt,
        "timestamp": now_z(),
        "use_llm": cfg.use_llm,
        "problems": total,
        "correct": correct,
        "accuracy": accuracy,
        "verify_threshold": cfg.verify_cfg.accuracy_threshold,
        "details": details,
    }
    (lane_dir / "yield.json").write_text(json.dumps(yield_json, ensure_ascii=False, indent=2), encoding="utf-8")

    yield_md = [
        f"# Lane {lane} — Attempt {attempt}",
        "",
        f"- Mission: {cfg.mission_id}",
        f"- Timestamp: {now_z()}",
        f"- Mode: {'LLM' if cfg.use_llm else 'Deterministic'}",
        f"- Problems: {total}",
        f"- Correct: {correct}",
        f"- Accuracy: {accuracy:.2%} (threshold {cfg.verify_cfg.accuracy_threshold:.0%})",
        "",
        "## Cases",
    ]
    for d in details:
        yield_md.append(f"- {d['q']} → got={d['got']} expected={d['expected']} ok={d['ok']} correct={d['correct']}")
    (lane_dir / "yield.md").write_text("\n".join(yield_md), encoding="utf-8")

    # Write verification MD
    verdict = "PASS" if passed else "FAIL"
    verify_md = [
        f"# Verify — Lane {lane} Attempt {attempt}: {verdict}",
        "",
        f"- Accuracy: {accuracy:.2%}",
        f"- Threshold: {cfg.verify_cfg.accuracy_threshold:.0%}",
        f"- Problems: {total}",
        f"- Correct: {correct}",
    ]
    (lane_dir / "verify.md").write_text("\n".join(verify_md), encoding="utf-8")

    model_used = None
    if cfg.use_llm and details:
        # If at least one ok, report model of the first ok response
        for d in details:
            # No model stored in details; use model_hint for now
            model_used = os.environ.get("OPENROUTER_MODEL_HINT")
            break

    return LaneAttemptResult(
        lane=lane,
        attempt=attempt,
        total=total,
        correct=correct,
        accuracy=accuracy,
        passed=passed,
        details=details,
        model=model_used,
    )


def generate_digest(cfg: RunCfg, out_dir: Path, best_results: Dict[str, LaneAttemptResult]) -> Path:
    date_str = out_dir.parents[0].name  # YYYY-MM-DD
    ts = out_dir.name.replace("run-", "")

    # BLUF
    passed = [r for r in best_results.values() if r.passed]
    failed = [r for r in best_results.values() if not r.passed]

    # Matrix (lane vs attempt/accuracy)
    matrix_lines = ["| Lane | Attempt | Accuracy | Verdict |", "|---|---:|---:|---|"]
    for lane in sorted(best_results.keys()):
        r = best_results[lane]
        matrix_lines.append(f"| {lane} | {r.attempt} | {r.accuracy:.2%} | {'PASS' if r.passed else 'FAIL'} |")

    # Mermaid diagram (safe)
    mermaid = [
        "```mermaid",
        "graph LR",
        "  A[Start] --> B[Per-lane Work]",
        "  B --> C[Verify]",
        "  C --> D[Pass]",
        "  C --> E[Fail]",
        "  D --> F[Digest]",
        "```",
    ]

    md = [
        f"# Swarmlord Digest — {cfg.mission_id}",
        "",
        f"- Date: {date_str}",
        f"- Run TS: {ts}",
        f"- Lanes: {len(cfg.lane_names)}",
        f"- Mode: {'LLM' if cfg.use_llm else 'Deterministic'}",
        f"- Verify threshold: {cfg.verify_cfg.accuracy_threshold:.0%}",
        f"- Passed: {len(passed)}  Failed: {len(failed)}",
        "",
        "## Matrix",
        *matrix_lines,
        "",
        "## Diagram",
        *mermaid,
        "",
        "## Notes",
        "- Each lane wrote yield.json, yield.md, and verify.md under its attempt folder.",
        "- Failing lanes retried according to policy; attempt shows final attempt #.",
        "- Inspect details in per-lane yield.md for case-level outcomes.",
    ]
    digest_path = out_dir / "swarmlord_digest.md"
    digest_path.write_text("\n".join(md), encoding="utf-8")
    return digest_path


def load_intent(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def plan_run_dirs() -> Tuple[Path, Path]:
    date_dir = RESULTS_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    ts = f"run-{int(time.time()*1000)}"
    run_dir = date_dir / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return date_dir, run_dir


def main() -> None:
    ap = argparse.ArgumentParser(description="Lane-parallel math runner with verification and digest")
    ap.add_argument("--intent", type=str, default=str(ROOT / "hfo_mission_intent/2025-10-30/mission_intent_parallel_10lanes_2025-10-30.v1.yml"))
    ap.add_argument("--use-llm", action="store_true", help="Use LLM to answer questions (cost)")
    ap.add_argument("--problems", type=int, default=10, help="Problems per lane (max 10)")
    ap.add_argument("--threshold", type=float, default=0.8, help="Accuracy threshold for PASS")
    args = ap.parse_args()

    load_dotenv(dotenv_path=ROOT / ".env", override=False)

    intent = load_intent(Path(args.intent))
    mission_id = str(intent.get("mission_id", f"mi_swarm_{now_z()}"))

    lanes = intent.get("lanes", {}) or {}
    count = int(lanes.get("count", 10))
    names = lanes.get("names") or [f"lane_{i+1}" for i in range(count)]
    names = [str(n) for n in names][:count]

    policy = lanes.get("policy", {}) or {}
    lane_policy = LanePolicy(
        auto_retries_max=int(policy.get("auto_retries_max", 2)),
        shrink_scope_on_retry=bool(policy.get("shrink_scope_on_retry", True)),
    )

    verify_cfg = VerifyCfg(accuracy_threshold=float(args.threshold))
    cfg = RunCfg(
        mission_id=mission_id,
        lane_names=names,
        lane_policy=lane_policy,
        verify_cfg=verify_cfg,
        use_llm=bool(args.use_llm),
        problems_per_lane=max(1, min(10, int(args.problems))),
    )

    _, run_dir = plan_run_dirs()

    def lane_flow(lane: str) -> LaneAttemptResult:
        problems = cfg.problems_per_lane
        for attempt in range(1, cfg.lane_policy.auto_retries_max + 2):  # initial + retries
            attempt_cfg = RunCfg(
                mission_id=cfg.mission_id,
                lane_names=[lane],
                lane_policy=cfg.lane_policy,
                verify_cfg=cfg.verify_cfg,
                use_llm=cfg.use_llm,
                problems_per_lane=problems,
            )
            r = run_lane_once(attempt_cfg, lane, attempt, run_dir)
            if r.passed:
                return r
            # Prepare next attempt
            if attempt <= cfg.lane_policy.auto_retries_max:
                if cfg.lane_policy.shrink_scope_on_retry and problems > 1:
                    problems = max(1, problems // 2)
            else:
                return r  # final failure
        return r  # unreachable

    results: Dict[str, LaneAttemptResult] = {}
    with ThreadPoolExecutor(max_workers=len(cfg.lane_names)) as ex:
        futs = {ex.submit(lane_flow, lane): lane for lane in cfg.lane_names}
        for fut in as_completed(futs):
            r = fut.result()
            results[r.lane] = r

    digest_path = generate_digest(cfg, run_dir, results)

    # Summary print
    passed = sum(1 for r in results.values() if r.passed)
    failed = len(results) - passed
    print("Run complete")
    print(f"Results dir: {run_dir.relative_to(ROOT)}")
    print(f"Digest: {digest_path.relative_to(ROOT)}")
    print(f"Passed: {passed}  Failed: {failed}")


if __name__ == "__main__":
    main()
