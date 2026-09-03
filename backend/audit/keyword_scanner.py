"""
Keyword scanner for detecting liability trigger phrases in patient utterances.
Uses exact substring matching only — the LLM handles contextual/paraphrase detection.
"""

from typing import List, Dict
from .trigger_phrases import TRIGGER_PHRASES, SEVERITY_MAP, EXCLUSION_PATTERNS


def is_excluded(text: str, category: str, matched_phrase: str) -> bool:
    """Check if the full utterance contains an innocuous-context pattern that suppresses this flag."""
    exclusions = EXCLUSION_PATTERNS.get((category, matched_phrase), [])
    text_lower = text.lower()
    return any(exc.lower() in text_lower for exc in exclusions)


def scan_utterance(text: str, category: str = None) -> List[Dict]:
    """
    Scan a single utterance for trigger phrases using exact substring matching.
    Returns list of matches: [{category, matched_phrase, detection_method, confidence}]
    """
    matches = []
    text_lower = text.lower()

    categories_to_check = [category] if category else TRIGGER_PHRASES.keys()

    for cat in categories_to_check:
        if cat not in TRIGGER_PHRASES:
            continue

        for phrase in TRIGGER_PHRASES[cat]:
            phrase_lower = phrase.lower()

            if phrase_lower in text_lower:
                if not is_excluded(text, cat, phrase):
                    matches.append({
                        "category": cat,
                        "matched_phrase": phrase,
                        "detection_method": "exact_match",
                        "confidence": 100,
                        "severity": SEVERITY_MAP.get(cat, "LOW")
                    })

    return matches


def scan_transcript(utterances: List[Dict]) -> List[Dict]:
    """
    Scan all patient utterances in a transcript.
    Returns one flag per (utterance_index, category) — first exact match per category wins.
    """
    flags = []

    for idx, utt in enumerate(utterances):
        if utt.get("speaker", "").lower() != "patient":
            continue

        text = utt.get("text", "")
        matches = scan_utterance(text)

        seen_categories: set = set()
        for match in matches:
            cat = match["category"]
            if cat not in seen_categories:
                seen_categories.add(cat)
                flags.append({
                    "utterance_index": idx,
                    "patient_quote": text,
                    "timestamp": utt.get("start_time"),
                    **match,
                })

    return flags
