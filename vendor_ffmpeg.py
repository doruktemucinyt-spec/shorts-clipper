"""Paketlemeye girecek ffmpeg'i indirir: vendor/ffmpeg.

Neden "shared" derleme: normal (static) derlemede ffmpeg.exe ve ffprobe.exe
butun kodekleri ayri ayri iceriyor, ikisi 424 MB tutuyor. Shared derlemede
kodekler ortak DLL'lerde duruyor -- ayni yetenek, 161 MB. ffplay oynaticisini
almiyoruz, kullanmiyoruz.

libx264 ve libass gerektigi icin GPL derleme sart (render.py x264 ile
kodluyor, altyazilari libass ile basiyor). ffmpeg ayri bir program olarak
calistiriliyor, lisansi da yaninda gidiyor.
"""
import shutil
import urllib.request
import zipfile
from pathlib import Path

ADRES = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
         "ffmpeg-master-latest-win64-gpl-shared.zip")
HEDEF = Path(__file__).parent / "vendor" / "ffmpeg"
ATLA = {"ffplay.exe"}


def indir() -> Path:
    gecici = HEDEF.parent / "ffmpeg-indirilen.zip"
    gecici.parent.mkdir(parents=True, exist_ok=True)
    print(f"  indiriliyor: {ADRES}")
    urllib.request.urlretrieve(ADRES, gecici)
    return gecici


def main():
    zip_yolu = indir()
    if HEDEF.exists():
        shutil.rmtree(HEDEF)
    HEDEF.mkdir(parents=True)

    with zipfile.ZipFile(zip_yolu) as z:
        for bilgi in z.infolist():
            if bilgi.is_dir():
                continue
            ad = bilgi.filename.split("/")[-1]
            if "/bin/" in bilgi.filename and ad not in ATLA:
                (HEDEF / ad).write_bytes(z.read(bilgi))
            elif ad in ("LICENSE.txt", "COPYING.GPLv3.txt"):
                (HEDEF / "FFMPEG-LICENSE.txt").write_bytes(z.read(bilgi))

    zip_yolu.unlink()
    mb = sum(f.stat().st_size for f in HEDEF.rglob("*") if f.is_file()) / 1048576
    print(f"  vendor/ffmpeg hazir: {mb:.0f} MB")


if __name__ == "__main__":
    main()
