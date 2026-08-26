; ClipClover kurulum programi.
;
; Onemli tercih: kullanicinin kendi klasorune kuruyor (Program Files degil).
; Boylece Windows yonetici izni penceresi (UAC) hic cikmiyor -- kullanici sadece
; Ileri, Ileri diyor. Program Files'a kurmak yonetici izni gerektirirdi ve
; oradaki klasore yazamadigi icin ayarlarin yeri de karisirdi.

#define Ad "ClipClover"
#define Surum "1.1"
#define Yayinci "ClipClover"
#define Site "https://clipclover.online"
#define AnaExe "ClipClover.exe"

[Setup]
AppId={{7C4B2E9A-3F1D-4A6E-9B08-C15D2E7F4A31}
AppName={#Ad}
AppVersion={#Surum}
AppPublisher={#Yayinci}
AppPublisherURL={#Site}
AppSupportURL={#Site}
DefaultDirName={autopf}\{#Ad}
DefaultGroupName={#Ad}
DisableProgramGroupPage=yes
DisableDirPage=yes
; Yonetici istemeden, kullanicinin kendi alanina kur
PrivilegesRequired=lowest
; PrivilegesRequiredOverridesAllowed=dialog BILEREK YOK. Acikken Inno, daha
; kurulum baslamadan "herkes icin mi, sadece benim icin mi" diye ayri bir
; pencere aciyordu -- sorulacak bir sey degil, cevabi hep ayni: kullanicinin
; kendi klasoru. Sessiz kurulumda gorunmedigi icin uzun sure fark edilmemisti.
OutputDir=dagitim
OutputBaseFilename=ClipCloverKurulum
SetupIconFile=brand\clipclover.ico
UninstallDisplayIcon={app}\{#AnaExe}
UninstallDisplayName={#Ad}
Compression=lzma2/max
SolidCompression=yes

; --- Gorunum ---------------------------------------------------------------
; Soldaki bant sadece hos geldin ve bitti sayfalarinda gorunuyor; kucuk kare
; digerlerinin ust kosesinde duruyor. Ikisi de brand_installer.py uretiyor,
; sitenin dilinde: koyu zemin, ustte yesil isik, ortada yonca. Inno ekranin
; DPI'sina gore listeden en uygun olcuyu kendi seciyor.
WizardStyle=modern
WizardImageFile=brand\setup\bant-164x314.bmp,brand\setup\bant-192x386.bmp,brand\setup\bant-256x515.bmp,brand\setup\bant-384x772.bmp
WizardSmallImageFile=brand\setup\kare-55.bmp,brand\setup\kare-110.bmp,brand\setup\kare-192.bmp
WizardImageStretch=yes

; --- Sayfa akisi -----------------------------------------------------------
; Hedef klasor, baslat menusu ve "hazir misin" sayfalari kapali; sorulacak bir
; sey yok. Geriye hos geldin -> kuruluyor -> bitti kaliyor. Hos geldin ve bitti
; sayfalari bilerek duruyor: bant orada gorunuyor ve kullanici ne kurdugunu
; okuyor. Dil penceresi de kapali, Windows'un dilinden seciliyor.
; Inno 6'da DisableWelcomePage VARSAYILAN OLARAK yes -- yani istemeden kapali
; geliyordu ve ilk ekran "kuruluma hazir" oluyordu. Aciyoruz: soldaki bant
; sadece bu sayfada ve bitti sayfasinda goruluyor, kapaliyken tasarim hic
; ortaya cikmiyordu.
DisableWelcomePage=no
DisableReadyPage=yes
ShowLanguageDialog=no
; Program 64-bit Python ile derlendi
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
; Inno'nun kendi "Kurulum Sihirbazina Hos Geldiniz" metni yerine ne kurdugunu
; ve neyin gerekmedigini soyleyen bir karsilama.
tr.WelcomeLabel1=ClipClover kuruluyor
tr.WelcomeLabel2=YouTube linkinden 9:16 dikey partlar.%n%nPython, ffmpeg ve altyazı motoru paketin içinde — ayrıca bir şey kurman gerekmiyor. Yönetici izni de istemiyor, kendi kullanıcı klasörüne kuruluyor.
en.WelcomeLabel1=Installing ClipClover
en.WelcomeLabel2=Turns a YouTube link into 9:16 vertical parts.%n%nPython, ffmpeg and the caption engine are inside the package — nothing else to install. It needs no administrator rights either; it installs into your own user folder.

[Files]
Source: "dist\ClipClover\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Ad}"; Filename: "{app}\{#AnaExe}"
Name: "{group}\{cm:UninstallProgram,{#Ad}}"; Filename: "{uninstallexe}"
; Masaustu simgesi soru sorulmadan kuruluyor -- sirf bunun icin bir "gorevler"
; sayfasi gostermek, kazandirdigi secimden daha pahaliydi. Programa ulasmanin
; baska gorunur bir yolu da yok: pencere acmiyor.
Name: "{autodesktop}\{#Ad}"; Filename: "{app}\{#AnaExe}"

[Run]
Filename: "{app}\{#AnaExe}"; Description: "{cm:LaunchProgram,{#Ad}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Programin kendi gecici dosyalari. Kullanicinin videolarina (Videolar\ClipClover)
; dokunmuyoruz -- onlar onun emegi, kaldirma islemi silmemeli.
Type: filesandordirs; Name: "{localappdata}\ClipClover"
