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
OTEL_DIR = ROOT / "temp/otel"
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


def write_span(trace_id: str, span: Dict[str, object]) -> None:
    OTEL_DIR.mkdir(parents=True, exist_ok=True)
    out = OTEL_DIR / f"{trace_id}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")


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


def ask_llm(q: str, model_hint: Optional[str]) -> Tuple[bool, Optional[int], str, Optional[str], str]:
    """
    Request strict JSON to improve parseability. Fallback to integer extraction.
    Returns: ok, got_int, model, error, raw_content
    """
    prompt = (
        "Return ONLY a JSON object with the schema {\"answer\": <integer>} and nothing else. "
        f"Question: {q}"
    )
    # Model-aware safe params (based on characterization sweep)
    hint_lc = (model_hint or "").lower()
    if (not model_hint) or ("oss-120b" in hint_lc):
        max_toks = 80  # ≥64 fixes empty-content for gpt-oss-120b
    elif "oss-20b" in hint_lc:
        max_toks = 96  # be generous; this model showed empties at low budgets
    else:
        max_toks = 32  # other models were fine with small budgets in probes

    def do_call(p: str):
        return call_openrouter(
            p,
            model_hint=model_hint,
            max_tokens=max_toks,
            temperature=0.0,
            response_format_type="text",
        )

    res = do_call(prompt)
    ok = bool(res.get("ok"))
    content = (res.get("content") or "").strip()
    got: Optional[int] = None
    if ok and content:
        # Try strict JSON first
        try:
            obj = json.loads(content)
            if isinstance(obj, dict) and "answer" in obj:
                if isinstance(obj["answer"], int):
                    got = obj["answer"]
                else:
                    # try to coerce if string number
                    try:
                        got = int(str(obj["answer"]))
                    except Exception:
                        got = None
            else:
                got = extract_int(content)
        except Exception:
            got = extract_int(content)
    # Fallback attempts if no parseable content
    if (not content or got is None) and ok:
        # Simpler instruction
        fallback1 = f"Answer with just the integer. Question: {q}"
        res2 = do_call(fallback1)
        c2 = (res2.get("content") or "").strip()
        if c2:
            try:
                got = extract_int(c2)
                content = c2
                ok = bool(res2.get("ok"))
            except Exception:
                pass

    if (not content or got is None) and ok:
        fallback2 = f"Only output a single integer on one line: {q}"
        res3 = do_call(fallback2)
        c3 = (res3.get("content") or "").strip()
        if c3:
            try:
                got = extract_int(c3)
                content = c3
                ok = bool(res3.get("ok"))
            except Exception:
                pass

    # One last retry-on-empty for OSS models with expanded token budget
    if (not content or got is None) and ((not model_hint) or ("oss" in hint_lc)):
        # Increase token budget further as a final attempt
        def do_call_big(p: str):
            return call_openrouter(
                p,
                model_hint=model_hint,
                max_tokens=max(max_toks, 128),
                temperature=0.0,
                response_format_type="text",
            )
        res4 = do_call_big(prompt)
        c4 = (res4.get("content") or "").strip()
        if c4:
            try:
                # Try JSON first, then integer extraction
                try:
                    obj = json.loads(c4)
                    if isinstance(obj, dict) and "answer" in obj:
                        val = obj["answer"]
                        got = int(val) if isinstance(val, (int, str)) else None
                    else:
                        got = extract_int(c4)
                except Exception:
                    got = extract_int(c4)
                content = c4
                ok = bool(res4.get("ok"))
            except Exception:
                pass

    return ok, got, (res.get("model") or ""), res.get("error"), content


def solve_locally(q: str, expected: int) -> Tuple[bool, int, str, Optional[str]]:
    # Deterministic: return expected directly as if computed.
    return True, expected, "local/deterministic", None


def run_lane_once(cfg: RunCfg, lane: str, attempt: int, out_dir: Path, trace_id: Optional[str]) -> LaneAttemptResult:
    model_hint = os.environ.get("OPENROUTER_MODEL_HINT")
    # Choose subset for this attempt (shrink if retries)
    subset = PROBLEMS[: cfg.problems_per_lane]

    details: List[Dict[str, object]] = []
    correct = 0
    start_ts = now_z()
    lane_latency_ms_total = 0
    for q, ans in subset:
        if cfg.use_llm:
            t0 = time.time()
            ok, got, model, err, raw = ask_llm(q, model_hint)
            lane_latency_ms_total += int((time.time() - t0) * 1000)
        else:
            ok, got, model, err = solve_locally(q, ans)
            raw = str(got)
            lane_latency_ms_total += 0
        is_correct = (got == ans)
        correct += 1 if is_correct else 0
        details.append({
            "q": q,
            "expected": ans,
            "got": got,
            "ok": ok,
            "correct": is_correct,
            "error": err,
            "raw": raw if cfg.use_llm else None,
            "latency_ms": None if not cfg.use_llm else lane_latency_ms_total,
            "model_hint": model_hint if cfg.use_llm else None,
        })
    total = len(subset)
    accuracy = (correct / total) if total else 0.0
    passed = accuracy >= cfg.verify_cfg.accuracy_threshold
    end_ts = now_z()

    # Emit one analyzer-compatible span per lane attempt
    if trace_id:
        write_span(trace_id, {
            "trace_id": trace_id,
            "span_id": f"{lane}-engage-llm-{int(time.time()*1000)}",
            "name": f"{lane}:engage_llm",
            "start_time": start_ts,
            "end_time": end_ts,
            "attributes": {
                "lane": lane,
                "mission_id": cfg.mission_id,
                "ok": True,
                "model": (model_hint or "openai/gpt-oss-120b") if cfg.use_llm else "deterministic",
                "latency_ms": lane_latency_ms_total if cfg.use_llm else 0,
            },
        })

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
    trace_id = f"trace-swarm_math-{int(time.time()*1000)}"

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
            r = run_lane_once(attempt_cfg, lane, attempt, run_dir, trace_id)
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
    print("Spans:", f"temp/otel/{trace_id}.jsonl")


if __name__ == "__main__":
    main()
