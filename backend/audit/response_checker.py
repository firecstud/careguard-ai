"""
Response window checker: verifies if therapist responded appropriately
after a patient disclosure. Scans next N therapist utterances for required phrases.
"""

from typing import List, Dict
from .required_responses import REQUIRED_RESPONSES

RESPONSE_WINDOW = 5

# How many required-response phrases must match before the category is cleared.
MINIMUM_MATCHES = {
    "suicidality": 2,
}


def check_response_window(
    utterances: List[Dict],
    trigger_index: int,
    category: str
) -> Dict:
    """
    Check if therapist responded appropriately within the next N utterances.
    Returns: {responded: bool, missing_phrases: list, matched_phrases: list}
    """
    if category not in REQUIRED_RESPONSES:
        return {"responded": False, "missing_phrases": [], "matched_phrases": []}

    required = REQUIRED_RESPONSES[category]
    window_end = min(trigger_index + RESPONSE_WINDOW + 1, len(utterances))

    therapist_texts = []
    for i in range(trigger_index + 1, window_end):
        utt = utterances[i]
        if utt.get("speaker", "").lower() == "therapist":
            therapist_texts.append(utt.get("text", "").lower())

    combined_text = " ".join(therapist_texts)
    matched = []
    missing = []

    for phrase in required:
        phrase_lower = phrase.lower()
        if phrase_lower in combined_text:
            matched.append(phrase)
        else:
            missing.append(phrase)

    min_required = MINIMUM_MATCHES.get(category, 1)
    responded = len(matched) >= min_required

    return {
        "responded": responded,
        "matched_phrases": matched,
        "missing_phrases": missing
    }
