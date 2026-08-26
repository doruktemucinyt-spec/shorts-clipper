"""Partlara bolme: her part tam surede kesiliyor."""

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
