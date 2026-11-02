"""Find how far camera B is shifted from camera A by cross-correlating their audio.

    python -X utf8 sync.py <camA> <camB> [--edit <edit>] [--window 120]

Prints offset = (time in B) - (time in A) for the same moment, i.e. B_time = A_time + offset.
With --edit it writes plan.json "sources" and "offsets" (creating the plan if needed).
Uses the onset envelope at 1 kHz, so claps are not required; any shared speech works.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

import common  # noqa: F401

SR = 8000


def envelope(path: Path, start: float, dur: float) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path), "-map", "0:a:0",
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = SR // 1000
    e = np.abs(x[: len(x) // hop * hop]).reshape(-1, hop).mean(1)
    e = np.log1p(e * 100)
    d = np.maximum(np.diff(e, prepend=e[0]), 0)
    return (d - d.mean()) / (d.std() + 1e-9)


def offset(a: Path, b: Path, window: float) -> tuple[float, float]:
    ea, eb = envelope(a, 0, window), envelope(b, 0, window)
    n = 1 << int(np.ceil(np.log2(len(ea) + len(eb))))
    c = np.fft.irfft(np.fft.rfft(eb, n) * np.conj(np.fft.rfft(ea, n)), n)
    lag = int(np.argmax(c))
    if lag > n // 2:
        lag -= n
    conf = float(c.max() / (np.sqrt((ea ** 2).sum() * (eb ** 2).sum()) + 1e-9))
    return lag / 1000.0, conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--edit")
    ap.add_argument("--window", type=float, default=120)
    x = ap.parse_args()
    off, conf = offset(Path(x.a), Path(x.b), x.window)
    print(f"offset B = A + {off:+.3f}s  (độ tin cậy {conf:.2f}; dưới 0.15 là đáng ngờ, kiểm tra bằng mắt)")
    if x.edit:
        edit = Path(x.edit)
        edit.mkdir(parents=True, exist_ok=True)
        f = edit / "plan.json"
        plan = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        plan.setdefault("sources", {}).update({"A": str(Path(x.a).resolve()), "B": str(Path(x.b).resolve())})
        plan.setdefault("offsets", {})["B"] = round(off, 3)
        f.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print("đã ghi", f)


if __name__ == "__main__":
    main()
