"""TikTok baglantisi: giris, token saklama ve bitmis bir parcayi taslaklara atma.

Neden bu kadar dolambacli, sirasiyla:

1. TikTok'un token ucu client_secret istiyor ve PKCE bunu degistirmiyor.
   Secret'i buraya koyamayiz -- program herkese dagitiliyor, ilk acan gorurdu.
   O yuzden hem giris hem token yenileme clipclover.online uzerindeki kucuk
   sunucu parcasindan geciyor (vercel_api/tiktok/*.js); secret orada, ortam
   degiskeninde duruyor ve hicbir zaman bu bilgisayara inmiyor.

2. Videonun kendisi TikTok'a DOGRUDAN bu bilgisayardan gidiyor. Aradan site
   gecmiyor, dosya kimsenin sunucusuna ugramiyor.

3. Taslak (inbox) yolu kullaniliyor, dogrudan paylasim degil. Dogrudan paylasim
   TikTok'un 2-4 haftalik denetimini gerektiriyor ve denetimden gecene kadar
   atilan her video gizli kaliyor. Taslakta video kullanicinin TikTok gelen
   kutusuna dusuyor, yayinlama karari onda.

   Bunun bir bedeli var ve gorunur bir bedel: taslaga baslik ve hashtag
   GONDERILEMIYOR. inbox ucu govdesinde sadece source_info aliyor, post_info
   diye bir alani yok. Basligi kullanici TikTok uygulamasinda yaziyor.

4. client_key kodun icinde degil, work/tiktok-config.json icinde duruyor.
   Dosya yoksa ozellik hic gorunmuyor. Sebep: uygulama TikTok'un sandbox
   modunda, yani sadece gelistiricinin Target Users listesine ekledigi
   hesaplar giris yapabiliyor. Anahtari pakete koysaydik herkeste buton
   cikar, herkeste hata verirdi.
"""
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from paths import WORK

CONFIG_FILE = WORK / "tiktok-config.json"
STORE_FILE = WORK / "tiktok.json"

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
API = "https://open.tiktokapis.com/v2"
REDIRECT_URI = "https://clipclover.online/api/tiktok/callback"
REFRESH_URL = "https://clipclover.online/api/tiktok/refresh"

# video.upload = taslaga gonderme. video.publish (dogrudan paylasim) bilerek
# istenmiyor; denetim gerektiriyor ve denetimden once her paylasim gizli kaliyor.
SCOPES = "user.info.basic,video.upload"

# Yarim kalmis giris istekleri bu sure sonunda dusuyor
STATE_TTL = 900.0

# TikTok'un sinirlari: parca 5 MB'tan buyuk, 64 MB'tan kucuk olmali; son parca
# daha buyuk olabiliyor. 64 MB'a kadar olan videolari tek parca gonderiyoruz.
TEK_PARCA_SINIRI = 64 * 1024 * 1024
PARCA_BOYU = 32 * 1024 * 1024

_lock = threading.Lock()
_bekleyen = {}          # state -> olusturulma zamani


# --- ayar ve depo ---------------------------------------------------------
def _oku(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _yaz(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def client_key() -> str:
    return str(_oku(CONFIG_FILE).get("client_key") or "")


def available() -> bool:
    """Bu bilgisayarda TikTok ozelligi acik mi (anahtar tanimli mi)."""
    return bool(client_key())


# --- HTTP -----------------------------------------------------------------
def _istek(url: str, *, method="GET", body=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ham = r.read()
    except urllib.error.HTTPError as e:
        ham = e.read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"TikTok'a ulasilamadi: {e}") from e
    try:
        return json.loads(ham.decode("utf-8"))
    except Exception:
        return {}


def _hata_mesaji(cevap: dict) -> str:
    """TikTok hatayi iki ayri sekilde donduruyor; ikisini de kariliyoruz."""
    err = (cevap or {}).get("error")
    if isinstance(err, dict):
        return err.get("message") or err.get("code") or ""
    if isinstance(err, str) and err not in ("", "ok"):
        return (cevap.get("error_description") or err)
    return ""


# --- giris ----------------------------------------------------------------
def _sup():
    now = time.time()
    with _lock:
        for s, at in list(_bekleyen.items()):
            if now - at > STATE_TTL:
                _bekleyen.pop(s, None)


def begin() -> str:
    """Giris adresini uretir. state'i sadece biz biliyoruz; donusu o dogruluyor."""
    key = client_key()
    if not key:
        raise RuntimeError("TikTok anahtari tanimli degil.")
    _sup()
    state = secrets.token_urlsafe(24)
    with _lock:
        _bekleyen[state] = time.time()
    sorgu = urllib.parse.urlencode({
        "client_key": key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    })
    return f"{AUTH_URL}?{sorgu}"


def finish(state: str, tokens: dict) -> dict:
    """Sitedeki callback sayfasindan gelen token'lari kaydeder.

    state kontrolu burada onemli: bu uc disaridan doldurulabiliyor, ama dogru
    state'i sadece bu surecin kendisi biliyor.
    """
    _sup()
    with _lock:
        taniyor = _bekleyen.pop(state, None) is not None
    if not taniyor:
        raise RuntimeError("Giris istegi taninmadi ya da zaman asimina ugradi.")

    access = str(tokens.get("access_token") or "")
    if not access:
        raise RuntimeError("Erisim anahtari gelmedi.")

    try:
        omur = float(tokens.get("expires_in") or 0)
    except ValueError:
        omur = 0.0

    kayit = {
        "access_token": access,
        "refresh_token": str(tokens.get("refresh_token") or ""),
        # Bir dakika pay birakiyoruz: tam siniri kovalayip 401 yemeyelim.
        "expires_at": time.time() + max(0.0, omur - 60),
        "open_id": str(tokens.get("open_id") or ""),
        "scope": str(tokens.get("scope") or ""),
    }
    kayit.update(_kullanici_bilgisi(access))
    _yaz(STORE_FILE, kayit)
    return status()


def _kullanici_bilgisi(access: str) -> dict:
    """Hangi hesabin bagli oldugunu gostermek icin. Baska bir yere gitmiyor."""
    url = f"{API}/user/info/?fields=open_id,display_name,avatar_url"
    cevap = _istek(url, headers={"Authorization": f"Bearer {access}"})
    kul = ((cevap or {}).get("data") or {}).get("user") or {}
    return {
        "display_name": kul.get("display_name") or "",
        "avatar_url": kul.get("avatar_url") or "",
    }


def _yenile(kayit: dict) -> dict:
    """Suresi dolan anahtari yeniler. Secret sitede oldugu icin oradan geciyor."""
    refresh = kayit.get("refresh_token")
    if not refresh:
        raise RuntimeError("Yenileme anahtari yok, tekrar baglanman gerekiyor.")
    govde = json.dumps({"refresh_token": refresh}).encode("utf-8")
    cevap = _istek(REFRESH_URL, method="POST", body=govde,
                   headers={"Content-Type": "application/json"})
    access = (cevap or {}).get("access_token")
    if not access:
        raise RuntimeError(_hata_mesaji(cevap) or "Anahtar yenilenemedi.")
    try:
        omur = float(cevap.get("expires_in") or 0)
    except ValueError:
        omur = 0.0
    kayit["access_token"] = access
    kayit["refresh_token"] = cevap.get("refresh_token") or refresh
    kayit["expires_at"] = time.time() + max(0.0, omur - 60)
    _yaz(STORE_FILE, kayit)
    return kayit


def _access_token() -> str:
    kayit = _oku(STORE_FILE)
    if not kayit.get("access_token"):
        raise RuntimeError("TikTok bagli degil.")
    if time.time() >= float(kayit.get("expires_at") or 0):
        kayit = _yenile(kayit)
    return kayit["access_token"]


def status() -> dict:
    kayit = _oku(STORE_FILE)
    return {
        "available": available(),
        "connected": bool(kayit.get("access_token")),
        "display_name": kayit.get("display_name") or "",
        "avatar_url": kayit.get("avatar_url") or "",
    }


def disconnect():
    STORE_FILE.unlink(missing_ok=True)


# --- taslaga yukleme ------------------------------------------------------
def _parcalar(boyut: int):
    """(parca_boyu, parca_sayisi, [(bas, son), ...]) uretir."""
    if boyut <= TEK_PARCA_SINIRI:
        return boyut, 1, [(0, boyut - 1)]
    sayi = boyut // PARCA_BOYU
    araliklar = []
    for i in range(sayi):
        bas = i * PARCA_BOYU
        # Son parca artani da yutuyor; TikTok bunu bilerek serbest birakiyor.
        son = boyut - 1 if i == sayi - 1 else bas + PARCA_BOYU - 1
        araliklar.append((bas, son))
    return PARCA_BOYU, sayi, araliklar


def send_to_drafts(video: Path, on_progress=None) -> dict:
    """Bitmis bir parcayi kullanicinin TikTok taslaklarina yukler.

    Yayinlamiyor: video gelen kutusuna dusuyor, kullanici TikTok uygulamasinda
    bildirime basip basligi yazarak paylasiyor.
    """
    video = Path(video)
    if not video.is_file():
        raise RuntimeError("Video dosyasi bulunamadi.")
    boyut = video.stat().st_size
    if not boyut:
        raise RuntimeError("Video dosyasi bos.")

    access = _access_token()
    parca_boyu, parca_sayisi, araliklar = _parcalar(boyut)

    if on_progress:
        on_progress(0)

    govde = json.dumps({"source_info": {
        "source": "FILE_UPLOAD",
        "video_size": boyut,
        "chunk_size": parca_boyu,
        "total_chunk_count": parca_sayisi,
    }}).encode("utf-8")
    cevap = _istek(f"{API}/post/publish/inbox/video/init/", method="POST", body=govde,
                   headers={"Authorization": f"Bearer {access}",
                            "Content-Type": "application/json; charset=UTF-8"})
    veri = (cevap or {}).get("data") or {}
    upload_url = veri.get("upload_url")
    if not upload_url:
        raise RuntimeError(_hata_mesaji(cevap) or "TikTok yukleme adresi vermedi.")

    with video.open("rb") as f:
        for i, (bas, son) in enumerate(araliklar):
            f.seek(bas)
            parca = f.read(son - bas + 1)
            _istek(upload_url, method="PUT", body=parca, timeout=600, headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(parca)),
                "Content-Range": f"bytes {bas}-{son}/{boyut}",
            })
            if on_progress:
                on_progress((i + 1) / len(araliklar) * 100)

    return {"publish_id": veri.get("publish_id") or ""}
