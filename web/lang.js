/* Her sayfada ortak olan parcalar: dil secimi, cam dil menusu, kaydirma
   davranisi ve kucuk yardimcilar. Hem ana sayfa hem bilgi sayfalari bunu
   kullaniyor, boylece menunun davranisi tek yerde duruyor.

   i18n.js'ten SONRA, sayfaya ozel scriptten ONCE yuklenmeli.              */

const $ = (id) => document.getElementById(id);
const LANG_KEY = "clipper.lang";

const load = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
};
const save = (key, value) => {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
};

const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

// --- Ceviri ---------------------------------------------------------------
// Sira: kullanicinin kendi secimi > bulundugu bolge > tarayici dili > Ingilizce.
//
// Tarayici dili tek basina yetmiyor: Windows cogu kurulumda en-US donduruyor,
// yani Turkiye'deki biri Ingilizce sayfayla karsilasiyordu. Saat dilimi ise
// makinenin dilini degil bulundugu yeri soyluyor, o yuzden once ona bakiyoruz.
// Adres istemiyor, ag istegi yok, her sey tarayicinin icinde.
const ZONE_LANG = {
  "Europe/Istanbul": "tr", "Asia/Istanbul": "tr",
  "Europe/Berlin": "de", "Europe/Vienna": "de", "Europe/Zurich": "de",
  "Europe/Busingen": "de",
  "Europe/Paris": "fr", "Europe/Brussels": "fr", "Europe/Luxembourg": "fr",
  "Europe/Monaco": "fr",
};

function guessLang() {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (ZONE_LANG[zone]) return ZONE_LANG[zone];
  } catch {}
  for (const tag of navigator.languages ?? [navigator.language ?? ""]) {
    const code = String(tag).slice(0, 2).toLowerCase();
    if (I18N[code]) return code;
  }
  return "en";
}

let lang = null;
try { lang = localStorage.getItem(LANG_KEY); } catch {}
if (!I18N[lang]) lang = guessLang();

/** Anahtari cevirir; {isim} yer tutucularini args ile doldurur. */
function t(key, args) {
  let text = (I18N[lang] && I18N[lang][key]) ?? I18N.tr[key] ?? key;
  if (args) {
    for (const [k, v] of Object.entries(args)) {
      text = text.split(`{${k}}`).join(v);
    }
  }
  return text;
}

// Sozlukten gelmeyen (elle uretilen) metinleri olan sayfalar buraya kaydolur.
const langHooks = [];
const onLangChange = (fn) => langHooks.push(fn);

function applyLang(next) {
  if (I18N[next]) lang = next;
  localStorage.setItem(LANG_KEY, lang);
  document.documentElement.lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("#lang-menu button").forEach((b) => {
    b.classList.toggle("active", b.dataset.lang === lang);
  });

  renderDiscord();
  for (const fn of langHooks) fn(lang);
}

/* Altbilgideki Discord maddesi. Adres config.js'te; bos oldugu surece
   tiklanamaz duz yazi olarak duruyor, doldurulunca baglantiya donusuyor. */
function renderDiscord() {
  disLink("foot-discord", typeof DISCORD_URL === "string" ? DISCORD_URL : "");
  disLink("foot-source", typeof REPO_URL === "string" ? REPO_URL : "");
  // Kurulum dosyasi GitHub'da durdugu icin baglanti config.js'ten geliyor
  disLink("install-btn", typeof SETUP_URL === "string" ? SETUP_URL : "");
}

/** Adres varsa baglanti, yoksa tiklanamaz duz yazi. */
function disLink(id, url) {
  const el = $(id);
  if (!el) return;
  if (url) {
    el.href = url;
    el.target = "_blank";
    el.rel = "noopener";
    el.classList.remove("soon");
  } else {
    el.removeAttribute("href");
    el.classList.add("soon");
  }
}

// --- Dil menusu -----------------------------------------------------------
const langMenu = $("lang-menu");
const langBtn = $("lang-btn");

function closeLangMenu() {
  if (!langMenu.classList.contains("open")) return;
  langMenu.classList.remove("open");
  langBtn.setAttribute("aria-expanded", "false");
  playDispersion();
}

/* Cam acilirken kanallari ayirip renk sacagi olusturur, sonra ust uste
   oturup kaybolurlar. SVG filtresindeki SMIL animasyonlarini tetikliyoruz. */
const dispersion = ["disp-r", "disp-b", "disp-r-sm", "disp-b-sm"]
  .map((id) => document.getElementById(id))
  .filter((el) => el && typeof el.beginElement === "function");

let dispersionTimer = null;

function playDispersion() {
  // Kanal ayrismasi pahali bir filtre; sadece animasyon suresince aciliyor.
  // Durgun filtreyle ayni goruntuyu verdigi icin gecis gorunmuyor.
  langBtn.classList.add("dispersing");
  langMenu.classList.add("dispersing");
  clearTimeout(dispersionTimer);
  dispersionTimer = setTimeout(() => {
    langBtn.classList.remove("dispersing");
    langMenu.classList.remove("dispersing");
  }, 660);

  for (const a of dispersion) {
    try { a.beginElement(); } catch {}
  }
}

langBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const open = !langMenu.classList.contains("open");
  langMenu.classList.toggle("open", open);
  langBtn.setAttribute("aria-expanded", String(open));
  playDispersion();   // hem acilista hem kapanista

  // Donme animasyonunu her tiklamada bastan tetikle
  langBtn.classList.remove("spin");
  void langBtn.offsetWidth;
  langBtn.classList.add("spin");
});

langBtn.addEventListener("animationend", () => langBtn.classList.remove("spin"));

langMenu.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-lang]");
  if (!btn) return;
  applyLang(btn.dataset.lang);
  closeLangMenu();
});

document.addEventListener("click", closeLangMenu);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLangMenu(); });

// Sayfaya ozel scriptler kancalarini kaydettikten sonra ilk ceviriyi yap
addEventListener("DOMContentLoaded", () => {
  applyLang(lang);
  requestAnimationFrame(playDispersion);   // SMIL zaman cizelgesini isit
});
