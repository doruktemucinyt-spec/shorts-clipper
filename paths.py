"""Exe olarak calisirken ve kaynak koddan calisirken yollar nereyi gosteriyor.

Exe halinde program Program Files altinda, salt okunur bir klasorde duruyor;
oraya is dosyasi yazamayiz. O yuzden yazilan her sey kullanicinin kendi
klasorlerine gidiyor:

  bitmis videolar -> Videolar klasoru icinde ClipClover      (kullanici kolay bulsun)
  gecici dosyalar -> AppData icinde ClipClover (goz onunde durmasin)

Kaynak koddan (python serve.py) calisirken hicbir sey degismiyor: work/ ve
output/ eskisi gibi proje klasorunde kaliyor. Doruk'un kendi renderlari orada.
"""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # PyInstaller acilan dosyalari _MEIPASS'e koyuyor: web/, ffmpeg vs.
    BUNDLE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    _local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    WORK = Path(_local) / "ClipClover" / "work"
    OUTPUT = Path.home() / "Videos" / "ClipClover"
else:
    BUNDLE = Path(__file__).parent
    WORK = BUNDLE / "work"
    OUTPUT = BUNDLE / "output"

WEB = BUNDLE / "web"
