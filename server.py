"""YouTube -> ClipClover. Yerel FastAPI sunucusu."""
import ipaddress
import json
import queue
import socket
import subprocess
import threading
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from pairing import LOCAL_ORIGINS, Pairing
from urllib.parse import urlparse

from pipeline import captions, preview, render, segment, transcribe
from pipeline.download import download
from pipeline.tools import probe_dimensions

ROOT = Path(__file__).parent
WEB = ROOT / "web"
WORK = ROOT / "work"
OUTPUT = ROOT / "output"
WORK.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)
PREVIEW = WORK / "preview"
PREVIEW.mkdir(parents=True, exist_ok=True)

# Ayarlar ve is gecmisi. Tarayicinin kendi deposu adrese bagli oldugu icin
# localhost:8000 ile internetteki site birbirinin gecmisini gormuyordu; ortak
# nokta bu bilgisayardaki yardimci, o yuzden bir kopya burada duruyor.
# Dosya kullanicinin kendi diskinde, disariya gonderilmiyor.
USER_FILE = WORK / "user.json"

# Asama agirliklari: toplam ilerleme yuzdesini bu araliklara dagitiyoruz.
# Su an tek model: small (~0,5 GB). Buyuk modeller araci agirlastirdigi icin
# kapali; arayuzde "yakinda" diye gorunuyorlar. Tanimadigimiz bir deger
# gelirse (eski bir tarayici ayari ya da elle gonderilmis istek) sessizce
# small'a dusuyoruz -- kimse farkinda olmadan 3 GB indirmesin.
MODELS = {"small"}
DEFAULT_MODEL = "small"

STAGES_FULL = {
    "download": (0, 18), "transcribe": (18, 55),
    "split": (55, 58), "render": (58, 100),
}
# Transkript atlanirsa render tum zamani kaplar
STAGES_FAST = {
    "download": (0, 12), "transcribe": (12, 12),
    "split": (12, 14), "render": (14, 100),
}

APP_VERSION = "1.0"

# Internetteki siteyle bu bilgisayar arasindaki izin mekanizmasi (pairing.py)
PAIR = Pairing(WORK / "pairing.json")

# Izin gerektirmeyen uclar: siteyi taniyip izin isteyebilmek icin gerekli
OPEN_PATHS = ("/api/hello", "/api/pair")

# Sunucunun kabul ettigi adresler. Bu kontrol DNS yeniden baglama (rebinding)
# saldirisini kesiyor: kotu bir site kendi alan adini 127.0.0.1'e cozdurup
# tarayiciya "ayni site" dedirtebiliyor ve boylece butun CORS/anahtar
# kontrollerini atlayabiliyordu. Istek baska bir alan adina geldiyse artik
# kapida duruyor.
ALLOWED_HOSTS = {"localhost:8000", "127.0.0.1:8000", "[::1]:8000"}

# Ayni anda kac is calisabilir: her is GB'larca indirme ve GPU demek.
MAX_ACTIVE_JOBS = 2

# Bellekte tutulan is kaydi sayisi
MAX_JOB_HISTORY = 50

app = FastAPI(title="ClipClover")


def _page_is_local(request: Request) -> bool:
    """Istek kullanicinin kendi bilgisayarindaki sayfadan mi geliyor?

    Origin varsa bakmasi kolay. Ama tarayici basit GET isteklerinde Origin
    gondermiyor: kotu bir sayfa <img src="http://127.0.0.1:8000/..."> ile
    istek atsa origin bos gelirdi ve eskiden bu "yerel" sayilirdi. Modern
    tarayicilar bu durumda Sec-Fetch-Site basligiyla istegin nereden geldigini
    soyluyor; cross-site ise yabancidir.
    """
    origin = request.headers.get("origin", "")
    if origin:
        return origin in LOCAL_ORIGINS
    return request.headers.get("sec-fetch-site", "") in ("", "none", "same-origin")


@app.middleware("http")
async def cross_site_guard(request: Request, call_next):
    """Internetteki sayfalarin bu sunucuyu kullanmasini kurala baglar.

    Tarayici, baska bir siteden yerel aga istek atarken once izin sorusu
    (preflight) gonderiyor; ona "Access-Control-Allow-Private-Network" ile
    cevap vermek zorundayiz, yoksa Chrome istegi hic yapmiyor.

    Asil kapi ise anahtar: tanimadigimiz bir siteden gelen is istekleri
    reddediliyor. Kullanicinin kendi bilgisayarindaki sayfa serbest.
    """
    origin = request.headers.get("origin", "")
    path = request.url.path

    if (request.headers.get("host") or "").lower() not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Beklenmeyen adres"}, status_code=403)

    if request.method == "OPTIONS":
        response = Response(status_code=204)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Clipper-Token"
        response.headers["Access-Control-Max-Age"] = "600"
    else:
        needs_key = path.startswith(("/api/", "/media/", "/preview/"))             and not path.startswith(OPEN_PATHS)
        if needs_key:
            # EventSource kendi basligini gonderemedigi icin anahtari adresten
            # de kabul ediyoruz; istek zaten sadece bu bilgisayardan geliyor.
            token = request.headers.get("x-clipper-token") or                 request.query_params.get("token", "")
            # Video/onizleme dosyalari <video> ve <img> ile yukleniyor,
            # tarayici bu isteklere Origin koymuyor: orada anahtarin kendisi
            # yetiyor.
            dosya_istegi = path.startswith(("/media/", "/preview/"))
            izinli = (_page_is_local(request)
                      or PAIR.allowed_site(origin, token)
                      or (dosya_istegi and PAIR.token_valid(token)))
            if not izinli:
                return JSONResponse(
                    {"detail": "Bu site icin izin yok.", "code": "unpaired"},
                    status_code=403,
                    headers={"Access-Control-Allow-Origin": origin} if origin else None,
                )
        response = await call_next(request)

    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"

    # Izin ekrani bir cerceve icine alinip yanlislikla tiklatilamasin
    # (clickjacking); adresler de disari sizmasin.
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response
jobs = {}
lock = threading.Lock()


class JobRequest(BaseModel):
    url: str
    part_minutes: float = 4.0
    highlight: str = "#4ADE80"
    model: str = "small"      # kucuk model varsayilan: ~0,5 GB iniyor
    font: str = "Arial Black"
    zoom: float = 1.4              # 1.0 = hic kesilmez, buyudukce video buyur
    captions: bool = False         # caption yakilsin mi


def check_url(url: str) -> str:
    """Sadece internetteki http/https adresleri kabul ediliyor.

    Iki sey engelleniyor:
    - file:// gibi semalar: izinli bir site yardimciya diskteki bir dosyayi
      okutup render ettirebilir, sonra da /media uzerinden geri okuyabilirdi.
    - yerel ve ic ag adresleri: yardimci, ev agindaki cihazlara (modem, kamera,
      NAS) istek atmak icin kullanilan bir arac haline gelmesin.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Sadece http veya https adresleri kullanilabilir.")
    host = parsed.hostname or ""
    if not host:
        raise HTTPException(400, "Adres okunamadi.")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise HTTPException(400, "Adres cozulemedi.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            raise HTTPException(400, "Yerel ag adresleri kullanilamaz.")
    return url.strip()


def _emit(job_id: str, **fields):
    with lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        snapshot = {k: v for k, v in job.items() if k != "queue"}
    jobs[job_id]["queue"].put(snapshot)


def _stage_pct(stage: str, inner: float, stages=None) -> float:
    lo, hi = (stages or STAGES_FULL)[stage]
    return lo + (hi - lo) * max(0.0, min(100.0, inner)) / 100.0


def run_job(job_id: str, req: JobRequest):
    workdir = WORK / job_id
    # Partlar her zaman tam surede kesiliyor; transkript yalnizca caption
    # yakilacaksa gerekiyor -- asil zamani yiyen adim o.
    need_transcript = req.captions
    stages = STAGES_FULL if need_transcript else STAGES_FAST
    pct = lambda stage, inner: _stage_pct(stage, inner, stages)

    try:
        if need_transcript and not transcribe.available():
            _emit(job_id, status="error", stage="error",
                  error="transcript-unavailable", msg_key="job.needFull", msg_args={})
            return

        # 1) Indirme
        _emit(job_id, stage="download", pct=0, msg_key="job.downloading", msg_args={})
        info = download(
            req.url, workdir,
            on_progress=lambda p, k, a: _emit(
                job_id, pct=pct("download", p), msg_key=k, msg_args=a),
        )
        title, slug, source = info["title"], info["slug"], info["path"]
        out_dir = OUTPUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        _emit(job_id, title=title, slug=slug, out_dir=str(out_dir),
              msg_key="job.downloaded", msg_args={"title": title})

        src_w, src_h = probe_dimensions(source)
        layout = render.compute_layout(src_w, src_h, req.zoom)
        _emit(job_id, layout={"video_h": layout["video_h"], "band": layout["band"]})

        # 2) Transkript (gerekiyorsa)
        segments = []
        if need_transcript:
            _emit(job_id, stage="transcribe", pct=pct("transcribe", 0),
                  msg_key="job.extractingAudio", msg_args={})
            wav = transcribe.extract_audio(source, workdir)
            model_size = req.model if req.model in MODELS else DEFAULT_MODEL
            result = transcribe.transcribe(
                wav, model_size=model_size, duration=info["duration"],
                on_progress=lambda p, k, a: _emit(
                    job_id, pct=pct("transcribe", p), msg_key=k, msg_args=a),
            )
            segments = result["segments"]
            _emit(job_id, device=result["device"], language=result["language"])
            wav.unlink(missing_ok=True)

        # 3) Bolme
        _emit(job_id, stage="split", pct=pct("split", 50),
              msg_key="job.splitting", msg_args={})
        target = req.part_minutes * 60
        parts = segment.build_parts_fixed(info["duration"], target=target)
        total = len(parts)
        if not total:
            raise RuntimeError("Video bolunemedi (sure okunamadi).")
        _emit(job_id, part_total=total,
              msg_key="job.partsFound", msg_args={"total": total})

        # 4) Render
        _emit(job_id, stage="render", pct=pct("render", 0))
        done_parts = []
        used_nvenc = True
        for p_ in parts:
            idx = p_["index"]
            name = f"part-{idx:02d}"
            words = segment.words_in_range(segments, p_["start"], p_["end"])                 if req.captions else []
            ass_text = captions.build_ass(
                words, p_["start"], p_["duration"], title, idx, total,
                font=req.font, highlight=req.highlight,
                include_words=req.captions,
            )
            ass_file = workdir / f"{name}.ass"
            ass_file.write_text(ass_text, encoding="utf-8")

            def on_part(inner, idx=idx):
                overall = ((idx - 1) + inner / 100.0) / total * 100.0
                _emit(job_id, pct=pct("render", overall), msg_key="job.rendering",
                      msg_args={"index": idx, "total": total, "pct": round(inner)})

            out_file = out_dir / f"{name}.mp4"
            used_nvenc = render.render_part(
                source, workdir, f"{name}.ass", p_["start"], p_["duration"],
                out_file, layout, use_nvenc=used_nvenc, on_progress=on_part,
            )
            done_parts.append({
                "index": idx, "name": out_file.name,
                "duration": round(p_["duration"], 1),
                "url": f"/media/{slug}/{out_file.name}",
            })
            _emit(job_id, parts=list(done_parts))

        _emit(job_id, stage="done", pct=100, status="done",
              encoder="NVENC (GPU)" if used_nvenc else "libx264 (CPU)",
              msg_key="job.done", msg_args={"total": total})
    except Exception as exc:
        _emit(job_id, status="error", stage="error", error=f"{exc}",
              msg_key="job.failed", msg_args={"error": str(exc)[:400]})
        traceback.print_exc()
    finally:
        jobs[job_id]["queue"].put(None)


@app.post("/api/jobs")
def create_job(req: JobRequest):
    check_url(req.url)

    active = sum(1 for j in jobs.values() if j.get("status") == "running")
    if active >= MAX_ACTIVE_JOBS:
        raise HTTPException(429, "Su an baska bir is calisiyor, bitmesini bekle.")

    # Eski kayitlar bellekte birikmesin
    if len(jobs) > MAX_JOB_HISTORY:
        for old in list(jobs)[: len(jobs) - MAX_JOB_HISTORY]:
            if jobs[old].get("status") != "running":
                jobs.pop(old, None)

    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {
        "id": job_id, "status": "running", "stage": "download", "pct": 0,
        "msg_key": "job.starting", "msg_args": {}, "parts": [], "title": "", "url": req.url,
        "queue": queue.Queue(),
    }
    threading.Thread(target=run_job, args=(job_id, req), daemon=True).start()
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Is bulunamadi")
    return {k: v for k, v in job.items() if k != "queue"}


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Is bulunamadi")

    def stream():
        snapshot = {k: v for k, v in job.items() if k != "queue"}
        yield f"data: {json.dumps(snapshot)}\n\n"
        while True:
            item = job["queue"].get()
            if item is None:
                yield "event: end\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


class PreviewRequest(BaseModel):
    url: str
    zoom: float = 1.4
    at: float = 0.25               # videonun neresinden kare alinacak (0-1)
    captions: bool = False
    highlight: str = "#4ADE80"
    font: str = "Arial Black"
    sample: str = "ornek altyazi"
    part_minutes: float = 4.0


@app.post("/api/preview")
def make_preview(req: PreviewRequest):
    """Render'a girmeden kadraji gosteren tek kare.

    Kare bir kez cekilip onbellege aliniyor; zoom degistikce sadece yeniden
    kadrajlaniyor, o yuzden ikinci istekten sonrasi anlik.
    """
    check_url(req.url)
    try:
        return preview.build(
            req.url, PREVIEW, zoom=req.zoom, at=req.at,
            with_captions=req.captions, highlight=req.highlight,
            font=req.font, sample=req.sample, part_minutes=req.part_minutes,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)[:400])


class RevealRequest(BaseModel):
    path: str


@app.get("/api/workspace")
def workspace_size():
    total = sum(f.stat().st_size for f in WORK.rglob("*") if f.is_file())
    return {"bytes": total, "mb": round(total / 1024 / 1024, 1)}


@app.post("/api/workspace/clear")
def workspace_clear():
    """Indirilen kaynak videolar ve ara dosyalar. output/ klasorune dokunmaz."""
    import shutil
    freed = 0
    for child in WORK.iterdir():
        if child.is_dir():
            freed += sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
            shutil.rmtree(child, ignore_errors=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)   # mount edilmis klasor kaybolmasin
    return {"freed_mb": round(freed / 1024 / 1024, 1)}


@app.get("/api/hello")
def hello(request: Request):
    """Site once buraya soruyor: yardimci calisiyor mu, izinli miyim?"""
    origin = request.headers.get("origin", "")
    return {"app": "shorts-clipper", "version": APP_VERSION,
            "paired": PAIR.is_local(origin) or PAIR.known(origin),
            # Hafif kurulumda transkript kutuphanesi yok; arayuz cumleye
            # hizali bolme ve caption seceneklerini buna gore kapatiyor.
            "transcript": transcribe.available()}


@app.post("/api/pair")
def pair_request(request: Request):
    """Site izin istiyor. Onay ekrani bu bilgisayarda aciliyor, sitede degil."""
    origin = request.headers.get("origin", "")
    if not origin:
        raise HTTPException(400, "Origin yok")
    request_id = PAIR.request(origin)
    return {"request_id": request_id, "url": f"http://127.0.0.1:8000/permission?id={request_id}"}


@app.get("/api/pair/{request_id}")
def pair_status(request_id: str):
    status, token = PAIR.claim(request_id)
    return {"status": status, "token": token}


class OriginBody(BaseModel):
    origin: str = ""


@app.get("/api/pair-info/{request_id}")
def pair_info(request: Request, request_id: str):
    """Onay ekrani hangi siteyi soracagini buradan ogreniyor (sadece yerel)."""
    _require_local(request)
    origin = PAIR.pending_origin(request_id)
    if not origin:
        raise HTTPException(404, "Istek dusmus")
    return {"origin": origin, "sites": PAIR.listing()}


@app.post("/api/pair-decide/{request_id}")
def pair_decide(request: Request, request_id: str, approve: bool = True):
    _require_local(request)
    ok = PAIR.approve(request_id) if approve else PAIR.reject(request_id)
    if not ok:
        raise HTTPException(404, "Istek dusmus")
    return {"ok": True}


@app.post("/api/sites/revoke")
def revoke_site(request: Request, body: OriginBody):
    _require_local(request)
    return {"ok": PAIR.revoke(body.origin)}


@app.get("/api/sites")
def list_sites(request: Request):
    _require_local(request)
    return {"sites": PAIR.listing()}


@app.get("/permission")
@app.get("/izin")
def pair_page():
    return FileResponse(WEB / "pair.html")


def _require_local(request: Request):
    """Izin ekrani sadece bu bilgisayardaki sayfadan kullanilabilir."""
    if not _page_is_local(request):
        raise HTTPException(403, "Sadece bu bilgisayardan")


@app.get("/api/settings")
def read_settings():
    """Yardimcida tutulan ayar/gecmis kopyasi."""
    try:
        return json.loads(USER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"at": 0}


@app.post("/api/settings")
def write_settings(body: dict):
    """Arayuz her degisiklikte buraya da yaziyor.

    Cakismayi zaman damgasi cozuyor: iki taraftan hangisi daha yeniyse o
    kazaniyor (bkz. web/app.js icindeki hafiza bolumu).
    """
    data = {
        "settings": body.get("settings") or {},
        "history": (body.get("history") or [])[:100],
        "lang": body.get("lang") or "tr",
        "at": float(body.get("at") or 0),
    }
    tmp = USER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(USER_FILE)
    return {"ok": True}


@app.post("/api/reveal")
def reveal(req: RevealRequest):
    target = Path(req.path).resolve()
    # Sadece kendi cikti klasorumuzun icini acabiliyoruz: disaridaki bir site
    # bu ucu kullanip rastgele bir klasoru actiramasin.
    if OUTPUT.resolve() not in target.parents and target != OUTPUT.resolve():
        raise HTTPException(400, "Bu klasor acilamaz")
    if not target.exists():
        raise HTTPException(404, "Klasor yok")
    subprocess.Popen(["explorer", str(target)])
    return {"ok": True}


app.mount("/preview", StaticFiles(directory=str(PREVIEW)), name="preview")
app.mount("/media", StaticFiles(directory=str(OUTPUT)), name="media")
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


# Bilgi sayfalarinin hepsi ayni kabugu kullaniyor; hangi metnin gosterilecegine
# tarayici tarafinda adrese bakarak karar veriliyor (web/page.js).
@app.get("/faq")
@app.get("/cookies")
@app.get("/privacy")
# Eski Turkce adresler de calismaya devam ediyor: paylasilmis baglantilar
# kirilmasin.
@app.get("/sss")
@app.get("/cerez")
@app.get("/gizlilik")
def info_page():
    return FileResponse(WEB / "page.html")


@app.exception_handler(StarletteHTTPException)
def not_found(request: Request, exc: StarletteHTTPException):
    """Olmayan adresler icin 404 sayfasi. API ve dosya yollari JSON aliyor."""
    api_like = request.url.path.startswith(("/api", "/media", "/static", "/preview"))
    if exc.status_code == 404 and not api_like:
        return FileResponse(WEB / "page.html", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
