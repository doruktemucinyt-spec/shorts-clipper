/* Bilgi sayfalari: /faq, /cookies, /privacy, /terms ve bulunamayan
   adresler.
   Metinler pages.js'te, dort dilde. Sayfa hangi adreste acildiysa ona ait
   boluma bakiyor; eslesme yoksa 404 gosteriyor.                          */

// Adresler Ingilizce; eski Turkce adresler de ayni sayfaya cikiyor.
const DOC_PATHS = {
  "/faq": "faq", "/cookies": "cookies", "/privacy": "privacy",
  "/terms": "terms",
  "/sss": "faq", "/cerez": "cookies", "/gizlilik": "privacy",
  "/kosullar": "terms",
};
const docKey = DOC_PATHS[location.pathname.replace(/\/+$/, "")] || "notfound";

function renderDoc() {
  const pack = PAGES[lang] || PAGES.tr;
  const doc = pack[docKey] || PAGES.tr[docKey];

  $("doc-tag").textContent = doc.tag;
  $("doc-title").textContent = doc.title;
  $("doc-lead").textContent = doc.lead;
  $("doc-home").textContent = pack.home || PAGES.tr.home;

  // Soru kullanicidan gelmiyor ama yine de kacisliyoruz; cevaplarda sadece
  // bizim yazdigimiz <b> etiketi var, o yuzden oldugu gibi basiliyor.
  $("doc-items").innerHTML = doc.items.map(([q, a]) => `
    <div class="qa">
      <h3>${escapeHtml(q)}</h3>
      <p>${a}</p>
    </div>`).join("");

  document.title = `${doc.title} · ClipClover`;
}

onLangChange(renderDoc);
