"""ffmpeg ile 9:16 render: blur arka plan + ortalanmis video + (istege bagli) altyazi."""
import subprocess
from pathlib import Path

from .tools import probe_dimensions, require_ffmpeg

W, H = 1080, 1920


def _even(n: int) -> int:
    n = int(round(n))
    return n if n % 2 == 0 else n + 1


def compute_layout(src_w: int, src_h: int, zoom: float = 1.4) -> dict:
    """Videonun kadraj icindeki boyutunu hesaplar.

    zoom=1.0  -> video tamamen sigar, hic kesilmez (en genis blur seritleri)
    zoom>1.0  -> video buyur, saga/sola tasan kisim kirpilir, seritler kisalir
    """
    zoom = max(1.0, min(3.5, float(zoom)))

    fit_h = W * src_h / src_w          # kirpma yokken yukseklik
    target_h = _even(min(H, fit_h * zoom))
    scaled_w = _even(src_w * target_h / src_h)

    if scaled_w < W:
        # Kaynak zaten dar/dikey: yatayda kirpacak fazlalik yok, genislige sigdir.
        scaled_w = W
        target_h = _even(min(H, src_h * W / src_w))

    band = max(0, (H - target_h) // 2)
    return {"scaled_w": scaled_w, "scaled_h": target_h,
            "video_h": target_h, "band": band}


# Blur'u 1080x1920'de almak pahaliydi: kare basina en buyuk maliyet oydu.
# Once dortte bir olcege indirip orada bulaniklastirip geri buyutuyoruz.
# Gozle fark yok (zaten bulanik goruntu), render iki kata yakin hizlaniyor.
BLUR_W, BLUR_H = W // 4, H // 4     # 270x480
BLUR_SIGMA = 7                      # 28 / 4 -- kucuk olcekte ayni yayilma


def build_filter(layout: dict, ass_name: str = None) -> str:
    chain = (
        f"[0:v]scale={BLUR_W}:{BLUR_H}:force_original_aspect_ratio=increase,"
        f"crop={BLUR_W}:{BLUR_H},gblur=sigma={BLUR_SIGMA},eq=brightness=-0.08,"
        f"scale={W}:{H}[bg];"
        f"[0:v]scale={layout['scaled_w']}:{layout['scaled_h']},"
        f"crop={W}:{layout['scaled_h']}[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
    )
    if ass_name:
        return chain + f";[base]ass={ass_name}[vout]"
    return chain.replace("[base]", "[vout]")


def _encoder_args(use_nvenc: bool):
    if use_nvenc:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr",
                "-cq", "21", "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]


def _build_cmd(source: Path, start: float, duration: float, filter_str: str,
               out_path: Path, use_nvenc: bool):
    return [
        require_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-progress", "pipe:1", "-nostats",
        "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
        "-i", str(Path(source).resolve()),
        "-filter_complex", filter_str,
        "-map", "[vout]", "-map", "0:a?",
        *_encoder_args(use_nvenc),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(Path(out_path).resolve()),
    ]


def render_part(source: Path, workdir: Path, ass_name, start: float,
                duration: float, out_path: Path, layout: dict,
                use_nvenc: bool = True, on_progress=None) -> bool:
    """Tek bir partı render eder. NVENC patlarsa libx264 ile tekrar dener.

    ass= filtresine mutlak yol vermek yerine ffmpeg'i workdir icinde calistirip
    goreli dosya adi veriyoruz -- Windows'ta yol escape sorunu boylece hic yok.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    filter_str = build_filter(layout, ass_name)

    for nvenc in ([True, False] if use_nvenc else [False]):
        cmd = _build_cmd(source, start, duration, filter_str, out_path, nvenc)
        proc = subprocess.Popen(
            cmd, cwd=str(workdir), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms=") and on_progress and duration > 0:
                try:
                    done = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                on_progress(min(100.0, done / duration * 100))
        proc.wait()
        if proc.returncode == 0:
            return nvenc
        err = (proc.stderr.read() or "").strip()
        if nvenc and any(k in err.lower() for k in
                         ("nvenc", "cuda", "encoder", "driver", "gpu")):
            continue  # NVENC olmadi, CPU ile dene
        raise RuntimeError(f"ffmpeg render hatasi:\n{err[-1500:]}")
    return False
