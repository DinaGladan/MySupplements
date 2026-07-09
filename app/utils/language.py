import re

# Letters that appear in Croatian but not in English — a strong signal.
_CROATIAN_CHARS = set("čćžšđ")

# Common Croatian words (used when the text has no diacritics).
_CROATIAN_HINTS = {
    "i", "sam", "imam", "godina", "godine", "godinu", "star", "stara",
    "spavam", "san", "sna", "stres", "stresa", "stresom", "umoran", "umorna",
    "umor", "zelim", "bolji", "bolje", "vise", "energije", "energija", "kava",
    "kave", "kavu", "kofein", "kofeina", "sunce", "suncu", "sunca", "malo",
    "puno", "cesto", "je", "su", "za", "smanjiti", "smanjenje", "fokus",
    "fokusa", "zena", "zensko", "muskarac", "dnevno", "osjecam", "htio",
    "htjela", "imati", "pijem", "ne", "na", "pod",
}

# Common English words.
_ENGLISH_HINTS = {
    "i", "am", "the", "and", "a", "sleep", "stress", "tired", "want", "more",
    "energy", "coffee", "sun", "years", "old", "female", "male", "have",
    "better", "reduce", "focus", "little", "lot", "often", "during", "day",
    "feel", "drink", "rarely", "eat", "fish", "good", "poorly", "stressed",
    "of", "to", "my", "get", "with", "in",
}


def detect_language(*texts: str) -> str:
    """
    Small heuristic language detector. Returns "hr" for Croatian or "en" for
    English.

    Croatian-specific letters (č, ć, ž, š, đ) are a strong signal. Without them,
    we compare how many Croatian vs English hint words appear. Defaults to "en"
    when the two are tied or nothing matches.
    """
    text = " ".join(t for t in texts if t).lower()

    if any(ch in _CROATIAN_CHARS for ch in text):
        return "hr"

    words = set(re.findall(r"[a-zčćžšđ]+", text))
    hr_hits = len(words & _CROATIAN_HINTS)
    en_hits = len(words & _ENGLISH_HINTS)

    return "hr" if hr_hits > en_hits else "en"
