"""YouTube indirme (yt-dlp)."""
import re
from pathlib import Path

from yt_dlp import YoutubeDL

from .tools import ffmpeg_dir


def slugify(text: str, limit: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    text = re.sub(r"[\s_-]+", "-", text)
    return (text[:limit].strip("-") or "video").lower()


def download(url: str, workdir: Path, on_progress=None) -> dict:
    """Videoyu workdir/source.mp4 olarak indirir. Basligi ve suresini dondurur."""
    workdir.mkdir(parents=True, exist_ok=True)

    def hook(d):
        if not on_progress:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            pct = (done / total * 100) if total else 0
            on_progress(pct, "job.downloadPct", {"pct": round(pct)})
        elif d.get("status") == "finished":
            on_progress(100, "job.downloadMerging", {})

    opts = {
        "format": (
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(workdir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "ffmpeg_location": ffmpeg_dir(),
        "retries": 5,
        "concurrent_fragment_downloads": 4,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    source = workdir / "source.mp4"
    if not source.exists():
        # merge baska bir uzantiyla bitmis olabilir
        candidates = sorted(workdir.glob("source.*"))
        if not candidates:
            raise RuntimeError("Video indirildi ama dosya bulunamadi.")
        source = candidates[0]

    title = (info.get("title") or "video").strip()
    return {
        "path": source,
        "title": title,
        "slug": slugify(title),
        "duration": float(info.get("duration") or 0),
    }
