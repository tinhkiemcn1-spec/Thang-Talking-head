"""Validate <edit>/plan.json before rendering. Prints PLAN OK, or errors (must fix) and warnings (taste).

    python -X utf8 check_plan.py <edit>
"""
from __future__ import annotations

import sys
from pathlib import Path

from common import ICONS_DIR, SFX_DIR, load_plan, resolve, timeline_length

LAYOUTS = {"boxes", "checklist", "flow", "compare", "equation", "bars", "stat", "timeline", "loop", "statement", "chips", "cta"}
ICONS = {p.stem for p in ICONS_DIR.glob("*.svg")}
SFX = {p.stem for p in SFX_DIR.glob("*.wav")}


def icons_in(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "icon" and isinstance(v, str):
                yield v
            else:
                yield from icons_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from icons_in(v)


def main():
    edit = Path(sys.argv[1]).resolve()
    plan = load_plan(edit)
    err, warn = [], []
    for cam, p in plan.get("sources", {}).items():
        if not Path(p).exists():
            err.append(f"nguồn {cam} không có: {p}")
    if "A" not in plan.get("sources", {}):
        err.append("thiếu sources.A (máy chính, lấy âm thanh)")
    segs = plan["segments"]
    if not segs:
        err.append("chưa có segments")
    for i, s in enumerate(segs):
        if s["out"] <= s["in"]:
            err.append(f"segment {i}: out <= in")
        if s.get("cam", "A") not in plan.get("sources", {}):
            err.append(f"segment {i}: cam {s.get('cam')} không có trong sources")
        if i and s["in"] < segs[i - 1]["out"] - 1e-3 and s.get("src") == segs[i - 1].get("src"):
            warn.append(f"segment {i}: chồng lên đoạn trước (lặp lời?)")
    total = timeline_length(plan) if segs else 0

    def window(kind, x):
        tag = f"{kind} {x['id']}"
        if x["end"] <= x["t"]:
            err.append(f"{tag}: end <= t")
        if x["end"] > total + 0.05:
            err.append(f"{tag}: kết thúc {x['end']:.2f}s, timeline chỉ dài {total:.2f}s")
        return tag

    cover = 0.0
    for c in plan["cards"]:
        tag = window("card", c)
        d = c["end"] - c["t"]
        cover += d
        if c.get("layout") not in LAYOUTS:
            err.append(f"{tag}: layout '{c.get('layout')}' không có ({', '.join(sorted(LAYOUTS))})")
        for ic in icons_in(c):
            if ic not in ICONS:
                err.append(f"{tag}: icon '{ic}' không có trong assets/icons")
        if c.get("sfx") and c["sfx"] not in SFX:
            err.append(f"{tag}: sfx '{c['sfx']}' không có ({', '.join(sorted(SFX))})")
        if c.get("image") and not resolve(edit, c["image"]).exists():
            err.append(f"{tag}: ảnh không có {c['image']}")
        if d < 3:
            warn.append(f"{tag}: chỉ {d:.1f}s, khó đọc kịp (mẫu 5-15s)")
        if d > 20:
            warn.append(f"{tag}: {d:.1f}s, quá lâu không thấy người nói")
        if len(c.get("title", "")) > 48:
            warn.append(f"{tag}: tiêu đề dài {len(c['title'])} ký tự, nên dưới 48")
        if len(c.get("items", [])) > 5:
            warn.append(f"{tag}: {len(c['items'])} mục, nên tối đa 4-5")
        for it in c.get("items", []):
            if len(str(it.get("label", "")).split()) > 4:
                warn.append(f"{tag}: nhãn '{it['label']}' dài, nên 1-3 từ")
            if it.get("at") is not None and it["at"] > d - 1:
                warn.append(f"{tag}: mục '{it.get('label')}' hiện ở {it['at']}s, sát cuối card")
    cs = sorted(plan["cards"], key=lambda c: c["t"])
    for a, b in zip(cs, cs[1:]):
        if b["t"] < a["end"]:
            err.append(f"card {a['id']} và {b['id']} chồng nhau")
        elif b["t"] - a["end"] < 2:
            warn.append(f"card {a['id']} -> {b['id']}: người nói chỉ hiện {b['t'] - a['end']:.1f}s, nên >= 4s")
    for c in plan["captions"]:
        tag = window("caption", c)
        if len(c["text"]) > 60:
            warn.append(f"{tag}: chữ dài {len(c['text'])} ký tự, nên dưới 45")
        for k in plan["cards"]:
            if c["t"] < k["end"] and k["t"] < c["end"]:
                err.append(f"{tag} trùng card {k['id']}: chữ chốt chỉ đặt lên cảnh người nói")
    for b in plan["broll"]:
        tag = window("broll", b)
        if not resolve(edit, b["file"]).exists():
            err.append(f"{tag}: không có file {b['file']}")
    if plan.get("logo"):
        f = plan["logo"]["file"] if isinstance(plan["logo"], dict) else plan["logo"]
        if not resolve(edit, f).exists():
            err.append(f"logo không có: {f}")
    if total:
        ratio = cover / total
        if ratio > .45:
            warn.append(f"card phủ {ratio:.0%} thời lượng, mẫu khoảng 30-40%")
        if ratio < .15 and total > 120:
            warn.append(f"card chỉ phủ {ratio:.0%}, mẫu khoảng 30-40%")
    for w in warn:
        print("  cảnh báo:", w)
    for e in err:
        print("  LỖI:", e)
    print(f"timeline {total:.1f}s, {len(plan['cards'])} card, {len(plan['captions'])} chữ chốt, {len(plan['broll'])} b-roll")
    print("PLAN OK" if not err else f"{len(err)} lỗi")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
