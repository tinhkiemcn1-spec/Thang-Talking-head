"""Clean, natural grade per camera + match camera B to camera A.

    python -X utf8 grade.py <edit>                # analyse, write plan.grade, save before/after stills
    python -X utf8 grade.py <edit> --look warm    # add a named look on top (see LOOKS)
    python -X utf8 grade.py --print-looks

The reference videos are graded lightly: neutral white wall, warm true skin, a touch more
contrast and saturation, shirt colours untouched. So the automatic grade only does:
  1. white balance from the brightest near-neutral pixels (the wall), applied at 70 %
  2. exposure/contrast/saturation nudges, each capped at about ±8 % (Thang-Edit auto-grade rules)
  3. camera B: per-channel gains so its average colour matches camera A after step 1-2
Result goes to plan.json "grade": {"A": "<ffmpeg filter>", "B": "..."}; edit by hand if needed.
Look at grade/compare.jpg (top: before, bottom: after) before rendering.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from common import load_plan, probe, run

LOOKS = {
    "none": "",
    "warm": "colorbalance=rs=0.02:rm=0.03:rh=0.02:bs=-0.02:bm=-0.03:bh=-0.02",
    "cool": "colorbalance=rs=-0.02:rm=-0.02:bs=0.02:bm=0.03",
    "punch": "eq=contrast=1.06:saturation=1.05,curves=master='0/0 0.25/0.23 0.75/0.77 1/1'",
    "soft": "curves=master='0/0.03 0.5/0.5 1/0.97',eq=saturation=0.96",
    "denoise": "hqdn3d=2:1.5:3:3",
    "sharpen": "unsharp=5:5:0.5:5:5:0.0",
}


def frames(path: Path, start: float, dur: float, n: int = 12, filt: str = "") -> np.ndarray:
    step = max(dur / n, 0.5)
    vf = (filt + "," if filt else "") + f"fps=1/{step:.3f},scale=320:180,format=rgb24"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path), "-vf", vf,
                          "-frames:v", str(n), "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 180, 320, 3).astype(np.float32) / 255


def wb_gains(px: np.ndarray, strength: float = 0.7) -> tuple[float, float, float]:
    flat = px.reshape(-1, 3)
    lum = flat.mean(1)
    sat = flat.max(1) - flat.min(1)
    sel = flat[(lum > np.percentile(lum, 70)) & (lum < 0.97) & (sat < 0.12)]
    if len(sel) < 500:
        return 1.0, 1.0, 1.0
    m = sel.mean(0)
    g = m.mean() / m
    g = 1 + (g - 1) * strength
    g = np.clip(g / g.max() * min(1.0, g.max()), 0.85, 1.15)
    return tuple(float(x) for x in g)


def tone(px: np.ndarray) -> str:
    lum = px.mean(3)
    y_mean, y_range = float(lum.mean()), float(lum.std() * 4)
    hsv_sat = float((px.max(3) - px.min(3)).mean())
    contrast = 1.08 - 0.05 * min(1, max(0, (y_range - .5) / .15)) if y_range < .65 else 1.04
    gamma = 1.10 - 0.08 * min(1, max(0, (y_mean - .30) / .12)) if y_mean < .42 else (0.97 if y_mean > .62 else 1.0)
    sat = 1.06 if hsv_sat < .15 else (0.98 if hsv_sat > .35 else 1.03)
    return f"eq=contrast={contrast:.3f}:gamma={gamma:.3f}:saturation={sat:.3f}"


def mixer(g) -> str:
    return f"colorchannelmixer=rr={g[0]:.4f}:gg={g[1]:.4f}:bb={g[2]:.4f}"


def chain(*parts) -> str:
    return ",".join(p for p in parts if p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit", nargs="?")
    ap.add_argument("--look", default="none", help="+ để ghép: warm+denoise")
    ap.add_argument("--print-looks", action="store_true")
    a = ap.parse_args()
    if a.print_looks:
        for k, v in LOOKS.items():
            print(f"{k:8s} {v}")
        return
    edit = Path(a.edit).resolve()
    plan = load_plan(edit)
    look = chain(*(LOOKS[k] for k in a.look.split("+")))
    srcs = plan["sources"]
    grades, samples = {}, {}
    for cam, p in srcs.items():
        d = probe(Path(p))["dur"]
        px = frames(Path(p), d * .05, d * .9)
        samples[cam] = px
        g = wb_gains(px)
        grades[cam] = chain(mixer(g) if max(abs(x - 1) for x in g) > .01 else "", tone(px), look)
    if "B" in srcs:
        a_after = frames(Path(srcs["A"]), 0, probe(Path(srcs["A"]))["dur"], filt=grades["A"]).reshape(-1, 3).mean(0)
        b_after = frames(Path(srcs["B"]), 0, probe(Path(srcs["B"]))["dur"], filt=grades["B"]).reshape(-1, 3).mean(0)
        m = np.clip(a_after / np.maximum(b_after, 1e-3), 0.85, 1.15)
        grades["B"] = chain(grades["B"], mixer(m))
    raw = json.loads((edit / "plan.json").read_text(encoding="utf-8"))
    raw["grade"] = grades
    (edit / "plan.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in grades.items():
        print(f"{k}: {v}")

    out = edit / "grade"
    out.mkdir(exist_ok=True)
    tiles = []
    for cam, p in srcs.items():
        t = probe(Path(p))["dur"] * .3
        run(["ffmpeg", "-y", "-v", "error", "-ss", t, "-i", p, "-frames:v", "1", "-vf", "scale=640:360", out / f"{cam}_before.jpg"])
        run(["ffmpeg", "-y", "-v", "error", "-ss", t, "-i", p, "-frames:v", "1", "-vf", chain(grades[cam], "scale=640:360"), out / f"{cam}_after.jpg"])
        tiles.append(cam)
    inputs = []
    for cam in tiles:
        inputs += ["-i", out / f"{cam}_before.jpg"]
    for cam in tiles:
        inputs += ["-i", out / f"{cam}_after.jpg"]
    n = len(tiles)
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", f"xstack=inputs={2 * n}:grid={n}x2", out / "compare.jpg"])
    print("xem:", out / "compare.jpg", "(trên: gốc, dưới: đã chỉnh)")


if __name__ == "__main__":
    main()
