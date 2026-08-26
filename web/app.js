/* Ana sayfa mantigi. Ortak parcalar (dil menusu, ceviri, kaydirma) lang.js'te;
   bu dosya lang.js'ten SONRA yukleniyor.                                     */

const SETTINGS_KEY = "clipper.settings";
const HISTORY_KEY = "clipper.history";

let lastJob = null;    // dil degisince ilerleme metnini yeniden cizmek icin
let drawnParts = "";   // part listesi en son hangi durumda cizildi

// Sozlukten gelmeyen metinler dil degisince elle yenilenmeli
onLangChange(() => {
  updateZoomHint();
  updateCaptionOpts();
  renderPreviewMsg();
  renderHistory();
  refreshWorkSize();
  if (lastJob) renderJob(lastJob);
  else $("status").textContent = t("status.ready");
});

// --- Ayarlar --------------------------------------------------------------
const settings = load(SETTINGS_KEY, {});
if (settings.minutes) $("minutes").value = settings.minutes;
if (settings.highlight) $("highlight").value = settings.highlight;
if (settings.model) $("model").value = settings.model;
if (settings.zoom) $("zoom").value = settings.zoom;
if (settings.split) $("split").value = settings.split;
if (settings.at) $("preview-at").value = settings.at;
$("captions").checked = Boolean(settings.captions);

const rememberSettings = () => save(SETTINGS_KEY, {
  minutes: $("minutes").value,
  highlight: $("highlight").value,
  model: $("model").value,
  zoom: $("zoom").value,
  split: $("split").value,
  captions: $("captions").checked,
  at: $("preview-at").value,
});

["minutes", "highlight", "model", "zoom", "split", "captions"].forEach(
  (id) => $(id).addEventListener("change", rememberSettings)
);

// --- Zoom onizlemesi (16:9 kaynak varsayimiyla) --------------------------
function updateZoomHint() {
  const zoom = $("zoom").value / 100;
  // Onizleme alindiysa kaynagin gercek orani, alinmadiysa 16:9 varsayimi
  const ratio = previewAspect || 16 / 9;
  const fitH = 1080 / ratio;                   // kirpma yokken video yuksekligi
  const videoH = Math.min(1920, Math.round(fitH * zoom));
  const band = Math.max(0, Math.round((1920 - videoH) / 2));
  const scaledW = videoH * ratio;
  const crop = Math.max(0, (1 - 1080 / scaledW) / 2 * 100);
  $("zoom-hint").textContent = t("hint.zoom", { videoH, band }) + " " +
    (crop < 0.5 ? t("hint.zoomNoCrop") : t("hint.zoomCrop", { crop: crop.toFixed(0) }));
}
$("zoom").addEventListener("input", updateZoomHint);

// --- Caption secenekleri -------------------------------------------------
function updateCaptionOpts() {
  $("caption-opts").classList.toggle("hidden", !$("captions").checked);
  const slow = $("captions").checked || $("split").value === "sentence";
  $("start").textContent = t(slow ? "btn.start" : "btn.startFast");
}
$("captions").addEventListener("change", updateCaptionOpts);
$("split").addEventListener("change", updateCaptionOpts);

// --- Onizleme -------------------------------------------------------------
// Kare cekmek birkac saniye suruyor, ayni kareyi yeniden kadrajlamak anlik.
// Bu yuzden zoom veya renk degisince sunucu ayni kareyi kullaniyor; sadece
// "kare konumu" degisince videodan yeni kare iniyor.
let previewAspect = null;    // kaynagin gercek en/boy orani
let previewOn = false;       // ekranda bir kare var mi
let previewTimer = null;
let previewSeq = 0;          // gec gelen eski cevap yenisini ezmesin
let previewMsgState = { key: "preview.empty", args: null, bad: false };

function renderPreviewMsg() {
  const el = $("preview-msg");
  if (!el) return;
  el.textContent = previewMsgState.key ? t(previewMsgState.key, previewMsgState.args) : "";
  el.classList.toggle("bad", Boolean(previewMsgState.bad));
}

function previewMsg(key, args, bad) {
  previewMsgState = { key, args, bad };
  renderPreviewMsg();
}

const clock = (sec) => {
  const s = Math.max(0, Math.round(sec || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

async function runPreview() {
  const url = $("url").value.trim();
  if (!url) { previewMsg("preview.noUrl", null, true); return; }

  const seq = ++previewSeq;
  const shot = $("preview-shot");
  shot.classList.add("busy");
  previewMsg(previewOn ? "preview.updating" : "preview.loading");
  $("preview-btn").disabled = true;

  try {
    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        zoom: ($("zoom").value / 100) || 1.4,
        at: ($("preview-at").value / 100) || 0,
        captions: $("captions").checked,
        highlight: $("highlight").value,
        sample: t("preview.sample"),
        part_minutes: parseFloat($("minutes").value) || 4,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || res.statusText);
    }
    const data = await res.json();
    if (seq !== previewSeq) return;      // arada daha yeni bir istek gitti

    const img = $("preview-img");
    const done = () => { if (seq === previewSeq) shot.classList.remove("busy"); };
    img.onload = done;
    img.onerror = done;
    if (img.getAttribute("src") === data.image) done();   // ayni kare, onbellekten
    else img.src = data.image;
    img.hidden = false;
    $("preview-empty").hidden = true;

    const [w, h] = (data.source || "").split("x").map(Number);
    if (w && h) { previewAspect = w / h; updateZoomHint(); }
    previewOn = true;
    previewMsg("preview.info", { source: data.source, time: clock(data.at) });
  } catch (err) {
    shot.classList.remove("busy");
    previewMsg("preview.fail", { error: err.message }, true);
  } finally {
    if (seq === previewSeq) $("preview-btn").disabled = false;
  }
}

/** Ayar degisikliklerinde: kare zaten varsa kadraji sessizce tazele. */
function schedulePreview(delay = 320) {
  if (!previewOn) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(runPreview, delay);
}

$("preview-btn").onclick = () => { clearTimeout(previewTimer); runPreview(); };
$("zoom").addEventListener("input", () => schedulePreview());
["captions", "highlight", "minutes"].forEach(
  (id) => $(id).addEventListener("change", () => schedulePreview(0))
);
// Kare konumu yeni indirme demek: kaydirirken degil, birakinca calis
$("preview-at").addEventListener("change", () => { if (previewOn) runPreview(); });

$("url").addEventListener("input", () => {
  previewSeq++;                     // ucusan istek varsa gecersiz kil
  clearTimeout(previewTimer);
  previewOn = false;
  previewAspect = null;
  $("preview-img").hidden = true;
  $("preview-img").removeAttribute("src");
  $("preview-empty").hidden = false;
  $("preview-shot").classList.remove("busy");
  $("preview-btn").disabled = false;
  previewMsg("preview.empty");
  updateZoomHint();
});

// --- Gecmis --------------------------------------------------------------
function renderHistory() {
  const items = load(HISTORY_KEY, []);
  const box = $("history");
  if (!items.length) {
    box.innerHTML = `<p class="empty">${escapeHtml(t("history.empty"))}</p>`;
    return;
  }
  box.innerHTML = items.map((it) => `
    <div>
      <span class="name">${escapeHtml(it.title)} &middot; ${escapeHtml(t("history.parts", { count: it.parts }))}</span>
      <span class="when">${new Date(it.at).toLocaleString(lang)}</span>
    </div>`).join("");
}

function addHistory(entry) {
  const items = load(HISTORY_KEY, []);
  items.unshift(entry);
  save(HISTORY_KEY, items.slice(0, 100));
  renderHistory();
}

// --- Yedek ---------------------------------------------------------------
$("export").onclick = () => {
  const blob = new Blob([JSON.stringify({
    settings: load(SETTINGS_KEY, {}),
    history: load(HISTORY_KEY, []),
    lang,
    exportedAt: new Date().toISOString(),
  }, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `clipper-yedek-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
};

$("import-btn").onclick = () => $("import").click();
$("import").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (data.settings) save(SETTINGS_KEY, data.settings);
    if (data.history) save(HISTORY_KEY, data.history);
    if (data.lang && I18N[data.lang]) localStorage.setItem(LANG_KEY, data.lang);
    location.reload();
  } catch {
    alert(t("alert.backupFail"));
  }
};

// --- Gecici dosyalar -----------------------------------------------------
async function refreshWorkSize() {
  try {
    const { mb } = await (await fetch("/api/workspace")).json();
    $("work-size").textContent = mb > 0 ? t("hint.work", { mb }) : t("hint.workEmpty");
  } catch {
    $("work-size").textContent = t("hint.workFail");
  }
}

$("clear-work").onclick = async () => {
  if (!confirm(t("confirm.clear"))) return;
  const { freed_mb } = await (await fetch("/api/workspace/clear", { method: "POST" })).json();
  alert(t("alert.cleaned", { mb: freed_mb }));
  refreshWorkSize();
};

// --- Is baslatma ---------------------------------------------------------
let outDir = null;

$("start").onclick = async () => {
  const url = $("url").value.trim();
  if (!url) { alert(t("alert.noUrl")); return; }

  rememberSettings();
  $("start").disabled = true;
  $("progress-card").classList.remove("hidden");
  $("parts").innerHTML = "";
  drawnParts = "";
  $("reveal").classList.add("hidden");
  $("fill").classList.remove("error");
  $("fill").style.width = "0%";
  $("meta").textContent = "";
  lastJob = null;
  outDir = null;

  let id;
  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        part_minutes: parseFloat($("minutes").value) || 4,
        highlight: $("highlight").value,
        model: $("model").value,
        zoom: ($("zoom").value / 100) || 1.4,
        captions: $("captions").checked,
        split_mode: $("split").value,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    id = (await res.json()).id;
  } catch (err) {
    fail(t("alert.startFail", { error: err.message }));
    return;
  }

  const es = new EventSource(`/api/jobs/${id}/events`);
  es.onmessage = (ev) => {
    const job = JSON.parse(ev.data);
    lastJob = job;
    renderJob(job);
    if (job.status === "done") {
      $("start").disabled = false;
      addHistory({ title: job.title, parts: job.parts.length, at: Date.now() });
    } else if (job.status === "error") {
      $("start").disabled = false;
    }
  };
  es.addEventListener("end", () => { es.close(); refreshWorkSize(); });
  es.onerror = () => { es.close(); $("start").disabled = false; };
};

/** Sunucu duz metin degil anahtar gonderiyor, cevirisi burada yapiliyor. */
function renderJob(job) {
  $("fill").style.width = `${(job.pct || 0).toFixed(1)}%`;
  $("fill").classList.toggle("error", job.status === "error");
  $("status").textContent = job.msg_key ? t(job.msg_key, job.msg_args) : "";

  const bits = [];
  if (job.title) bits.push(job.title);
  if (job.device) bits.push(t("meta.whisper", { device: job.device.toUpperCase() }));
  if (job.language) bits.push(t("meta.lang", { lang: job.language }));
  if (job.encoder) bits.push(job.encoder);
  if (job.layout) bits.push(t("meta.layout", { videoH: job.layout.video_h, band: job.layout.band }));
  $("meta").textContent = bits.join("  ·  ");

  if (job.out_dir) {
    outDir = job.out_dir;
    $("reveal").classList.remove("hidden");
  }

  // Ilerleme mesajlari saniyede birkac kez geliyor; listeyi her seferinde
  // bastan kurmak video kutularini da bastan yukluyor ve is bitene kadar
  // arayuzu tirmaliyordu. Sadece yeni part eklendiginde (ya da dil degisince)
  // yeniden ciziliyor.
  const partsKey = `${lang}|${(job.parts || []).length}`;
  if (job.parts?.length && partsKey !== drawnParts) {
    drawnParts = partsKey;
    $("parts").innerHTML = job.parts.map((p) => `
      <div class="part">
        <video src="${p.url}" controls preload="metadata"></video>
        <span>${escapeHtml(t("part.label", { index: p.index, duration: p.duration }))}</span>
      </div>`).join("");
  }
}

function fail(message) {
  $("fill").classList.add("error");
  $("fill").style.width = "100%";
  $("status").textContent = message;
  $("start").disabled = false;
}

$("reveal").onclick = () => {
  if (!outDir) return;
  fetch("/api/reveal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: outDir }),
  });
};

