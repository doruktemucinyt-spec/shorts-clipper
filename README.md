# ClipClover

Turn a YouTube link into 9:16 vertical parts: blurred bands top and bottom, the
original video centred, the title and "Part N" on top, and optional pop-up
captions that highlight the spoken word.

**The work happens on your own machine.** The website is only the interface — a
small helper program on your computer does the downloading, the transcription
and the rendering. Your video, your audio and your transcript never leave the
machine.

*Türkçe ayrıntılı notlar: [README.tr.md](README.tr.md)*

- Site: <https://clipclover.online> (invite-only beta)
- Source: <https://github.com/doruktemucinyt-spec/shorts-clipper>
- Help / invite keys: [Discord](https://discord.gg/8buKAhTPEs)

## Why a helper program

A browser cannot fetch YouTube video streams: YouTube does not allow other
sites to read them. So the part that downloads has to be a local program. That
turns out to be a feature — the heavy work (Whisper, ffmpeg, your GPU) stays on
your own hardware, and hosting the site costs nothing because it is static.

```
browser (site or localhost)
        │  invite key → browser's local-network permission → pairing key
        ▼
local helper  ──►  yt-dlp        download
   FastAPI    ──►  faster-whisper transcript (only when captions are on)
              ──►  ffmpeg         9:16 render, NVENC when available
                                  ↓
                            output/<video>/part-01.mp4
```

## Install (Windows)

Download **`ClipCloverKurulum.exe`** from the
[latest release](https://github.com/doruktemucinyt-spec/shorts-clipper/releases/latest),
double-click it, press Install. That is the whole procedure — Python, ffmpeg and
the caption engine are all inside. It installs into your own user folder, so
Windows never asks for administrator rights.

Windows will show a blue **"Windows protected your PC"** screen: the installer
is not code signed, so SmartScreen has no reputation for it. Choose *More info*
→ *Run anyway*. This is a reputation warning, not a malware detection.

Where things end up:

| | |
|---|---|
| finished videos | `Videos\ClipClover` — untouched when you uninstall |
| temporary files | `AppData\Local\ClipClover` — removed when you uninstall |
| the program | `AppData\Local\Programs\ClipClover` |

The program runs **without a window**. There used to be a black console that
you closed to stop it; now there is a clover icon next to the clock -- double
click opens the site, right click gives you *Quit*. On start it opens
**clipclover.online** in the browser, not localhost: the site is the face we
show people. (The local UI is still there -- `localhost:8000` serves the same
page -- it just is not opened for you.)

Dropping the console forced two things, both in `app_main.py`:

- Everything printed goes to `AppData\Local\ClipClover\work\clipclover.log`.
  In a windowed build `sys.stdout` is **None**, and the process died silently
  the moment uvicorn wrote its first log line.
- `subprocess.Popen` is patched to pass `CREATE_NO_WINDOW` to every child. On
  Windows a console program started from a windowless process opens its own
  window, so rendering flashed black boxes across the screen. Adding the flag
  at each call site is not enough: yt-dlp runs ffmpeg from inside itself.

An NVIDIA GPU is optional. Rendering still uses NVENC when the driver supports
it, but transcription runs on the CPU: CUDA acceleration in ctranslate2 needs
cuBLAS and cuDNN, which are over 2 GB and deliberately not packaged.
`transcribe.py` falls back on its own, so nothing breaks either way.

## Install from source (any platform)

For development, or on machines where the packaged build does not apply:

1. Download or clone this repository.
2. Double-click **`install.bat`**. It asks one question: whether to install the
   caption feature (~2 GB extra plus a ~0.5 GB subtitle model on first use).
   Without it you still get the 9:16 parts, just no burned-in captions.
3. Double-click **`start.bat`**.
4. Open the site and press **Connect my computer**, or just go to
   <http://localhost:8000>.

Requirements: Python 3.10+, ffmpeg (the installer offers to install it via
winget).

## Building the installer

`python build_setup.py` (or double-click `buildsetup.bat`) does all three steps:
downloads ffmpeg into `vendor/`, runs PyInstaller against `clipclover.spec`, and
compiles `installer.iss` with Inno Setup into `dagitim/ClipCloverKurulum.exe`.

It builds from `.buildvenv`, a separate environment, on purpose: the main Python
has the CUDA packages installed and PyInstaller would sweep them into the bundle,
taking it past 2 GB. Set that environment up once with

```
python -m venv .buildvenv
.buildvenv/Scripts/python.exe -m pip install -r requirements.txt pyinstaller
```

Inno Setup itself: `winget install --id JRSoftware.InnoSetup -e --source winget`.

Two packaging choices worth keeping:

- **A folder plus an installer, not a single-file exe.** A one-file PyInstaller
  build unpacks itself into a temp directory at every launch, and Defender
  frequently reads that as a dropper. UPX compression is off for the same reason.
- **ffmpeg from a *shared* build** (`vendor_ffmpeg.py`). In the usual static
  build `ffmpeg.exe` and `ffprobe.exe` each carry every codec: 424 MB for the
  pair. Sharing them through DLLs gives the same capabilities in 161 MB.

## What it does

- **Preview before rendering.** One frame is pulled from the video and pushed
  through the exact same framing maths and filter chain as the render, so the
  preview is the output.
- **Adjustable framing.** A zoom slider trades blurred band height against how
  much is cropped from the sides; the preview updates as you drag it.
- **Captions.** Word-level timing from faster-whisper, burned in with a pop
  animation on the spoken word.
- **Four languages** (Turkish, English, German, French), including progress
  messages: the server sends keys, the interface translates them.
- **One memory.** Settings and history are mirrored through the helper, so the
  site and `localhost` remember the same thing.
- No cookies, no analytics, no accounts.

## Security

A public web page talking to a local server is a dangerous shape if left open —
any website could drive the helper. What the helper does about it:

| Attack | Defence |
| --- | --- |
| DNS rebinding | `Host` header must be one of the loopback addresses |
| Origin-less `GET` from a foreign page | `Sec-Fetch-Site` is checked too |
| `file://` or intranet job URLs | only http/https, and private IPs are refused |
| Clickjacking the approval screen | `X-Frame-Options: DENY`, `frame-ancestors 'none'` |
| Stolen pairing key | keys are bound to one origin, compared in constant time |

The approval screen is served by the helper on the user's own machine, so a
website cannot draw a fake one. Permissions can be revoked at any time from
<http://localhost:8000/permission>.

## Layout

| Path | What |
| --- | --- |
| `server.py`, `serve.py`, `pairing.py` | the helper: API, launcher, permission handling |
| `pipeline/` | download, transcribe, split, captions, render |
| `web/` | the interface (plain HTML/CSS/JS, no framework) |
| `build_site.py`, `deployclover.bat` | build and publish the static site |
| `install.py`, `install.bat`, `start.bat` | setup and launcher |
| `package.py` | build the distributable zip |
| `brand/` | logo, square and reversed |

## Licence

MIT — see [LICENSE](LICENSE).

Downloading from YouTube is against its terms of service unless the content is
yours or you have permission. What you download is your call.
