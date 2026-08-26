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
// Varsayilan Turkce. Tarayici dilinden tahmin etmiyoruz: Windows cogu kurulumda
// en-US dondurdugu icin ilk acilis yanlis dilde geliyordu.
let lang = localStorage.getItem(LANG_KEY);
if (!I18N[lang]) lang = "tr";

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
  const el = $("foot-discord");
  if (!el) return;
  const url = typeof DISCORD_URL === "string" ? DISCORD_URL : "";
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

// --- Kaydirma ------------------------------------------------------------
// Kaydirma suresince arka plandaki akan cizgiler duruyor (CSS'te
// html.scrolling). Sebebi: o animasyonun her karesi kartlarin arkasindaki
// goruntuyu degistirdigi icin cam bulanikligi da her karede yeniden
// hesaplaniyordu. Dinleyici passive, yani kaydirmayi hic bekletmiyor.
let scrollIdle = null;
addEventListener("scroll", () => {
  const root = document.documentElement;
  if (!root.classList.contains("scrolling")) root.classList.add("scrolling");
  clearTimeout(scrollIdle);
  scrollIdle = setTimeout(() => root.classList.remove("scrolling"), 140);
}, { passive: true });

// Sayfaya ozel scriptler kancalarini kaydettikten sonra ilk ceviriyi yap
addEventListener("DOMContentLoaded", () => {
  applyLang(lang);
  requestAnimationFrame(playDispersion);   // SMIL zaman cizelgesini isit
});
