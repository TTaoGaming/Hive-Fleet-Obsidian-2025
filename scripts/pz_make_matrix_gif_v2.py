#!/usr/bin/env python3#!/usr/bin/env python3

from __future__ import annotations"""

import argparse, osGenerate a 2x2 animated GIF for PettingZoo MPE simple_tag_v3 across four matchups:

from datetime import datetime, timezone- RvsR  (random predators vs random prey)

from typing import Dict, List, Tuple- HvsR  (heuristic predators vs random prey)

import numpy as np- RvsH  (random predators vs heuristic prey)

from PIL import Image, ImageDraw- HvsH  (heuristic predators vs heuristic prey)

try:

    from mpe2 import simple_tag_v3  # type: ignoreEach cell runs N episodes (default: 3). We stitch frames from each cell into

except Exception:composite 2x2 frames with quadrant headers and step/episode overlays.

    from pettingzoo.mpe import simple_tag_v3  # type: ignore

Output: hfo_petting_zoo_results/gifs/simple_tag_v3_matrix_<TS>_seed<seed>_eps<episodes>.gif

def unit(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:"""

    n = np.linalg.norm(vec)from __future__ import annotations

    if n < eps: return np.zeros_like(vec)

    return vec / nimport argparse

import os

def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:from datetime import datetime, timezone

    ax = float(d[0]); ay = float(d[1])from typing import Dict, List, Tuple

    out = np.zeros(5, dtype=np.float32)

    if abs(ax) < 1e-6 and abs(ay) < 1e-6:import numpy as np

        out[0] = 1.0; return outfrom PIL import Image, ImageDraw

    if ax < 0: out[1] = -ax

    else: out[2] = axtry:

    if ay < 0: out[3] = -ay    from mpe2 import simple_tag_v3  # type: ignore

    else: out[4] = ayexcept Exception:  # pragma: no cover

    mx = out[1:5].max() if out[1:5].size else 1.0    from pettingzoo.mpe import simple_tag_v3  # type: ignore

    if mx > 1e-6: out[1:5] = out[1:5] / mx

    return out

# ---------- Math / mapping ----------

class WorldView:

    def __init__(self, raw_env) -> None:def unit(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:

        w = raw_env.world    n = np.linalg.norm(vec)

        self.prey = [a for a in w.agents if not getattr(a, "adversary", False)][0]    if n < eps:

        self.preds = [a for a in w.agents if getattr(a, "adversary", False)]        return np.zeros_like(vec)

    def prey_pos(self) -> np.ndarray: return self.prey.state.p_pos.copy()    return vec / n

    def prey_vel(self) -> np.ndarray: return self.prey.state.p_vel.copy()

    def pred_pos(self) -> List[np.ndarray]: return [p.state.p_pos.copy() for p in self.preds]

    def pred_vel(self) -> List[np.ndarray]: return [p.state.p_vel.copy() for p in self.preds]def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:

    """Map R^2 desired direction to 5-dim Box action [noop, left, right, down, up]."""

def predator_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:    ax = float(d[0])

    return unit(view.prey_pos() - my_pos)    ay = float(d[1])

    out = np.zeros(5, dtype=np.float32)

def prey_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:    if abs(ax) < 1e-6 and abs(ay) < 1e-6:

    rep = np.zeros(2, dtype=np.float32)        out[0] = 1.0

    for p in view.pred_pos():        return out

        v = my_pos - p; rep += unit(v) / (np.linalg.norm(v) + 1e-6)    if ax < 0:

    return unit(rep)        out[1] = -ax

    else:

def predator_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:        out[2] = ax

    k_lead = 0.15; bound = 1.0    if ay < 0:

    prey_future = view.prey_pos() + k_lead * view.prey_vel()        out[3] = -ay

    prey_future = np.clip(prey_future, -bound, bound)    else:

    d = unit(prey_future - my_pos)        out[4] = ay

    near = 0.01; inward = np.zeros(2, dtype=np.float32)    mx = out[1:5].max() if out[1:5].size else 1.0

    for i in range(2):    if mx > 1e-6:

        if abs(my_pos[i]) > (bound - near) and not (abs(prey_future[i]) > (bound - near)):        out[1:5] = out[1:5] / mx

            inward[i] = -0.15 * np.sign(my_pos[i])    return out

    return unit(d + inward)



def prey_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:# ---------- Heuristics ----------

    k_rep_pred = 1.25; k_inertia = 0.10

    rep = np.zeros(2, dtype=np.float32)class WorldView:

    for p in view.pred_pos():    def __init__(self, raw_env) -> None:

        v = my_pos - p; rep += unit(v) / (np.linalg.norm(v) + 1e-6)        w = raw_env.world

    d = k_rep_pred * rep + k_inertia * unit(my_vel)        self.prey = [a for a in w.agents if not getattr(a, "adversary", False)][0]

    return unit(d)        self.preds = [a for a in w.agents if getattr(a, "adversary", False)]

        self.landmarks = [l for l in w.landmarks]

def action_for_agent(env, agent_name: str, matchup: str, baseline: str) -> np.ndarray | int | None:

    raw = env.unwrapped    def prey_pos(self) -> np.ndarray:

    aobj = next(a for a in raw.world.agents if getattr(a, "name", None) == agent_name)        return self.prey.state.p_pos.copy()

    is_pred = getattr(aobj, "adversary", False)

    my_pos = aobj.state.p_pos.copy(); my_vel = aobj.state.p_vel.copy()    def prey_vel(self) -> np.ndarray:

    pred_fn = predator_dir_research if baseline == "research" else predator_dir_enhanced        return self.prey.state.p_vel.copy()

    prey_fn = prey_dir_research if baseline == "research" else prey_dir_enhanced

    if matchup == "RvsR":    def pred_pos(self) -> List[np.ndarray]:

        return env.action_space(agent_name).sample()        return [p.state.p_pos.copy() for p in self.preds]

    elif matchup == "HvsR":

        if is_pred:    def pred_vel(self) -> List[np.ndarray]:

            view = WorldView(raw); d = pred_fn(view, my_pos, my_vel)        return [p.state.p_vel.copy() for p in self.preds]

            return dir_to_continuous_action(d)

        return env.action_space(agent_name).sample()

    elif matchup == "RvsH":# Enhanced (for parity with runner 'enhanced')

        if is_pred: return env.action_space(agent_name).sample()

        view = WorldView(raw); d = prey_fn(view, my_pos, my_vel)def predator_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:

        return dir_to_continuous_action(d)    k_lead = 0.15

    elif matchup == "HvsH":    bound = 1.0

        view = WorldView(raw)    prey_future = view.prey_pos() + k_lead * view.prey_vel()

        d = pred_fn(view, my_pos, my_vel) if is_pred else prey_fn(view, my_pos, my_vel)    prey_future = np.clip(prey_future, -bound, bound)

        return dir_to_continuous_action(d)    d = unit(prey_future - my_pos)

    else:    near = 0.01

        raise ValueError(f"unknown matchup {matchup}")    inward = np.zeros(2, dtype=np.float32)

    for i in range(2):

def run_episode_frames(matchup: str, seed: int, max_cycles: int, baseline: str) -> List[Image.Image]:        if abs(my_pos[i]) > (bound - near) and not (abs(prey_future[i]) > (bound - near)):

    env = simple_tag_v3.env(continuous_actions=True, render_mode="rgb_array")            inward[i] = -0.15 * np.sign(my_pos[i])

    env.reset(seed=seed)    return unit(d + inward)

    n_agents = len(env.possible_agents)

    frames: List[Image.Image] = []

    step_idx = 0; cycle = 0def prey_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:

    for agent in env.agent_iter():    k_rep_pred = 1.25

        obs, reward, terminated, truncated, info = env.last()    k_inertia = 0.10

        if terminated or truncated: env.step(None)    rep = np.zeros(2, dtype=np.float32)

        else:    for p in view.pred_pos():

            act = action_for_agent(env, agent, matchup, baseline); env.step(act)        v = my_pos - p

        step_idx += 1        rep += unit(v) / (np.linalg.norm(v) + 1e-6)

        if step_idx % n_agents == 0:    d = k_rep_pred * rep + k_inertia * unit(my_vel)

            frame = env.render()    return unit(d)

            if frame is not None: frames.append(Image.fromarray(frame))

            cycle += 1

            if cycle >= max_cycles: break# Research baseline: pure pursuit + inverse-distance flee

    try:

        env.close()def predator_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:

    except Exception:    return unit(view.prey_pos() - my_pos)

        pass

    return frames

def prey_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:

def overlay_header(img: Image.Image, text: str, subtext: str | None = None) -> Image.Image:    rep = np.zeros(2, dtype=np.float32)

    draw = ImageDraw.Draw(img, "RGBA"); pad = 4    for p in view.pred_pos():

    box_w = max(80, len(text) * 10); box_h = 22 if subtext is None else 38        v = my_pos - p

    draw.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0, 140))        rep += unit(v) / (np.linalg.norm(v) + 1e-6)

    draw.text((pad, 2), text, fill=(255, 255, 255, 255))    return unit(rep)

    if subtext: draw.text((pad, 18), subtext, fill=(200, 200, 200, 255))

    return img

def action_for_agent(env, agent_name: str, matchup: str, baseline: str) -> np.ndarray | int | None:

def tile2x2(a: Image.Image, b: Image.Image, c: Image.Image, d: Image.Image,    # If agent is already done, caller should pass None

            labels: Tuple[str, str, str, str], subtexts: Tuple[str, str, str, str]) -> Image.Image:    raw = env.unwrapped

    w, h = a.size    aobj = next(a for a in raw.world.agents if getattr(a, "name", None) == agent_name)

    canvas = Image.new("RGB", (w * 2, h * 2), (0, 0, 0))    is_pred = getattr(aobj, "adversary", False)

    a = overlay_header(a.copy(), labels[0], subtexts[0])    my_pos = aobj.state.p_pos.copy()

    b = overlay_header(b.copy(), labels[1], subtexts[1])    my_vel = aobj.state.p_vel.copy()

    c = overlay_header(c.copy(), labels[2], subtexts[2])

    d = overlay_header(d.copy(), labels[3], subtexts[3])    if baseline == "research":

    canvas.paste(a, (0, 0)); canvas.paste(b, (w, 0))        pred_fn = predator_dir_research

    canvas.paste(c, (0, h)); canvas.paste(d, (w, h))        prey_fn = prey_dir_research

    return canvas    else:

        pred_fn = predator_dir_enhanced

def main() -> None:        prey_fn = prey_dir_enhanced

    p = argparse.ArgumentParser()

    p.add_argument("--episodes", type=int, default=3)    if matchup == "RvsR":

    p.add_argument("--seed", type=int, default=42)        return env.action_space(agent_name).sample()

    p.add_argument("--max-cycles", type=int, default=25)    elif matchup == "HvsR":

    p.add_argument("--duration-ms", type=int, default=120)        if is_pred:

    p.add_argument("--outdir", type=str, default="hfo_petting_zoo_results/gifs")            view = WorldView(raw)

    p.add_argument("--baseline", type=str, choices=["research", "enhanced"], default="research")            d = pred_fn(view, my_pos, my_vel)

    args = p.parse_args()            return dir_to_continuous_action(d)

    cells = ["RvsR", "HvsR", "RvsH", "HvsH"]        else:

    frames_per_cell: Dict[str, List[Image.Image]] = {k: [] for k in cells}            return env.action_space(agent_name).sample()

    for cell in cells:    elif matchup == "RvsH":

        for ep in range(args.episodes):        if is_pred:

            ep_seed = args.seed + ep            return env.action_space(agent_name).sample()

            frames_per_cell[cell].extend(run_episode_frames(cell, seed=ep_seed, max_cycles=args.max_cycles, baseline=args.baseline))        else:

    widths: List[int] = []; heights: List[int] = []            view = WorldView(raw)

    for seq in frames_per_cell.values():            d = prey_fn(view, my_pos, my_vel)

        for im in seq: widths.append(im.width); heights.append(im.height)            return dir_to_continuous_action(d)

    base_w = min(widths) if widths else 300; base_h = min(heights) if heights else 300    elif matchup == "HvsH":

    for k, seq in frames_per_cell.items():        view = WorldView(raw)

        frames_per_cell[k] = [im.resize((base_w, base_h), Image.BILINEAR) for im in seq]        if is_pred:

    max_len = max((len(v) for v in frames_per_cell.values()), default=0)            d = pred_fn(view, my_pos, my_vel)

    if max_len == 0: raise SystemExit("No frames generated. Check that PettingZoo and dependencies are installed.")        else:

    labels = ("RvsR", "HvsR", "RvsH", "HvsH")            d = prey_fn(view, my_pos, my_vel)

    composite_frames: List[Image.Image] = []        return dir_to_continuous_action(d)

    fpe = args.max_cycles    else:

    for i in range(max_len):        raise ValueError(f"unknown matchup {matchup}")

        a = frames_per_cell["RvsR"][i if i < len(frames_per_cell["RvsR"]) else -1]

        b = frames_per_cell["HvsR"][i if i < len(frames_per_cell["HvsR"]) else -1]

        c = frames_per_cell["RvsH"][i if i < len(frames_per_cell["RvsH"]) else -1]# ---------- Episode rendering ----------

        d = frames_per_cell["HvsH"][i if i < len(frames_per_cell["HvsH"]) else -1]

        subs = (def run_episode_frames(matchup: str, seed: int, max_cycles: int, baseline: str) -> List[Image.Image]:

            f"ep {i // fpe + 1} step {i % fpe + 1}",    env = simple_tag_v3.env(continuous_actions=True, render_mode="rgb_array")

            f"ep {i // fpe + 1} step {i % fpe + 1}",    env.reset(seed=seed)

            f"ep {i // fpe + 1} step {i % fpe + 1}",    n_agents = len(env.possible_agents)

            f"ep {i // fpe + 1} step {i % fpe + 1}",    frames: List[Image.Image] = []

        )

        composite_frames.append(tile2x2(a, b, c, d, labels, subs))    step_idx = 0

    os.makedirs(args.outdir, exist_ok=True)    cycle = 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")    for agent in env.agent_iter():

    out_path = os.path.join(args.outdir, f"simple_tag_v3_matrix_{ts}_seed{args.seed}_eps{args.episodes}.gif")        obs, reward, terminated, truncated, info = env.last()

    composite_frames[0].save(out_path, save_all=True, append_images=composite_frames[1:], duration=args.duration_ms, loop=0, optimize=False)        if terminated or truncated:

    print("GIF written:", out_path)            env.step(None)

        else:

if __name__ == "__main__":            act = action_for_agent(env, agent, matchup, baseline)

    main()            env.step(act)


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
    p.add_argument("--baseline", type=str, choices=["research", "enhanced"], default="research")
    args = p.parse_args()

    cells = ["RvsR", "HvsR", "RvsH", "HvsH"]
    frames_per_cell: Dict[str, List[Image.Image]] = {k: [] for k in cells}

    # Collect frames: concatenate episodes per cell
    for ci, cell in enumerate(cells):
        for ep in range(args.episodes):
            ep_seed = args.seed + ep
            ep_frames = run_episode_frames(cell, seed=ep_seed, max_cycles=args.max_cycles, baseline=args.baseline)
            frames_per_cell[cell].extend(ep_frames)

    # Normalize sizes
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
        raise SystemExit("No frames generated. Check that PettingZoo and dependencies are installed.")

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
        composite = tile2x2(a, b, c, d, labels, subs)
        composite_frames.append(composite)

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
