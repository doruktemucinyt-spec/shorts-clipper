# -*- mode: python ; coding: utf-8 -*-
"""ClipClover'i tek klasorluk, penceresiz bir Windows programina cevirir.

Neden "onefile" degil de klasor: tek dosyalik exe kendini her acilista gecici
klasore acar; Windows Defender bu davranisi zararli yazilim kalibi sayip sik
sik yanlis alarm veriyor. Klasor + kurulum programi Windows'un tanidigi
siradan bir kalip, hem daha az uyari cikariyor hem daha hizli aciliyor.

ffmpeg iceri gomuluyor: kullanicidan ayrica bir sey kurmasini istemiyoruz.
CUDA kutuphaneleri gomulmuyor -- 2 GB'in uzerinde yer tutuyorlar. GPU yoksa
transcribe.py zaten kendiliginden CPU'ya dusuyor.
"""
import shutil
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "web"), "web"),
    # Tepsi simgesi calisma aninda bu dosyadan okunuyor (app_main.py)
    (str(ROOT / "brand" / "clipclover.ico"), "brand"),
]
binaries = []
hiddenimports = [
    "truststore",
    # pystray arka ucunu isim uzerinden seciyor, import satiri yok
    "pystray._win32",
    # uvicorn bunlari isim uzerinden yukluyor, import satiri yok
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on", "uvicorn.lifespan.off",
]

# yt-dlp cikaricilarini isim uzerinden buluyor
hiddenimports += collect_submodules("yt_dlp.extractor")

for paket in ("faster_whisper", "ctranslate2", "tokenizers", "onnxruntime", "av"):
    d, b, h = collect_all(paket)
    datas += d
    binaries += b
    hiddenimports += h

# ffmpeg'i yaninda tasi. PATH'teki surumu degil vendor/ffmpeg'dekini
# kullaniyoruz: o "shared" derleme, kodekleri exe'lerin icine kopyalamak
# yerine ortak DLL'lerde tutuyor -- ayni yetenek, ucte bir yer.
FFMPEG_DIR = ROOT / "vendor" / "ffmpeg"
if not (FFMPEG_DIR / "ffmpeg.exe").is_file():
    raise SystemExit(
        "vendor/ffmpeg bos. Doldurmak icin:  python vendor_ffmpeg.py"
    )
for dosya in FFMPEG_DIR.iterdir():
    if dosya.suffix.lower() in (".exe", ".dll"):
        binaries.append((str(dosya), "ffmpeg"))
    else:
        datas.append((str(dosya), "ffmpeg"))

a = Analysis(
    ["app_main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[
        # Gerekmeyen agir paketler: girerse boyut bosuna sisiyor
        "torch", "tensorflow", "matplotlib", "scipy", "pandas",
        "tkinter", "PyQt5", "PySide6", "IPython", "notebook", "pytest",
    ],
    noarchive=False,
)
# PyInstaller ffmpeg.exe'yi tarayip ihtiyac duydugu DLL'leri bir de ana klasore
# kopyaliyor -- ayni 153 MB iki kez pakete giriyor. Ana klasordekiler kimsenin
# import etmedigi olu kopyalar; ffmpeg.exe zaten kendi yanindakileri yukluyor.
_ffmpeg_adlari = {d.name.lower() for d in FFMPEG_DIR.iterdir()}
a.binaries = [
    girdi for girdi in a.binaries
    if not ("\\" not in girdi[0] and "/" not in girdi[0]
            and girdi[0].lower() in _ffmpeg_adlari)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ClipClover",
    # Pencere yok: siyah konsol yerine tepsi simgesi var (app_main.py).
    # Bunu True yapmak konsolu geri getirir ama o zaman ffmpeg her cagrildiginda
    # ekranda kutu yanip sonmesin diye app_main'deki Popen yamasi da gozden
    # gecirilmeli.
    console=False,
    icon=str(ROOT / "brand" / "clipclover.ico"),
    version=str(ROOT / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,          # UPX sikistirma antivirus alarmlarinin bir numarali sebebi
    name="ClipClover",
)
