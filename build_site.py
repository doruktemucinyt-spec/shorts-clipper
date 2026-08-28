"""Internette duracak siteyi uretir (site/ klasoru).

Site sadece arayuz: HTML, CSS ve JS. Isi yapan yardimci kullanicinin kendi
bilgisayarinda calisiyor, sayfa ona baglaniyor (web/api.js). Bu yuzden site
herhangi bir statik barindirmaya konabiliyor -- sunucu, ekran karti, disk
gerektirmiyor.

Ciktilar:
  shorts-clipper/index.html            ana arayuz
  shorts-clipper/faq|cookies|privacy|terms/  bilgi sayfalari (temiz adresler)
  shorts-clipper/404.html              bulunamayan adresler
  shorts-clipper/api/tiktok/...        TikTok girisinin sunucu tarafi
  shorts-clipper/assets/...            css + js + ikon
  shorts-clipper/download/...          kaynak koddan kurmak isteyenler icin zip

Sitedeki "Bilgisayara kur" dugmesi buradaki zipi degil, GitHub Releases'teki
ClipCloverKurulum.exe dosyasini gosteriyor (adres web/config.js icinde).
Sebep: kurulum dosyasi 200 MB civari ve Vercel statik dosya barindirmak icin
dogru yer degil; GitHub Releases bu is icin ucretsiz ve sinirsiz.
"""
import hashlib
import json
import shutil
from pathlib import Path

import package

ROOT = Path(__file__).parent
WEB = ROOT / "web"
# Klasor adi Vercel'de proje adi ve adres oluyor (shorts-clipper.vercel.app),
# o yuzden "site" degil.
OUT = ROOT / "shorts-clipper"

ASSETS = ["style.css", "config.js", "i18n.js", "lang.js", "api.js", "app.js",
          "pages.js", "page.js", "gate.js", "favicon.svg"]
DOC_PAGES = ["faq", "cookies", "privacy", "terms"]
# Eski Turkce adresler: paylasilmis baglantilar kirilmasin diye ayni sayfa
# bir de bu klasorlerden servis ediliyor.
DOC_ALIASES = ["sss", "cerez", "gizlilik", "kosullar"]

# Kaynak koddan kurmak isteyenler icin duran zip. Normal kullanicinin
# dugmesi buraya degil GitHub Releases'teki exe'ye gidiyor -- bu dosya sadece
# gelistiriciler ve Windows disindakiler icin duruyor.
DOWNLOAD_DIR = "download"
DOWNLOAD_NAME = "ClipClover-Setup.zip"

# Sitedeki tek sunucu parcasi: TikTok girisi. Vercel api/ altindaki her
# .js dosyasini kendisi fonksiyon yapiyor, uzantisiz adresten servis
# ediyor. Burada durmasinin sebebi client_secret: kullanicinin
# bilgisayarina inemez, ortam degiskeni olarak Vercel'de duruyor.
API_DIR = ROOT / "vercel_api"


def rewrite(html: str, harita: dict) -> str:
    """Yardimcidaki /static/ yolu sitede /assets/ oluyor; dosya adlari da
    icerige gore damgalanmis hallerine cevriliyor."""
    html = html.replace("/static/", "/assets/")
    for eski_yol, yeni_yol in harita.items():
        html = html.replace(eski_yol, yeni_yol)
    return html


def damgali_ad(ad: str, veri: bytes) -> str:
    """style.css -> style.9f2a1c04.css

    Adin icinde iceriğin ozeti oldugu icin dosya degistiginde adres de
    degisiyor. Bu sayede dosyalari bir yil boyunca "bir daha sorma" diye
    isaretleyebiliyoruz: yeni surum zaten yeni adresten iniyor, eskisini
    tarayici hic sormadan kendi kopyasindan aciyor.
    """
    p = Path(ad)
    return f"{p.stem}.{hashlib.sha256(veri).hexdigest()[:8]}{p.suffix}"


# Vercel'de temiz adresler: /sss klasorunun index.html'i /sss olarak aciliyor,
# bilinmeyen adresler 404.html'e dusuyor.
VERCEL_CONFIG = {
    "cleanUrls": True,
    "trailingSlash": False,
    # www ile girenler asil adrese gonderiliyor: tek adres, tek izin kaydi.
    "redirects": [{
        "source": "/(.*)",
        "has": [{"type": "host", "value": "www.clipclover.online"}],
        "destination": "https://clipclover.online/$1",
        "permanent": True,
    }],
    # assets/ altindaki her dosyanin adinda icerigin ozeti var, yani bir
    # dosyanin adresi ancak icerigi degistiginde degisiyor. O yuzden
    # "bir daha sorma" diyebiliyoruz. HTML damgasiz kaliyor ve her acilista
    # tazeleniyor -- yeni surume gecisi o saglıyor.
    "headers": [{
        "source": "/assets/(.*)",
        "headers": [{
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable",
        }],
    }],
}


def build() -> Path:
    # Vercel proje baglantisi site/.vercel icinde tutuluyor; klasoru silerken
    # onu kaybedersek her yayinda yeni proje aciliyor. Once kenara aliyoruz.
    link = OUT / ".vercel"
    stash = None
    if link.exists():
        stash = ROOT / ".vercel-link-yedek"
        if stash.exists():
            shutil.rmtree(stash)
        shutil.move(str(link), str(stash))

    try:
        if OUT.exists():
            shutil.rmtree(OUT)
        (OUT / "assets").mkdir(parents=True)
    finally:
        # Buradan hatayla cikilsa bile baglanti geri konmali. Konmazsa
        # bir sonraki yayin Vercel'de YENI bir proje aciyor, alan adi
        # eski projede kaliyor ve site bos gorunuyor.
        if stash and stash.exists():
            link.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stash), str(link))

    (OUT / "vercel.json").write_text(
        json.dumps(VERCEL_CONFIG, indent=2), encoding="utf-8")

    harita = {}
    for name in ASSETS:
        veri = (WEB / name).read_bytes()
        yeni_ad = damgali_ad(name, veri)
        (OUT / "assets" / yeni_ad).write_bytes(veri)
        harita[f"/assets/{name}"] = f"/assets/{yeni_ad}"

    (OUT / "index.html").write_text(
        rewrite((WEB / "index.html").read_text(encoding="utf-8"), harita),
        encoding="utf-8")

    page = rewrite((WEB / "page.html").read_text(encoding="utf-8"), harita)
    for name in DOC_PAGES + DOC_ALIASES:
        (OUT / name).mkdir(parents=True, exist_ok=True)
        (OUT / name / "index.html").write_text(page, encoding="utf-8")
    (OUT / "404.html").write_text(page, encoding="utf-8")

    if API_DIR.is_dir():
        shutil.copytree(API_DIR, OUT / "api", dirs_exist_ok=True)

    (OUT / DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    shutil.copy2(package.paketle(), OUT / DOWNLOAD_DIR / DOWNLOAD_NAME)

    return OUT


if __name__ == "__main__":
    out = build()
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    print(f"{out} hazir, {len(files)} dosya:")
    for f in files:
        print(" ", f)
