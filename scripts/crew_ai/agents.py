#!/usr/bin/env python3
"""
Minimal multi-agent crew for the pilot lanes.

Roles implemented:
- PlannerAgent: creates a short plan; optional small LLM assist
- PerceiverAgent: collects a tiny perception snapshot
- ImplementerAgent: performs a stubbed action
- AssimilatorAgent: synthesizes a short digest of lane outputs
- ImmunizerAgent: checks for basic invariants (evidence present)
- DisruptorAgent: runs a tiny adversarial probe (e.g., expects a span/receipt hint)

Contracts:
- Each agent exposes run(ctx: dict) -> dict with fields:
  {
    "ok": bool,
    "summary": str,
    "data": dict (optional),
    "llm_used": bool (optional),
  }
- The ctx will include: mission (dict), lane (str), phase (str), and arbitrary prior results.

Note: Keep token usage minimal; defer to llm_client with small limits when used.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
import os

# Optional LLM usage for Planner
try:
    from .llm_client import call_openrouter as _llm
except Exception:  # pragma: no cover - fallback for direct script runs
    from llm_client import call_openrouter as _llm  # type: ignore


@dataclass
class AgentResult:
    ok: bool
    summary: str
    data: Dict[str, Any] | None = None
    llm_used: bool = False


class BaseAgent:
    name: str = "agent"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError


class BridgerAgent(BaseAgent):
    name = "bridger"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        mission = ctx.get("mission", {})
        mission_id = mission.get("mission_id", "mi")
        hint = os.environ.get("OPENROUTER_MODEL_HINT")
        # Try a tiny LLM restatement if key is present; else a local stub
        if os.environ.get("OPENROUTER_API_KEY"):
            prompt = (
                "Restate the mission and safety posture in one short sentence. "
                f"mission_id={mission_id}"
            )
            res = _llm(prompt, model_hint=hint, max_tokens=48, temperature=0.1)
            llm_used = True
            if res.get("ok"):
                content = (res.get("content") or "").strip().replace("\n", " ")[:160]
                return AgentResult(True, f"Bridge: {content}", {"model": res.get("model")}, llm_used)
            return AgentResult(False, f"Bridge failed (LLM {res.get('error')})", {"error": res.get("error")}, llm_used)
        # Fallback plan
        return AgentResult(True, "Bridge: run PREY, log receipts, verify quorum", {"llm": False}, False)


class ObserverAgent(BaseAgent):
    name = "observer"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        lane = ctx.get("lane")
        mission = ctx.get("mission", {})
        tripwires = mission.get("safety", {}).get("tripwires", [])
        return AgentResult(True, f"Observe lane={lane} with tripwires={tripwires}", {"tripwires": tripwires})


class ShaperAgent(BaseAgent):
    name = "shaper"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        lane = ctx.get("lane")
        return AgentResult(True, f"Shaped/Engaged planned actions for {lane}")


class AssimilatorAgent(BaseAgent):
    name = "assimilator"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        lane = ctx.get("lane")
        collected = ctx.get("collected", {})
        return AgentResult(True, f"Assimilated outputs for {lane}", {"keys": list(collected.keys())})


class ImmunizerAgent(BaseAgent):
    name = "immunizer"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        # Basic invariant: prior phases produced at least one evidence item
        evidence = ctx.get("evidence", [])
        ok = len(evidence) >= 1
        return AgentResult(ok, "Immunizer check: evidence present" if ok else "Immunizer failure: no evidence")


class DisruptorAgent(BaseAgent):
    name = "disruptor"

    def run(self, ctx: Dict[str, Any]) -> AgentResult:
        # Minimal probe: require a PREY phase to have run
        flags = ctx.get("flags", {})
        ok = bool(flags.get("phases_seen"))
        return AgentResult(ok, "Disruptor probe: phases seen" if ok else "Disruptor failure: no phases seen")


# Simple registry
REGISTRY: Dict[str, BaseAgent] = {
    # OBSIDIAN canonical roles
    "observer": ObserverAgent(),
    "bridger": BridgerAgent(),
    "shaper": ShaperAgent(),
    "assimilator": AssimilatorAgent(),
    "immunizer": ImmunizerAgent(),
    "disruptor": DisruptorAgent(),
}
