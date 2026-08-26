"""Shorts Clipper kurulumu.

Neden .bat degil de Python: kurulum isini bir toplu is dosyasinda yaptigimizda
antivirus programlari (Norton, Avast...) bunu zararli yazilim kalibi sayip
uyari veriyor. Ozellikle bat'in icinden PowerShell cagirmak ve masaustune
dosya yazmak dogrudan "dropper" olarak isaretleniyor. Ayni isi Python'da
yapinca hem uyari cikmiyor hem de ne yaptigi okunabiliyor.

Bu betik ne yapiyor:
  1. Python surumunu kontrol ediyor
  2. ffmpeg'i ariyor, yoksa winget ile kurmayi ONERIYOR (sessizce kurmuyor)
  3. .venv olusturup gerekli kutuphaneleri kuruyor
  4. Nasil baslatilacagini yaziyor

Sistemde hicbir seyi gizlice degistirmiyor: kurulan her sey bu klasorde ya da
kullanicinin onayiyla winget uzerinden.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
PY_MIN = (3, 10)

HAFIF = ROOT / "requirements-hafif.txt"
TAM = ROOT / "requirements.txt"


def baslik(text: str):
    print()
    print("  " + text)
    print("  " + "-" * (len(text) + 2))


def sor(soru: str, varsayilan: str = "e") -> bool:
    cevap = input(f"  {soru} (e/h) [{varsayilan}]: ").strip().lower() or varsayilan
    return cevap.startswith("e")


def venv_python() -> Path:
    return VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"


def ffmpeg_var() -> bool:
    if shutil.which("ffmpeg"):
        return True
    # winget ile kurulanlar PATH'e yeni pencere acilana kadar yansimiyor
    import os
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        base = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if base.is_dir():
            return any(base.glob("*FFmpeg*/**/bin/ffmpeg.exe"))
    return False


def main() -> int:
    print()
    print("  ===========================================")
    print("   Shorts Clipper - kurulum")
    print("  ===========================================")
    print()
    print("  Bu kurulum su klasore yaziyor:")
    print(f"    {ROOT}")
    print()

    if sys.version_info < PY_MIN:
        print(f"  Python {PY_MIN[0]}.{PY_MIN[1]} veya ustu gerekiyor. Simdiki: "
              f"{sys.version.split()[0]}")
        return 1

    print("  Iki secenek var:")
    print()
    print("    [1] HAFIF  (~200 MB)")
    print("        YouTube linkinden 9:16 partlar cikarir. Bolme tam surede")
    print("        yapilir, caption yoktur. Hizli ve kucuk.")
    print()
    print("    [2] TAM    (~2 GB kurulum + ilk kullanimda ~3 GB altyazi modeli)")
    print("        Ustune cumle sonuna hizali bolme ve caption yakma gelir.")
    print("        NVIDIA ekran karti varsa onu kullanir, yoksa islemciye duser.")
    print()
    secim = input("  Secimin (1 veya 2) [1]: ").strip() or "1"
    gereksinim = TAM if secim == "2" else HAFIF

    baslik("1/3  ffmpeg")
    if ffmpeg_var():
        print("  Zaten var.")
    else:
        print("  ffmpeg bulunamadi. Video kesme ve birlestirme onsuz calismaz.")
        if sor("  winget ile kurulsun mu?"):
            subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e",
                            "--source", "winget", "--accept-package-agreements",
                            "--accept-source-agreements"], check=False)
        else:
            print("  Atlandi. Sonradan kurmak icin:")
            print("    winget install --id Gyan.FFmpeg -e --source winget")

    baslik("2/3  Kutuphaneler")
    if not venv_python().exists():
        print("  Sanal ortam olusturuluyor (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    print(f"  {gereksinim.name} kuruluyor, birkac dakika surebilir...")
    print()
    sonuc = subprocess.run([str(venv_python()), "-m", "pip", "install",
                            "--upgrade", "-r", str(gereksinim)], check=False)
    if sonuc.returncode != 0:
        print()
        print("  Kutuphaneler kurulamadi. Yukaridaki satirlar sebebini soyluyor.")
        return 1

    baslik("3/3  Hazir")
    print("  Baslatmak icin: baslat.bat dosyasina cift tikla.")
    print("  Masaustunde dursun istersen: baslat.bat'a sag tikla ->")
    print("  'Kisayol olustur' -> cikan kisayolu masaustune tasi.")
    print()
    print("  Sonra sunlardan biriyle kullan:")
    print("    https://shorts-clipper-seven.vercel.app   (site, izin ister)")
    print("    http://localhost:8000                     (dogrudan, izin gerekmez)")
    print()
    return 0


if __name__ == "__main__":
    try:
        kod = main()
    except KeyboardInterrupt:
        print()
        print("  Iptal edildi.")
        kod = 1
    input("  Kapatmak icin Enter'a bas...")
    sys.exit(kod)
