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

1. Download or clone this repository.
2. Double-click **`install.bat`**. It asks one question: whether to install the
   caption feature (~2 GB extra plus a ~0.5 GB subtitle model on first use).
   Without it you still get the 9:16 parts, just no burned-in captions.
3. Double-click **`start.bat`**.
4. Open the site and press **Connect my computer**, or just go to
   <http://localhost:8000>.

Requirements: Python 3.10+, ffmpeg (the installer offers to install it via
winget). An NVIDIA GPU is optional — without one, rendering falls back to the
CPU and is slower.

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
| `build_site.py`, `deploy.bat` | build and publish the static site |
| `install.py`, `install.bat`, `start.bat` | setup and launcher |
| `package.py` | build the distributable zip |
| `brand/` | logo, square and reversed |

## Licence

MIT — see [LICENSE](LICENSE).

Downloading from YouTube is against its terms of service unless the content is
yours or you have permission. What you download is your call.
