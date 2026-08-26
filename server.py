"""YouTube -> Shorts Clipper. Yerel FastAPI sunucusu."""
import json
import queue
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

from pairing import Pairing
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

# Asama agirliklari: toplam ilerleme yuzdesini bu araliklara dagitiyoruz.
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

app = FastAPI(title="Shorts Clipper")


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
            if not PAIR.allowed(origin, token):
                return JSONResponse(
                    {"detail": "Bu site icin izin yok.", "code": "unpaired"},
                    status_code=403,
                    headers={"Access-Control-Allow-Origin": origin} if origin else None,
                )
        response = await call_next(request)

    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response
jobs = {}
lock = threading.Lock()


class JobRequest(BaseModel):
    url: str
    part_minutes: float = 4.0
    highlight: str = "#FFD400"
    model: str = "large-v3"
    font: str = "Arial Black"
    zoom: float = 1.4              # 1.0 = hic kesilmez, buyudukce video buyur
    captions: bool = False         # caption yakilsin mi
    split_mode: str = "sentence"   # "sentence" | "fixed"


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
    # Transkript sadece caption yakilacaksa ya da cumle sonuna hizali bolme
    # istenirse gerekli. Ikisi de yoksa Whisper'i tamamen atliyoruz -- asil
    # zamani yiyen adim o.
    need_transcript = req.captions or req.split_mode == "sentence"
    stages = STAGES_FULL if need_transcript else STAGES_FAST
    pct = lambda stage, inner: _stage_pct(stage, inner, stages)

    try:
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
            result = transcribe.transcribe(
                wav, model_size=req.model, duration=info["duration"],
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
        if need_transcript and req.split_mode == "sentence":
            parts = segment.build_parts(segments, target=target)
        else:
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
    highlight: str = "#FFD400"
    font: str = "Arial Black"
    sample: str = "ornek altyazi"
    part_minutes: float = 4.0


@app.post("/api/preview")
def make_preview(req: PreviewRequest):
    """Render'a girmeden kadraji gosteren tek kare.

    Kare bir kez cekilip onbellege aliniyor; zoom degistikce sadece yeniden
    kadrajlaniyor, o yuzden ikinci istekten sonrasi anlik.
    """
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
            "paired": PAIR.is_local(origin) or PAIR.known(origin)}


@app.post("/api/pair")
def pair_request(request: Request):
    """Site izin istiyor. Onay ekrani bu bilgisayarda aciliyor, sitede degil."""
    origin = request.headers.get("origin", "")
    if not origin:
        raise HTTPException(400, "Origin yok")
    request_id = PAIR.request(origin)
    return {"request_id": request_id, "url": f"http://127.0.0.1:8000/izin?id={request_id}"}


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


@app.get("/izin")
def pair_page():
    return FileResponse(WEB / "pair.html")


def _require_local(request: Request):
    """Izin ekrani sadece bu bilgisayardan calistirilabilir."""
    if not PAIR.is_local(request.headers.get("origin", "")):
        raise HTTPException(403, "Sadece bu bilgisayardan")


@app.post("/api/perf")
def perf(sample: dict):
    """Gecici olcum modu (?perf=1) buraya yaziyor. Bkz. web/perf.js."""
    with (WORK / "perf.log").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sample, ensure_ascii=False) + chr(10))
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
