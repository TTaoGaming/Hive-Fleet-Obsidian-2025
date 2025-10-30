#!/usr/bin/env python3
from __future__ import annotations
"""
Custom 2x2 animated GIF for PettingZoo MPE simple_tag_v3 with per-cell policy specs.
- Each cell (A,B,C,D) accepts: pred spec, prey spec, pred/prey kwargs JSON, optional force-prey-near-wall.
- Policy specs: random | heuristic | custom:module:Class (same as pz_eval_simple_tag_v3.py)
- Writes: hfo_petting_zoo_results/<DATE>/simple_tag_v3_custom_matrix_<TS>_seed<seed>_eps<episodes>.gif
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

# Ensure repo root on sys.path so 'scripts.*' imports resolve
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from mpe2 import simple_tag_v3  # type: ignore
except Exception:  # pragma: no cover
    from pettingzoo.mpe import simple_tag_v3  # type: ignore

# Reuse evaluator policies
from scripts.pz_eval_simple_tag_v3 import parse_policy  # type: ignore


def _prey_near_wall(raw_env, thr: float) -> bool:
    w = raw_env.world
    prey = [a for a in w.agents if not getattr(a, 'adversary', False)][0]
    pos = prey.state.p_pos
    return (abs(pos[0]) >= thr) or (abs(pos[1]) >= thr)


def _maybe_force_prey_near_wall_reset(env, seed0: int, thr: float, max_attempts: int) -> None:
    env.reset(seed=seed0)
    if _prey_near_wall(env.unwrapped, thr):
        return
    for k in range(1, max_attempts + 1):
        env.reset(seed=seed0 + k)
        if _prey_near_wall(env.unwrapped, thr):
            return


def _label_from_specs(pred: str, prey: str) -> str:
    def tag(s: str, is_pred: bool) -> str:
        s = (s or '').strip()
        if s in ('heuristic', 'h', 'heur'):
            return 'H'
        if s in ('random', 'r', 'rand'):
            return 'R'
        if s.startswith('custom:'):
            if 'pf_pursuit:PFPursuit' in s and is_pred:
                return 'PF'
            if 'stationary:Stationary' in s and not is_pred:
                return 'Static'
            return 'Cust'
        return 'Cust'
    return f"{tag(pred, True)} vs {tag(prey, False)}"


def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    ax, ay = float(d[0]), float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0
        return out
    out[1] = max(0.0, -ax)
    out[2] = max(0.0, ax)
    out[3] = max(0.0, -ay)
    out[4] = max(0.0, ay)
    mx = out[1:5].max() or 1.0
    out[1:5] = out[1:5] / mx
    return out


def overlay_header(img: Image.Image, text: str, subtext: str | None = None) -> Image.Image:
    draw = ImageDraw.Draw(img, "RGBA")
    pad = 4
    box_w = max(80, len(text) * 10)
    box_h = 22 if subtext is None else 38
    draw.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0, 140))
    draw.text((pad, 2), text, fill=(255, 255, 255, 255))
    if subtext:
        draw.text((pad, 18), subtext, fill=(200, 200, 200, 255))
    return img


def tile2x2(a: Image.Image, b: Image.Image, c: Image.Image, d: Image.Image,
            labels: Tuple[str, str, str, str], subtexts: Tuple[str, str, str, str]) -> Image.Image:
    w, h = a.size
    canvas = Image.new("RGB", (w * 2, h * 2), (0, 0, 0))
    a = overlay_header(a.copy(), labels[0], subtexts[0])
    b = overlay_header(b.copy(), labels[1], subtexts[1])
    c = overlay_header(c.copy(), labels[2], subtexts[2])
    d = overlay_header(d.copy(), labels[3], subtexts[3])
    canvas.paste(a, (0, 0))
    canvas.paste(b, (w, 0))
    canvas.paste(c, (0, h))
    canvas.paste(d, (w, h))
    return canvas


def run_episode_frames_for_cell(cell_cfg: dict, seed: int, max_cycles: int, baseline: str,
                                force_prey_near_wall: bool, thr: float, force_max: int) -> List[Image.Image]:
    env = simple_tag_v3.env(continuous_actions=True, render_mode="rgb_array")
    # Build policies once
    pred_policy = parse_policy(cell_cfg['pred'], role='pred', baseline=baseline, extra_kwargs=cell_cfg.get('pred_kwargs'))
    prey_policy = parse_policy(cell_cfg['prey'], role='prey', baseline=baseline, extra_kwargs=cell_cfg.get('prey_kwargs'))

    if force_prey_near_wall:
        _maybe_force_prey_near_wall_reset(env, seed0=seed, thr=thr, max_attempts=force_max)
    else:
        env.reset(seed=seed)

    n_agents = len(env.possible_agents)
    frames: List[Image.Image] = []

    step_idx = 0
    cycle = 0
    for agent in env.agent_iter():
        obs, reward, terminated, truncated, info = env.last()  # noqa: F841
        if terminated or truncated:
            env.step(None)
        else:
            # Select per current agent
            raw = env.unwrapped
            aobj = next(a for a in raw.world.agents if getattr(a, 'name', None) == agent)
            is_pred = getattr(aobj, 'adversary', False)
            if is_pred:
                act = pred_policy.select_action(env, agent)
            else:
                act = prey_policy.select_action(env, agent)
            env.step(act)

        step_idx += 1
        if step_idx % n_agents == 0:
            frame = env.render()
            if frame is not None:
                frames.append(Image.fromarray(frame))
            cycle += 1
            if cycle >= max_cycles:
                break

    try:
        env.close()
    except Exception:
        pass
    return frames


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-cycles", type=int, default=25)
    p.add_argument("--duration-ms", type=int, default=120)
    p.add_argument("--outdir", type=str, default="hfo_petting_zoo_results")
    p.add_argument("--baseline", type=str, choices=["research", "enhanced"], default="research")
    p.add_argument("--thr", type=float, default=0.98, help="abs position threshold to count near-wall for forcing")
    p.add_argument("--force-max", type=int, default=50)
    # Cell A
    p.add_argument("--cell-a-pred", type=str, required=True)
    p.add_argument("--cell-a-prey", type=str, required=True)
    p.add_argument("--cell-a-pred-kwargs", type=str, default=None)
    p.add_argument("--cell-a-prey-kwargs", type=str, default=None)
    p.add_argument("--cell-a-label", type=str, default=None)
    p.add_argument("--cell-a-force-prey-near-wall", action="store_true")
    # Cell B
    p.add_argument("--cell-b-pred", type=str, required=True)
    p.add_argument("--cell-b-prey", type=str, required=True)
    p.add_argument("--cell-b-pred-kwargs", type=str, default=None)
    p.add_argument("--cell-b-prey-kwargs", type=str, default=None)
    p.add_argument("--cell-b-label", type=str, default=None)
    p.add_argument("--cell-b-force-prey-near-wall", action="store_true")
    # Cell C
    p.add_argument("--cell-c-pred", type=str, required=True)
    p.add_argument("--cell-c-prey", type=str, required=True)
    p.add_argument("--cell-c-pred-kwargs", type=str, default=None)
    p.add_argument("--cell-c-prey-kwargs", type=str, default=None)
    p.add_argument("--cell-c-label", type=str, default=None)
    p.add_argument("--cell-c-force-prey-near-wall", action="store_true")
    # Cell D
    p.add_argument("--cell-d-pred", type=str, required=True)
    p.add_argument("--cell-d-prey", type=str, required=True)
    p.add_argument("--cell-d-pred-kwargs", type=str, default=None)
    p.add_argument("--cell-d-prey-kwargs", type=str, default=None)
    p.add_argument("--cell-d-label", type=str, default=None)
    p.add_argument("--cell-d-force-prey-near-wall", action="store_true")

    args = p.parse_args()

    def parse_kwargs(s: str | None) -> dict | None:
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return None

    cells_cfg: Dict[str, dict] = {
        'A': {
            'pred': args.cell_a_pred,
            'prey': args.cell_a_prey,
            'pred_kwargs': parse_kwargs(args.cell_a_pred_kwargs),
            'prey_kwargs': parse_kwargs(args.cell_a_prey_kwargs),
            'label': args.cell_a_label or _label_from_specs(args.cell_a_pred, args.cell_a_prey),
            'force': bool(args.cell_a_force_prey_near_wall),
        },
        'B': {
            'pred': args.cell_b_pred,
            'prey': args.cell_b_prey,
            'pred_kwargs': parse_kwargs(args.cell_b_pred_kwargs),
            'prey_kwargs': parse_kwargs(args.cell_b_prey_kwargs),
            'label': args.cell_b_label or _label_from_specs(args.cell_b_pred, args.cell_b_prey),
            'force': bool(args.cell_b_force_prey_near_wall),
        },
        'C': {
            'pred': args.cell_c_pred,
            'prey': args.cell_c_prey,
            'pred_kwargs': parse_kwargs(args.cell_c_pred_kwargs),
            'prey_kwargs': parse_kwargs(args.cell_c_prey_kwargs),
            'label': args.cell_c_label or _label_from_specs(args.cell_c_pred, args.cell_c_prey),
            'force': bool(args.cell_c_force_prey_near_wall),
        },
        'D': {
            'pred': args.cell_d_pred,
            'prey': args.cell_d_prey,
            'pred_kwargs': parse_kwargs(args.cell_d_pred_kwargs),
            'prey_kwargs': parse_kwargs(args.cell_d_prey_kwargs),
            'label': args.cell_d_label or _label_from_specs(args.cell_d_pred, args.cell_d_prey),
            'force': bool(args.cell_d_force_prey_near_wall),
        },
    }

    # Collect frames per cell per episode
    frames_per_cell_eps: Dict[str, List[List[Image.Image]]] = {k: [] for k in cells_cfg.keys()}

    for cell_key, cfg in cells_cfg.items():
        for ep in range(args.episodes):
            ep_seed = args.seed + ep
            frames = run_episode_frames_for_cell(
                cfg, seed=ep_seed, max_cycles=args.max_cycles, baseline=args.baseline,
                force_prey_near_wall=cfg['force'], thr=float(args.thr), force_max=int(args.force_max)
            )
            frames_per_cell_eps[cell_key].append(frames)

    # Resize to smallest common size
    widths: List[int] = []
    heights: List[int] = []
    for eps_list in frames_per_cell_eps.values():
        for seq in eps_list:
            for im in seq:
                widths.append(im.width)
                heights.append(im.height)
    base_w = min(widths) if widths else 300
    base_h = min(heights) if heights else 300
    for k, eps_list in frames_per_cell_eps.items():
        for e_idx, seq in enumerate(eps_list):
            frames_per_cell_eps[k][e_idx] = [im.resize((base_w, base_h), Image.BILINEAR) for im in seq]

    # Ensure we have at least one frame overall
    any_len = 0
    for eps_list in frames_per_cell_eps.values():
        for seq in eps_list:
            any_len += len(seq)
    if any_len == 0:
        raise SystemExit("No frames generated. Ensure PettingZoo is installed and renderable.")

    labels = (
        cells_cfg['A']['label'],
        cells_cfg['B']['label'],
        cells_cfg['C']['label'],
        cells_cfg['D']['label'],
    )

    composite_frames: List[Image.Image] = []
    for ep in range(args.episodes):
        A = frames_per_cell_eps['A'][ep]
        B = frames_per_cell_eps['B'][ep]
        C = frames_per_cell_eps['C'][ep]
        D = frames_per_cell_eps['D'][ep]
        max_len_ep = max(len(A), len(B), len(C), len(D))
        if max_len_ep == 0:
            continue
        for i in range(max_len_ep):
            a = A[i] if i < len(A) else A[-1]
            b = B[i] if i < len(B) else B[-1]
            c = C[i] if i < len(C) else C[-1]
            d = D[i] if i < len(D) else D[-1]
            subs = (
                f"ep {ep + 1} step {i + 1}" if i < len(A) else f"ep {ep + 1} done",
                f"ep {ep + 1} step {i + 1}" if i < len(B) else f"ep {ep + 1} done",
                f"ep {ep + 1} step {i + 1}" if i < len(C) else f"ep {ep + 1} done",
                f"ep {ep + 1} step {i + 1}" if i < len(D) else f"ep {ep + 1} done",
            )
            composite_frames.append(tile2x2(a, b, c, d, labels, subs))

    date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    outdir = os.path.join(args.outdir, date_dir)
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(outdir, f"simple_tag_v3_custom_matrix_{ts}_seed{args.seed}_eps{args.episodes}.gif")
    composite_frames[0].save(
        out_path,
        save_all=True,
        append_images=composite_frames[1:],
        duration=args.duration_ms,
        loop=0,
        optimize=False,
    )
    print("GIF written:", out_path)


if __name__ == "__main__":
    main()
