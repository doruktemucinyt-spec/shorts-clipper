/* Token yenileme. Girisin kendisi callback.js'te; bu uc sadece suresi dolan
 * anahtari tazeliyor.
 *
 * Neden burada: TikTok'un token ucu client_secret istiyor ve secret
 * kullanicinin bilgisayarina inmiyor. Yardimci program bu uca kendi
 * refresh_token'iyla geliyor, karsiliginda yeni bir access_token aliyor.
 *
 * Ek bir yetki kontrolu yok, cunku gereksiz: bu uc calisan tek sey elinde
 * gecerli bir refresh_token olan taraf. O anahtar zaten sirrin kendisi --
 * bilmeyen birinin buradan alabilecegi bir sey yok.
 */

const TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/";

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  // Govde JSON gelmezse Vercel string birakabiliyor; ikisini de kariliyoruz.
  let govde = req.body;
  if (typeof govde === "string") {
    try { govde = JSON.parse(govde); } catch { govde = {}; }
  }
  const refreshToken = govde && govde.refresh_token;
  if (!refreshToken) {
    res.status(400).json({ error: "missing_refresh_token" });
    return;
  }

  const clientKey = process.env.TIKTOK_CLIENT_KEY;
  const clientSecret = process.env.TIKTOK_CLIENT_SECRET;
  if (!clientKey || !clientSecret) {
    res.status(500).json({ error: "server_not_configured" });
    return;
  }

  try {
    const yanit = await fetch(TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_key: clientKey,
        client_secret: clientSecret,
        grant_type: "refresh_token",
        refresh_token: String(refreshToken),
      }),
    });
    const veri = await yanit.json();
    res.status(veri && veri.access_token ? 200 : 400).json(veri);
  } catch (e) {
    res.status(502).json({ error: "tiktok_unreachable" });
  }
};
