"""ffmpeg / ffprobe bulucu.

winget ile kurulan Gyan.FFmpeg PATH'e yeni kabuk acilana kadar yansimadigi icin
PATH'te bulamazsak WinGet paket klasorune de bakiyoruz.
"""
import os
import shutil
from pathlib import Path


def _find(name: str):
    found = shutil.which(name)
    if found:
        return found

    local = os.environ.get("LOCALAPPDATA")
    if local:
        base = Path(local) / "Microsoft" / "WinGet" / "Packages"
        for pattern in (f"Gyan.FFmpeg*/**/bin/{name}.exe", f"*FFmpeg*/**/bin/{name}.exe"):
            for candidate in base.glob(pattern):
                return str(candidate)
    return None


FFMPEG = _find("ffmpeg")
FFPROBE = _find("ffprobe")


def require_ffmpeg() -> str:
    if not FFMPEG:
        raise RuntimeError(
            "ffmpeg bulunamadi. Kurmak icin:\n"
            "  winget install --id Gyan.FFmpeg -e --source winget"
        )
    return FFMPEG


def ffmpeg_dir() -> str:
    return str(Path(require_ffmpeg()).parent)


def probe_dimensions(path) -> tuple:
    """Kaynak videonun (genislik, yukseklik) degerini dondurur."""
    import json
    import subprocess

    if not FFPROBE:
        raise RuntimeError("ffprobe bulunamadi.")
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    stream = json.loads(out)["streams"][0]
    return int(stream["width"]), int(stream["height"])
