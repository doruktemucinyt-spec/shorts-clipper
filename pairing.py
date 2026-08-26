"""Siteyle bilgisayar arasindaki izin (eslesme) mekanizmasi.

Site internette duruyor, isi yapan yardimci ise kullanicinin kendi
bilgisayarinda. Yani internetteki bir sayfa, buradaki sunucuya istek atacak.
Bunu kontrolsuz birakmak tehlikeli olur: o zaman herhangi bir web sayfasi da
sessizce ayni sunucuya emir verebilirdi. Onun icin sunlar yapiliyor:

1. Yardimci, kendisine hangi sitelerin baglanabilecegini biliyor. Tanimadigi
   bir adresten gelen istek dogrudan reddediliyor.
2. Tanimadigi bir site once izin istiyor. Izin ekrani INTERNETTEKI sitede
   degil, kullanicinin kendi bilgisayarindaki sunucuda aciliyor -- yani onay
   ekranini site cizemiyor, sahtesini yapamiyor.
3. Kullanici "Izin ver" derse siteye bir anahtar veriliyor. Sonraki her istek
   o anahtari tasimak zorunda; anahtarsiz istek is baslatamiyor.
4. Izin her zaman geri alinabiliyor (izin sayfasindaki liste).

Anahtar ve izinli site listesi work/pairing.json icinde tutuluyor.
"""
import json
import secrets
import threading
import time
from pathlib import Path

# Izin istegi bu sure icinde onaylanmazsa dusuyor
REQUEST_TTL = 300.0

# Kendi bilgisayarindan gelen istekler zaten guvenli sayiliyor
LOCAL_ORIGINS = {
    "http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000",
}


class Pairing:
    def __init__(self, store: Path):
        self.store = store
        self.lock = threading.Lock()
        self.sites = {}       # origin -> {"token": str, "at": float, "name": str}
        self.pending = {}     # request_id -> {"origin": str, "at": float, "token": str|None}
        self._read()

    # --- disk -------------------------------------------------------------
    def _read(self):
        try:
            data = json.loads(self.store.read_text(encoding="utf-8"))
            self.sites = data.get("sites", {})
        except Exception:
            self.sites = {}

    def _write(self):
        self.store.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store.with_suffix(".tmp")
        tmp.write_text(json.dumps({"sites": self.sites}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(self.store)

    # --- sorgular ---------------------------------------------------------
    def is_local(self, origin: str) -> bool:
        return not origin or origin in LOCAL_ORIGINS

    def allowed(self, origin: str, token: str) -> bool:
        """Bu istek gecerli mi? Yerel sayfa serbest, disaridaki site anahtarli."""
        if self.is_local(origin):
            return True
        with self.lock:
            entry = self.sites.get(origin)
        return bool(entry and token and secrets.compare_digest(entry["token"], token))

    def known(self, origin: str) -> bool:
        with self.lock:
            return origin in self.sites

    def listing(self) -> list:
        with self.lock:
            return [{"origin": o, "at": e.get("at", 0)} for o, e in sorted(self.sites.items())]

    # --- izin akisi -------------------------------------------------------
    def request(self, origin: str) -> str:
        """Site izin istiyor; onay ekraninda kullanilacak istek numarasi."""
        self._sweep()
        request_id = secrets.token_urlsafe(9)
        with self.lock:
            self.pending[request_id] = {"origin": origin, "at": time.time(), "token": None}
        return request_id

    def pending_origin(self, request_id: str):
        with self.lock:
            entry = self.pending.get(request_id)
        return entry["origin"] if entry else None

    def approve(self, request_id: str) -> bool:
        with self.lock:
            entry = self.pending.get(request_id)
            if not entry:
                return False
            origin = entry["origin"]
            token = self.sites.get(origin, {}).get("token") or secrets.token_urlsafe(24)
            self.sites[origin] = {"token": token, "at": time.time()}
            entry["token"] = token
            self._write()
        return True

    def reject(self, request_id: str) -> bool:
        with self.lock:
            return self.pending.pop(request_id, None) is not None

    def claim(self, request_id: str):
        """Site sonucu soruyor: onaylandiysa anahtari BIR kez veriyoruz."""
        self._sweep()
        with self.lock:
            entry = self.pending.get(request_id)
            if not entry:
                return "expired", None
            if not entry["token"]:
                return "waiting", None
            token = entry.pop("token")
            self.pending.pop(request_id, None)
        return "approved", token

    def revoke(self, origin: str) -> bool:
        with self.lock:
            gone = self.sites.pop(origin, None) is not None
            if gone:
                self._write()
        return gone

    def _sweep(self):
        now = time.time()
        with self.lock:
            for rid, entry in list(self.pending.items()):
                if now - entry["at"] > REQUEST_TTL:
                    self.pending.pop(rid, None)
