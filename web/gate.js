/* Beta anahtar kapisi.

   Site tamamen tarayicida calistigi icin bu YUMUSAK bir kapidir: konsolu
   acmayi bilen biri atlayabilir. Amac betayi davetle sinirlamak, kirilmaz bir
   kilit kurmak degil. Anahtarlarin kendisi kodda yok; sadece SHA-256 parmak
   izleri var, yani dosyayi okuyan anahtari ogrenemiyor.

   Bir kez dogru anahtar girilince tarayici hatirliyor, her acilista sormuyor.
*/

const BETA_KEY_HASHES = [
  "021e202d9b31f6b148699f7b59364d4ededb498cb1f1698804a38e3d9b8c9713",
  "063c5065b27559bf9c624e6f25677df3a158ddf466847b305e704c7060f4ffc1",
  "07c821e9538f71ff8fcea2a10fdf94d7bc6cd4d59df793c0a9b409ee486e5cfd",
  "095ef805249dff418d3cf38f463e2d3331dc7bc69a2694dd5bbf4b9f9e1e476b",
  "15b482536b79b90e8e5c2319b68a38c6ffb89cc0f9bb539042fdef07f0a36111",
  "1dd852606992013282c314864e7d623df5eda6c8b2b7bc9da42c4917b08ae33b",
  "2a4bb1af34f3bdb696a27a885d5978e46a2fe1b3f7604bfb05f220c20ebf007d",
  "33d6a65db7e8679ae1171cccc542bad60f0ddc849ff8075294815c010a46ea72",
  "3540ecbf9a7a1d75c8fccb6e08462c8f888611ce3106aa1a72a7ef046856ead9",
  "3575aca31b74a05a9cae809ce0b3bba5dd0ed21ffae1dc1cf4214d776117a218",
  "426e7d906ac37f5184b5f996b8d149e22805696ca3fd9cd8af4d9703de388457",
  "4b230875b6566f61b7b128d6847c5aae4f26471ec520852abdb06d09d79c2e3d",
  "5b0de26e8e2f17afc399166bba76b6dfe809af6181b30e961a9b3dc724e71a5d",
  "5dd2669033b823e519998ddd77600f64c432dfce69114a98952b960b6c9d643d",
  "5f9a8589fd7429f689f6b7f813a9892d356c58d156cec480f11c71b6fcc07070",
  "63870ec5ccc2424f334221dbd49b12beee6d897e4504b8568df6c1f6b8b4c152",
  "65226f8e744c7b2fd3efe5c0082b9ae8deaeca99e1c9b9aac5f2a2c89ff326e7",
  "737fd4dd68b662c6daf935d27bd7b7aaf7457bf315bc306dcba665ac31c83c6c",
  "7fa137631a68f0652e3ebcf04f399a53d70b1f0cfe7ffa370b6e2fa220f7deb7",
  "8362dd69e9da9b21528cf7de2f4c11ad4fcd14d2747bd72c0ed927720a90be59",
  "89a6106beb9cb56e9a2ef9b2e8aea25b15b67151062f95df1d0af402d45aa266",
  "8bc1b3757b5506108ed41778d288bfeeab43ca9aaf74de75da5098bf0aecb4a2",
  "8fea4fa84087faf5127791460281f7073dd91d4b54eb482dbf898ce4a545d96f",
  "928acf6a394aed85a74a2fc99d73fddf1b256bf482be31909db8f93b2c41f976",
  "999851f9df940a320865cb57603da890ee3b04a5e223cc1908a753eb8cd7d592",
  "a3e77aedbd459413dd1df698ebd50c8ef6e54d28f5ce5de3520468fba06251e0",
  "a551ab5831003b7a9339bac6417f0af4c4004079b7b7b008ed9d04a1278dd825",
  "a7bbf6850bfa9ec2c23b6bd7be5c15fea3a413a71ba2b5f34954ca7d92470f72",
  "ab001d7eac4f160cf6308e4d195a9508f6e5a55efac4a32e3276c7c8453e6c02",
  "ab6903545b68b3b9726f99311bf397e056f24b1f1ecdb85b5044d3300d8580ef",
  "ac842b6698494c32f061876668a7c715ce8bbb78d58f180f1220f79d5de247c4",
  "b53f50a2268ed56f4cc7659cddeafefa6f6dd19c132ccbd34b40d39add3ec454",
  "b597fd1f1b151e72693e8052a5aea3797db72d207422c346fdc0644829299989",
  "c01baed842a40086294227fc125ac84997bd302a2154b500333e6838cd0a8129",
  "c3592cd3c810ba115a77a0b8a391c159e85527d555560b0c98e1807f6add2ee7",
  "c5f0fa0ef8d3d5270b598c9d8b564b60f66d6a57ac1dc1c05021b4ab93edd565",
  "c67bc69d082b9af5bdabaf5db0f49551b4ad0fc48c853c14b4a0976f45ea8fa0",
  "cc9f82ec9b64e5188e09c298475d1c0a1f83811946095aa769af91567cbd54a1",
  "cf67cf004fc1668087a08076bd8404fe8c3ba2eb83832fc78843ff2e98b9be87",
  "d463114194e54a0ce744e0a1cbbdb470c2fcc9882d277f41e67dce6e71381a15",
  "d9c4914d8c43257d3519b5ddccb4a666fd0bedf01312a458657cf92bfe95ec4d",
  "e744a1c882689bca88922037525b7e4378cb65afb32adf41871a72f3ec0dc290",
  "e8c2e843d1ad4642aebe799a6421b2c15e3d1d18fa651e46166fa75d1f216c5f",
  "ea671e358be627d444a68ee12c84256d5ff181b00eb81b3f6e932cd00dfe8fae",
  "ecc20dd6a2d5ebe216b13da92ebc4a54ac8d9b73eb7c18a18b59a269bef8718c",
  "f2213c6984a9acf5f02504e92c98a745a58fb1d3699aa3439d3b52ee6ed854fe",
  "f68867d024ce3693440b18611a3d4ff2937db6ff7815e722815ba73a740b323a",
  "fe29e1b8fc4836f24b815c83342fbe428c868ae23de548a9c8cbac40cfa5f9cf"
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
      <div class="gate-top">
        <span class="tag" data-i18n="gate.tag"></span>
        <div class="gate-langs" role="group" aria-label="Language"></div>
      </div>
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

  /* Dil bayraklari kartin ustunde duruyor. Sebep: sayfadaki kure kapinin
     ARKASINDA kaliyor, yani anahtar girilmeden dil degistirilemiyordu --
     Turkce okuyamayan biri kapiya sikisiyordu. Bayraklar menudekilerin
     kopyasi; isaretleme tek yerde, menude kaliyor. */
  const langRow = el.querySelector(".gate-langs");
  document.querySelectorAll("#lang-menu button[data-lang]").forEach((src) => {
    const flag = src.querySelector(".flag");
    if (!flag) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.lang = src.dataset.lang;
    btn.title = src.textContent.trim();
    btn.setAttribute("aria-label", src.textContent.trim());
    btn.appendChild(flag.cloneNode(true));
    btn.onclick = () => applyLang(src.dataset.lang);
    langRow.appendChild(btn);
  });

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
  onLangChange((secili) => {
    document.querySelectorAll("#gate [data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    const alan = document.getElementById("gate-key");
    if (alan) alan.placeholder = t("gate.placeholder");
    document.querySelectorAll("#gate .gate-langs button").forEach((b) => {
      b.classList.toggle("active", b.dataset.lang === secili);
    });
  });
}
