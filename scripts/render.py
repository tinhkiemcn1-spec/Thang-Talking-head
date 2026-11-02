"""plan.json -> final video with ffmpeg.

    python -X utf8 render.py <edit> [--preview] [--out final.mp4] [--from 60 --to 120]

Steps
  1. segments: each kept range is cut from its camera (video) with camera-A audio, graded,
     conformed to WxH@fps, 30 ms audio fades at both ends. Cached per segment in seg/.
  2. concat with -c copy -> seg/base.mkv (lossless join, no double encode)
  3. one composite pass: base -> b-roll -> cards -> captions -> logo, every overlay with an
     alpha fade of plan.fade seconds and setpts shifted to its window; voice chain
     (highpass, denoise, de-ess, compressor), optional music bed and card SFX
  4. two-pass loudnorm to plan.audio.lufs (default -14 LUFS, true peak -1 dB)
  5. optional outro clip joined with a 0.5 s crossfade
--preview renders 960x540 ultrafast for checking timing; segments stay cached at full size.
Never overwrites: if the output exists it writes final_v2.mp4, final_v3.mp4 ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import SFX_DIR, graph_args, load_plan, probe, resolve, run, timeline_length


def seg_filter(plan, seg) -> str:
    W, H, fps = plan["width"], plan["height"], plan["fps"]
    grade = plan.get("grade", {}).get(seg.get("cam", "A"), "")
    z = float(seg.get("zoom", 1.0))
    vf = [grade] if grade else []
    vf.append(f"scale={round(W * z / 2) * 2}:{round(H * z / 2) * 2}:force_original_aspect_ratio=increase")
    vf.append(f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{seg.get('zoom_y', 0.35)}")
    vf += [f"fps={fps}", "format=yuv420p", "setsar=1"]
    return ",".join(vf)


def render_segment(plan, edit, i, seg) -> Path:
    cam = seg.get("cam", "A")
    src_v = Path(plan["sources"][cam])
    src_a = Path(plan["sources"]["A"])
    off = plan.get("offsets", {}).get(cam, 0.0)
    dur = seg["out"] - seg["in"]
    vf = seg_filter(plan, seg)
    af = f"aresample=48000,afade=t=in:st=0:d=0.03,afade=t=out:st={max(dur - 0.03, 0):.3f}:d=0.03"
    key = hashlib.sha1(json.dumps([str(src_v), str(src_a), off, seg["in"], seg["out"], vf], sort_keys=True).encode()).hexdigest()[:12]
    out = edit / "seg" / f"{i:04d}_{key}.mkv"
    if out.exists():
        return out
    tmp = out.with_suffix(".tmp.mkv")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seg['in'] + off:.3f}", "-i", src_v, "-ss", f"{seg['in']:.3f}", "-i", src_a,
         "-t", f"{dur:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-vf", vf, "-af", af,
         "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-g", str(plan["fps"] * 2), "-c:a", "pcm_s16le", "-ac", "2", tmp])
    tmp.replace(out)
    return out


def build_base(plan, edit) -> Path:
    (edit / "seg").mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        parts = list(ex.map(lambda x: render_segment(plan, edit, *x), enumerate(plan["segments"])))
    lst = edit / "seg" / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    base = edit / "seg" / "base.mkv"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base])
    return base


def voice_chain(au: dict) -> str:
    f = [f"highpass=f={au['highpass']}"]
    if au.get("denoise"):
        f.append(f"afftdn=nr={au['denoise']}:nf=-40:tn=1")
    if au.get("deess"):
        f.append("deesser=i=0.4")
    if au.get("compress"):
        f.append("acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2")
    return ",".join(f)


def composite(plan, edit, base: Path, out: Path, preview: bool, rng):
    W, H, fps, F = plan["width"], plan["height"], plan["fps"], plan["fade"]
    total = probe(base)["dur"]
    t0, t1 = rng if rng else (0.0, total)
    inputs: list = ["-i", base]
    fc: list[str] = [f"[0:v]setpts=PTS-STARTPTS[v0]"]
    cur, n = "v0", 1
    audio_mix = [f"[0:a]{voice_chain(plan['audio'])}[voice]"]
    mix_labels = ["[voice]"]

    def overlay(label, t, end, x="0", y="0"):
        nonlocal cur
        nxt = f"v{len(fc)}"
        fc.append(f"[{cur}][{label}]overlay={x}:{y}:eof_action=pass:enable='between(t,{t:.3f},{end:.3f})'[{nxt}]")
        cur = nxt

    def faded(idx, t, end, prep, fade=F):
        d = end - t
        lab = f"o{idx}"
        fc.append(f"[{idx}:v]{prep}format=yuva420p,fade=t=in:st=0:d={fade}:alpha=1,"
                  f"fade=t=out:st={max(d - fade, 0):.3f}:d={fade}:alpha=1,setpts=PTS-STARTPTS+{t:.3f}/TB[{lab}]")
        return lab

    for b in plan["broll"]:
        d = b["end"] - b["t"]
        inputs += ["-ss", f"{b.get('src', 0):.3f}", "-t", f"{d:.3f}", "-i", resolve(edit, b["file"])]
        prep = (f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                + (f"{plan['grade'].get('broll')}," if plan.get("grade", {}).get("broll") else ""))
        overlay(faded(n, b["t"], b["end"], prep, b.get("fade", F)), b["t"], b["end"])
        n += 1
    for c in plan["cards"]:
        f = edit / "cards" / f"{c['id']}.mp4"
        if not f.exists():
            raise SystemExit(f"thiếu {f}: chạy render_cards.py trước")
        inputs += ["-i", f]
        overlay(faded(n, c["t"], c["end"], f"fps={fps},", c.get("fade", F)), c["t"], c["end"])
        n += 1
        if c.get("sfx"):
            inputs += ["-i", SFX_DIR / f"{c['sfx']}.wav"]
            ms = int(c["t"] * 1000)
            audio_mix.append(f"[{n}:a]aresample=48000,volume={c.get('sfx_db', -16)}dB,adelay={ms}|{ms}[s{n}]")
            mix_labels.append(f"[s{n}]")
            n += 1
    for c in plan["captions"]:
        d = c["end"] - c["t"]
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{d:.3f}", "-i", edit / "captions" / f"{c['id']}.png"]
        overlay(faded(n, c["t"], c["end"], "", 0.25), c["t"], c["end"])
        n += 1
    if plan.get("logo"):
        lg = plan["logo"] if isinstance(plan["logo"], dict) else {"file": plan["logo"]}
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{total:.3f}", "-i", resolve(edit, lg["file"])]
        fc.append(f"[{n}:v]scale={lg.get('width', 150)}:-1,format=rgba,colorchannelmixer=aa={lg.get('opacity', 0.9)}[logo]")
        m = lg.get("margin", 32)
        pos = {"tr": (f"W-w-{m}", f"{m}"), "tl": (f"{m}", f"{m}"), "br": (f"W-w-{m}", f"H-h-{m}"), "bl": (f"{m}", f"H-h-{m}")}[lg.get("pos", "tr")]
        overlay("logo", 0, total, *pos)
        n += 1
    if plan.get("music"):
        mu = plan["music"] if isinstance(plan["music"], dict) else {"file": plan["music"]}
        inputs += ["-stream_loop", "-1", "-i", resolve(edit, mu["file"])]
        audio_mix.append(f"[{n}:a]aresample=48000,volume={mu.get('db', -26)}dB,atrim=0:{total:.3f},"
                         f"afade=t=in:d=1.5,afade=t=out:st={max(total - 3, 0):.3f}:d=3[mus]")
        mix_labels.append("[mus]")
        n += 1

    vout = cur
    if preview:
        fc.append(f"[{cur}]scale=960:540[vp]")
        vout = "vp"
    audio_mix.append(f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:normalize=0:duration=first[aout]"
                     if len(mix_labels) > 1 else "[voice]anull[aout]")
    graph = ";".join(fc + audio_mix)
    gfile = edit / "seg" / "graph.txt"
    gfile.write_text(graph, encoding="utf-8")
    enc = ["-c:v", "libx264", "-preset", "ultrafast" if preview else "medium", "-crf", "28" if preview else "18", "-pix_fmt", "yuv420p"]
    trim = ["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}"] if rng else ["-t", f"{total:.3f}"]
    run(["ffmpeg", "-y", "-v", "error", *inputs, *graph_args(gfile), "-map", f"[{vout}]", "-map", "[aout]",
         *trim, *enc, "-r", str(fps), "-c:a", "pcm_s16le", out])


def loudnorm(src: Path, out: Path, lufs: float):
    r = run(["ffmpeg", "-hide_banner", "-i", src, "-vn", "-af", f"loudnorm=I={lufs}:TP=-1:LRA=11:print_format=json", "-f", "null", "-"])
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    af = (f"loudnorm=I={lufs}:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])


def add_outro(plan, edit, main: Path, out: Path):
    o = resolve(edit, plan["outro"]["file"] if isinstance(plan["outro"], dict) else plan["outro"])
    d = probe(main)["dur"]
    W, H, fps = plan["width"], plan["height"], plan["fps"]
    run(["ffmpeg", "-y", "-v", "error", "-i", main, "-i", o, "-filter_complex",
         f"[1:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p,setsar=1[o];"
         f"[0:v]setsar=1[m];[m][o]xfade=transition=fade:duration=0.5:offset={d - 0.5:.3f}[v];"
         f"[0:a][1:a]acrossfade=d=0.5[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])


def free_name(p: Path) -> Path:
    if not p.exists():
        return p
    k = 2
    while (q := p.with_name(f"{p.stem}_v{k}{p.suffix}")).exists():
        k += 1
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--from", dest="t0", type=float)
    ap.add_argument("--to", dest="t1", type=float)
    a = ap.parse_args()
    edit = Path(a.edit).resolve()
    plan = load_plan(edit)
    if not plan["segments"]:
        raise SystemExit("plan.json chưa có segments: chạy rough_cut.py")
    print(f"1/4 cắt {len(plan['segments'])} đoạn ({timeline_length(plan):.1f}s)…", flush=True)
    base = build_base(plan, edit)
    print("2/4 ghép lớp đồ họa…", flush=True)
    mix = edit / "seg" / "mix.mkv"
    rng = (a.t0 or 0.0, a.t1 or probe(base)["dur"]) if (a.t0 is not None or a.t1 is not None) else None
    composite(plan, edit, base, mix, a.preview, rng)
    print("3/4 chuẩn hóa âm lượng…", flush=True)
    name = a.out or ("preview.mp4" if a.preview else "final.mp4")
    out = free_name(edit / name) if not a.preview else edit / name
    if plan.get("outro") and not a.preview:
        tmp = edit / "seg" / "norm.mp4"
        loudnorm(mix, tmp, plan["audio"]["lufs"])
        print("4/4 nối outro…", flush=True)
        add_outro(plan, edit, tmp, out)
    else:
        loudnorm(mix, out, plan["audio"]["lufs"])
    print(f"xong: {out} ({probe(out)['dur']:.1f}s)")


if __name__ == "__main__":
    main()
