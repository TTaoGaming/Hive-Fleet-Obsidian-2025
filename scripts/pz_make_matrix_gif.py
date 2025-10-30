#!/usr/bin/env python3
"""
Generate a 2x2 animated GIF for PettingZoo MPE simple_tag_v3 across four matchups:
- RvsR  (random predators vs random prey)
- HvsR  (heuristic predators vs random prey)
- RvsH  (random predators vs heuristic prey)
- HvsH  (heuristic predators vs heuristic prey)

Each cell runs N episodes (default: 3). We stitch frames from each cell into
composite 2x2 frames with quadrant headers and step/episode overlays.

Output: hfo_petting_zoo_results/gifs/simple_tag_v3_matrix_<TS>_seed<seed>_eps<episodes>.gif
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


# ---------- Math / mapping ----------

def unit(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(vec)
    if n < eps:
        return np.zeros_like(vec)
    return vec / n


def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    """Map R^2 desired direction to 5-dim Box action [noop, left, right, down, up]."""
    ax = float(d[0])
    ay = float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0
        return out
    if ax < 0:
        out[1] = -ax
    else:
        out[2] = ax
    if ay < 0:
        out[3] = -ay
    else:
        out[4] = ay
    mx = out[1:5].max() if out[1:5].size else 1.0
    if mx > 1e-6:
        out[1:5] = out[1:5] / mx
    return out


# ---------- Heuristics ----------

class WorldView:
    def __init__(self, raw_env) -> None:
        w = raw_env.world
        self.prey = [a for a in w.agents if not getattr(a, "adversary", False)][0]
        self.preds = [a for a in w.agents if getattr(a, "adversary", False)]
        self.landmarks = [l for l in w.landmarks]

    def prey_pos(self) -> np.ndarray:
        return self.prey.state.p_pos.copy()

    def prey_vel(self) -> np.ndarray:
        return self.prey.state.p_vel.copy()

    def pred_pos(self) -> List[np.ndarray]:
        return [p.state.p_pos.copy() for p in self.preds]

    def pred_vel(self) -> List[np.ndarray]:
        return [p.state.p_vel.copy() for p in self.preds]

    def landmarks_pos(self) -> List[np.ndarray]:
        return [l.state.p_pos.copy() for l in self.landmarks]


def predator_dir(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    # Wall-aware pursuit (mirror runner): allow approaching walls; bias inward only if prey not near that wall.
    k_lead = 0.15
    bound = 1.0
    prey_future = view.prey_pos() + k_lead * view.prey_vel()
    prey_future = np.clip(prey_future, -bound, bound)
    d = unit(prey_future - my_pos)
    near = 0.01
    inward = np.zeros(2, dtype=np.float32)
    for i in range(2):
        if abs(my_pos[i]) > (bound - near):
            if not (abs(prey_future[i]) > (bound - near)):
                inward[i] = -0.15 * np.sign(my_pos[i])
    return unit(d + inward)


def prey_dir(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    k_rep_pred = 1.25
    k_inertia = 0.10

    rep = np.zeros(2, dtype=np.float32)
    for p in view.pred_pos():
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    d = k_rep_pred * rep + k_inertia * unit(my_vel)
    return unit(d)


def action_for_agent(env, agent_name: str, matchup: str) -> np.ndarray | int | None:
    # If agent is already done, caller should pass None
    raw = env.unwrapped
    # Find matching agent in raw world
    aobj = next(a for a in raw.world.agents if getattr(a, "name", None) == agent_name)
    is_pred = getattr(aobj, "adversary", False)
    my_pos = aobj.state.p_pos.copy()
    my_vel = aobj.state.p_vel.copy()

    if matchup == "RvsR":
        return env.action_space(agent_name).sample()
    elif matchup == "HvsR":
        if is_pred:
            view = WorldView(raw)
            d = predator_dir(view, my_pos, my_vel)
            return dir_to_continuous_action(d)
        else:
            return env.action_space(agent_name).sample()
    elif matchup == "RvsH":
        if is_pred:
            return env.action_space(agent_name).sample()
        else:
            view = WorldView(raw)
            d = prey_dir(view, my_pos, my_vel)
            return dir_to_continuous_action(d)
    elif matchup == "HvsH":
        view = WorldView(raw)
        if is_pred:
            d = predator_dir(view, my_pos, my_vel)
        else:
            d = prey_dir(view, my_pos, my_vel)
        return dir_to_continuous_action(d)
    else:
        raise ValueError(f"unknown matchup {matchup}")


# ---------- Episode rendering ----------

def run_episode_frames(matchup: str, seed: int, max_cycles: int) -> List[Image.Image]:
    env = simple_tag_v3.env(continuous_actions=True, render_mode="rgb_array")
    env.reset(seed=seed)
    n_agents = len(env.possible_agents)
    frames: List[Image.Image] = []

    # Iterate over agents; capture a frame after each full pass of all agents
    step_idx = 0
    cycle = 0
    for agent in env.agent_iter():
        obs, reward, terminated, truncated, info = env.last()
        if terminated or truncated:
            env.step(None)
        else:
            act = action_for_agent(env, agent, matchup)
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


def overlay_header(img: Image.Image, text: str, subtext: str | None = None) -> Image.Image:
    draw = ImageDraw.Draw(img, "RGBA")
    pad = 4
    # Header box
    box_w = max(80, len(text) * 10)
    box_h = 22 if subtext is None else 38
    draw.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0, 140))
    draw.text((pad, 2), text, fill=(255, 255, 255, 255))
    if subtext:
        draw.text((pad, 18), subtext, fill=(200, 200, 200, 255))
    return img


def tile2x2(a: Image.Image, b: Image.Image, c: Image.Image, d: Image.Image, labels: Tuple[str, str, str, str], subtexts: Tuple[str, str, str, str]) -> Image.Image:
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


# ---------- Main ----------

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=3, help="episodes per cell")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-cycles", type=int, default=25, help="max environment cycles per episode (frame count per episode)")
    p.add_argument("--duration-ms", type=int, default=120, help="GIF frame duration in milliseconds")
    p.add_argument("--outdir", type=str, default="hfo_petting_zoo_results/gifs")
    args = p.parse_args()

    cells = ["RvsR", "HvsR", "RvsH", "HvsH"]
    frames_per_cell: Dict[str, List[Image.Image]] = {k: [] for k in cells}

    # Collect frames: concatenate episodes per cell
    for ci, cell in enumerate(cells):
        for ep in range(args.episodes):
            ep_seed = args.seed + ep
            ep_frames = run_episode_frames(cell, seed=ep_seed, max_cycles=args.max_cycles)
            # annotate episode/step as subtext later (per-frame info)
            frames_per_cell[cell].extend(ep_frames)

    # Normalize frame sizes and lengths
    # Use smallest common size to avoid upscaling artifacts
    widths = []
    heights = []
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
        raise SystemExit("No frames generated. Check that PettingZoo and dependencies are installed.")

    labels = ("RvsR", "HvsR", "RvsH", "HvsH")
    composite_frames: List[Image.Image] = []
    for i in range(max_len):
        a = frames_per_cell["RvsR"][i if i < len(frames_per_cell["RvsR"]) else -1]
        b = frames_per_cell["HvsR"][i if i < len(frames_per_cell["HvsR"]) else -1]
        c = frames_per_cell["RvsH"][i if i < len(frames_per_cell["RvsH"]) else -1]
        d = frames_per_cell["HvsH"][i if i < len(frames_per_cell["HvsH"]) else -1]

        # Compute subtexts: episode and step indices per cell based on frame index
        def ep_step(idx: int, frames_per_ep: int) -> Tuple[int, int]:
            if frames_per_ep <= 0:
                return (0, idx)
            ep = idx // frames_per_ep
            step = idx % frames_per_ep
            return (ep, step)

        fpe = args.max_cycles  # approximate frames per episode per cell
        subs = (
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
            f"ep {i // fpe + 1} step {i % fpe + 1}",
        )
        composite = tile2x2(a, b, c, d, labels, subs)
        composite_frames.append(composite)

    # Save GIF
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
