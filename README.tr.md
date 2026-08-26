# Shorts Clipper — Türkçe notlar

*(English: [README.md](README.md))*

YouTube linki ver → 9:16 dikey partlar çıkar. Üst/alt blur, ortada yatay video,
konuşulan kelimeyi vurgulayan pop-up caption, üstte başlık ve "Part N".

## Çalıştırma

`run.bat` dosyasına çift tıkla. Tarayıcı `http://localhost:8000` adresinde açılır.
Kapatmak için siyah komut penceresini kapat.

## Kullanım

1. YouTube linkini yapıştır
2. Part süresini ve video boyutunu seç
3. **Önizle** — kadrajı render'a girmeden gör (aşağıda anlatılıyor)
4. **Başla**

Çıktılar `output/<video-adı>/part-01.mp4` şeklinde kaydedilir.

## Önizleme

**Önizle** butonu videonun tamamını indirmeden tek bir kare çekip çıktının
birebir aynısını gösteriyor: blur şeritler, başlık, "Part 1" ve caption açıksa
örnek bir caption satırı. Böylece "render bitti, kadraj olmamış" durumu ortadan
kalkıyor.

- İlk kare birkaç saniyede geliyor (yt-dlp akış adresini veriyor, ffmpeg o andan
  tek kare çekiyor).
- Sonrasında **video boyutu**, **vurgu rengi** veya caption anahtarını
  oynattığında aynı kare yeniden kadrajlanıyor — yeni indirme yok, anında.
- **Kare konumu** kaydıracı videonun neresinden bakacağını seçiyor; bunu
  değiştirmek yeni bir kare indirdiği için birkaç saniye sürüyor.

Kadraj hesabı ve filtre zinciri render ile aynı koddan (`pipeline/render.py`)
geliyor, yani önizlemede gördüğün şey çıktının kendisi. Önizleme kareleri
`work/preview/` altında birikiyor, **Temizle** onları da siliyor.

Kaydırıcının altındaki piksel/kırpma yazısı önizleme alındıktan sonra kaynağın
gerçek en-boy oranıyla hesaplanıyor (öncesinde 16:9 varsayıyor).

## Hız

İki yerde iş ciddi şekilde kısaldı (bu makinede ölçüldü):

- **Render** — blur artık 1080x1920'de değil, dörtte bir ölçekte alınıp geri
  büyütülüyor. Gözle fark yok, kare başına en pahalı adım oydu.
  60 sn'lik video: **17,6 sn → 8,4 sn**. Kalan süre neredeyse tamamen NVENC'in
  kendi hızı, yani bu adım artık dibe yakın.
- **Transkript** — faster-whisper'ın toplu (batched) çıkarımı kullanılıyor:
  ses parçaları tek tek değil demet halinde GPU'ya giriyor.
  60 sn'lik ses (o zamanki large-v3 modeliyle ölçüldü): **10,7 sn → 4,0 sn**.
  Kelimeler aynı.
  Toplu çıkarım tutmazsa otomatik olarak eski yönteme, o da olmazsa CPU'ya
  düşüyor.

Ayrıca part sınırları artık Whisper'ın segmentlerine değil, kelime
noktalamasından üretilen cümlelere hizalanıyor — kesim noktaları daha isabetli.

## Ayarlar

- **Part süresi** — hedef süre.
  Partlar her zaman tam bu sürede kesilir; son part çok kısa kalırsa bir
  öncekiyle birleşir. (Cümle sonuna hizalayan mod kaldırıldı: transkript
  gerektirdiği için yavaştı ve kurulumu şişiriyordu.)
- **Video boyutu** — videonun kadraj içindeki büyüklüğü. %100'de video hiç
  kesilmez ama blur şeritler en kalın halinde olur. Büyüttükçe video büyür,
  şeritler kısalır, sağdan ve soldan biraz kırpılır. Kaydırıcının altındaki yazı
  seçtiğin değerde tam olarak kaç piksel ve yüzde kaç kırpma olacağını gösterir.
  Varsayılan %140.
- **Caption yak** — kapalı geldi. Açarsan konuşulan kelimeyi vurgulayan pop-up
  caption videoya gömülür; bunun için transkript şart, yani iş yavaşlar.
  - *Vurgu rengi* — o an konuşulan kelimenin rengi.
  - *Altyazı modeli* — tek seçenek: `small` (~0,5 GB, bir kez iner). `medium`
    ve `large-v3` listede "yakında" olarak duruyor ama seçilemiyor.

    Sebep: büyük modeller aracı ağırlaştırıyordu (`large-v3` tek başına 3 GB).
    Sunucu tanımadığı bir model değeri gelirse sessizce `small`'a düşüyor —
    yani eski bir tarayıcı ayarı ya da elle gönderilen bir istek büyük
    indirmeyi başlatamıyor. Açmak için `server.py` içindeki `MODELS`
    kümesine eklemek yeterli.

Video başlığı ve "Part N" yazısı caption ayarından bağımsız, her zaman basılır.

Ayarlar ve geçmiş iki yerde tutulur, ikisi de kendi bilgisayarında: tarayıcının
deposunda ve yardımcının `work/user.json` dosyasında. İkincisinin sebebi şu:
tarayıcı deposu adrese bağlı, yani siteden girdiğinle `localhost:8000`'den
girdiğin ayrı ayrı hatırlanırdı. Yardımcıdaki kopya ikisini birleştiriyor;
hangisinin geçerli olduğunu son değişiklik zamanı belirliyor.

Not: çerez kullanılmıyor. Çerez zaten bu işi tarayıcı deposundan daha iyi
yapmazdı ve her ikisi de adrese bağlı olduğu için asıl sorunu çözmezdi. **Yedek indir** ile JSON olarak
dışarı alıp başka bilgisayarda **Yedekten yükle** ile geri koyabilirsin.

## Site + yardımcı mimarisi

Arayüz internetteki bir siteden de açılabiliyor. O zaman iş yine kullanıcının
kendi bilgisayarında dönüyor: site sadece arayüz, indirme/transkript/render
kullanıcının makinesindeki bu yardımcıda çalışıyor.

Sebep: tarayıcı YouTube'dan video indiremiyor (YouTube başka sitelerin
sayfalarının video adreslerini çekmesine izin vermiyor). Bu yüzden indiren
taraf her zaman yerel bir program olmak zorunda.

Site **https://shorts-clipper-seven.vercel.app** adresinde yayında (Vercel,
statik). Yeniden yayınlamak için `deploy.bat` — siteyi baştan üretip aynı
adrese gönderiyor.

**İki ayrı izin var, karıştırmamak lazım:**

1. *Tarayıcının izni* — Chrome, bir internet sitesinin yerel bilgisayara
   bağlanmasına kendi penceresiyle karar veriyor. Bu pencere ancak kullanıcı
   bir şeye tıkladığında açılıyor, o yüzden sayfa açılır açılmaz bağlanmayı
   denemiyoruz: kullanıcı **Bilgisayarıma bağlan** diyor, istek o tıklamanın
   içinde gidiyor. İsteğe `targetAddressSpace: "loopback"` eklenmezse Chrome
   pencereyi hiç göstermeden reddediyor.
2. *Yardımcının izni* — aşağıdaki eşleşme akışı.

Aynı sebeple ilerleme takibi sitede canlı akış (SSE) yerine saniyede bir
yoklamayla yapılıyor: EventSource'a o ipucu verilemiyor.

**İzin akışı** (`pairing.py`, `web/pair.html`, `web/api.js`):

1. Site `GET /api/hello` ile yardımcının açık olup olmadığına bakıyor.
2. İzinli değilse `POST /api/pair` ile izin istiyor; yardımcı bir istek
   numarası ve `http://127.0.0.1:8000/permission?id=...` adresi dönüyor.
3. Onay ekranı **kullanıcının kendi bilgisayarında** açılıyor — site o ekranı
   çizemediği için sahtesini yapıp kendine izin veremiyor.
4. Kullanıcı izin verirse siteye bir anahtar veriliyor. Sonraki her istek o
   anahtarı taşımak zorunda; anahtar siteye (origin'e) bağlı, başka bir site
   aynı anahtarla iş yaptıramıyor.
5. İzin `http://localhost:8000/permission` sayfasından geri alınabiliyor.

Ayrıca tarayıcı, bir siteden yerel ağa istek atmadan önce izin soruyor
(preflight); sunucu buna `Access-Control-Allow-Private-Network` ile cevap
veriyor. `server.py` içindeki `cross_site_guard` bu ikisini birlikte yapıyor.

`python build_site.py` internete konacak statik siteyi `site/` klasörüne
üretiyor: sadece HTML/CSS/JS, sunucu ve ekran kartı gerektirmiyor.

## Güvenlik

Yardımcı, kullanıcının kendi bilgisayarında çalışan bir sunucu ve internetteki
bir sayfa ona istek atıyor. Bu, dikkat edilmezse tehlikeli bir kurgu: o zaman
**herhangi bir web sayfası** da aynı sunucuya emir verebilirdi. Kapatılan
saldırılar ve kontrolleri (`server.py` içindeki `cross_site_guard`,
`_page_is_local`, `check_url` ve `pairing.py`):

**DNS yeniden bağlama (rebinding).** Kötü bir site kendi alan adını
`127.0.0.1`'e çözdürüp tarayıcıya "bu aynı site" dedirtebiliyor; o anda bütün
CORS ve anahtar kontrolleri devre dışı kalır. Sunucu artık `Host` başlığına
bakıyor: istek `localhost:8000`, `127.0.0.1:8000` veya `[::1]:8000` adına
gelmediyse kapıda duruyor.

**Origin göndermeyen istekler.** Tarayıcı basit GET isteklerinde `Origin`
göndermiyor. Yani kötü bir sayfa `<img src="http://127.0.0.1:8000/api/sites">`
yazsa istek "yerel" sanılıyordu ve izinli site listesi sızıyordu. Artık
`Sec-Fetch-Site` başlığına bakılıyor: `cross-site` ise yabancıdır.

**Dosya ve iç ağ adresleri.** İzinli bir site iş adresi olarak
`file:///C:/...` verip diskteki bir videoyu render ettirip `/media` üzerinden
geri okuyabilirdi; ya da `http://192.168.1.1/...` ile ev ağındaki cihazlara
istek attırabilirdi. `check_url` yalnızca http/https kabul ediyor ve adresin
çözüldüğü IP yerel/özel ağdaysa reddediyor.

**Onay ekranının çerçevelenmesi (clickjacking).** İzin ekranı görünmez bir
çerçeveye alınıp kullanıcıya yanlışlıkla tıklatılabilirdi. Tüm yanıtlarda
`X-Frame-Options: DENY` ve `frame-ancestors 'none'` var.

**Anahtar hırsızlığı.** Anahtar siteye (origin'e) bağlı: bir sitenin anahtarı
başka bir siteden gönderilirse reddediliyor. Karşılaştırma sabit zamanlı
(`secrets.compare_digest`).

**Video ve önizleme dosyaları.** Bunlar sayfaya `<video>` ve `<img>` ile
yükleniyor, tarayıcı bu isteklere `Origin` koymuyor. Orada tahmin edilemez
anahtarın kendisi yeterli sayılıyor; anahtarsız istek 403.

**Klasör açma ucu.** `/api/reveal` yalnızca çıktı klasörünün içini açabiliyor,
başka bir yolu değil.

**Altyazı dosyasına satır enjeksiyonu.** Video başlığı dışarıdan geliyor ve ASS
dosyasına yazılıyor; içinde satır sonu olsa sahte bir altyazı satırı
eklenebilirdi. `captions.esc` satır sonlarını da temizliyor.

**Kaynak tüketimi.** Aynı anda en fazla iki iş çalışabiliyor, bekleyen izin
istekleri 20 ile sınırlı, ölçüm günlüğü 1 MB'ı geçince yazmayı bırakıyor.

Kapsam dışı olan bir şey var, bilerek: bilgisayarda **zaten çalışan** bir
program bu sunucuya istediği başlıkla istek atabilir. Ama o programın zaten
dosyalara doğrudan erişimi var, yani orada korunacak bir sınır kalmıyor.

## Bilgi sayfaları

Alt taraftaki bağlantılardan üç sayfa açılıyor: **SSS** (`/faq`), **Çerezler**
(`/cookies`) ve **Gizlilik** (`/privacy`). Olmayan bir adres yazılırsa aynı
kabuk 404 sayfası olarak açılıyor (API adresleri JSON dönmeye devam ediyor).

Metinler `web/pages.js` içinde, dört dilde; sayfa kabuğu `web/page.html`,
gösterim `web/page.js`. Dil menüsü ve çeviri artık ortak `web/lang.js`
dosyasında — ana sayfa da bilgi sayfaları da onu kullanıyor, yani menü tek
yerden yönetiliyor.

## Dil

Sağ üstteki küre butonundan Türkçe, İngilizce, Almanca ve Fransızca arasında
geçiş yapılır. Seçim tarayıcıda saklanır. İlerleme mesajları dahil her şey çevrilir:
sunucu düz metin değil anahtar gönderiyor, çeviri arayüzde yapılıyor.

Yeni dil eklemek için `web/i18n.js` içindeki nesneye bir dil anahtarı, sonra
`web/index.html` içindeki menüye bir buton eklemek yeterli.

## Geçici dosyalar

İndirilen kaynak videolar `work/` altında birikir. Alt taraftaki **Temizle**
butonu bunları siler; `output/` klasörüne dokunmaz.

## Başka bir bilgisayara kurmak

`kurulum.bat`'a çift tıkla (ya da `python kurulum.py`). İki seçenek sunuyor:

Kurulum tek bir şey soruyor: **caption özelliği de kurulsun mu?**

- **Hayır** (varsayılan) — ~200 MB. YouTube linkinden 9:16 partlar çıkarır.
- **Evet** — üstüne ~2 GB kütüphane, artı ilk kullanımda seçilen altyazı
  modeli (varsayılan `small` ~0,5 GB). Sonradan fikir değişirse kurulum tekrar
  çalıştırılıp eklenebiliyor.

Kurulum sanal ortamı (`.venv`) proje klasörüne kuruyor, sistemde başka bir yeri
değiştirmiyor; ffmpeg'i winget ile kurmayı ise soruyor, sessizce kurmuyor.

Başlatmak için `baslat.bat`. Hafif kurulumda arayüz cümleye hizalı bölme ve
caption seçeneklerini kendiliğinden kapatıyor, sunucu da `/api/hello` içinde
`transcript: false` diyerek durumu bildiriyor.

**Kurulum neden `.bat` değil de Python:** ilk sürüm toplu iş dosyasıydı ve
içinden `powershell -ExecutionPolicy Bypass` çağırıp masaüstüne kısayol
yazıyordu. Antivirüs bunu zararlı yazılım kalıbı sayıp karantinaya aldı —
haklı olarak, çünkü kalıp birebir aynı. Aynı iş Python'da yapılınca uyarı çıkmıyor.
Kuruluma PowerShell çağrısı veya masaüstüne dosya yazma eklenirse sorun geri
gelir.

## Bağımlılıklar

- Python 3.12 + `pip install -r requirements.txt`
- ffmpeg — `winget install --id Gyan.FFmpeg -e --source winget`

NVIDIA GPU altyazı çıkarma ve NVENC encode için kullanılır. GPU bir sebeple
çalışmazsa otomatik CPU'ya düşer, iş durmaz — sadece yavaşlar.

## Windows'a özel üç not

Kurulumda çıkabilecek iki Windows sorunu (`pipeline/__init__.py` içinde):

1. **TLS** — makinede TLS'i araya giren bir güvenlik yazılımı var. Kök sertifikası
   Windows deposunda kayıtlı ama Python'un `certifi` paketinde yok, bu yüzden
   yt-dlp ve model indirmeleri SSL hatası veriyordu. `truststore` ile Python
   Windows deposunu kullanıyor.
2. **CUDA** — pip'ten gelen `cublas`/`cudnn` DLL'leri `site-packages/nvidia/*/bin`
   altına kuruluyor ama Windows'un DLL arama yolunda değil. `os.add_dll_directory`
   ile kaydediliyor.

Bu ikisi silinirse GPU ve indirme çalışmaz.

3. **localhost / IPv6** — bu makinede `localhost` önce IPv6 adresine (`::1`)
   çözülüyor. Sunucu yalnızca `127.0.0.1` dinlediğinde Chrome sessizce IPv4'e
   düşüp açabiliyor, başka tarayıcılar "bağlantı kurulamadı" diyordu. `serve.py`
   bu yüzden iki yerel soket açıyor: biri IPv4, biri IPv6. İkisi de sadece bu
   bilgisayara açık, dışarıya bir şey açılmıyor. `run.bat` artık `serve.py`
   çağırıyor; doğrudan `uvicorn server:app` ile başlatılırsa sorun geri gelir.

## Lisans

MIT. Kısaca: kullan, değiştir, dağıt; telif satırını koru; garanti yok.
`LICENSE` dosyasındaki isim satırını istediğin gibi değiştirebilirsin.

## Yasal

YouTube'dan video indirmek, kendi içeriğin veya izin aldığın içerik dışında
YouTube kullanım şartlarına aykırıdır. Sorumluluk kullanıcıya aittir.
