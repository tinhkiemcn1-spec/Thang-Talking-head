"""Install the skill into Claude Code, its Python dependencies, Chromium for the cards and the Resolve menu script.

    python install.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent
DEST = Path.home() / ".claude" / "skills" / "thang-talking-head"

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
if DEST.resolve() != ROOT:
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(ROOT, DEST, ignore=shutil.ignore_patterns(".git", "__pycache__", ".env"))
    print("Skill:", DEST)
subprocess.run([sys.executable, "-X", "utf8", str(DEST / "scripts" / "resolve_build.py"), "install-script"], check=False)
if not shutil.which("ffmpeg"):
    print("Cần cài ffmpeg (bản 6 trở lên) và thêm vào PATH: winget install Gyan.FFmpeg")
print("Xong. Trong Claude Code gõ /thang-talking-head")
