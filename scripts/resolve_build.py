"""plan.json -> editable DaVinci Resolve timeline (needs render_cards.py first).

    python -X utf8 resolve_build.py <edit> [--name "Tên timeline"]
    python -X utf8 resolve_build.py install-script     # adds Workspace > Scripts > Thang Talking-head Build

Tracks: V1 talking head (cut + angle), V2 b-roll, V3 cards, V4 captions, V5 logo;
A1 camera-A audio, A2 card SFX. Cards, b-roll and captions get Cross Dissolves of plan.fade
(Resolve 21 TimelineItem.AddTransition). The auto grade goes in as a CDL on node 1 of every
talking-head clip (white-balance gains -> slope, saturation), so the colourist starts from it.
External scripting needs Resolve Studio with Preferences > System > General > External scripting
= Local. On the free version run the menu script inside Resolve instead (same code).
An existing timeline is never replaced: a taken name gets " 2", " 3" ...
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

POINTER = Path(os.environ.get("APPDATA", Path.home())) / "thang-talking-head" / "last_edit.json"


def connect():
    if sys.platform == "win32":
        api = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting"
        os.environ.setdefault("RESOLVE_SCRIPT_API", str(api))
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blackmagic Design/DaVinci Resolve/fusionscript.dll"))
        sys.path.append(str(api / "Modules"))
    elif sys.platform == "darwin":
        sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
    import DaVinciResolveScript as dvr
    return dvr.scriptapp("Resolve")


def cdl_from_grade(f: str) -> dict | None:
    gains = [1.0, 1.0, 1.0]
    for m in re.finditer(r"colorchannelmixer=rr=([\d.]+):gg=([\d.]+):bb=([\d.]+)", f or ""):
        gains = [g * float(x) for g, x in zip(gains, m.groups())]
    sat = re.search(r"saturation=([\d.]+)", f or "")
    if gains == [1.0, 1.0, 1.0] and not sat:
        return None
    return {"NodeIndex": "1", "Slope": " ".join(f"{g:.4f}" for g in gains), "Offset": "0 0 0", "Power": "1 1 1",
            "Saturation": f"{float(sat.group(1)) if sat else 1.0:.3f}"}


def build(resolve, edit: Path, name: str | None = None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import SFX_DIR, load_plan, probe, resolve as rpath, run

    plan = load_plan(edit)
    fps = plan["fps"]
    F = lambda s: int(round(s * fps))  # noqa: E731
    project = resolve.GetProjectManager().GetCurrentProject()
    pool = project.GetMediaPool()
    if not pool.GetRootFolder().GetClipList():
        project.SetSetting("timelineFrameRate", str(fps))
        project.SetSetting("timelineResolutionWidth", str(plan["width"]))
        project.SetSetting("timelineResolutionHeight", str(plan["height"]))
    names = {project.GetTimelineByIndex(i).GetName() for i in range(1, project.GetTimelineCount() + 1)}
    base = name or edit.name
    name, k = base, 2
    while name in names:
        name, k = f"{base} {k}", k + 1

    folder = pool.AddSubFolder(pool.GetRootFolder(), name)
    pool.SetCurrentFolder(folder)
    cache = {}

    def item(path: Path):
        key = str(Path(path).resolve())
        if key not in cache:
            got = pool.ImportMedia([key])
            if not got:
                raise SystemExit(f"Resolve không nhập được {key}")
            cache[key] = got[0]
        return cache[key]

    tl = pool.CreateEmptyTimeline(name)
    project.SetCurrentTimeline(tl)
    while tl.GetTrackCount("video") < 5:
        tl.AddTrack("video")
    while tl.GetTrackCount("audio") < 2:
        tl.AddTrack("audio", "stereo")
    for i, n in enumerate(["Talking head", "B-roll", "Cards", "Captions", "Logo"], 1):
        tl.SetTrackName("video", i, n)
    start = tl.GetStartFrame()
    fade = F(plan["fade"])

    def put(path, src_in, dur, track, rec, media=1):
        info = {"mediaPoolItem": item(path), "startFrame": src_in, "endFrame": src_in + dur,
                "trackIndex": track, "recordFrame": start + rec, "mediaType": media}
        got = pool.AppendToTimeline([info])
        return got[0] if got else None

    def still(png: Path, seconds: float, width: int | None = None) -> Path:
        """Resolve gives imported stills a fixed 5 s, so stills become ProRes 4444 clips with alpha."""
        out = edit / "resolve" / f"{Path(png).stem}_{round(seconds * fps)}.mov"
        if not out.exists():
            out.parent.mkdir(exist_ok=True)
            vf = (f"scale={width}:-2," if width else "") + "format=yuva444p10le"
            run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", fps, "-t", f"{seconds:.3f}", "-i", png,
                 "-vf", vf, "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", out])
        return out

    def dissolve(ti, frames):
        if ti and frames > 0:
            for pos in ("start", "end"):
                ti.AddTransition({"type": "Cross Dissolve", "category": "simple", "position": pos, "alignment": "right" if pos == "start" else "left", "duration": frames})

    rec = 0
    for s in plan["segments"]:
        cam = s.get("cam", "A")
        off = plan.get("offsets", {}).get(cam, 0.0)
        dur = F(s["out"]) - F(s["in"])
        v = put(plan["sources"][cam], F(s["in"] + off), dur, 1, rec, 1)
        put(plan["sources"]["A"], F(s["in"]), dur, 1, rec, 2)
        cdl = cdl_from_grade(plan.get("grade", {}).get(cam, ""))
        if v and cdl:
            v.SetCDL(cdl)
        if v and s.get("zoom", 1) != 1:
            v.SetProperty("ZoomX", float(s["zoom"]))
            v.SetProperty("ZoomY", float(s["zoom"]))
        rec += dur
    for b in plan["broll"]:
        dissolve(put(rpath(edit, b["file"]), F(b.get("src", 0)), F(b["end"]) - F(b["t"]), 2, F(b["t"])), F(b.get("fade", plan["fade"])))
    for c in plan["cards"]:
        dissolve(put(edit / "cards" / f"{c['id']}.mp4", 0, F(c["end"]) - F(c["t"]), 3, F(c["t"])), F(c.get("fade", plan["fade"])))
        if c.get("sfx"):
            put(SFX_DIR / f"{c['sfx']}.wav", 0, F(0.8), 2, F(c["t"]), 2)
    for c in plan["captions"]:
        d = F(c["end"]) - F(c["t"])
        dissolve(put(still(edit / "captions" / f"{c['id']}.png", d / fps), 0, d, 4, F(c["t"])), F(0.25))
    if plan.get("logo"):
        lg = plan["logo"] if isinstance(plan["logo"], dict) else {"file": plan["logo"]}
        clip = still(rpath(edit, lg["file"]), rec / fps, lg.get("width", 150))
        ti = put(clip, 0, rec, 5, 0)
        if ti:
            # the clip comes in at its own pixel size, centred: move it to the corner like render.py
            v = probe(clip)["v"]
            m = lg.get("margin", 32)
            ti.SetProperty("Pan", plan["width"] / 2 - m - v["width"] / 2)
            ti.SetProperty("Tilt", plan["height"] / 2 - m - v["height"] / 2)
            ti.SetProperty("Opacity", lg.get("opacity", 0.9) * 100)
    resolve.OpenPage("edit")
    print(f"Timeline '{name}': {len(plan['segments'])} đoạn, {len(plan['cards'])} card, {len(plan['captions'])} chữ chốt, "
          f"{len(plan['broll'])} b-roll, {rec / fps:.1f}s")
    return tl


MENU = r'''"""Thang Talking-head: build a timeline from the last edit folder (Workspace > Scripts)."""
import json, os, sys
info = json.load(open(os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "thang-talking-head", "last_edit.json"), encoding="utf-8"))
sys.path.insert(0, info["scripts"])
import resolve_build
from pathlib import Path
resolve_build.build(resolve, Path(info["edit"]))
'''


def install_script():
    if sys.platform == "win32":
        d = Path(os.environ["APPDATA"]) / "Blackmagic Design/DaVinci Resolve/Support/Fusion/Scripts/Utility"
    elif sys.platform == "darwin":
        d = Path.home() / "Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"
    else:
        d = Path.home() / ".local/share/DaVinciResolve/Fusion/Scripts/Utility"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Thang Talking-head Build.py").write_text(MENU, encoding="utf-8")
    print("Đã cài:", d / "Thang Talking-head Build.py")


if __name__ == "__main__":
    if sys.argv[1:] == ["install-script"]:
        install_script()
        sys.exit()
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--name")
    a = ap.parse_args()
    edit = Path(a.edit).resolve()
    POINTER.parent.mkdir(parents=True, exist_ok=True)
    POINTER.write_text(json.dumps({"edit": str(edit), "scripts": str(Path(__file__).resolve().parent)}, ensure_ascii=False), encoding="utf-8")
    r = connect()
    if r is None:
        sys.exit("Không kết nối được Resolve qua script ngoài (bản Free hoặc chưa bật External scripting = Local). "
                 "Mở Resolve > Workspace > Scripts > Thang Talking-head Build (chạy install-script trước).")
    build(r, edit, a.name)
