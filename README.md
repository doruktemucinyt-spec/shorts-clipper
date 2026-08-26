# Shorts Clipper

YouTube linki ver → 9:16 dikey partlar çıkar. Üst/alt blur, ortada yatay video,
konuşulan kelimeyi vurgulayan pop-up caption, üstte başlık ve "Part N".

## Çalıştırma

`run.bat` dosyasına çift tıkla. Tarayıcı `http://localhost:8000` adresinde açılır.
Kapatmak için siyah komut penceresini kapat.

## Kullanım

1. YouTube linkini yapıştır
2. Part süresini, bölme yöntemini ve video boyutunu seç
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
  60 sn'lik ses, large-v3: **10,7 sn → 4,0 sn**. Kelimeler aynı.
  Toplu çıkarım tutmazsa otomatik olarak eski yönteme, o da olmazsa CPU'ya
  düşüyor.

Ayrıca part sınırları artık Whisper'ın segmentlerine değil, kelime
noktalamasından üretilen cümlelere hizalanıyor — kesim noktaları daha isabetli.

## Ayarlar

- **Part süresi** — hedef süre.
- **Bölme yöntemi**
  - *Cümle sonuna hizala* — Whisper transkripti çıkarır, hiçbir part cümlenin
    ortasında kesilmez. Gerçek süreler ±40 sn oynar. **Yavaş** (transkript
    videonun uzunluğuna göre dakikalar sürer).
  - *Tam sürede kes* — transkript hiç çalışmaz, tam sürede keser. **Çok hızlı**,
    ama cümle ortasında kesebilir.
- **Video boyutu** — videonun kadraj içindeki büyüklüğü. %100'de video hiç
  kesilmez ama blur şeritler en kalın halinde olur. Büyüttükçe video büyür,
  şeritler kısalır, sağdan ve soldan biraz kırpılır. Kaydırıcının altındaki yazı
  seçtiğin değerde tam olarak kaç piksel ve yüzde kaç kırpma olacağını gösterir.
  Varsayılan %140.
- **Caption yak** — kapalı geldi. Açarsan konuşulan kelimeyi vurgulayan pop-up
  caption videoya gömülür; bunun için transkript şart, yani iş yavaşlar.
  - *Vurgu rengi* — o an konuşulan kelimenin rengi.
  - *Altyazı modeli* — `large-v3` en doğrusu, `medium` daha hızlı.

Video başlığı ve "Part N" yazısı caption ayarından bağımsız, her zaman basılır.

Ayarlar ve geçmiş tarayıcıda (localStorage) tutulur. **Yedek indir** ile JSON olarak
dışarı alıp başka bilgisayarda **Yedekten yükle** ile geri koyabilirsin.

## Dil

Sağ üstteki küre butonundan Türkçe, İngilizce, Almanca ve Fransızca arasında
geçiş yapılır. Seçim tarayıcıda saklanır. İlerleme mesajları dahil her şey çevrilir:
sunucu düz metin değil anahtar gönderiyor, çeviri arayüzde yapılıyor.

Yeni dil eklemek için `web/i18n.js` içindeki nesneye bir dil anahtarı, sonra
`web/index.html` içindeki menüye bir buton eklemek yeterli.

## Geçici dosyalar

İndirilen kaynak videolar `work/` altında birikir. Alt taraftaki **Temizle**
butonu bunları siler; `output/` klasörüne dokunmaz.

## Bağımlılıklar

- Python 3.12 + `pip install -r requirements.txt`
- ffmpeg — `winget install --id Gyan.FFmpeg -e --source winget`

GPU (RTX 3080 Ti) altyazı çıkarma ve NVENC encode için kullanılır. GPU bir sebeple
çalışmazsa otomatik CPU'ya düşer, iş durmaz — sadece yavaşlar.

## Bu makineye özel iki not

Kurulumda çıkan ve çözülen iki Windows sorunu (`pipeline/__init__.py` içinde):

1. **TLS** — makinede TLS'i araya giren bir güvenlik yazılımı var. Kök sertifikası
   Windows deposunda kayıtlı ama Python'un `certifi` paketinde yok, bu yüzden
   yt-dlp ve model indirmeleri SSL hatası veriyordu. `truststore` ile Python
   Windows deposunu kullanıyor.
2. **CUDA** — pip'ten gelen `cublas`/`cudnn` DLL'leri `site-packages/nvidia/*/bin`
   altına kuruluyor ama Windows'un DLL arama yolunda değil. `os.add_dll_directory`
   ile kaydediliyor.

Bu ikisi silinirse GPU ve indirme çalışmaz.

## Yasal

YouTube'dan video indirmek, kendi içeriğin veya izin aldığın içerik dışında
YouTube kullanım şartlarına aykırıdır. Sorumluluk kullanıcıya aittir.
