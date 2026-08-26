"""Internette duracak siteyi uretir (site/ klasoru).

Site sadece arayuz: HTML, CSS ve JS. Isi yapan yardimci kullanicinin kendi
bilgisayarinda calisiyor, sayfa ona baglaniyor (web/api.js). Bu yuzden site
herhangi bir statik barindirmaya konabiliyor -- sunucu, ekran karti, disk
gerektirmiyor.

Ciktilar:
  shorts-clipper/index.html            ana arayuz
  shorts-clipper/faq|cookies|privacy/  bilgi sayfalari (temiz adresler)
  shorts-clipper/404.html              bulunamayan adresler
  shorts-clipper/assets/...            css + js + ikon
  shorts-clipper/download/...          kaynak koddan kurmak isteyenler icin zip

Sitedeki "Bilgisayara kur" dugmesi buradaki zipi degil, GitHub Releases'teki
ClipCloverKurulum.exe dosyasini gosteriyor (adres web/config.js icinde).
Sebep: kurulum dosyasi 200 MB civari ve Vercel statik dosya barindirmak icin
dogru yer degil; GitHub Releases bu is icin ucretsiz ve sinirsiz.
"""
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
DOC_PAGES = ["faq", "cookies", "privacy"]
# Eski Turkce adresler: paylasilmis baglantilar kirilmasin diye ayni sayfa
# bir de bu klasorlerden servis ediliyor.
DOC_ALIASES = ["sss", "cerez", "gizlilik"]

# Kaynak koddan kurmak isteyenler icin duran zip. Normal kullanicinin
# dugmesi buraya degil GitHub Releases'teki exe'ye gidiyor -- bu dosya sadece
# gelistiriciler ve Windows disindakiler icin duruyor.
DOWNLOAD_DIR = "download"
DOWNLOAD_NAME = "ClipClover-Setup.zip"


def rewrite(html: str) -> str:
    """Yardimcidaki /static/ yolu, sitede /assets/ oluyor."""
    return html.replace("/static/", "/assets/")


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

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)

    if stash:
        shutil.move(str(stash), str(link))

    (OUT / "vercel.json").write_text(
        json.dumps(VERCEL_CONFIG, indent=2), encoding="utf-8")

    for name in ASSETS:
        shutil.copy2(WEB / name, OUT / "assets" / name)

    (OUT / "index.html").write_text(
        rewrite((WEB / "index.html").read_text(encoding="utf-8")), encoding="utf-8")

    page = rewrite((WEB / "page.html").read_text(encoding="utf-8"))
    for name in DOC_PAGES + DOC_ALIASES:
        (OUT / name).mkdir(parents=True, exist_ok=True)
        (OUT / name / "index.html").write_text(page, encoding="utf-8")
    (OUT / "404.html").write_text(page, encoding="utf-8")

    (OUT / DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    shutil.copy2(package.paketle(), OUT / DOWNLOAD_DIR / DOWNLOAD_NAME)

    return OUT


if __name__ == "__main__":
    out = build()
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    print(f"{out} hazir, {len(files)} dosya:")
    for f in files:
        print(" ", f)
