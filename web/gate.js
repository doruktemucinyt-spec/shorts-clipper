/* Beta anahtar kapisi.

   Site tamamen tarayicida calistigi icin bu YUMUSAK bir kapidir: konsolu
   acmayi bilen biri atlayabilir. Amac betayi davetle sinirlamak, kirilmaz bir
   kilit kurmak degil. Anahtarlarin kendisi kodda yok; sadece SHA-256 parmak
   izleri var, yani dosyayi okuyan anahtari ogrenemiyor.

   Bir kez dogru anahtar girilince tarayici hatirliyor, her acilista sormuyor.
*/

const BETA_KEY_HASHES = [
  "737fd4dd68b662c6daf935d27bd7b7aaf7457bf315bc306dcba665ac31c83c6c",
  "89a6106beb9cb56e9a2ef9b2e8aea25b15b67151062f95df1d0af402d45aa266",
  "4b230875b6566f61b7b128d6847c5aae4f26471ec520852abdb06d09d79c2e3d",
  "426e7d906ac37f5184b5f996b8d149e22805696ca3fd9cd8af4d9703de388457",
  "5dd2669033b823e519998ddd77600f64c432dfce69114a98952b960b6c9d643d",
  "e8c2e843d1ad4642aebe799a6421b2c15e3d1d18fa651e46166fa75d1f216c5f",
  "021e202d9b31f6b148699f7b59364d4ededb498cb1f1698804a38e3d9b8c9713",
  "a3e77aedbd459413dd1df698ebd50c8ef6e54d28f5ce5de3520468fba06251e0",
  "1dd852606992013282c314864e7d623df5eda6c8b2b7bc9da42c4917b08ae33b",
  "c5f0fa0ef8d3d5270b598c9d8b564b60f66d6a57ac1dc1c05021b4ab93edd565",
  "15b482536b79b90e8e5c2319b68a38c6ffb89cc0f9bb539042fdef07f0a36111",
  "d463114194e54a0ce744e0a1cbbdb470c2fcc9882d277f41e67dce6e71381a15"
];

const BETA_STORE = "clipper.beta";

async function betaHash(text) {
  const veri = new TextEncoder().encode(text.trim().toUpperCase());
  const ozet = await crypto.subtle.digest("SHA-256", veri);
  return [...new Uint8Array(ozet)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function betaUnlocked() {
  try { return localStorage.getItem(BETA_STORE) === "1"; } catch { return false; }
}

function buildGate() {
  const el = document.createElement("div");
  el.className = "gate";
  el.id = "gate";
  el.innerHTML = `
    <div class="gate-card">
      <span class="tag" data-i18n="gate.tag"></span>
      <h2 class="doc-title" data-i18n="gate.title"></h2>
      <p class="doc-lead" data-i18n="gate.lead"></p>
      <input id="gate-key" type="text" autocomplete="off" spellcheck="false"
             data-i18n-placeholder="gate.placeholder">
      <p class="hint gate-error" id="gate-error"></p>
      <button id="gate-btn" class="primary" data-i18n="gate.button"></button>
      <p class="hint gate-foot">
        <span data-i18n="gate.nokey"></span>
        <a id="gate-discord" target="_blank" rel="noopener" data-i18n="gate.discord"></a>
      </p>
    </div>`;
  document.body.appendChild(el);

  const url = typeof DISCORD_URL === "string" ? DISCORD_URL : "";
  if (url) $("gate-discord").href = url;
  else $("gate-discord").classList.add("soon");

  const dene = async () => {
    const girilen = $("gate-key").value.trim();
    if (!girilen) return;
    $("gate-btn").disabled = true;
    const ozet = await betaHash(girilen);
    if (BETA_KEY_HASHES.includes(ozet)) {
      try { localStorage.setItem(BETA_STORE, "1"); } catch {}
      el.classList.add("open");                 // cam kapanma animasyonu
      setTimeout(() => el.remove(), 420);
      document.documentElement.classList.remove("gated");
      return;
    }
    $("gate-btn").disabled = false;
    $("gate-error").textContent = t("gate.error");
    $("gate-key").classList.add("bad");
    setTimeout(() => $("gate-key").classList.remove("bad"), 600);
  };

  $("gate-btn").onclick = dene;
  $("gate-key").addEventListener("keydown", (e) => { if (e.key === "Enter") dene(); });
  $("gate-key").addEventListener("input", () => { $("gate-error").textContent = ""; });
  setTimeout(() => $("gate-key").focus(), 120);
}

if (!betaUnlocked()) {
  document.documentElement.classList.add("gated");
  buildGate();
  // Metinler dil degisiminde de yenilensin
  onLangChange(() => {
    document.querySelectorAll("#gate [data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    const alan = document.getElementById("gate-key");
    if (alan) alan.placeholder = t("gate.placeholder");
  });
}
