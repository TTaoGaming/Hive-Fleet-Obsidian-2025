#!/usr/bin/env python3
"""
2x2 animated GIF for PettingZoo MPE simple_tag_v3 across matchups:
- RvsR, HvsR, RvsH, HvsH
Outputs to: hfo_petting_zoo_results/<DATE>/simple_tag_v3_matrix_<TS>_seed<seed>_eps<episodes>.gif
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

try:
    from mpe2 import simple_tag_v3  # type: ignore
except Exception:  # pragma: no cover
    from pettingzoo.mpe import simple_tag_v3  # type: ignore


# ---- helpers ----

def unit(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(vec)
    return np.zeros_like(vec) if n < eps else vec / n


def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    """Map 2D direction to 5-dim action [noop, left, right, down, up]."""
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


class WorldView:
    def __init__(self, raw_env) -> None:
        w = raw_env.world
        self.prey = [a for a in w.agents if not getattr(a, "adversary", False)][0]
        self.preds = [a for a in w.agents if getattr(a, "adversary", False)]

    def prey_pos(self) -> np.ndarray:
        return self.prey.state.p_pos.copy()

    def prey_vel(self) -> np.ndarray:
        return self.prey.state.p_vel.copy()

    def pred_pos(self) -> List[np.ndarray]:
        return [p.state.p_pos.copy() for p in self.preds]


# ---- heuristic policies ----

def predator_dir_research(view: WorldView, my_pos: np.ndarray, _my_vel: np.ndarray) -> np.ndarray:
    return unit(view.prey_pos() - my_pos)


def prey_dir_research(view: WorldView, my_pos: np.ndarray, _my_vel: np.ndarray) -> np.ndarray:
    rep = np.zeros(2, dtype=np.float32)
    for p in view.pred_pos():
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    return unit(rep)


def predator_dir_enhanced(view: WorldView, my_pos: np.ndarray, _my_vel: np.ndarray) -> np.ndarray:
    k_lead = 0.15
    bound = 1.0
    prey_future = view.prey_pos() + k_lead * view.prey_vel()
    prey_future = np.clip(prey_future, -bound, bound)
    d = unit(prey_future - my_pos)
    near = 0.01
    inward = np.zeros(2, dtype=np.float32)
    for i in range(2):
        if abs(my_pos[i]) > (bound - near) and not (abs(prey_future[i]) > (bound - near)):
            inward[i] = -0.15 * np.sign(my_pos[i])
    return unit(d + inward)


def prey_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    k_rep_pred = 1.25
    k_inertia = 0.10
    rep = np.zeros(2, dtype=np.float32)
    for p in view.pred_pos():
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    d = k_rep_pred * rep + k_inertia * unit(my_vel)
    return unit(d)


def action_for_agent(env, agent_name: str, matchup: str, baseline: str):
    raw = env.unwrapped
    aobj = next(a for a in raw.world.agents if getattr(a, "name", None) == agent_name)
    is_pred = getattr(aobj, "adversary", False)
    my_pos = aobj.state.p_pos.copy()
    my_vel = aobj.state.p_vel.copy()

    if baseline == "research":
        pred_fn = predator_dir_research
        prey_fn = prey_dir_research
    else:
        pred_fn = predator_dir_enhanced
        prey_fn = prey_dir_enhanced

    if matchup == "RvsR":
        return env.action_space(agent_name).sample()
    if matchup == "HvsR":
        if is_pred:
            view = WorldView(raw)
            return dir_to_continuous_action(pred_fn(view, my_pos, my_vel))
        return env.action_space(agent_name).sample()
    if matchup == "RvsH":
        if is_pred:
            return env.action_space(agent_name).sample()
        view = WorldView(raw)
        return dir_to_continuous_action(prey_fn(view, my_pos, my_vel))
    if matchup == "HvsH":
        view = WorldView(raw)
        d = pred_fn(view, my_pos, my_vel) if is_pred else prey_fn(view, my_pos, my_vel)
        return dir_to_continuous_action(d)
    raise ValueError(f"unknown matchup {matchup}")


# ---- per-episode frame collection ----

def run_episode_frames(matchup: str, seed: int, max_cycles: int, baseline: str) -> List[Image.Image]:
    env = simple_tag_v3.env(continuous_actions=True, render_mode="rgb_array")
    env.reset(seed=seed)
    n_agents = len(env.possible_agents)
    frames: List[Image.Image] = []

    step_idx = 0
    cycle = 0
    for agent in env.agent_iter():
        _obs, _reward, terminated, truncated, _info = env.last()
        if terminated or truncated:
            env.step(None)
        else:
            env.step(action_for_agent(env, agent, matchup, baseline))

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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=3, help="episodes per cell")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-cycles", type=int, default=25, help="cycles per episode")
    p.add_argument("--duration-ms", type=int, default=120, help="GIF frame duration ms")
    p.add_argument("--outdir", type=str, default="hfo_petting_zoo_results/gifs")
    p.add_argument("--baseline", type=str, choices=["research", "enhanced"], default="research")
    args = p.parse_args()

    cells = ["RvsR", "HvsR", "RvsH", "HvsH"]
    frames_per_cell: Dict[str, List[Image.Image]] = {k: [] for k in cells}

    for cell in cells:
        for ep in range(args.episodes):
            ep_seed = args.seed + ep
            frames = run_episode_frames(cell, seed=ep_seed, max_cycles=args.max_cycles, baseline=args.baseline)
            frames_per_cell[cell].extend(frames)

    widths: List[int] = []
    heights: List[int] = []
    for seq in frames_per_cell.values():
        for im in seq:
            widths.append(im.width)
            heights.append(im.height)
    base_w = min(widths) if widths else 300
    base_h = min(heights) if heights else 300
    for k, seq in frames_per_cell.items():
        frames_per_cell[k] = [im.resize((base_w, base_h), Image.BILINEAR) for im in seq]

    max_len = max((len(v) for v in frames_per_cell.values()), default=0)
    if max_len == 0:
        raise SystemExit("No frames generated. Ensure PettingZoo is installed and renderable.")

    labels = ("RvsR", "HvsR", "RvsH", "HvsH")
    composite_frames: List[Image.Image] = []
    fpe = args.max_cycles
    for i in range(max_len):
        a = frames_per_cell["RvsR"][i if i < len(frames_per_cell["RvsR"]) else -1]
        b = frames_per_cell["HvsR"][i if i < len(frames_per_cell["HvsR"]) else -1]
        c = frames_per_cell["RvsH"][i if i < len(frames_per_cell["RvsH"]) else -1]
        d = frames_per_cell["HvsH"][i if i < len(frames_per_cell["HvsH"]) else -1]
        subs = (
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
        )
        composite_frames.append(tile2x2(a, b, c, d, labels, subs))

    os.makedirs(args.outdir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(
        args.outdir, f"simple_tag_v3_matrix_{ts}_seed{args.seed}_eps{args.episodes}.gif"
    )
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
