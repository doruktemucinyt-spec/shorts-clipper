"""Kurulum ekraninin gorsellerini uretir: brand/setup/*.bmp

Inno Setup iki gorsel istiyor -- solda duran uzun bant (sadece hos geldin ve
bitti sayfalarinda gorunuyor) ve ust koseye giren kucuk kare. Ikisi de BMP
olmak zorunda, PNG kabul etmiyor.

Tasarim sitenin diliyle ayni tutuldu: neredeyse siyah zemin, ustte yesil bir
isik kubbesi, ortada yonca. Yazi YOK -- kurulum penceresinin kendi basligi
zaten "ClipClover" diyor, ve gomulu yazi tipi olmadigi icin sistemde bulunan
bir yaziyla yazmak sitedeki Inter 800 gorunumunu tutturamazdi.

Inno ekran cozunurlugune gore listedeki en uygun boyutu kendi seciyor, o
yuzden her gorsel birkac olcude uretiliyor.

Calistir:  .buildvenv/Scripts/python.exe brand_installer.py
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

KOK = Path(__file__).parent
LOGO = KOK / "brand" / "logo-square-dark-1024.png"
CIKTI = KOK / "brand" / "setup"

ZEMIN = (8, 8, 10)          # --bg
YESIL = (119, 232, 79)      # --accent

# Inno'nun tanidigi olculer. Ilki taban, digerleri yuksek DPI karsiliklari.
BANT_OLCULERI = [(164, 314), (192, 386), (256, 515), (384, 772)]
KARE_OLCULERI = [(55, 55), (110, 110), (192, 192)]


def yonca() -> Image.Image:
    """Logoyu kare zemininden ayirip sadece yoncayi dondurur.

    Dosyada yonca koyu bir karenin uzerinde duruyor. Bandin kendi zemini de
    koyu oldugu icin kareyi oldugu gibi yapistirmak ise yariyor, ama kosede
    hafif bir renk farki cikiyordu; bu yuzden kare zemin saydama cekiliyor.
    """
    img = Image.open(LOGO).convert("RGBA")
    piksel = img.load()
    g, y = img.size
    for j in range(y):
        for i in range(g):
            r, ye, m, a = piksel[i, j]
            # Yesil kanal digerlerinden belirgin ustunse yoncadayiz
            yoncada = ye > r + 24 and ye > m + 24
            if not yoncada:
                piksel[i, j] = (r, ye, m, 0)
    return img


def isik_kubbesi(en: int, boy: int) -> Image.Image:
    """Ustte duran yumusak yesil parilti -- sitedeki .glow katmaninin karsiligi.

    Iki maske carpiliyor. Tek basina eliptik maske kullanmak yetmiyordu:
    elipsin alt kenari tuvalin icine dusuyor ve orada goze carpan yatay bir
    kesim cizgisi birakiyordu. Ustune bindirilen dikey sonumleme parlakligi
    asagi dogru sifira cekiyor, boylece kenar hic gorunmuyor.
    """
    kubbe = Image.new("RGB", (en, boy), ZEMIN)

    # radial_gradient ortasi siyah, kenari beyaz veriyor; ters cevirince
    # ortasi parlak bir maske oluyor. Elips tuvalden buyuk tutuluyor.
    kubbe_en, kubbe_boy = int(en * 2.8), int(boy * 2.4)
    elips = ImageOps.invert(Image.radial_gradient("L"))
    elips = elips.resize((kubbe_en, kubbe_boy), Image.LANCZOS)

    tam = Image.new("L", (en, boy), 0)
    tam.paste(elips, ((en - kubbe_en) // 2, -int(kubbe_boy * 0.42)))

    # Dikey sonumleme: ustte tam parlak, BITIS yuksekliginde sifir.
    # linear_gradient ustte siyah / altta beyaz veriyor, ters cevrilince deger
    # (1 - yukseklik orani) oluyor; asagidaki donusum bunu duz bir rampaya
    # ceviriyor. 0.50 denendi ve bandin alt yarisi dumduz siyah kaldi; 0.72'de
    # gecis asagi dogru surup gozle secilmeden tukeniyor.
    BITIS = 0.72
    sonum = ImageOps.invert(Image.linear_gradient("L")).resize((en, boy), Image.LANCZOS)
    sonum = sonum.point(
        lambda v: max(0, min(255, int(((v / 255) - (1 - BITIS)) / BITIS * 255)))
    )

    maske = ImageChops.multiply(tam, sonum)
    # Ustel egri parlakligi tepeye topluyor; gecisi uzattigimiz icin carpan
    # biraz dusuruldu, yoksa bant yesile boguluyor.
    maske = maske.point(lambda v: int((v / 255) ** 2.2 * 96))

    renk = Image.new("RGB", (en, boy), YESIL)
    kubbe.paste(renk, (0, 0), maske)
    return kubbe


def bant(en: int, boy: int, logo: Image.Image) -> Image.Image:
    tuval = isik_kubbesi(en, boy)
    olcu = int(en * 0.46)
    kucuk = logo.resize((olcu, olcu), Image.LANCZOS)
    tuval.paste(kucuk, ((en - olcu) // 2, int(boy * 0.30) - olcu // 2), kucuk)
    return tuval


def kare(olcu: int, logo: Image.Image) -> Image.Image:
    tuval = Image.new("RGB", (olcu, olcu), ZEMIN)
    ic = int(olcu * 0.78)
    kucuk = logo.resize((ic, ic), Image.LANCZOS)
    tuval.paste(kucuk, ((olcu - ic) // 2, (olcu - ic) // 2), kucuk)
    return tuval


def main():
    CIKTI.mkdir(parents=True, exist_ok=True)
    logo = yonca()

    for en, boy in BANT_OLCULERI:
        ad = CIKTI / f"bant-{en}x{boy}.bmp"
        bant(en, boy, logo).save(ad, "BMP")
        print(" ", ad.name)

    for olcu, _ in KARE_OLCULERI:
        ad = CIKTI / f"kare-{olcu}.bmp"
        kare(olcu, logo).save(ad, "BMP")
        print(" ", ad.name)

    print(f"{len(BANT_OLCULERI) + len(KARE_OLCULERI)} gorsel hazir: {CIKTI}")


if __name__ == "__main__":
    main()
