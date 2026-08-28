/* Elle degistirilecek tek ayar dosyasi.

   Discord sunucusunun adresi belli olunca asagiya yazmak yeterli: hem ustteki
   akan seritte hem de altbilgide kendiliginden tiklanabilir baglantiya
   donusuyor. Bos kaldigi surece ikisi de duz yazi olarak duruyor.        */

const DISCORD_URL = "https://discord.gg/8buKAhTPEs";

/* Kaynak kodun adresi. Bos oldugu surece altbilgideki madde tiklanamaz duz
   yazi olarak duruyor, doldurulunca baglantiya donusuyor. */
const REPO_URL = "https://github.com/doruktemucinyt-spec/shorts-clipper";

/* Kurulum dosyasinin adresi. GitHub'in "latest" adresi her zaman en son
   surumdeki dosyayi veriyor, o yuzden yeni surum cikinca burayi degistirmeye
   gerek yok -- yeni Release'e ayni isimde dosyayi yuklemek yetiyor.
   Kurulum dosyasi 200 MB civari; Vercel'de degil GitHub'da duruyor. */
const SETUP_URL =
  "https://github.com/doruktemucinyt-spec/shorts-clipper/releases/latest/download/ClipCloverKurulum.exe";

/* Yayinlanan surum. Tek kaynak server.py'deki APP_VERSION; build_site.py
   siteyi uretirken bu satiri onunla dolduruyor. Yardimcinin kendi adresinden
   acilan sayfada bos kaliyor -- orada surum zaten /api/hello'dan geliyor. */
const APP_VERSION = "";
