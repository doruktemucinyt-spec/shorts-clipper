/* Aray√ºz ile yardimci arasindaki baglanti katmani.

   Sayfa iki yerden aciliyor olabilir:
   - Kullanicinin kendi bilgisayarindaki yardimcidan (localhost) -- o zaman
     istekler ayni adrese gidiyor, izne gerek yok.
   - Internetteki siteden -- o zaman istekler kullanicinin bilgisayarindaki
     yardimciya gidiyor ve bir anahtar tasimak zorunda (bkz. pairing.py).

   Anahtar tarayicinin deposunda duruyor; izin geri alinirsa sunucu 403
   donuyor ve burada temizleniyor.                                        */

const HELPER_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "clipper.token";

// "Yardimcidan mi acildi" sorusu: yerel adres VE yardimcinin portu. Sadece
// adrese bakmak yetmiyor, cunku site de gelistirme sirasinda localhost'ta
// yayinlanabiliyor.
const LOOPBACK = ["localhost", "127.0.0.1", "[::1]", "::1"];
const IS_LOCAL = LOOPBACK.includes(location.hostname) && location.port === "8000";
const API_BASE = IS_LOCAL ? "" : HELPER_BASE;

let helperToken = IS_LOCAL ? "" : (localStorage.getItem(TOKEN_KEY) || "");
const unpairedHooks = [];
const onUnpaired = (fn) => unpairedHooks.push(fn);

function forgetToken() {
  helperToken = "";
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
  for (const fn of unpairedHooks) fn();
}

/** Dosya adresleri (video, onizleme karesi) icin: adres + anahtar. */
function mediaUrl(path) {
  if (!API_BASE) return path;
  return API_BASE + path + (helperToken ? `?token=${encodeURIComponent(helperToken)}` : "");
}

async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers);
  if (helperToken) headers["X-Clipper-Token"] = helperToken;
  const res = await fetch(API_BASE + path, Object.assign({}, opts, { headers }));
  if (res.status === 403) forgetToken();
  return res;
}

/** Yardimci calisiyor mu, bu site izinli mi? */
async function helperStatus() {
  try {
    const res = await fetch(API_BASE + "/api/hello", {
      headers: helperToken ? { "X-Clipper-Token": helperToken } : {},
    });
    if (!res.ok) return { running: true, paired: false };
    const info = await res.json();
    return { running: true, paired: Boolean(info.paired) || Boolean(helperToken), version: info.version };
  } catch {
    return { running: false, paired: false };     // yardimci kapali ya da kurulu degil
  }
}

/** EventSource kendi basligini gonderemiyor, anahtar adrese ekleniyor. */
function eventsUrl(jobId) {
  const base = `${API_BASE}/api/jobs/${jobId}/events`;
  return helperToken ? `${base}?token=${encodeURIComponent(helperToken)}` : base;
}

/** Izin akisi: onay ekrani kullanicinin kendi bilgisayarinda aciliyor. */
async function requestPairing(onWaiting) {
  const res = await fetch(API_BASE + "/api/pair", { method: "POST" });
  if (!res.ok) throw new Error("pair-failed");
  const { request_id, url } = await res.json();

  window.open(url, "_blank", "noopener");
  if (onWaiting) onWaiting();

  // Onay ekranindaki karari bekliyoruz
  for (let i = 0; i < 150; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const poll = await fetch(`${API_BASE}/api/pair/${request_id}`);
    if (!poll.ok) continue;
    const data = await poll.json();
    if (data.status === "approved" && data.token) {
      helperToken = data.token;
      try { localStorage.setItem(TOKEN_KEY, helperToken); } catch {}
      return true;
    }
    if (data.status === "expired") return false;
  }
  return false;
}
