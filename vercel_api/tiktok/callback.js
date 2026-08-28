/* TikTok girisinin son adimi. Sitede calisan TEK sunucu parcasi.
 *
 * Neden var: TikTok'un token ucu client_secret istiyor ve secret'i kullanicinin
 * bilgisayarina koyamayiz -- program herkese dagitiliyor, ilk acan gorurdu.
 * O yuzden kodu token'a cevirme isi burada, Vercel'de yapiliyor; secret
 * ortam degiskeninde duruyor ve tarayiciya hicbir zaman inmiyor.
 *
 * Token'i yardimciya nasil veriyoruz: bu sayfa, kullanicinin kendi
 * bilgisayarindaki http://127.0.0.1:8000/api/tiktok/finish adresine kendini
 * gonderen bir form basiyor. Ust seviye form gonderimi tercih edildi, fetch
 * DEGIL: Chrome'un yerel ag izni sadece sayfa ici isteklere bakiyor, sayfa
 * gecislerine karismiyor -- yani ayrica izin penceresi cikmiyor. Ayrica
 * token adres satirinda degil govdede gidiyor, yardimcinin gunlugune
 * dusmuyor.
 *
 * Sahte istek koruma: yardimci "state" degerini kendisi uretiyor ve sadece
 * kendi urettigini kabul ediyor. Baska bir site bu ucu doldurmaya calisirsa
 * dogru state'i bilemez.
 */

const TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/";
const REDIRECT_URI = "https://clipclover.online/api/tiktok/callback";
const HELPER_FINISH = "http://127.0.0.1:8000/api/tiktok/finish";

function sayfa({ baslik, mesaj, alanlar }) {
  const gizli = Object.entries(alanlar || {})
    .map(([k, v]) => `<input type="hidden" name="${k}" value="${kacisla(v)}">`)
    .join("\n    ");
  const form = alanlar
    ? `<form id="f" method="POST" action="${HELPER_FINISH}">
    ${gizli}
    <button type="submit">Bağlantıyı tamamla</button>
  </form>
  <script>setTimeout(function () { document.getElementById("f").submit(); }, 400);</script>`
    : "";
  return `<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${kacisla(baslik)} · ClipClover</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center;
         background: #08090a; color: #e8ebe9;
         font: 400 15px/1.6 Inter, system-ui, -apple-system, sans-serif; }
  .kutu { max-width: 30rem; padding: 2.5rem 2rem; text-align: center; }
  h1 { font-size: 1.35rem; font-weight: 800; margin: 0 0 .75rem; }
  p { margin: 0 0 1.5rem; color: #9aa3a0; }
  button { font: inherit; font-weight: 600; color: #08090a; background: #4ade80;
           border: 0; border-radius: 10px; padding: .7rem 1.4rem; cursor: pointer; }
  button:hover { background: #22c55e; }
</style></head>
<body><div class="kutu">
  <h1>${kacisla(baslik)}</h1>
  <p>${kacisla(mesaj)}</p>
  ${form}
</div></body></html>`;
}

function kacisla(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  // Bu sayfa tek seferlik ve token tasiyor; hicbir yerde durmasin.
  res.setHeader("Cache-Control", "no-store");

  const { code, state, error, error_description } = req.query || {};

  if (error) {
    res.status(400).send(sayfa({
      baslik: "Bağlantı iptal edildi",
      mesaj: error_description || String(error),
    }));
    return;
  }
  if (!code || !state) {
    res.status(400).send(sayfa({
      baslik: "Eksik yanıt",
      mesaj: "TikTok beklenen bilgileri göndermedi. Programdan tekrar dene.",
    }));
    return;
  }

  const clientKey = process.env.TIKTOK_CLIENT_KEY;
  const clientSecret = process.env.TIKTOK_CLIENT_SECRET;
  if (!clientKey || !clientSecret) {
    res.status(500).send(sayfa({
      baslik: "Sunucu ayarı eksik",
      mesaj: "TikTok anahtarları tanımlı değil.",
    }));
    return;
  }

  let veri;
  try {
    const yanit = await fetch(TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_key: clientKey,
        client_secret: clientSecret,
        code: String(code),
        grant_type: "authorization_code",
        redirect_uri: REDIRECT_URI,
      }),
    });
    veri = await yanit.json();
  } catch (e) {
    res.status(502).send(sayfa({
      baslik: "TikTok'a ulaşılamadı",
      mesaj: "Bağlantı kurulamadı, birazdan tekrar dene.",
    }));
    return;
  }

  if (!veri || !veri.access_token) {
    // TikTok hatayi govdede dondurüyor; sebebini kullaniciya gosteriyoruz ama
    // ham cevabi degil -- icinde tanimlayici alanlar olabiliyor.
    res.status(400).send(sayfa({
      baslik: "TikTok izni alınamadı",
      mesaj: veri && (veri.error_description || veri.error)
        ? String(veri.error_description || veri.error)
        : "Beklenmeyen bir yanıt geldi.",
    }));
    return;
  }

  res.status(200).send(sayfa({
    baslik: "TikTok bağlandı",
    baslikYok: true,
    mesaj: "Son adım: bilgisayarındaki ClipClover'a aktarılıyor.",
    alanlar: {
      state: String(state),
      access_token: veri.access_token,
      refresh_token: veri.refresh_token || "",
      expires_in: String(veri.expires_in || ""),
      refresh_expires_in: String(veri.refresh_expires_in || ""),
      open_id: veri.open_id || "",
      scope: veri.scope || "",
    },
  }));
};
