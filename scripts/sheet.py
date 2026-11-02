"""Contact sheet + loudness of any video: QC a render or study a reference.

    python -X utf8 sheet.py <video> [--every 10] [--from 0 --to 60] [--cols 6] [--out sheet.jpg]

Prints duration, size, fps, integrated loudness (LUFS) and loudness range; writes a tiled
sheet (one frame every --every seconds, timestamp under each) next to the video.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from common import probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=10)
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--out")
    a = ap.parse_args()
    v = Path(a.video)
    info = probe(v)
    t1 = a.t1 or info["dur"]
    n = max(1, int((t1 - a.t0) / a.every))
    out = Path(a.out) if a.out else v.with_name(v.stem + "_sheet.jpg")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.t0), "-t", str(t1 - a.t0), "-i", str(v),
                          "-vf", f"fps=1/{a.every},scale=480:270", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    from PIL import Image, ImageDraw  # drawtext needs fontconfig, which Windows builds often lack
    frames = [Image.frombytes("RGB", (480, 270), raw[i:i + 480 * 270 * 3]) for i in range(0, len(raw), 480 * 270 * 3)]
    rows = (len(frames) + a.cols - 1) // a.cols
    im = Image.new("RGB", (480 * a.cols, 270 * rows))
    d = ImageDraw.Draw(im)
    for k, f in enumerate(frames):
        x, y = (k % a.cols) * 480, (k // a.cols) * 270
        im.paste(f, (x, y))
        t = a.t0 + k * a.every
        d.rectangle((x, y + 244, x + 70, y + 270), fill=(0, 0, 0))
        d.text((x + 6, y + 250), f"{int(t // 60):02d}:{t % 60:04.1f}", fill=(255, 255, 255))
    im.save(out, quality=88)
    vs = info["v"] or {}
    print(f"{v.name}: {info['dur']:.1f}s {vs.get('width')}x{vs.get('height')} {vs.get('r_frame_rate')}")
    if info["a"]:
        e = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(v), "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
        i = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
        lra = re.findall(r"LRA:\s+([\d.]+) LU", e)
        print(f"loudness {i[-1] if i else '?'} LUFS, LRA {lra[-1] if lra else '?'} LU")
    print("sheet:", out)


if __name__ == "__main__":
    main()
