"""ClipClover.exe'nin giris noktasi.

serve.py ile ayni sunucuyu baslatiyor, ustune iki sey ekliyor: tarayiciyi
kendisi aciyor (kullanici adres yazmasin) ve bir hata cikarsa pencereyi
kapatmadan once hatayi ekranda tutuyor -- yoksa siyah pencere bir anda
kaybolur ve kimse ne oldugunu goremez.
"""
import sys
import threading
import time
import webbrowser

import serve

ADRES = f"http://localhost:{serve.PORT}"


def tarayiciyi_ac():
    # Sunucu soketi acilana kadar kisa bir nefes; erken acilan sekme
    # "baglanti kurulamadi" gosterip kullaniciyi bosuna korkutuyor.
    time.sleep(1.5)
    try:
        webbrowser.open(ADRES)
    except Exception:
        pass


def main() -> int:
    print()
    print("   ClipClover calisiyor.")
    print()
    print(f"   Tarayici birazdan acilacak:  {ADRES}")
    print("   Acilmazsa bu adresi kendin yazabilirsin.")
    print()
    print("   Bu pencereyi kapatinca program durur.")
    print("   Bitmis videolar: Videolar klasorundeki ClipClover icinde.")
    print()

    threading.Thread(target=tarayiciyi_ac, daemon=True).start()
    return serve.main()


if __name__ == "__main__":
    try:
        kod = main()
    except KeyboardInterrupt:
        kod = 0
    except Exception:
        import traceback

        traceback.print_exc()
        print()
        print("   Program beklenmedik bir hatayla durdu.")
        print("   Yukaridaki yaziyi kopyalayip Discord'da paylasirsan bakariz.")
        input("   Kapatmak icin Enter'a bas...")
        kod = 1
    sys.exit(kod)
