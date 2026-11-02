"""Shared helpers: plan loading, paths, ffprobe. Every script imports this."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"
ICONS_DIR = SKILL / "assets" / "icons"
SFX_DIR = SKILL / "assets" / "sfx"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULTS = {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "font": "inter",
    "fade": 0.35,
    "segments": [],
    "cards": [],
    "captions": [],
    "broll": [],
    "audio": {"highpass": 80, "denoise": 10, "deess": True, "compress": True, "lufs": -14},
}


def run(cmd: list, quiet: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"lệnh lỗi: {' '.join(map(str, cmd[:6]))} ...\n{r.stderr[-2000:]}")
    if not quiet:
        print(r.stdout)
    return r


def graph_args(gfile: Path) -> list:
    """ffmpeg 7+ reads a filtergraph file with -/filter_complex; 6 and older need -filter_complex_script."""
    v = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
    m = re.search(r"version n?(\d+)", v)
    return ["-/filter_complex", gfile] if not m or int(m.group(1)) >= 7 else ["-filter_complex_script", gfile]


def probe(path: Path) -> dict:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8")
    d = json.loads(o.stdout or "{}")
    streams = d.get("streams", [])
    return {"dur": float(d.get("format", {}).get("duration") or 0),
            "v": next((s for s in streams if s["codec_type"] == "video"), None),
            "a": next((s for s in streams if s["codec_type"] == "audio"), None)}


def resolve(edit: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (edit / q)


def load_plan(edit: Path) -> dict:
    f = edit / "plan.json"
    if not f.exists():
        sys.exit(f"không thấy {f}")
    plan = {**DEFAULTS, **json.loads(f.read_text(encoding="utf-8"))}
    plan["audio"] = {**DEFAULTS["audio"], **plan.get("audio", {})}
    for key, prefix in (("cards", "c"), ("captions", "t"), ("broll", "b")):
        for i, item in enumerate(plan[key], 1):
            item.setdefault("id", f"{prefix}{i:02d}")
    return plan


def timeline_length(plan: dict) -> float:
    return sum(s["out"] - s["in"] for s in plan["segments"])


def icons() -> dict:
    out = {}
    for p in ICONS_DIR.glob("*.svg"):
        s = p.read_text(encoding="utf-8")
        out[p.stem] = s[s.index("<svg"):]
    return out
