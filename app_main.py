"""ClipClover.exe'nin giris noktasi.

Program artik pencere acmadan calisiyor. Eskiden siyah bir konsol penceresi
aciliyordu ve kullanici onu kapatarak programi durduruyordu; simdi yerine
saatin yanindaki tepsi simgesi var. Simgeye cift tiklamak siteyi aciyor, sag
tiklamak menuyu.

Acilista tarayicida clipclover.online aciliyor -- localhost DEGIL. Kullaniciya
gosterdigimiz yuz site; yerel sunucu sadece isi yapan yardimci ve adresi
ekranda gorunmesi gerekmiyor. (Yine de duruyor: gerekirse localhost:8000 hala
ayni arayuzu veriyor.)

Konsol olmadigi icin iki sey ayrica halledilmek zorunda:
  - Ekrana basilan her sey bir kayit dosyasina gidiyor. Yoksa sys.stdout None
    oluyor ve uvicorn'un gunlukleri programi dusuruyor.
  - Alt sureclerin (ffmpeg, ffprobe, yt-dlp) kendi pencerelerini acmasi
    engelleniyor -- bkz. _pencereleri_gizle.
"""
import sys
import threading

SITE = "https://clipclover.online"


def _kayda_yonlendir():
    """Konsol yokken ekrana basilanlari dosyaya yazar.

    Penceresiz derlemede sys.stdout ve sys.stderr None oluyor. uvicorn ilk
    gunluk satirini yazmaya calistigi anda program sessizce oluyordu. Ayrica
    bir sey ters giderse bakilacak bir yer olmus oluyor.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None

    from paths import WORK

    WORK.mkdir(parents=True, exist_ok=True)
    kayit = open(WORK / "clipclover.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = kayit
    sys.stderr = kayit
    return kayit


def _pencereleri_gizle():
    """Alt sureclerin siyah pencere acmasini engeller.

    Windows'ta penceresiz bir surecten baslatilan her konsol programi KENDI
    penceresini aciyor. Render sirasinda ekranda arka arkaya siyah kutular
    yanip sonuyordu. Bayragi cagri yerlerine tek tek eklemek yetmiyor: yt-dlp
    de kendi icinden ffmpeg calistiriyor ve oraya erisemiyoruz. Bu yuzden
    Popen'in varsayilani degistiriliyor -- her alt surec bu bayragi aliyor.
    """
    if sys.platform != "win32":
        return

    import subprocess

    orijinal = subprocess.Popen.__init__

    def yamali(self, *args, **kwargs):
        kwargs["creationflags"] = (
            kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        )
        orijinal(self, *args, **kwargs)

    subprocess.Popen.__init__ = yamali


def pencere(baslik: str, mesaj: str, hata: bool = False):
    """Konsol olmadigi icin kullaniciya tek yol: kucuk bir Windows penceresi."""
    if sys.platform != "win32":
        print(f"{baslik}: {mesaj}")
        return
    import ctypes

    simge = 0x10 if hata else 0x40           # MB_ICONERROR / MB_ICONINFORMATION
    ctypes.windll.user32.MessageBoxW(0, mesaj, baslik, simge)


def siteyi_ac():
    import webbrowser

    try:
        webbrowser.open(SITE)
    except Exception:
        pass


def tepsi_simgesi():
    """Saat yanindaki simge. Programi gorunur ve kapatilabilir kilan tek sey."""
    import pystray
    from PIL import Image

    from paths import BUNDLE

    resim = Image.open(BUNDLE / "brand" / "clipclover.ico")

    def cik(simge):
        simge.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Siteyi ac", lambda: siteyi_ac(), default=True),
        pystray.MenuItem("Cik", cik),
    )
    return pystray.Icon("ClipClover", resim, "ClipClover calisiyor", menu)


def main() -> int:
    kayit = _kayda_yonlendir()
    _pencereleri_gizle()

    import serve

    # Soketleri sunucudan once aciyoruz: port doluysa bunu simdi ogrenip
    # kullaniciya soyleyebiliyoruz. Sunucuyu baslattiktan sonra ogrenseydik
    # penceresiz surec sessizce olurdu.
    sockets = serve.dinle()
    if not sockets:
        pencere(
            "ClipClover",
            "ClipClover zaten calisiyor gibi gorunuyor.\n\n"
            "Saatin yanindaki yonca simgesine bak; oradan Siteyi ac diyebilirsin.",
        )
        return 1

    threading.Thread(
        target=serve.calistir, args=(sockets,), daemon=True
    ).start()

    siteyi_ac()

    try:
        tepsi_simgesi().run()          # kullanici Cik diyene kadar donmez
    except Exception:
        # Tepsi kurulamadiysa program yine de calissin: simgesiz ama ayakta.
        import traceback

        traceback.print_exc()
        threading.Event().wait()

    if kayit:
        kayit.close()
    return 0


if __name__ == "__main__":
    try:
        kod = main()
    except Exception:
        import traceback

        traceback.print_exc()
        pencere(
            "ClipClover",
            "Program beklenmedik bir hatayla durdu.\n\n"
            "Ayrintilar kayit dosyasinda:\n"
            "%LOCALAPPDATA%\\ClipClover\\work\\clipclover.log\n\n"
            "Dosyayi Discord'da paylasirsan bakariz.",
            hata=True,
        )
        kod = 1
    sys.exit(kod)
