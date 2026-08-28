"""Render oncesi tek kare onizleme.

Videonun tamamini indirmeden, yt-dlp'nin verdigi dogrudan akis adresinden tek
bir kare cekiyoruz (birkac saniye). Kare diske yaziliyor; zoom degistikce ayni
kare gercek render filtresiyle yeniden kadrajlaniyor -- o adim anlik oldugu
icin kaydiraci oynatirken kadraj canli guncelleniyor.

Kadraj hesabi ve filtre zinciri render.py'den geliyor: onizlemede gordugun
cerceve, ciktidaki cerceveyle ayni kodun urunu.
"""
import hashlib
import json
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

from . import captions, render
from .tools import ffmpeg_dir, probe_dimensions, require_ffmpeg

# Onizleme icin dusuk cozunurluk yetiyor: kare 1080'e buyutulup kadrajlaniyor,
# ekranda kucuk gorunuyor. Dusuk format = cok daha hizli kare cekme.
FRAME_FORMAT = ("bestvideo[height<=480][ext=mp4]/bestvideo[height<=480]/"
                "best[height<=480]/worst[ext=mp4]/worst")

SAMPLE_STEP = 0.35     # ornek altyazi kelimelerinin araligi
FRAME_AT = 0.4         # ass zaman cizelgesinde bu ana bakiyoruz (pop bitmis olur)


def _key(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:12]


def _extract(url: str) -> dict:
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "format": FRAME_FORMAT, "ffmpeg_location": ffmpeg_dir(),
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    fmt = info if info.get("url") else (info.get("requested_formats") or [{}])[0]
    if not fmt.get("url"):
        raise RuntimeError("Videonun akis adresi alinamadi.")
    return {
        "title": (info.get("title") or "video").strip(),
        "duration": float(info.get("duration") or 0),
        "stream": fmt["url"],
        "headers": fmt.get("http_headers") or {},
    }


def _grab(meta: dict, at: float, frame: Path) -> None:
    """Akistan tek kare ceker."""
    cmd = [require_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    if meta["headers"]:
        cmd += ["-headers", "".join(f"{k}: {v}\r\n" for k, v in meta["headers"].items())]
    cmd += ["-ss", f"{max(0.0, at):.2f}", "-i", meta["stream"],
            "-frames:v", "1", "-q:v", "3", str(frame)]
    res = subprocess.run(cmd, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if res.returncode != 0 or not frame.exists():
        raise RuntimeError(f"Kare alinamadi:\n{(res.stderr or '')[-400:]}")


def _sample_words(text: str) -> list:
    words = [w for w in (text or "").split() if w][:4] or ["ornek", "altyazi"]
    return [{"word": w, "start": i * SAMPLE_STEP, "end": i * SAMPLE_STEP + 0.3}
            for i, w in enumerate(words)]


def _compose(frame: Path, out: Path, workdir: Path, layout: dict, ass_name: str,
             mirror: bool = False):
    """Kareyi gercek render filtresinden gecirir."""
    cmd = [
        require_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-t", "1", "-i", str(frame),
        "-filter_complex", render.build_filter(layout, ass_name, mirror),
        "-map", "[vout]", "-ss", str(FRAME_AT), "-frames:v", "1", "-q:v", "3",
        str(out.resolve()),
    ]
    res = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if res.returncode != 0 or not out.exists():
        raise RuntimeError(f"Onizleme uretilemedi:\n{(res.stderr or '')[-400:]}")


def build(url: str, root: Path, zoom: float = 1.4, at: float = 0.25,
          with_captions: bool = False, highlight: str = "#FFD400",
          font: str = "Arial Black", sample: str = "ornek altyazi",
          part_minutes: float = 4.0, mirror: bool = False) -> dict:
    """Onizleme karesi uretir ve dosya adini + kadraj bilgisini dondurur."""
    key = _key(url)
    workdir = root / key
    workdir.mkdir(parents=True, exist_ok=True)
    meta_file = workdir / "meta.json"

    at = min(0.98, max(0.0, float(at)))
    slot = round(at * 1000)
    frame = workdir / f"frame-{slot:04d}.jpg"

    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    if not frame.exists() or not meta:
        info = _extract(url)                 # akis adresi kisa omurlu, her seferinde tazele
        _grab(info, (info["duration"] or 0) * at, frame)
        meta = {"title": info["title"], "duration": info["duration"]}
        meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    src_w, src_h = probe_dimensions(frame)   # oran onemli, cozunurluk degil
    layout = render.compute_layout(src_w, src_h, zoom)

    words = _sample_words(sample) if with_captions else []
    ass_name = f"prev-{slot:04d}.ass"
    (workdir / ass_name).write_text(
        captions.build_ass(words, 0.0, 1.0, meta["title"], 1,
                           max(1, round((meta["duration"] or 0) / (part_minutes * 60)) or 1),
                           font=font, highlight=highlight,
                           include_words=with_captions),
        encoding="utf-8",
    )

    tag = (f"{round(zoom * 100)}-{1 if with_captions else 0}"
           f"-{highlight.lstrip('#')}-{1 if mirror else 0}")
    out = workdir / f"out-{slot:04d}-{tag}.jpg"
    _compose(frame, out, workdir, layout, ass_name, mirror)

    crop = max(0.0, (1 - render.W / layout["scaled_w"]) / 2 * 100)
    return {
        "image": f"/preview/{key}/{out.name}",
        "title": meta["title"],
        "duration": meta["duration"],
        "at": (meta["duration"] or 0) * at,
        "video_h": layout["video_h"],
        "band": layout["band"],
        "crop": round(crop, 1),
        "source": f"{src_w}x{src_h}",
    }
