"""Baska bir bilgisayara gonderilecek zip'i hazirlar.

Icine sadece calismak icin gerekenler giriyor: kod, arayuz, kurulum. Senin
videolarin (output), indirilen kaynaklar (work), sanal ortam ve git gecmisi
disarida kaliyor.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
HEDEF = ROOT / "shorts-clipper-setup.zip"

KLASORLER = ["pipeline", "web"]
DOSYALAR = ["server.py", "serve.py", "pairing.py", "install.py", "install.bat",
            "start.bat", "requirements.txt", "requirements-lite.txt",
            "README.md", "README.tr.md", "LICENSE"]
ATLA = {"__pycache__", ".venv", ".git"}


def paketle() -> Path:
    with zipfile.ZipFile(HEDEF, "w", zipfile.ZIP_DEFLATED) as z:
        for ad in DOSYALAR:
            yol = ROOT / ad
            if yol.exists():
                z.write(yol, f"shorts-clipper/{ad}")
        for klasor in KLASORLER:
            for yol in (ROOT / klasor).rglob("*"):
                if yol.is_file() and not any(p in ATLA for p in yol.parts):
                    z.write(yol, f"shorts-clipper/{yol.relative_to(ROOT).as_posix()}")
    return HEDEF


if __name__ == "__main__":
    hedef = paketle()
    mb = hedef.stat().st_size / 1024 / 1024
    with zipfile.ZipFile(hedef) as z:
        adet = len(z.namelist())
    print(f"{hedef.name} hazir: {adet} dosya, {mb:.1f} MB")
