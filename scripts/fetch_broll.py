"""Search and download licensed stock B-roll from Pexels (free licence, no attribution required).

    python -X utf8 fetch_broll.py <edit> "doctor meeting" [--n 4] [--min-dur 5]

Needs PEXELS_API_KEY (environment variable or a .env next to the skill / in <edit>); a free key
comes from https://www.pexels.com/api/. Saves HD landscape clips to <edit>/broll/, a thumbnail
sheet broll/_<query>.jpg to look at before choosing, and appends broll/credits.csv.
Clips the user supplies need no fetching: put them in <edit>/broll/ and reference them in plan.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from common import SKILL


def api_key(edit: Path) -> str:
    if os.environ.get("PEXELS_API_KEY"):
        return os.environ["PEXELS_API_KEY"]
    for env in (edit / ".env", SKILL / ".env"):
        if env.exists():
            m = re.search(r"^PEXELS_API_KEY\s*=\s*(\S+)", env.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip("'\"")
    raise SystemExit("Thiếu PEXELS_API_KEY (lấy miễn phí ở https://www.pexels.com/api/, ghi vào .env).")


def get(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "Thang-Talking-head"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--min-dur", type=float, default=5)
    a = ap.parse_args()
    edit = Path(a.edit).resolve()
    key = api_key(edit)
    q = urllib.parse.urlencode({"query": a.query, "orientation": "landscape", "size": "medium", "per_page": 15})
    vids = [v for v in get(f"https://api.pexels.com/videos/search?{q}", key).get("videos", []) if v["duration"] >= a.min_dur]
    out = edit / "broll"
    out.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", a.query.lower()).strip("-")
    saved = []
    for v in vids[: a.n]:
        files = sorted((f for f in v["video_files"] if f.get("width") and f["width"] >= 1280 and f.get("file_type") == "video/mp4"),
                       key=lambda f: abs(f["width"] - 1920))
        if not files:
            continue
        dst = out / f"{slug}_{v['id']}.mp4"
        if not dst.exists():
            urllib.request.urlretrieve(files[0]["link"], dst)
        saved.append(dst)
        new = not (out / "credits.csv").exists()
        with open(out / "credits.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["file", "author", "url", "licence"])
            w.writerow([dst.name, v["user"]["name"], v["url"], "Pexels License"])
        print(f"  {dst.name}  {v['duration']}s  {files[0]['width']}x{files[0]['height']}  by {v['user']['name']}")
    if not saved:
        raise SystemExit("Không tìm thấy clip phù hợp, thử từ khóa tiếng Anh khác.")
    sheet = out / f"_{slug}.jpg"
    ins = sum((["-ss", "1", "-i", str(p)] for p in saved), [])
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
                    "".join(f"[{i}:v]scale=480:270,setsar=1[t{i}];" for i in range(len(saved))) +
                    "".join(f"[t{i}]" for i in range(len(saved))) + f"hstack=inputs={len(saved)}" if len(saved) > 1 else "[0:v]scale=480:270",
                    "-frames:v", "1", str(sheet)], check=True)
    print("xem:", sheet)


if __name__ == "__main__":
    main()
