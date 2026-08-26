"""Tek komutla ClipCloverKurulum.exe uretir.

Sirasiyla:
  1. vendor/ffmpeg bos ise doldurur (vendor_ffmpeg.py)
  2. PyInstaller ile dist/ClipClover klasorunu derler (clipclover.spec)
  3. Inno Setup ile dagitim/ClipCloverKurulum.exe kurulum dosyasini yapar

Derleme .buildvenv icindeki temiz ortamla yapiliyor. Sebebi: ana Python'da
CUDA paketleri kurulu ve onlar pakete girerse boyut 2 GB'i asiyor. Ayri ortam
ayni zamanda "bende calisiyordu" durumunu da onluyor.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_PY = ROOT / ".buildvenv" / "Scripts" / "python.exe"
FFMPEG = ROOT / "vendor" / "ffmpeg" / "ffmpeg.exe"
# Kurulum ekraninin gorselleri. Pillow gerektirdigi icin ana Python'la degil
# .buildvenv ile uretiliyorlar.
BANT = ROOT / "brand" / "setup" / "bant-164x314.bmp"
CIKTI = ROOT / "dagitim" / "ClipCloverKurulum.exe"

ISCC_ADAYLARI = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def baslik(text: str):
    print()
    print(f"  {text}")
    print("  " + "-" * (len(text) + 2))


def iscc() -> Path:
    for aday in ISCC_ADAYLARI:
        if aday.is_file():
            return aday
    raise SystemExit(
        "Inno Setup bulunamadi. Kurmak icin:\n"
        "  winget install --id JRSoftware.InnoSetup -e --source winget"
    )


def calistir(cmd: list):
    print("  >", " ".join(str(c) for c in cmd))
    sonuc = subprocess.run(cmd, cwd=ROOT)
    if sonuc.returncode != 0:
        raise SystemExit(f"Adim basarisiz oldu (kod {sonuc.returncode}).")


def main() -> int:
    if not BUILD_PY.is_file():
        raise SystemExit(
            "Derleme ortami yok. Bir kereligine kur:\n"
            "  python -m venv .buildvenv\n"
            "  .buildvenv/Scripts/python.exe -m pip install -r requirements.txt pyinstaller"
        )

    if not FFMPEG.is_file():
        baslik("1/3  ffmpeg indiriliyor")
        calistir([sys.executable, str(ROOT / "vendor_ffmpeg.py")])
    else:
        baslik("1/3  ffmpeg zaten var, atlandi")

    if not BANT.is_file():
        baslik("1b/3  Kurulum ekraninin gorselleri uretiliyor")
        calistir([str(BUILD_PY), str(ROOT / "brand_installer.py")])

    baslik("2/3  Program derleniyor")
    calistir([str(BUILD_PY), "-m", "PyInstaller", "clipclover.spec",
              "--noconfirm", "--clean"])

    baslik("3/3  Kurulum dosyasi hazirlaniyor")
    calistir([str(iscc()), "installer.iss"])

    if not CIKTI.is_file():
        raise SystemExit("Kurulum dosyasi olusmadi.")
    mb = CIKTI.stat().st_size / 1048576
    print()
    print(f"  Hazir:  {CIKTI}  ({mb:.0f} MB)")
    print()
    print("  Simdi yapilacak: dosyayi GitHub'da yeni bir Release'e yukle,")
    print("  sonra web/config.js icindeki indirme adresini o dosyaya cevir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
