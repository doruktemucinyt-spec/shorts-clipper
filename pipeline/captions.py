"""ASS altyazi uretimi: 2-4 kelimelik gruplar, aktif kelime vurgulu + pop.

Baslik ve "Part N" de ayni dosyaya ayri stillerle yaziliyor -- ffmpeg drawtext
Windows'ta yol/font escape'i yuzunden surekli patladigi icin her seyi ASS'e
koymak cok daha guvenilir.
"""

BS = chr(92)  # tek ters bolu

W, H = 1080, 1920

BASE_COLOR = "&H00FFFFFF"   # beyaz (ASS: &HAABBGGRR)
POP = r"{\fscx70\fscy70\t(0,130,\fscx100\fscy100)}"


def hex_to_ass(hex_color: str) -> str:
    """#RRGGBB -> &H00BBGGRR"""
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        h = "FFD400"
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def esc(text: str) -> str:
    """ASS dosyasina yazilacak metni zararsiz hale getirir.

    Satir sonlari da temizleniyor: video basligi disaridan geliyor ve icinde
    satir sonu olsa ASS dosyasina sahte bir Dialogue satiri eklenebilirdi.
    """
    text = (text or "").replace("\\", "").replace("{", "(").replace("}", ")")
    return " ".join(text.split()).strip()


def group_words(words, max_words=4, min_words=2, max_gap=0.5, max_dur=1.8):
    """Kelimeleri 2-4'luk obeklere ayirir."""
    groups, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            dur = w["end"] - cur[0]["start"]
            if len(cur) >= max_words or gap > max_gap or dur > max_dur:
                groups.append(cur)
                cur = []
        cur.append(w)
        tail = (w["word"] or "").strip()
        if len(cur) >= min_words and tail and tail[-1] in ".?!…,;:":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def _header(font: str, highlight: str) -> str:
    hl = hex_to_ass(highlight)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},84,{BASE_COLOR},{hl},&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,420,1
Style: Title,{font},56,{BASE_COLOR},{BASE_COLOR},&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,8,70,70,80,1
Style: Part,{font},64,{hl},{hl},&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,8,70,70,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_ass(words, part_start: float, part_duration: float, title: str,
              part_index: int, part_total: int, font: str = "Arial Black",
              highlight: str = "#FFD400", include_words: bool = True) -> str:
    """Bir part icin tam ASS dosyasi metni uretir. Zamanlar part basina gore."""
    hl = hex_to_ass(highlight)
    lines = [_header(font, highlight)]

    # Ust bilgi: baslik + Part N (part boyunca sabit)
    end_all = ass_time(part_duration)
    safe_title = esc(title)
    if len(safe_title) > 70:
        safe_title = safe_title[:67].rstrip() + "..."
    lines.append(f"Dialogue: 0,0:00:00.00,{end_all},Title,,0,0,0,,{safe_title}")
    lines.append(f"Dialogue: 0,0:00:00.00,{end_all},Part,,0,0,0,,Part {part_index}")

    if not include_words:
        return "\n".join(lines) + "\n"

    groups = group_words(words)
    for gi, g in enumerate(groups):
        for wi, w in enumerate(g):
            st = w["start"] - part_start
            if wi < len(g) - 1:
                en = g[wi + 1]["start"] - part_start
            else:
                en = w["end"] - part_start
                if gi < len(groups) - 1:
                    nxt = groups[gi + 1][0]["start"] - part_start
                    en = min(nxt, en + 0.4)
                else:
                    en = en + 0.3
            st = max(0.0, st)
            en = min(part_duration, max(en, st + 0.08))
            if en <= st:
                continue

            chunks = []
            for j, ww in enumerate(g):
                t = esc(ww["word"])
                if not t:
                    continue
                if j == wi:
                    tag_on = "{" + BS + "c" + hl + "&}"
                    tag_off = "{" + BS + "c" + BASE_COLOR + "&}"
                    chunks.append(tag_on + t + tag_off)
                else:
                    chunks.append(t)
            text = " ".join(chunks)
            if not text:
                continue

            prefix = POP if wi == 0 else ""
            lines.append(
                f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{prefix}{text}"
            )

    return "\n".join(lines) + "\n"
