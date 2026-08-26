/* Izin ekrani. Bu sayfa INTERNETTEKI sitede degil, kullanicinin kendi
   bilgisayarindaki yardimcida aciliyor -- adres cubugunda 127.0.0.1 yaziyor.
   Bir site bu ekrani cizemez, dolayisiyla sahtesini yapip kendine izin
   veremez.                                                                */

const params = new URLSearchParams(location.search);
const requestId = params.get("id");

const show = (id, on) => $(id).classList.toggle("hidden", !on);

function finish(titleKey, textKey) {
  show("ask", false);
  show("result", true);
  $("result-title").textContent = t(titleKey);
  $("result-text").textContent = t(textKey);
}

async function loadSites() {
  try {
    const { sites } = await (await fetch("/api/sites")).json();
    $("sites").innerHTML = sites.length
      ? sites.map((s) => `
          <div>
            <span class="name">${escapeHtml(s.origin)}</span>
            <button class="ghost" data-revoke="${escapeHtml(s.origin)}">${escapeHtml(t("pair.remove"))}</button>
          </div>`).join("")
      : `<p class="empty">${escapeHtml(t("pair.none"))}</p>`;
  } catch {
    $("sites").innerHTML = "";
  }
}

$("sites").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-revoke]");
  if (!btn) return;
  await fetch("/api/sites/revoke", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ origin: btn.dataset.revoke }),
  });
  loadSites();
});

async function start() {
  loadSites();
  if (!requestId) return;                 // id yoksa sayfa sadece liste gosteriyor
  try {
    const res = await fetch(`/api/pair-info/${requestId}`);
    if (!res.ok) throw new Error("expired");
    const info = await res.json();
    $("ask-origin").textContent = info.origin;
    show("ask", true);
  } catch {
    finish("pair.expiredTitle", "pair.expired");
  }
}

async function decide(approve) {
  await fetch(`/api/pair-decide/${requestId}?approve=${approve}`, { method: "POST" });
  finish(approve ? "pair.doneTitle" : "pair.rejectedTitle",
         approve ? "pair.done" : "pair.rejected");
  loadSites();
}

$("approve").onclick = () => decide(true);
$("reject").onclick = () => decide(false);

onLangChange(() => { loadSites(); });
start();
