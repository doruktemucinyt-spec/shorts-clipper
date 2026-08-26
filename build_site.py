"""Internette duracak siteyi uretir (site/ klasoru).

Site sadece arayuz: HTML, CSS ve JS. Isi yapan yardimci kullanicinin kendi
bilgisayarinda calisiyor, sayfa ona baglaniyor (web/api.js). Bu yuzden site
herhangi bir statik barindirmaya konabiliyor -- sunucu, ekran karti, disk
gerektirmiyor.

Ciktilar:
  shorts-clipper/index.html            ana arayuz
  shorts-clipper/sss|cerez|gizlilik/   bilgi sayfalari (temiz adresler)
  shorts-clipper/404.html              bulunamayan adresler
  shorts-clipper/assets/...            css + js + ikon
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
WEB = ROOT / "web"
# Klasor adi Vercel'de proje adi ve adres oluyor (shorts-clipper.vercel.app),
# o yuzden "site" degil.
OUT = ROOT / "shorts-clipper"

ASSETS = ["style.css", "i18n.js", "lang.js", "api.js", "app.js", "pages.js",
          "page.js", "favicon.svg"]
DOC_PAGES = ["sss", "cerez", "gizlilik"]


def rewrite(html: str) -> str:
    """Yardimcidaki /static/ yolu, sitede /assets/ oluyor."""
    return html.replace("/static/", "/assets/")


# Vercel'de temiz adresler: /sss klasorunun index.html'i /sss olarak aciliyor,
# bilinmeyen adresler 404.html'e dusuyor.
VERCEL_CONFIG = {"cleanUrls": True, "trailingSlash": False}


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

    index = rewrite((WEB / "index.html").read_text(encoding="utf-8"))
    # Olcum modu sadece gelistirme icin
    index = re.sub(r'\s*<script src="/assets/perf\.js"></script>', "", index)
    (OUT / "index.html").write_text(index, encoding="utf-8")

    page = rewrite((WEB / "page.html").read_text(encoding="utf-8"))
    for name in DOC_PAGES:
        (OUT / name).mkdir(parents=True, exist_ok=True)
        (OUT / name / "index.html").write_text(page, encoding="utf-8")
    (OUT / "404.html").write_text(page, encoding="utf-8")

    return OUT


if __name__ == "__main__":
    out = build()
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    print(f"{out} hazir, {len(files)} dosya:")
    for f in files:
        print(" ", f)
