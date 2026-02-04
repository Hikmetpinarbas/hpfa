from __future__ import annotations
import re

CAUSAL_WORDS = [
    r"\bçünkü\b",
    r"\bbundan dolayı\b",
    r"\bbunun sonucu\b",
    r"\bsebebiyle\b",
]

def guard(text: str) -> str:
    out = text
    for w in CAUSAL_WORDS:
        out = re.sub(w, "bununla uyumlu olarak", out, flags=re.IGNORECASE)
    return out
