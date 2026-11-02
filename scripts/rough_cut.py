"""Rough cut from the camera-A transcript: drop silences, fillers and retakes, pick angles.

    python -X utf8 rough_cut.py <edit> [--gap 0.6] [--pad-in 0.12] [--pad-out 0.18] [--switch 20]
    python -X utf8 rough_cut.py <edit> --text      # only rebuild timeline.md from plan.segments

Writes plan.json "segments" ([{src, in, out, cam, why?}] in camera-A seconds) and two files to read:
  cut_review.md  every kept segment with its words, and everything dropped (with the reason)
  timeline.md    the spoken text on the OUTPUT clock, one sentence per line, for planning cards

Rules (Thang-Edit hard rules): cut edges snap to word boundaries, never inside a word, padded
30-200 ms; a pause shorter than --gap stays in so speech keeps its breath.
Retake: a sentence whose first 3 words (or 80 % of its text) reappear within 20 s is the
failed take; the later one is kept. This is a heuristic, so read cut_review.md before render.
Angles: with a camera B, switch angle at a cut once the current angle has run --switch seconds;
B runs at most --b-max seconds, so A stays the main angle like the reference videos.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from common import load_plan

FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "hmm", "mm", "ah", "eh",
           "ờ", "à", "ừm", "ờm", "ơ", "ừ", "ầy", "ừa"}


def norm(w: str) -> str:
    return re.sub(r"[^\w']+", "", w.lower())


def fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def sentences(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 9
        if w["w"][-1:] in ".!?" or gap > .8:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def find_retakes(words, sents):
    drop = set()
    texts = [[norm(words[i]["w"]) for i in s] for s in sents]
    for k, s in enumerate(sents):
        a = [x for x in texts[k] if x]
        if len(a) < 3:
            continue
        for j in range(k + 1, len(sents)):
            if words[sents[j][0]]["s"] - words[s[-1]]["e"] > 20:
                break
            b = [x for x in texts[j] if x]
            same_start = len(b) >= 3 and a[:3] == b[:3]
            similar = difflib.SequenceMatcher(None, " ".join(a), " ".join(b[:len(a) + 2])).ratio() > .8
            if same_start or similar:
                drop.add(k)
                break
    return drop


def build_segments(words, keep, a):
    segs, cur = [], None
    for i in keep:
        # a dropped word in between forces a cut, otherwise its audio would stay in
        if cur and cur[-1] == i - 1 and words[i]["s"] - words[cur[-1]]["e"] <= a.gap:
            cur.append(i)
        else:
            if cur:
                segs.append(cur)
            cur = [i]
    if cur:
        segs.append(cur)
    out = []
    for n, s in enumerate(segs):
        prev_end = words[segs[n - 1][-1]]["e"] if n else 0
        next_start = words[segs[n + 1][0]]["s"] if n + 1 < len(segs) else 1e9
        st = max(words[s[0]]["s"] - a.pad_in, (prev_end + words[s[0]]["s"]) / 2, 0)
        en = min(words[s[-1]]["e"] + a.pad_out, (words[s[-1]]["e"] + next_start) / 2)
        out.append({"src": "A", "in": round(st, 3), "out": round(en, 3), "words": s})
    merged = []
    for s in out:  # cuts closer than 0.15 s are not worth a cut
        if merged and s["in"] - merged[-1]["out"] < .15:
            merged[-1]["out"] = s["out"]
            merged[-1]["words"] += s["words"]
        else:
            merged.append(s)
    return merged


def split_long(segs, words, limit):
    """Split segments longer than `limit` at sentence ends (no time removed) so the angle can change."""
    out = []
    for s in segs:
        cur = dict(s, words=[])
        for k, i in enumerate(s["words"]):
            cur["words"].append(i)
            nxt = s["words"][k + 1] if k + 1 < len(s["words"]) else None
            if nxt is not None and words[i]["w"][-1:] in ".!?" and words[i]["e"] - cur["in"] >= limit:
                cut = round((words[i]["e"] + words[nxt]["s"]) / 2, 3)
                out.append(dict(cur, out=cut))
                cur = dict(s, words=[], **{"in": cut})
        out.append(cur)
    return out


def pick_angles(segs, has_b, switch, b_max):
    cam, run = "A", 0.0
    for s in segs:
        d = s["out"] - s["in"]
        if has_b and run > 0 and (run >= (b_max if cam == "B" else switch)):
            cam, run = ("B" if cam == "A" else "A"), 0.0
        s["cam"] = cam
        run += d


def write_timeline(edit: Path, plan: dict, words):
    lines, t_out = [], 0.0
    for seg in plan["segments"]:
        ws = [w for w in words if w["s"] >= seg["in"] - 1e-3 and w["e"] <= seg["out"] + 1e-3]
        for w in ws:
            w["o"] = t_out + (w["s"] - seg["in"])
        if ws:
            lines.append(ws)
        t_out += seg["out"] - seg["in"]
    flat = [w for ws in lines for w in ws]
    out, cur = [], []
    for i, w in enumerate(flat):
        cur.append(w)
        if w["w"][-1:] in ".!?" or i + 1 == len(flat):
            out.append(f"[{fmt(cur[0]['o'])}–{fmt(cur[-1]['o'] + cur[-1]['e'] - cur[-1]['s'])}] {' '.join(x['w'] for x in cur)}")
            cur = []
    (edit / "timeline.md").write_text(
        f"# Lời thoại theo đồng hồ OUTPUT ({fmt(t_out)})\n\nDùng các mốc này cho cards/captions/broll trong plan.json.\n\n" + "\n".join(out) + "\n",
        encoding="utf-8")
    json.dump([{"o": round(w["o"], 3), "d": round(w["e"] - w["s"], 3), "w": w["w"]} for w in flat],
              open(edit / "timeline_words.json", "w", encoding="utf-8"), ensure_ascii=False)
    return t_out



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--gap", type=float, default=0.6, help="khoảng lặng dài hơn mức này thì cắt (s)")
    ap.add_argument("--pad-in", type=float, default=0.12)
    ap.add_argument("--pad-out", type=float, default=0.18)
    ap.add_argument("--switch", type=float, default=20, help="đổi góc sau bao nhiêu giây ở góc A")
    ap.add_argument("--b-max", type=float, default=10, help="góc B chạy tối đa bao nhiêu giây")
    ap.add_argument("--keep-retakes", action="store_true")
    ap.add_argument("--text", action="store_true", help="chỉ dựng lại timeline.md từ plan.segments")
    a = ap.parse_args()
    edit = Path(a.edit).resolve()
    plan = load_plan(edit)
    src_a = Path(plan["sources"]["A"])
    tr = json.loads((edit / "transcripts" / f"{src_a.stem}.json").read_text(encoding="utf-8"))
    words = tr["words"]

    if a.text:
        print(f"timeline.md: {fmt(write_timeline(edit, plan, words))}")
        return

    drop_fill = {i for i, w in enumerate(words) if norm(w["w"]) in FILLERS}
    sents = sentences(words)
    retake = set() if a.keep_retakes else find_retakes(words, sents)
    drop_retake = {i for k in retake for i in sents[k]}
    keep = [i for i in range(len(words)) if i not in drop_fill and i not in drop_retake]
    segs = build_segments(words, keep, a)
    has_b = "B" in plan.get("sources", {})
    if has_b:
        segs = split_long(segs, words, a.b_max)
    pick_angles(segs, has_b, a.switch, a.b_max)

    raw = json.loads((edit / "plan.json").read_text(encoding="utf-8"))
    raw["segments"] = [{k: s[k] for k in ("src", "in", "out", "cam")} for s in segs]
    (edit / "plan.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    plan["segments"] = raw["segments"]
    total = write_timeline(edit, plan, words)

    rv = [f"# Cắt thô: {len(segs)} đoạn, {fmt(tr['duration'])} -> {fmt(total)}\n", "## Bỏ vì nói lại (kiểm tra kỹ)\n"]
    rv += [f"- [{fmt(words[sents[k][0]]['s'])}] {' '.join(words[i]['w'] for i in sents[k])}" for k in sorted(retake)] or ["- (không có)"]
    rv += ["\n## Từ đệm đã bỏ\n", ", ".join(f"{words[i]['w']}@{fmt(words[i]['s'])}" for i in sorted(drop_fill)) or "(không có)", "\n## Đoạn giữ lại\n"]
    t = 0.0
    for n, s in enumerate(segs):
        d = s["out"] - s["in"]
        rv.append(f"{n:03d} out {fmt(t)} | src {fmt(s['in'])}-{fmt(s['out'])} | cam {s['cam']} | {' '.join(words[i]['w'] for i in s['words'])}")
        t += d
    (edit / "cut_review.md").write_text("\n".join(rv) + "\n", encoding="utf-8")
    print(f"{len(segs)} đoạn, {fmt(tr['duration'])} -> {fmt(total)}; nói lại bỏ {len(retake)} câu, từ đệm {len(drop_fill)}")
    print("đọc:", edit / "cut_review.md", "và", edit / "timeline.md")


if __name__ == "__main__":
    main()
