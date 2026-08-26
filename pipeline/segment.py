"""Part sinirlarini cumle sonuna hizalayarak belirler."""

SENTENCE_END = ".?!…"


def _ends_sentence(text: str) -> bool:
    text = (text or "").strip().rstrip('"”’\')]')
    return bool(text) and text[-1] in SENTENCE_END


def build_parts(segments, target=240.0, tolerance=40.0, min_last=45.0):
    """Segmentleri partlara boler.

    Hedef sureye yaklasinca +/- tolerance penceresinde cumle bitisi arar ve
    orada keser. Pencerede cumle bitisi yoksa hedefe en yakin segment sonunda
    keser -- boylece hicbir zaman cumlenin ortasindan kesilmez.
    """
    if not segments:
        return []

    video_end = segments[-1]["end"]
    parts = []
    part_start = segments[0]["start"]
    i = 0
    n = len(segments)

    while i < n:
        deadline = part_start + target
        lo, hi = deadline - tolerance, deadline + tolerance

        best_any = None      # (mesafe, index, cut)
        best_sentence = None
        j = i
        while j < n:
            cut = segments[j]["end"]
            if cut > hi:
                break
            if cut >= lo:
                dist = abs(cut - deadline)
                if best_any is None or dist < best_any[0]:
                    best_any = (dist, j, cut)
                if _ends_sentence(segments[j]["text"]):
                    if best_sentence is None or dist < best_sentence[0]:
                        best_sentence = (dist, j, cut)
            j += 1

        chosen = best_sentence or best_any

        if chosen is None:
            # Pencerede hic aday yok (cok uzun segment). Deadline'i gecen ilk
            # segmentin sonunda kes.
            k = i
            while k < n and segments[k]["end"] < deadline:
                k += 1
            if k >= n:
                parts.append({"start": part_start, "end": video_end})
                break
            chosen = (0, k, segments[k]["end"])

        _, idx, cut = chosen

        if idx >= n - 1:
            parts.append({"start": part_start, "end": video_end})
            break

        parts.append({"start": part_start, "end": cut})
        part_start = segments[idx + 1]["start"]
        i = idx + 1

    if not parts:
        parts = [{"start": segments[0]["start"], "end": video_end}]

    # Cok kisa kalan son partı bir oncekiyle birlestir
    if len(parts) > 1 and (parts[-1]["end"] - parts[-1]["start"]) < min_last:
        tail = parts.pop()
        parts[-1]["end"] = tail["end"]

    for n_, p in enumerate(parts, 1):
        p["index"] = n_
        p["duration"] = p["end"] - p["start"]

    return parts


def words_in_range(segments, start, end):
    """Verilen araliktaki tum kelimeleri duz liste olarak dondurur."""
    out = []
    for seg in segments:
        if seg["end"] < start or seg["start"] > end:
            continue
        for w in seg["words"]:
            if w["end"] > start and w["start"] < end:
                out.append(w)
    return out


def build_parts_fixed(duration: float, target: float = 240.0, min_last: float = 45.0):
    """Transkript olmadan, tam surede sert kesim. Cok daha hizli ama cumle
    ortasindan kesebilir."""
    if duration <= 0:
        return []

    parts = []
    start = 0.0
    while start < duration:
        end = min(duration, start + target)
        parts.append({"start": start, "end": end})
        start = end

    if len(parts) > 1 and (parts[-1]["end"] - parts[-1]["start"]) < min_last:
        tail = parts.pop()
        parts[-1]["end"] = tail["end"]

    for n, p in enumerate(parts, 1):
        p["index"] = n
        p["duration"] = p["end"] - p["start"]
    return parts
