"""Word-level transcript of one source -> <edit>/transcripts/<stem>.json (cached).

    python -X utf8 transcribe.py <video> <edit> [--model large-v3] [--lang en] [--prompt "names ..."] [--force]

faster-whisper, offline. GPU when it really works, otherwise CPU (a CUDA card without cuBLAS
loads the model and only fails at the first encode, so the fallback wraps the transcription).
Audio goes through ffmpeg because faster-whisper's PyAV decoder breaks across releases.
The filler prompt nudges Whisper to keep "um / uh / ờ" so rough_cut.py can remove them.
Creates <edit>/plan.json with this video as camera A when there is no plan yet.
Output: {"duration", "words": [{s, e, w, p}], "sentences": [{t, end, text}]}.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import common  # noqa: F401  (utf-8 stdout)

FILLER_PROMPTS = {
    "en": "Umm, so, uh, let me think... Okay, uh, here's what I mean.",
    "vi": "Ờ, thì... à, ừm, kiểu như là, ờm, mình nghĩ là vậy.",
}


def transcript_path(edit: Path, video: Path) -> Path:
    return edit / "transcripts" / f"{video.stem}.json"


def sentences(words, max_len=9.0):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 9
        span = cur[-1]["e"] - cur[0]["s"]
        if w["w"][-1:] in ".!?" or gap > .6 or span > max_len or (w["w"][-1:] == "," and span > 5):
            out.append({"t": cur[0]["s"], "end": cur[-1]["e"], "text": " ".join(x["w"] for x in cur)})
            cur = []
    return out


def run(audio, model, device, lang, prompt):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device=device, compute_type="float16" if device == "cuda" else "int8")
    segs, info = m.transcribe(audio, language=lang, vad_filter=True, word_timestamps=True, initial_prompt=prompt,
                              condition_on_previous_text=False, beam_size=5)
    words = [{"s": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip(), "p": round(w.probability, 3)}
             for s in segs for w in s.words or [] if w.word.strip()]
    return words, info.language


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("edit")
    ap.add_argument("--model", default="large-v3", help="tiny, base, small, medium, large-v3, turbo")
    ap.add_argument("--lang", default=None, help="en, vi, ... (bỏ trống = tự nhận)")
    ap.add_argument("--prompt", default=None, help="tên riêng, thuật ngữ")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    video, edit = Path(a.video).resolve(), Path(a.edit).resolve()
    out = transcript_path(edit, video)
    if out.exists() and not a.force:
        print("cached:", out)
        return
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, np.float32)
    prompt = " ".join(x for x in (FILLER_PROMPTS.get(a.lang or "en"), a.prompt) if x)
    try:
        words, lang = run(audio, a.model, "cuda", a.lang, prompt)
    except Exception as e:  # noqa: BLE001
        print("GPU không dùng được, chạy CPU:", str(e)[:120], flush=True)
        words, lang = run(audio, a.model, "cpu", a.lang, prompt)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"source": str(video), "language": lang, "duration": len(audio) / 16000, "words": words, "sentences": sentences(words)}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    plan = edit / "plan.json"
    if not plan.exists():  # single camera: this source becomes camera A
        plan.write_text(json.dumps({"sources": {"A": str(video)}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(words)} từ, {len(data['sentences'])} câu, {data['duration']:.1f}s, lang={lang} -> {out}")


if __name__ == "__main__":
    sys.exit(main())
