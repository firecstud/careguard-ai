"""
Trigger phrases that indicate liability-relevant patient disclosures.
When a patient says any of these, the therapist MUST respond appropriately.
"""

TRIGGER_PHRASES = {
    "suicidality": [
        "better off without me",
        "want to die",
        "end it all",
        "not worth living",
        "hurt myself",
        "hurting myself",
        "kill myself",
        "killing myself",
        "no reason to live",
        "tired of living",
        "can't go on",
        "wish I was dead",
        "thinking about suicide",
        "what's the point",
        "don't want to be here",
        "everyone would be better off",
        "better off gone",
        "don't want to wake up",
        "just want it to stop",
        "thinking about it",
        "make it all stop",
        "if I disappeared",
        "if I just disappeared",
        "no one would notice",
        "anyone would notice",
        "nothing matters anymore",
        "life has no meaning",
        "no point in living",
        "wouldn't miss me",
        # indirect / cultural expressions
        "life has no value",
        "my life has no value",
        "no value anymore",
        "wishes something would happen",
        "wish something would happen",
        "no use for it anymore",
        "have no use for it",
        "made peace with everything",
        "made peace with things",
        "finally made peace",
        "get my affairs in order",
        "getting my affairs in order",
        "get things in order",
        "getting things in order",
        # behavioral warning signs: giving away possessions, farewell letters, funeral ideation
        "giving away my",
        "gave away my",
        "wrote letters to",
        "writing letters to",
        "written letters to",
        "picturing my funeral",
        "imagining my funeral",
        "thinking about my funeral",
        "just in case something happens to me",
        "just in case i'm not around",
        "just in case I won't be",
        # explicit plan/means/intent disclosures
        "ending my life",
        "end my life",
        "take my life",
        "taking my life",
        "i have a plan",
        "have a plan and",
        "have the means",
        "have a timeline",
        "set a date",
        "i've set a date",
    ],
    "duty_to_warn": [
        "going to hurt",
        "going to kill",
        "want to kill",
        "make them pay",
        "they deserve to die",
        "I'll hurt",
        "I'll make them",
        "they won't see it coming",
        "I know where they live",
        "they're going to regret",
        # explicit harm intent
        "want to hurt",
        "want to hurt him",
        "want to hurt her",
        "want to hurt them",
        "i want to hurt",
        "going to hurt him",
        "going to hurt her",
        "i can't stop myself",
        "don't know if i can stop",
        "don't know if i can stop myself",
        # premeditation / surveillance indicators
        "mapped out his",
        "mapped out her",
        "mapped out their",
        "know his schedule",
        "know her schedule",
        "know their schedule",
        "know when he arrives",
        "know when she arrives",
        "know when they arrive",
        "same spot",
        "i know where he",
        "i know where she",
        "i know where they",
        # stalking indicators
        "been outside her",
        "been outside his",
        "been outside their",
        "watching her building",
        "watching his building",
        "outside her apartment",
        "outside his apartment",
        "know her routine",
        "know his routine",
        "know where she'll be",
        "know where he'll be",
        "know where they'll be",
        # weapon possession / carrying
        "bought a knife",
        "carrying a knife",
        "bought a gun",
        "carrying a gun",
        "have a weapon",
        "got a weapon",
        "i've been carrying",
        "carrying it",
    ],
    "mandatory_reporting": [
        "hitting me",
        "abusing me",
        "hurt my child",
        "someone is abusing",
        "they beat me",
        "being abused",
        "my kid is being hurt",
        "elder abuse",
        "my parent hits me",
        "someone touched me",
        "they don't feed me",
        "locked in my room",
    ],
    "informed_consent": [],
    "crisis_resources": [],
    "treatment_plan": [
        "new medication",
        "started taking",
        "stopped taking",
        "changed my medication",
        "new symptom",
        "new diagnosis",
        "haven't been sleeping",
        "haven't been eating",
        "panic attacks",
    ],
}


# Patterns that indicate innocuous context — if any of these substrings appear
# in the full utterance alongside the trigger, the flag is suppressed.
# Key: (category, trigger_phrase)  Value: list of safe-context substrings
EXCLUSION_PATTERNS = {
    # duty_to_warn — common idioms that use violent language non-literally
    ("duty_to_warn", "going to kill"): [
        "kill time", "kill some time", "kill a little time", "kill it", "kill the presentation", "kill the pitch",
        "kill the interview", "kill the audition", "kill the test",
        "kill the exam", "kill the performance", "kill the song",
        "threatened to kill", "he threatened", "she threatened",
        "said he would kill", "said she would kill", "said they would kill",
    ],
    ("duty_to_warn", "going to hurt"): [
        "hurt my chances", "hurt my grade", "hurt my career",
        "hurt my reputation", "hurt my score", "hurt my resume",
        "hurt my application", "hurt my standing", "hurt my ranking",
        "hurt the team", "hurt our chances",
        "threatened to hurt", "he threatened", "she threatened",
    ],
    ("duty_to_warn", "want to kill"): [
        "kill that boss", "kill this boss", "kill the boss",
        "kill the level", "kill this level", "kill that level",
        "kill that final", "kill the final", "kill the last",
        "kill it on", "kill it at",
    ],
    ("duty_to_warn", "I'll hurt"): [
        "hurt my ankle", "hurt my knee", "hurt my back", "hurt my shoulder",
        "hurt my wrist", "hurt my neck", "hurt my hip", "hurt my leg",
        "hurt myself if", "hurt my elbow",
    ],
    ("duty_to_warn", "they're going to regret"): [
        "regret not hiring", "regret not picking", "regret not choosing",
        "regret not promoting", "regret not signing", "regret not selecting",
        "regret not taking", "regret letting",
    ],
    ("duty_to_warn", "make them pay"): [
        "pay attention", "pay for the", "pay their share",
        "pay their fair", "pay for their", "pay up",
    ],
    # "I know where they live" — patient reporting someone else's threat, not their own
    ("duty_to_warn", "I know where they live"): [
        "he said he knows", "she said she knows", "they said they know",
        "he apparently said", "she apparently said", "apparently said he",
        "apparently said she", "told me that he", "told me that she",
        "said he knows where", "said she knows where",
    ],
    # mandatory_reporting — innocent physical contact / metaphorical language
    ("mandatory_reporting", "someone touched me"): [
        "touched my shoulder", "touched my arm", "touched my back",
        "touched my hand", "touched my elbow", "touched my knee",
        "touched my sleeve", "touched my coat",
    ],
    ("mandatory_reporting", "my parent hits me"): [
        "hits me up", "hits me for",
    ],
    # suicidality — common expressions that use existential language non-literally
    ("suicidality", "what's the point"): [
        "point of this meeting", "point of the meeting", "point of doing",
        "point of this exercise", "point of this project",
        "point of this discussion", "point of this class",
    ],
    ("suicidality", "just want it to stop"): [
        "stop raining", "stop snowing", "stop leaking", "stop dripping",
        "stop making that noise", "stop barking", "stop playing",
    ],
    ("suicidality", "if I disappeared"): [
        "from the group chat", "from the chat", "from social media",
        "from the server", "from the app", "from the thread",
    ],
    ("suicidality", "if I just disappeared"): [
        "from the group chat", "from the chat", "from social media",
        "from the server", "from the app", "from the thread",
    ],
    # "don't want to break up the family" fuzzy-matches "don't want to wake up"
    ("suicidality", "don't want to wake up"): [
        "break up", "breaking up", "wake up early", "wake up on time",
        "wake up late", "wake up for",
    ],
    # "thinking about it" used to describe worrying about someone else's safety
    ("suicidality", "thinking about it"): [
        "thinking about her safety", "thinking about his safety", "thinking about their safety",
        "thinking about her all", "thinking about him all", "thinking about them all",
        "thinking about her situation", "thinking about his situation",
        "thinking about whether i should", "thinking about what i should",
        # "it's worse than that" fuzzy-matches "thinking about it"
        "worse than that", "showed me a bruise", "bruise on his", "bruise on her",
        "care home", "care facility", "night staff", "night aide",
        # premeditation about harming others — "thinking about it" is about the planned act, not self-harm
        "mapped out", "parking garage", "sitting in that garage", "sitting in the garage",
        "i know when he", "i know when she", "know when he arrives", "know when she arrives",
        "made a plan to", "waiting for", "been watching", "been sitting",
    ],
    # "nothing matters anymore" used about a job/career, not life itself
    ("suicidality", "nothing matters anymore"): [
        "nothing matters anymore at", "nothing matters anymore in my current",
        "nothing matters anymore in this job", "nothing matters anymore about this",
        "nothing matters anymore about the job", "nothing matters anymore about work",
    ],
    # "end it all" — ending a relationship rather than life
    ("suicidality", "end it all"): [
        "end it with", "end it and", "end it between",
    ],
    # "can't go on" — about a relationship ending, not life
    ("suicidality", "can't go on"): [
        "break up", "breaking up", "end the relationship", "leave him", "leave her", "leave them",
    ],
    # treatment_plan — common phrases that overlap with clinical language
    ("treatment_plan", "started taking"): [
        "taking piano", "taking guitar", "taking violin", "taking dance",
        "taking art", "taking cooking", "taking photography",
        "taking lessons", "taking classes", "taking a class",
        "taking a course", "taking yoga", "taking swimming",
        # exercise / non-medication contexts
        "taking a walk", "taking walks", "taking a thirty", "taking a twenty",
        "taking a ten", "taking a fifteen", "taking a forty", "taking a sixty",
        "taking a short", "taking a long", "taking a morning", "taking an evening",
        "taking a daily", "taking a brisk",
    ],
    ("treatment_plan", "new medication"): [
        # medication working well — not a gap
        "medication is working", "medication works", "medication has been working",
        "happy with the", "happy with how", "staying on", "stay on the same",
        "same dose", "same dosage", "no changes", "psychiatrist is happy",
        "doctor is happy", "she's happy", "he's happy",
        # compliance / positive-outcome contexts
        "alongside the medication", "following her advice", "following his advice",
        "following their advice", "following doctor", "following my doctor",
        "following the plan", "following her recommendation", "following his recommendation",
    ],
    ("duty_to_warn", "carrying it"): [
        # emotional carrying idioms
        "carrying it well", "carrying it with", "carrying it forward",
        "carrying it into", "carrying it around with me emotionally",
        "still carrying it", "been carrying it with me",
        "been carrying it alone", "carrying it alone", "carrying it by myself",
        "carrying it on my own", "carrying it together",
    ],
    ("suicidality", "want to die"): [
        # explicit negations — patient is denying the thought
        "don't want to die", "do not want to die", "i don't want to die",
        "i do not want to die", "never wanted to die", "i never wanted to die",
        "i don't want that", "not wanting to die",
    ],
    ("duty_to_warn", "same spot"): [
        # innocent context: someone else parks in the same spot, general location description
        "same spot as always", "same spot for years",
    ],
    ("treatment_plan", "haven't been sleeping"): [
        "sleeping on the couch", "sleeping on the floor",
        "sleeping in the guest", "sleeping at my",
        "sleeping over at", "sleeping bag",
    ],
    ("treatment_plan", "haven't been eating"): [
        "eating at that", "eating at the", "eating there",
        "eating out much", "eating out lately",
        "eating breakfast", "eating lunch", "eating dinner",
    ],
}


SEVERITY_MAP = {
    "suicidality": "HIGH",
    "duty_to_warn": "HIGH",
    "mandatory_reporting": "HIGH",
    "informed_consent": "MEDIUM",
    "crisis_resources": "MEDIUM",
    "treatment_plan": "LOW",
}


CATEGORY_DISPLAY_NAMES = {
    "suicidality": "Suicidality Assessment",
    "duty_to_warn": "Duty to Warn / Tarasoff",
    "mandatory_reporting": "Mandatory Reporting",
    "informed_consent": "Informed Consent",
    "crisis_resources": "Crisis Resource Provision",
    "treatment_plan": "Treatment Plan & Documentation",
}
