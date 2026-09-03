"""
Comprehensive edge-case test suite for CareGuard AI.
Tests:
  - TRUE POSITIVES: real threats that MUST be flagged
  - TRUE NEGATIVES: innocuous conversations that must NOT be flagged
  - BORDERLINE: ambiguous phrases that test fuzzy matching precision
"""

import sys
import json
sys.path.insert(0, "/home/saad/Documents/careguard ai")
from backend.audit.keyword_scanner import scan_transcript
from backend.audit.response_checker import check_response_window
from backend.audit.trigger_phrases import TRIGGER_PHRASES
from rapidfuzz import fuzz


def make_utterance(speaker, text, idx=0):
    return {"speaker": speaker, "text": text, "start_time": f"00:{idx:02d}:00"}


def make_transcript(lines):
    """lines: list of (speaker, text) tuples"""
    return [make_utterance(s, t, i) for i, (s, t) in enumerate(lines)]


def get_patient_flags(utterances):
    """Return just the (category, matched_phrase) tuples for patient utterances."""
    flags = scan_transcript(utterances)
    return [(f["category"], f["matched_phrase"], f["confidence"], f["detection_method"]) for f in flags]


# ============================================================
# PART 1: Diagnostic — check every trigger phrase against common idioms
# ============================================================
print("=" * 70)
print("PART 1: Trigger phrase idiom collision diagnostic")
print("=" * 70)

IDIOMS_TO_TEST = [
    ("going to kill time this weekend", "going to kill / want to kill", "should NOT be duty_to_warn"),
    ("going to kill it at the presentation", "going to kill", "should NOT be duty_to_warn"),
    ("I want to kill that boss in the game", "want to kill", "should NOT be duty_to_warn (but likely will)"),
    ("my back is killing me", "kill myself", "should NOT be suicidality"),
    ("I could just die of embarrassment", "want to die", "should NOT be suicidality"),
    ("I'm dying to try that restaurant", "want to die / tired of living", "should NOT be suicidality"),
    ("I'm dead tired today", "want to die", "should NOT be suicidality"),
    ("the kids killed it at the recital", "kill myself / want to kill", "should NOT be flagged"),
    ("going to hurt my chances", "going to hurt", "should NOT be duty_to_warn"),
    ("this is going to hurt my grade", "going to hurt", "should NOT be duty_to_warn"),
    ("I'll hurt my ankle if I run", "I'll hurt", "should NOT be duty_to_warn"),
    ("how am I going to get through another month", "duty_to_warn phrases", "should NOT be flagged"),
    ("I ended it with my girlfriend", "end it all", "should NOT be suicidality"),
    ("I want to end the meeting early", "end it all", "should NOT be suicidality"),
    ("I haven't been sleeping on the couch", "haven't been sleeping", "should NOT be treatment_plan"),
    ("my parent hits me up for money", "hitting me / my parent hits me", "should NOT be mandatory_reporting"),
    ("someone touched my shoulder on the bus", "someone touched me", "should NOT be mandatory_reporting"),
    ("I'm locked in my office all day", "locked in my room", "should NOT be mandatory_reporting"),
    ("I started taking piano lessons", "started taking", "should NOT be treatment_plan"),
    ("I haven't been eating at that restaurant", "haven't been eating", "should NOT be treatment_plan"),
    ("nothing matters to me when it comes to politics", "nothing matters anymore", "should NOT be suicidality"),
    ("what's the point of this meeting", "what's the point", "should NOT be suicidality (but likely will)"),
    ("if I disappeared from the group chat", "if I disappeared", "should NOT be suicidality (but borderline)"),
    ("I just want it to stop raining", "just want it to stop", "should NOT be suicidality (but likely will)"),
    ("they're going to regret not hiring me", "they're going to regret", "should NOT be duty_to_warn"),
    ("make them pay attention to me", "make them pay", "should NOT be duty_to_warn"),
]

for text, triggers, note in IDIOMS_TO_TEST:
    text_lower = text.lower()
    hits = []
    for cat, phrases in TRIGGER_PHRASES.items():
        for phrase in phrases:
            phrase_lower = phrase.lower()
            if phrase_lower in text_lower:
                hits.append((cat, phrase, 100, "exact"))
            else:
                ratio = fuzz.partial_ratio(phrase_lower, text_lower)
                if ratio >= 85:
                    hits.append((cat, phrase, int(ratio), "fuzzy"))
    status = "HIT" if hits else "CLEAN"
    icon = "!!" if hits else "OK"
    print(f"  [{icon}] \"{text}\"")
    if hits:
        for cat, phrase, conf, method in hits:
            print(f"       -> {cat}: \"{phrase}\" ({method}, {conf}%)")
    print(f"       Note: {note}")
    print()


# ============================================================
# PART 2: True positive tests — MUST flag
# ============================================================
print("=" * 70)
print("PART 2: TRUE POSITIVES — real threats that MUST be flagged")
print("=" * 70)

TRUE_POSITIVE_TESTS = [
    {
        "name": "Direct suicidal statement",
        "lines": [
            ("Patient", "I have been thinking about killing myself for weeks now."),
            ("Therapist", "Thank you for sharing that with me."),
        ],
        "expected_categories": ["suicidality"],
    },
    {
        "name": "Passive death wish",
        "lines": [
            ("Patient", "Honestly, I just wish I was dead sometimes."),
            ("Therapist", "That sounds really painful."),
        ],
        "expected_categories": ["suicidality"],
    },
    {
        "name": "Tarasoff threat against specific person",
        "lines": [
            ("Patient", "I know where my ex lives and they're going to regret what they did to me."),
            ("Therapist", "I hear how angry you are."),
        ],
        "expected_categories": ["duty_to_warn"],
    },
    {
        "name": "Direct violence threat",
        "lines": [
            ("Patient", "I'm going to hurt my neighbor if he plays that music one more time."),
            ("Therapist", "That sounds frustrating."),
        ],
        "expected_categories": ["duty_to_warn"],
    },
    {
        "name": "Child abuse disclosure",
        "lines": [
            ("Patient", "My stepdad has been hitting me when my mom isn't home."),
            ("Therapist", "I'm sorry you're going through that."),
        ],
        "expected_categories": ["mandatory_reporting"],
    },
    {
        "name": "Medication change without follow-up",
        "lines": [
            ("Patient", "My doctor changed my medication last week and I feel terrible."),
            ("Therapist", "That must be difficult."),
        ],
        "expected_categories": ["treatment_plan"],
    },
    {
        "name": "Subtle passive ideation",
        "lines": [
            ("Patient", "I wonder if anyone would notice if I just disappeared for a while."),
            ("Therapist", "It sounds like you're feeling isolated."),
        ],
        "expected_categories": ["suicidality"],
    },
    {
        "name": "Elder abuse witness",
        "lines": [
            ("Patient", "I saw elder abuse happening at my mother's care facility."),
            ("Therapist", "That's concerning to hear."),
        ],
        "expected_categories": ["mandatory_reporting"],
    },
    {
        "name": "Multiple categories in one session",
        "lines": [
            ("Patient", "I've been thinking about suicide a lot lately."),
            ("Therapist", "Thank you for telling me."),
            ("Patient", "And my husband changed my medication without telling the doctor."),
            ("Therapist", "Let's talk about that."),
        ],
        "expected_categories": ["suicidality", "treatment_plan"],
    },
]

tp_pass = 0
tp_fail = 0
for test in TRUE_POSITIVE_TESTS:
    utterances = make_transcript(test["lines"])
    flags = get_patient_flags(utterances)
    found_cats = list(set(f[0] for f in flags))

    missing = [c for c in test["expected_categories"] if c not in found_cats]
    passed = len(missing) == 0

    icon = "PASS" if passed else "FAIL"
    if passed:
        tp_pass += 1
    else:
        tp_fail += 1

    print(f"  [{icon}] {test['name']}")
    print(f"         Expected: {test['expected_categories']}")
    print(f"         Found:    {found_cats}")
    if flags:
        for cat, phrase, conf, method in flags:
            print(f"         Flag: {cat} -> \"{phrase}\" ({method}, {conf}%)")
    if missing:
        print(f"         MISSING: {missing}")
    print()

print(f"  True positives: {tp_pass} passed, {tp_fail} failed\n")


# ============================================================
# PART 3: True negative tests — MUST NOT flag
# ============================================================
print("=" * 70)
print("PART 3: TRUE NEGATIVES — innocuous conversations that must NOT flag")
print("=" * 70)

TRUE_NEGATIVE_TESTS = [
    {
        "name": "Casual weekend chat",
        "lines": [
            ("Patient", "I went hiking with my family this weekend. It was really nice."),
            ("Therapist", "That sounds wonderful."),
            ("Patient", "Yeah, we spent the whole day outdoors. The kids loved it."),
            ("Therapist", "Quality time like that is so important."),
        ],
    },
    {
        "name": "Work stress (normal range)",
        "lines": [
            ("Patient", "Work has been busy but I'm managing. I've been taking on more projects."),
            ("Therapist", "How does that workload feel?"),
            ("Patient", "It's a lot but I enjoy it. I think I'm growing from the challenge."),
            ("Therapist", "That's a healthy perspective."),
        ],
    },
    {
        "name": "Going to kill time",
        "lines": [
            ("Patient", "I'm going to kill some time at the bookstore before my appointment."),
            ("Therapist", "Sounds like a nice way to spend the afternoon."),
        ],
    },
    {
        "name": "Going to kill it (positive idiom)",
        "lines": [
            ("Patient", "I have a big presentation tomorrow and I'm going to kill it."),
            ("Therapist", "I love your confidence."),
        ],
    },
    {
        "name": "My back is killing me (pain idiom)",
        "lines": [
            ("Patient", "My back is killing me after moving all those boxes yesterday."),
            ("Therapist", "Moving can be tough on the body."),
        ],
    },
    {
        "name": "End a relationship (not suicidal)",
        "lines": [
            ("Patient", "I finally ended it with my boyfriend last week. It was the right call."),
            ("Therapist", "That must have been a difficult decision."),
            ("Patient", "It was, but I feel lighter now. Like a weight is off."),
            ("Therapist", "That's a positive sign."),
        ],
    },
    {
        "name": "End the meeting (innocuous)",
        "lines": [
            ("Patient", "Can we end the session a few minutes early today? I have to pick up the kids."),
            ("Therapist", "Of course, let's wrap up."),
        ],
    },
    {
        "name": "Parent hits me up for money",
        "lines": [
            ("Patient", "My parent hits me up for money every month. It's getting annoying."),
            ("Therapist", "Financial boundaries with family can be tricky."),
        ],
    },
    {
        "name": "Locked in office (metaphorical)",
        "lines": [
            ("Patient", "I feel like I'm locked in my office all day. I need more fresh air."),
            ("Therapist", "Finding time to get outside is important."),
        ],
    },
    {
        "name": "Started taking piano lessons",
        "lines": [
            ("Patient", "I started taking piano lessons last month. It's been really therapeutic."),
            ("Therapist", "Music can be a wonderful outlet."),
        ],
    },
    {
        "name": "Haven't been eating at restaurant",
        "lines": [
            ("Patient", "I haven't been eating at that new restaurant yet. Have you tried it?"),
            ("Therapist", "I haven't, but I've heard good things."),
        ],
    },
    {
        "name": "Nothing matters in politics",
        "lines": [
            ("Patient", "I've stopped following the news. Nothing matters when it comes to politics anyway."),
            ("Therapist", "It can definitely feel overwhelming."),
        ],
    },
    {
        "name": "Someone touched my shoulder (innocuous)",
        "lines": [
            ("Patient", "Someone touched my shoulder on the crowded bus and it startled me."),
            ("Therapist", "Crowded spaces can be uncomfortable."),
        ],
    },
    {
        "name": "Going to get through (the previously fixed case)",
        "lines": [
            ("Patient", "I just end up staring at the ceiling wondering how I am going to get through another month."),
            ("Therapist", "That fatigue can make everything feel heavier."),
        ],
    },
    {
        "name": "Going to regret (mild frustration)",
        "lines": [
            ("Patient", "They're going to regret not promoting me when they see my quarterly numbers."),
            ("Therapist", "Sounds like you're motivated to prove yourself."),
        ],
    },
    {
        "name": "Make them pay attention",
        "lines": [
            ("Patient", "I just want to make them pay attention to the quality of my work."),
            ("Therapist", "Feeling seen at work is important."),
        ],
    },
    {
        "name": "Dying to try restaurant (excitement idiom)",
        "lines": [
            ("Patient", "I'm dying to try that new Italian place downtown."),
            ("Therapist", "Food can be a great way to explore new experiences."),
        ],
    },
    {
        "name": "Dead tired (colloquial)",
        "lines": [
            ("Patient", "I'm dead tired after the gym today. Leg day really wiped me out."),
            ("Therapist", "Exercise can definitely take it out of you."),
        ],
    },
    {
        "name": "Die of embarrassment (idiom)",
        "lines": [
            ("Patient", "I tripped in front of everyone and I could have just died of embarrassment."),
            ("Therapist", "Those moments can feel awful in the moment."),
        ],
    },
    {
        "name": "Clean session — hobbies and family",
        "lines": [
            ("Patient", "I've been reading a lot lately. Just finished a great mystery novel."),
            ("Therapist", "Reading is a wonderful way to unwind."),
            ("Patient", "My daughter also started playing soccer. We go to her games every Saturday."),
            ("Therapist", "That sounds like a great family activity."),
            ("Patient", "Yeah, and my husband grilled burgers after the last game."),
            ("Therapist", "Sounds like a perfect weekend."),
        ],
    },
    {
        "name": "The user's original test transcript (full)",
        "lines": [
            ("Therapist", "Hello, Sarah. It is wonderful to see you today. How has your week been going?"),
            ("Patient", "Hi. It has been a bit of a mixed week, honestly. Work has been busy, but manageable for the most part."),
            ("Therapist", "I am glad work is going alright. Did you manage to get outside and enjoy any of the weekend weather?"),
            ("Patient", "I went for a short walk on Saturday morning. Though lately, even when I am out, my mind just races. Sometimes things feel so heavy that I find myself thinking it might just be easier if I simply disappeared for a long while."),
            ("Therapist", "It sounds like you have been carrying a lot of mental weight lately, and wanting a break from that pressure is completely understandable."),
            ("Patient", "Yeah, exactly. It is just this lingering fatigue. On top of that, my doctor changed my antidepressant dosage on Friday, and since then I have felt totally jittery and disconnected from everything around me."),
            ("Therapist", "Adjusting to shifts in routine or daily habits can definitely throw us off balance. Let us talk about what strategies we can use to help you stay grounded when those feelings pop up."),
            ("Patient", "I mean, we could try. But when the heaviness hits, it feels like nothing I do really changes the baseline. I just end up staring at the ceiling wondering how I am going to get through another month."),
            ("Therapist", "That kind of fatigue can make everyday tasks feel like climbing a mountain. What if we focus on breaking down your daily routine into very small, manageable steps for now?"),
            ("Patient", "Breaking things down sounds fine in theory, but my brain feels so fried right now. Still, I am willing to try whatever might make the evenings a bit less overwhelming."),
            ("Therapist", "We will take it at whatever pace works best for you. Before we wrap up, do you want to keep our normal Thursday time slot for next week?"),
            ("Patient", "Yes, Thursday at three works perfectly for me. See you then."),
        ],
    },
]

tn_pass = 0
tn_fail = 0
for test in TRUE_NEGATIVE_TESTS:
    utterances = make_transcript(test["lines"])
    flags = get_patient_flags(utterances)

    passed = len(flags) == 0
    icon = "PASS" if passed else "FAIL"
    if passed:
        tn_pass += 1
    else:
        tn_fail += 1

    print(f"  [{icon}] {test['name']}")
    if flags:
        for cat, phrase, conf, method in flags:
            print(f"         FALSE FLAG: {cat} -> \"{phrase}\" ({method}, {conf}%)")
    print()

print(f"  True negatives: {tn_pass} passed, {tn_fail} failed\n")


# ============================================================
# SUMMARY
# ============================================================
print("=" * 70)
total_pass = tp_pass + tn_pass
total_fail = tp_fail + tn_fail
print(f"OVERALL: {total_pass} passed, {total_fail} failed out of {total_pass + total_fail} tests")
if total_fail == 0:
    print("ALL TESTS PASSED")
else:
    print(f"ATTENTION: {total_fail} tests need review")
print("=" * 70)
