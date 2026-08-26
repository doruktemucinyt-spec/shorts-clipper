; ClipClover kurulum programi.
;
; Onemli tercih: kullanicinin kendi klasorune kuruyor (Program Files degil).
; Boylece Windows yonetici izni penceresi (UAC) hic cikmiyor -- kullanici sadece
; Ileri, Ileri diyor. Program Files'a kurmak yonetici izni gerektirirdi ve
; oradaki klasore yazamadigi icin ayarlarin yeri de karisirdi.

#define Ad "ClipClover"
#define Surum "1.0"
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
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dagitim
OutputBaseFilename=ClipCloverKurulum
SetupIconFile=brand\clipclover.ico
UninstallDisplayIcon={app}\{#AnaExe}
UninstallDisplayName={#Ad}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Program 64-bit Python ile derlendi
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "masaustu"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\ClipClover\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Ad}"; Filename: "{app}\{#AnaExe}"
Name: "{group}\{cm:UninstallProgram,{#Ad}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Ad}"; Filename: "{app}\{#AnaExe}"; Tasks: masaustu

[Run]
Filename: "{app}\{#AnaExe}"; Description: "{cm:LaunchProgram,{#Ad}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Programin kendi gecici dosyalari. Kullanicinin videolarina (Videolar\ClipClover)
; dokunmuyoruz -- onlar onun emegi, kaldirma islemi silmemeli.
Type: filesandordirs; Name: "{localappdata}\ClipClover"
