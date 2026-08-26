"""faster-whisper ile kelime bazli transkript. GPU denenir, olmazsa CPU.

Onemli: CUDA hatasi model olusturulurken degil, ILK encode sirasinda ortaya
cikiyor (cublas DLL'i o an yukleniyor). Bu yuzden fallback'in model yuklemeyi
degil, transkripsiyonun tamamini sarmasi gerekiyor.
"""
import subprocess
from pathlib import Path

from .tools import require_ffmpeg

_MODEL_CACHE = {}
_BATCH_CACHE = {}

# GPU'da toplu (batched) cikarim: ses parcalari tek tek degil, demet halinde
# modele giriyor. Ayni kelimeler, yaklasik ucte bir surede.
BATCH_SIZE = 8

SENTENCE_END = ".?!…"
TRAIL = "”’\"')]"   # cumle sonundaki tirnak/parantezleri at
MAX_UNIT = 14.0          # noktalama hic gelmezse en fazla bu kadar birikir


def extract_audio(source: Path, workdir: Path) -> Path:
    """Whisper icin 16kHz mono wav. mp4'u dogrudan okutmaktan daha guvenilir."""
    wav = workdir / "audio.wav"
    cmd = [
        require_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(wav),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return wav


def _get_model(size: str, device: str, compute: str):
    key = (size, device)
    if key not in _MODEL_CACHE:
        from faster_whisper import WhisperModel

        _MODEL_CACHE[key] = WhisperModel(size, device=device, compute_type=compute)
    return _MODEL_CACHE[key]


def _get_batched(model, key):
    if key not in _BATCH_CACHE:
        from faster_whisper import BatchedInferencePipeline

        _BATCH_CACHE[key] = BatchedInferencePipeline(model=model)
    return _BATCH_CACHE[key]


def _sentence_units(segments: list) -> list:
    """Segmentleri kelime noktalamasina bakarak cumlelere boler.

    Toplu cikarim uzun bloklar donduruyor; part sinirlarini cumle sonuna
    hizalayabilmek icin cumle bazli birimlere ihtiyacimiz var. Kelimeden
    uretmek Whisper'in kendi segment sinirlarindan da isabetli.
    """
    units = []

    def flush(words):
        if not words:
            return
        units.append({
            "start": words[0]["start"], "end": words[-1]["end"],
            "text": " ".join((w["word"] or "").strip() for w in words).strip(),
            "words": list(words),
        })

    cur = []
    for seg in segments:
        for w in seg["words"]:
            cur.append(w)
            tail = (w["word"] or "").strip().rstrip(TRAIL)
            long_enough = w["end"] - cur[0]["start"] >= MAX_UNIT
            if (tail and tail[-1] in SENTENCE_END) or long_enough:
                flush(cur)
                cur = []
    flush(cur)
    return units


def _run(model, audio: Path, device: str, duration: float, on_progress,
         batched: bool = False) -> list:
    """Generator'u tamamen tuketir -- hatalar burada ortaya cikar."""
    if batched:
        engine = _get_batched(model, (id(model), device))
        seg_iter, info = engine.transcribe(
            str(audio), word_timestamps=True, vad_filter=True, beam_size=5,
            batch_size=BATCH_SIZE,
        )
    else:
        seg_iter, info = model.transcribe(
            str(audio), word_timestamps=True, vad_filter=True, beam_size=5,
        )
    total = duration or float(getattr(info, "duration", 0) or 0)

    segments = []
    for seg in seg_iter:
        words = [
            {"word": w.word, "start": float(w.start), "end": float(w.end)}
            for w in (seg.words or []) if w.word and w.word.strip()
        ]
        if not words:
            continue
        segments.append({
            "start": float(seg.start), "end": float(seg.end),
            "text": (seg.text or "").strip(), "words": words,
        })
        if on_progress and total:
            pct = min(99, seg.end / total * 100)
            on_progress(pct, "job.transcribing", {"device": device.upper(), "pct": round(pct)})

    return segments, getattr(info, "language", "?")


def transcribe(audio: Path, model_size: str = "large-v3", duration: float = 0,
               on_progress=None) -> dict:
    attempts = (("cuda", "float16"), ("cpu", "int8"))
    last_error = None

    for device, compute in attempts:
        try:
            if on_progress:
                on_progress(0, "job.whisperLoading", {"model": model_size, "device": device.upper()})
            model = _get_model(model_size, device, compute)
            try:
                segments, language = _run(model, audio, device, duration,
                                          on_progress, batched=(device == "cuda"))
            except Exception:
                if device != "cuda":
                    raise
                # Toplu cikarim tutmadi: ayni cihazda tek tek dene, GPU'yu birakma
                _BATCH_CACHE.clear()
                segments, language = _run(model, audio, device, duration, on_progress)
            segments = _sentence_units(segments)
        except Exception as exc:
            last_error = exc
            _MODEL_CACHE.pop((model_size, device), None)
            if device == "cpu":
                raise
            if on_progress:
                on_progress(2, "job.gpuFallback", {"error": str(exc)[:120]})
            continue

        if not segments:
            raise RuntimeError("Videoda konusma bulunamadi, altyazi cikarilamadi.")

        if on_progress:
            on_progress(100, "job.transcriptReady", {"count": len(segments), "device": device.upper()})
        return {"segments": segments, "language": language, "device": device}

    raise last_error or RuntimeError("Transkript alinamadi.")
