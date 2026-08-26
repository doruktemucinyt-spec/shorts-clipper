"""Internette duracak siteyi uretir (site/ klasoru).

Site sadece arayuz: HTML, CSS ve JS. Isi yapan yardimci kullanicinin kendi
bilgisayarinda calisiyor, sayfa ona baglaniyor (web/api.js). Bu yuzden site
herhangi bir statik barindirmaya konabiliyor -- sunucu, ekran karti, disk
gerektirmiyor.

Ciktilar:
  site/index.html            ana arayuz
  site/sss|cerez|gizlilik/   bilgi sayfalari (temiz adresler icin klasor)
  site/404.html              bulunamayan adresler
  site/assets/...            css + js + ikon
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
WEB = ROOT / "web"
OUT = ROOT / "site"

ASSETS = ["style.css", "i18n.js", "lang.js", "api.js", "app.js", "pages.js",
          "page.js", "favicon.svg"]
DOC_PAGES = ["sss", "cerez", "gizlilik"]


def rewrite(html: str) -> str:
    """Yardimcidaki /static/ yolu, sitede /assets/ oluyor."""
    return html.replace("/static/", "/assets/")


def build() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)

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
