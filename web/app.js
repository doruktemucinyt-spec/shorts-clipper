/* Ana sayfa mantigi. Ortak parcalar (dil menusu, ceviri, kaydirma) lang.js'te;
   bu dosya lang.js'ten SONRA yukleniyor.                                     */

const SETTINGS_KEY = "clipper.settings";
const STAMP_KEY = "clipper.stamp";      // son degisiklik zamani
const HISTORY_KEY = "clipper.history";

let lastJob = null;    // dil degisince ilerleme metnini yeniden cizmek icin
let drawnParts = "";   // part listesi en son hangi durumda cizildi
let ttConnected = false;  // TikTok bagli mi (part butonlari buna bakiyor)

// Sozlukten gelmeyen metinler dil degisince elle yenilenmeli
// Sayfa ilk acilista da bir kez ceviriliyor; o "kullanici degisiklik yapti"
// demek degil. Damgayi sadece gercek degisikliklerde yeniliyoruz, yoksa yerel
// kopya her acilista en yeni gorunur ve yardimcidaki hafiza asla okunmazdi.
let memoryReady = false;
let applyingRemote = false;

onLangChange(() => {
  if (memoryReady && !applyingRemote) {
    save(STAMP_KEY, Date.now());
    pushMemory();
  }
  memoryReady = true;
  updateZoomHint();
  updateCaptionOpts();
  renderPreviewMsg();
  renderHistory();
  refreshWorkSize();
  refreshTikTok();
  if (lastJob) renderJob(lastJob);
  else $("status").textContent = t("status.ready");
});

// --- Ayarlar --------------------------------------------------------------
const settings = load(SETTINGS_KEY, {});
if (settings.minutes) $("minutes").value = settings.minutes;
if (settings.highlight) $("highlight").value = settings.highlight;
// Kayitli model listeden kalkmis olabilir (large-v3 kaldirildi); oyleyse
// secim bos kalmasin diye dokunmuyoruz, listenin ilki secili geliyor.
if (settings.model && $("model").querySelector(`option[value="${settings.model}"]`)) {
  $("model").value = settings.model;
}
if (settings.zoom) $("zoom").value = settings.zoom;
if (settings.at) $("preview-at").value = settings.at;
$("captions").checked = Boolean(settings.captions);

const rememberSettings = () => {
  save(STAMP_KEY, Date.now());
  pushMemory();
  return save(SETTINGS_KEY, {
    minutes: $("minutes").value,
    highlight: $("highlight").value,
    model: $("model").value,
    zoom: $("zoom").value,
    captions: $("captions").checked,
    at: $("preview-at").value,
  });
};

["minutes", "highlight", "model", "zoom", "captions"].forEach(
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
  // Caption yakmak transkript istiyor, yani isi yavaslatiyor: butonun yazisi
  // hangi moda girildigini bastan soyluyor.
  $("caption-opts").classList.toggle("hidden", !$("captions").checked);
  $("start").textContent = t($("captions").checked ? "btn.start" : "btn.startFast");
}
$("captions").addEventListener("change", updateCaptionOpts);

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
    const res = await api("/api/preview", {
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
    if (img.getAttribute("src") === mediaUrl(data.image)) done();   // ayni kare, onbellekten
    else img.src = mediaUrl(data.image);
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

// --- Ustteki serit --------------------------------------------------------
// Discord adresi config.js icinde; hem burada hem altbilgide ayni degeri
// kullaniyoruz ki iki yerde birden guncellemek gerekmesin.
const TICKER_KEYS = ["ticker.open", "ticker.cookies", "ticker.local", "ticker.discord"];

function renderTicker() {
  const parca = TICKER_KEYS.map((key) => {
    const yazi = escapeHtml(t(key));
    const govde = (key === "ticker.discord" && DISCORD_URL)
      ? `<a href="${escapeHtml(DISCORD_URL)}" target="_blank" rel="noopener">${yazi}</a>`
      : `<b>${yazi}</b>`;
    return `${govde}<i>&bull;</i>`;
  }).join("");

  // Ayni metin iki kez: animasyon yariya geldiginde basa donuyor ve dikis
  // gorunmuyor.
  $("ticker").innerHTML = `<span>${parca}</span><span>${parca}</span>`;
}

onLangChange(renderTicker);

// --- Hafiza ---------------------------------------------------------------
// Tarayicinin kendi deposu adrese bagli: localhost:8000 ile internetteki site
// ayri ayri hatirliyor. Ortak nokta bu bilgisayardaki yardimci, o yuzden ayni
// bilgiyi oraya da yaziyoruz. Hangisinin gecerli oldugunu zaman damgasi
// belirliyor -- son degisiklik kazaniyor.
let memoryTimer = null;

function pushMemory() {
  // Ilk yazmada damga yoksa simdiyi koyuyoruz: yoksa iki taraf da sifir kalir
  // ve hangisinin yeni oldugu hic anlasilmaz.
  if (!load(STAMP_KEY, 0)) save(STAMP_KEY, Date.now());
  clearTimeout(memoryTimer);
  memoryTimer = setTimeout(async () => {
    try {
      await api("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          settings: load(SETTINGS_KEY, {}),
          history: load(HISTORY_KEY, []),
          lang,
          at: load(STAMP_KEY, 0),
        }),
      });
    } catch { /* yardimci kapaliysa tarayici kopyasi zaten duruyor */ }
  }, 600);
}

/** Acilista: yardimcidaki kopya daha yeniyse onu al. */
async function pullMemory() {
  let uzak;
  try {
    const res = await api("/api/settings");
    if (!res.ok) return;
    uzak = await res.json();
  } catch {
    return;
  }
  if (!uzak || !uzak.at || uzak.at <= load(STAMP_KEY, 0)) {
    pushMemory();        // buradaki kopya daha yeni: yardimciyi guncelle
    return;
  }

  applyingRemote = true;
  if (uzak.settings) save(SETTINGS_KEY, uzak.settings);
  if (uzak.history) save(HISTORY_KEY, uzak.history);
  save(STAMP_KEY, uzak.at);

  const ayar = uzak.settings || {};
  if (ayar.minutes) $("minutes").value = ayar.minutes;
  if (ayar.highlight) $("highlight").value = ayar.highlight;
  if (ayar.zoom) $("zoom").value = ayar.zoom;
  if (ayar.at) $("preview-at").value = ayar.at;
  if (ayar.model && $("model").querySelector(`option[value="${ayar.model}"]`)) {
    $("model").value = ayar.model;
  }
  $("captions").checked = Boolean(ayar.captions);

  updateZoomHint();
  updateCaptionOpts();
  renderHistory();
  if (uzak.lang && uzak.lang !== lang) applyLang(uzak.lang);
  applyingRemote = false;
}

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
  save(STAMP_KEY, Date.now());
  pushMemory();
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
    const { mb } = await (await api("/api/workspace")).json();
    $("work-size").textContent = mb > 0 ? t("hint.work", { mb }) : t("hint.workEmpty");
  } catch {
    $("work-size").textContent = t("hint.workFail");
  }
}

$("clear-work").onclick = async () => {
  if (!confirm(t("confirm.clear"))) return;
  const { freed_mb } = await (await api("/api/workspace/clear", { method: "POST" })).json();
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
    const res = await api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        part_minutes: parseFloat($("minutes").value) || 4,
        highlight: $("highlight").value,
        model: $("model").value,
        zoom: ($("zoom").value / 100) || 1.4,
        captions: $("captions").checked,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    id = (await res.json()).id;
  } catch (err) {
    fail(t("alert.startFail", { error: err.message }));
    return;
  }

  watchJob(id, (job) => {
    lastJob = job;
    renderJob(job);
    if (job.status === "done") {
      $("start").disabled = false;
      addHistory({ title: job.title, parts: job.parts.length, at: Date.now() });
    } else if (job.status === "error") {
      $("start").disabled = false;
    }
  }, () => {
    $("start").disabled = false;
    refreshWorkSize();
  });
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
  const partsKey = `${lang}|${ttConnected}|${(job.parts || []).length}`;
  if (job.parts?.length && partsKey !== drawnParts) {
    drawnParts = partsKey;
    $("parts").innerHTML = job.parts.map((p) => `
      <div class="part">
        <video src="${mediaUrl(p.url)}" controls preload="metadata"></video>
        <span>${escapeHtml(t("part.label", { index: p.index, duration: p.duration }))}</span>
        ${ttConnected ? `<button class="tt" data-name="${escapeHtml(p.name)}">${escapeHtml(t("part.toTikTok"))}</button>` : ""}
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
  api("/api/reveal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: outDir }),
  });
};



// --- Yardimci baglantisi ---------------------------------------------------
// Sayfa internetteki siteden aciliyorsa isi yapan yardimci kullanicinin kendi
// bilgisayarinda. Once calisiyor mu diye bakiyoruz, sonra izin.

let connState = "idle";

function paintConnection() {
  if (IS_LOCAL) return;
  const titles = {
    idle: ["connect.idleTitle", "connect.idle", "connect.idleBtn"],
    checking: ["connect.checking", "", ""],
    denied: ["connect.deniedTitle", "connect.denied", "connect.missingBtn"],
    missing: ["connect.missingTitle", "connect.missing", "connect.missingBtn"],
    unpaired: ["connect.unpairedTitle", "connect.unpaired", "connect.unpairedBtn"],
    waiting: ["connect.unpairedTitle", "connect.waiting", "connect.unpairedBtn"],
    ok: ["connect.okTitle", "connect.ok", ""],
  };
  const [titleKey, textKey, btnKey] = titles[connState] || titles.checking;
  $("connect-title").textContent = t(titleKey);
  $("connect-text").textContent = textKey ? t(textKey) : "";
  $("connect-btn").textContent = btnKey ? t(btnKey) : "";
  $("connect-btn").classList.toggle("hidden", !btnKey);
  $("connect-btn").disabled = connState === "waiting" || connState === "checking";
  paintSteps();

  // Baglanti yokken is baslatilamasin
  const blocked = connState !== "ok";
  $("start").disabled = blocked;
  $("preview-btn").disabled = blocked;
}

/* Kurulum kartindaki uc adim: hangisi bitti, hangisinde duruyoruz.

   Ucu de bitince kart hemen kaybolmuyor. Once 3. adim yesile donup "hazirsin"
   diyor, kullanici bunu okuyor, sonra kart yukari suzuluyor. Ama sayfa zaten
   bagli acildiysa -- ikinci ziyaretten sonra her seferinde boyle -- bu
   gosteriyi hic oynatmiyoruz: kart gorunmeden kapali kaliyor.

   "checking" bilerek gorunurlugu degistirmiyor: kayitli anahtarla acilista
   birkac yuz milisaniye suren o ara durumda kart bir yanip sonuyordu.      */
let setupSeen = false;
let setupTimer = null;

function markStep(id, durum) {
  const el = $(id);
  el.classList.toggle("done", durum === "done");
  el.classList.toggle("active", durum === "active");
  el.classList.toggle("todo", durum === "todo");
}

function paintSteps() {
  const kart = $("setup");
  // Yardimciya ulasabiliyorsak kurulum adimi bitmis demektir
  const kurulu = connState === "unpaired" || connState === "waiting" || connState === "ok";
  const hazir = connState === "ok";

  markStep("step-install", kurulu ? "done" : "active");
  markStep("step-connect", hazir ? "done" : (kurulu ? "active" : "todo"));
  markStep("step-enjoy", hazir ? "active" : "todo");

  clearTimeout(setupTimer);
  if (connState === "checking") return;

  if (!hazir) {
    setupSeen = true;
    kart.classList.remove("hidden", "gone");
    return;
  }
  if (!setupSeen) {
    kart.classList.add("hidden");
    return;
  }
  setupTimer = setTimeout(() => {
    kart.classList.add("gone");
    setupTimer = setTimeout(() => kart.classList.add("hidden"), 500);
  }, 2400);
}

function setConnState(next) {
  connState = next;
  paintConnection();
  // Baglanti kurulur kurulmaz TikTok'u da yokluyoruz: durumu ancak yardimci
  // konusabildigimizde ogrenebiliyoruz, yoksa buton ve kart sayfa yenilenene
  // kadar gizli kaliyordu.
  if (next === "ok") refreshTikTok();
}

/** Hafif kurulumda transkript yok: o secenekleri kapatiyoruz ki kullanici
    calismayacak bir isi baslatmasin. */
function applyHelperFeatures(status) {
  const noTranscript = status.running && status.transcript === false;
  $("light-note").classList.toggle("hidden", !noTranscript);
  $("captions").disabled = noTranscript;
  if (noTranscript && $("captions").checked) {
    $("captions").checked = false;
    updateCaptionOpts();
  }
}

async function refreshConnection() {
  if (IS_LOCAL) return;
  setConnState("checking");
  const status = await helperStatus();
  applyHelperFeatures(status);
  if (status.running) {
    setConnState(status.paired ? "ok" : "unpaired");
    if (status.paired) pullMemory();
    return;
  }
  // Ulasamadik: ya yardimci kapali ya da tarayici yerel aga izin vermedi
  setConnState(await localNetworkPermission() === "denied" ? "denied" : "missing");
}

$("connect-btn").onclick = async () => {
  // Tarayicinin yerel ag izin penceresi ancak kullanici hareketiyle aciliyor,
  // o yuzden ilk baglanti denemesi bu tiklamanin icinde yapiliyor.
  if (connState === "idle" || connState === "missing" || connState === "denied") {
    refreshConnection();
    return;
  }
  try {
    setConnState("waiting");
    const ok = await requestPairing();
    setConnState(ok ? "ok" : "unpaired");
  } catch {
    setConnState("missing");
  }
};


// --- TikTok ----------------------------------------------------------------
// Video dogrudan bu bilgisayardan TikTok'a gidiyor ve TASLAK olarak dusuyor;
// program hicbir sey yayinlamiyor. Basligi kullanici TikTok uygulamasinda
// yaziyor -- taslak ucu baslik alani kabul etmiyor (bkz. tiktok.py).
// Anahtar tanimli degilse kart hic gorunmuyor.

async function refreshTikTok() {
  let info;
  try {
    const res = await api("/api/tiktok/status");
    if (!res.ok) return;
    info = await res.json();
  } catch { return; }                      // yardimci kapaliysa sessiz gec

  ttConnected = Boolean(info.connected);
  $("tiktok-card").classList.toggle("hidden", !info.available);
  paintTikTokButton(info);
  if (!info.available) return;

  $("tiktok-connect").classList.toggle("hidden", ttConnected);
  $("tiktok-disconnect").classList.toggle("hidden", !ttConnected);
  $("tiktok-state").textContent = ttConnected
    ? t("tiktok.on", { name: info.display_name || "TikTok" })
    : t("tiktok.off");
}

// Ust sagdaki buton: bagli degilken "TikTok ile giris", bagliyken hesabin
// adi ve yesil bir nokta. Anahtar yoksa ya da yardimci kapaliysa hic yok.
function paintTikTokButton(info) {
  const btn = $("tt-login");
  btn.classList.toggle("hidden", !info || !info.available);
  if (!info || !info.available) return;

  $("tt-login-label").textContent = ttConnected
    ? (info.display_name || "TikTok")
    : t("btn.ttLogin");

  // Bagliyken adin yaninda TikTok profil fotografi duruyor. Fotograf yoksa ya
  // da yuklenemezse yerine yesil nokta geciyor -- baglilik isareti her halukarda
  // kalsin, buton bir anda "cikis yapilmis" gibi gorunmesin.
  btn.querySelector(".tt-avatar")?.remove();
  btn.querySelector(".dot")?.remove();
  if (!ttConnected) return;

  if (info.avatar_url) {
    const foto = document.createElement("img");
    foto.className = "tt-avatar";
    foto.alt = "";
    // TikTok'un gorsel sunucusuna nereden geldigimizi bildirmiyoruz.
    foto.referrerPolicy = "no-referrer";
    foto.onerror = () => { foto.replaceWith(nokta()); };
    foto.src = info.avatar_url;
    btn.append(foto);
  } else {
    btn.append(nokta());
  }
}

function nokta() {
  const s = document.createElement("span");
  s.className = "dot";
  return s;
}

async function ttLogin() {
  // Pencere tiklamanin KENDINDE aciliyor. Adres ancak istekten sonra belli
  // oluyor ama araya await girmis bir window.open'i tarayici engelliyor --
  // once bos pencere aciliyor, adresi sonra yaziliyor.
  const pencere = window.open("about:blank", "_blank");
  if (pencere) pencere.opener = null;

  let res, veri;
  try {
    res = await api("/api/tiktok/start", { method: "POST" });
    veri = await res.json().catch(() => ({}));
  } catch { pencere?.close(); return; }

  if (!res.ok) { pencere?.close(); alert(veri.detail || t("tiktok.off")); return; }

  if (pencere) pencere.location = veri.url;
  else window.open(veri.url, "_blank", "noopener");
  $("tiktok-state").textContent = t("tiktok.waiting");

  // Izni kullanici TikTok'ta veriyor, donus de yardimciya gidiyor; bittigini
  // buradan gormenin tek yolu durumu yoklamak.
  for (let i = 0; i < 60 && !ttConnected; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    await refreshTikTok();
  }
}

$("tiktok-connect").onclick = ttLogin;

// Bagliyken ayni butona basmak asagidaki TikTok kartina goturuyor -- baglanti
// kesme ve aciklama orada duruyor.
$("tt-login").onclick = () => {
  if (!ttConnected) { ttLogin(); return; }
  $("tiktok-card").scrollIntoView({ behavior: "smooth", block: "center" });
};

$("tiktok-disconnect").onclick = async () => {
  await api("/api/tiktok/disconnect", { method: "POST" });
  refreshTikTok();
};

// Butonlar liste her cizildiginde yeniden olusuyor, o yuzden dinleyici
// listenin kendisinde duruyor.
$("parts").addEventListener("click", async (ev) => {
  const btn = ev.target.closest(".tt");
  if (!btn || btn.disabled) return;

  btn.disabled = true;
  btn.classList.remove("ok", "err");
  btn.textContent = t("part.sending");
  try {
    const res = await api("/api/tiktok/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: btn.dataset.name }),
    });
    if (!res.ok) {
      const veri = await res.json().catch(() => ({}));
      throw new Error(veri.detail || "");
    }
    btn.textContent = t("part.sent");
    btn.classList.add("ok");
  } catch (e) {
    btn.textContent = e.message || t("part.sendFail");
    btn.classList.add("err");
    btn.disabled = false;                  // tekrar denenebilsin
  }
});

onUnpaired(() => setConnState("idle"));
onLangChange(() => {
  paintConnection();
  // Ust sagdaki butonun yazisi data-i18n ile degil elle yaziliyor (bagliyken
  // yerine hesap adi geciyor), o yuzden dil degisince ayrica tazeleniyor.
  refreshTikTok();
});

// Yardimcidan acildiysa hicbir sey sorulmuyor; siteden acildiysa kullanici
// "Bagla" diyene kadar bekliyoruz.
if (IS_LOCAL) {
  setConnState("ok");                          // TikTok'u da bu tetikliyor
  helperStatus().then(applyHelperFeatures);    // hafif kurulum mu?
  pullMemory();
}
else if (helperToken) refreshConnection();
else paintConnection();
