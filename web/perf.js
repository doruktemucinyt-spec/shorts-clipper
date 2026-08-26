/* Gecici olcum modu. Sayfayi ?perf=1 ile acinca kare surelerini olcup
   sunucuya yolluyor (work/perf.log). Adreste perf yoksa hicbir sey yapmiyor,
   normal kullanimda maliyeti sifir.

   Iki kovaya ayiriyor: kaydirirken gecen kareler ve bos duruken gecenler.
   "Bos duruken de kare sureleri uzunsa" sorun kaydirma degil, surekli donen
   arka plan yuku demektir -- ikisinin ilaci farkli.                        */
if (new URLSearchParams(location.search).has("perf")) {
  const bucket = () => ({ n: 0, sum: 0, max: 0, janky: 0, times: [] });
  let scrolling = bucket(), idle = bucket();
  let lastScroll = 0, last = performance.now(), sent = performance.now();

  addEventListener("scroll", () => { lastScroll = performance.now(); }, { passive: true });

  const stats = (b) => {
    if (!b.n) return null;
    const s = b.times.sort((x, y) => x - y);
    return {
      kare: b.n,
      ort: +(b.sum / b.n).toFixed(1),
      p95: +s[Math.floor(s.length * 0.95)].toFixed(1),
      max: +b.max.toFixed(1),
      takilan: b.janky,          // 20 ms'den uzun kareler
      fps: +(1000 / (b.sum / b.n)).toFixed(1),
    };
  };

  const tick = (now) => {
    const d = now - last; last = now;
    if (d < 500) {                       // sekme arka plana gectiyse sayma
      const b = now - lastScroll < 180 ? scrolling : idle;
      b.n++; b.sum += d; b.times.push(d);
      if (d > b.max) b.max = d;
      if (d > 20) b.janky++;
    }
    if (now - sent > 4000) {
      const body = { kaydirirken: stats(scrolling), bos: stats(idle),
                     etiket: new URLSearchParams(location.search).get("perf") };
      if (body.kaydirirken || body.bos) {
        fetch("/api/perf", { method: "POST", headers: { "Content-Type": "application/json" },
                             body: JSON.stringify(body) }).catch(() => {});
      }
      scrolling = bucket(); idle = bucket(); sent = now;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  console.log("[perf] olcum acik");
}
