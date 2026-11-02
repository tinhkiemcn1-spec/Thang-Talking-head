"""plan.json -> animated cards (cards/<id>.mp4) and caption stills (captions/<id>.png).

    python -X utf8 render_cards.py <edit> [--only c03,c07] [--stills] [--workers 4] [--force]

Cards are HTML (templates/card.html) driven frame by frame through Playwright, so a frame is
a pure function of time. Frames after the last reveal are identical and reused, which makes
long holds free. Each card is cached by the hash of its JSON + font + template files.
--stills writes only the settled frame of every card plus cards/_sheet.jpg to review the
look before spending time on video.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from common import TEMPLATES, icons, load_plan, resolve


def card_hash(card: dict, font: str) -> str:
    h = hashlib.sha1(json.dumps(card, sort_keys=True, ensure_ascii=False).encode())
    h.update(font.encode())
    for f in ("card.js", "card.css", "card.html"):
        h.update((TEMPLATES / f).read_bytes())
    return h.hexdigest()[:16]


def prepare(card: dict, edit: Path) -> dict:
    c = dict(card)
    if c.get("image"):
        c["image"] = resolve(edit, c["image"]).resolve().as_uri()
    return c


async def load(page, card, ico, font):
    await page.goto((TEMPLATES / "card.html").resolve().as_uri())
    settle = await page.evaluate("([c, i, o]) => build(c, i, o)", [card, ico, {"font": font}])
    await page.evaluate("Promise.all([document.fonts.ready, ...[...document.images].map(i => i.decode().catch(() => 0))])")
    return settle


async def render_video(page, card, out: Path, fps: int, ico, font):
    settle = await load(page, card, ico, font)
    n = max(1, round((card["end"] - card["t"]) * fps))
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), str(out),
        stdin=asyncio.subprocess.PIPE)
    last = None
    for f in range(n):
        t = f / fps
        if last is None or t <= settle + 1 / fps:
            await page.evaluate(f"seek({t})")
            last = await page.screenshot(type="jpeg", quality=93)
        proc.stdin.write(last)
        await proc.stdin.drain()
    proc.stdin.close()
    if await proc.wait():
        raise RuntimeError(f"ffmpeg lỗi khi ghi {out}")


async def render_still(page, card, out: Path, ico, font, transparent=False):
    settle = await load(page, card, ico, font)
    await page.evaluate(f"seek({settle + 1})")
    if transparent:
        await page.screenshot(path=str(out), type="png", omit_background=True)
    else:
        await page.screenshot(path=str(out), type="jpeg", quality=90)


def sheet(stills: list[Path], out: Path):
    from PIL import Image, ImageDraw
    if not stills:
        return
    w, h, cols = 480, 270, 4
    rows = (len(stills) + cols - 1) // cols
    im = Image.new("RGB", (w * cols, (h + 28) * rows), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for i, p in enumerate(stills):
        x, y = (i % cols) * w, (i // cols) * (h + 28)
        im.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y))
        d.text((x + 8, y + h + 6), p.stem, fill=(230, 230, 230))
    im.save(out, quality=88)


async def main_async(a):
    from playwright.async_api import async_playwright

    edit = Path(a.edit).resolve()
    plan = load_plan(edit)
    font, fps = plan["font"], plan["fps"]
    only = set(a.only.split(",")) if a.only else None
    ico = icons()
    (edit / "cards").mkdir(exist_ok=True)
    (edit / "captions").mkdir(exist_ok=True)
    stills_dir = edit / "cards" / "_stills"
    stills_dir.mkdir(exist_ok=True)

    jobs = []
    for c in plan["cards"]:
        if only and c["id"] not in only:
            continue
        card = prepare(c, edit)
        hsh = card_hash(card, font)
        if a.stills:
            jobs.append(("still", card, stills_dir / f"{c['id']}.jpg", None))
            continue
        out = edit / "cards" / f"{c['id']}.mp4"
        stamp = out.with_suffix(".hash")
        if not a.force and out.exists() and stamp.exists() and stamp.read_text() == hsh:
            continue
        jobs.append(("video", card, out, (stamp, hsh)))
    for c in plan["captions"]:
        if only and c["id"] not in only:
            continue
        jobs.append(("caption", {**c, "layout": "caption"}, edit / "captions" / f"{c['id']}.png", None))

    if not jobs:
        print("Không có gì cần render (đã cache). Dùng --force để render lại.")
        return
    print(f"{len(jobs)} việc, {a.workers} trang song song…", flush=True)
    queue: asyncio.Queue = asyncio.Queue()
    for j in jobs:
        queue.put_nowait(j)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--allow-file-access-from-files"])

        async def worker():
            page = await browser.new_page(viewport={"width": plan["width"], "height": plan["height"]})
            page.on("pageerror", lambda e: print("  lỗi JS:", e))
            while not queue.empty():
                kind, card, out, stamp = queue.get_nowait()
                if kind == "video":
                    await render_video(page, card, out, fps, ico, font)
                    stamp[0].write_text(stamp[1])
                elif kind == "still":
                    await render_still(page, card, out, ico, font)
                else:
                    await render_still(page, card, out, ico, font, transparent=True)
                print(f"  {out.name}", flush=True)
            await page.close()

        await asyncio.gather(*(worker() for _ in range(a.workers)))
        await browser.close()

    if a.stills:
        stills = sorted(stills_dir.glob("*.jpg"))
        sheet(stills, edit / "cards" / "_sheet.jpg")
        print("xem:", edit / "cards" / "_sheet.jpg")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--only")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    asyncio.run(main_async(ap.parse_args()))
