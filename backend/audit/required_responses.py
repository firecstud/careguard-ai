"""
Required therapist responses for each liability category.
If a trigger phrase is detected, the therapist MUST say something like these
within the next N utterances (default N=5).
"""

REQUIRED_RESPONSES = {
    "suicidality": [
        "are you thinking about",
        "do you have a plan",
        "have you thought about how",
        "safety plan",
        "988",
        "crisis line",
        "thoughts of suicide",
        "hurting yourself",
        "risk assessment",
        "ideation",
        "intent",
        "means",
    ],
    "duty_to_warn": [
        "I have to take that seriously",
        "I'm obligated",
        "I may need to",
        "contact authorities",
        "warn",
        "law enforcement",
        "duty to warn",
        "Tarasoff",
    ],
    "mandatory_reporting": [
        "I'm required to report",
        "mandated reporter",
        "I need to make a report",
        "child protective",
        "adult protective",
        "reporting obligation",
    ],
    "informed_consent": [
        "confidential",
        "limits of confidentiality",
        "exceptions",
        "emergency procedures",
        "crisis contact",
    ],
    "crisis_resources": [
        "988",
        "crisis line",
        "hotline",
        "emergency contact",
        "someone you can call",
        "crisis center",
        "Suicide & Crisis Lifeline",
    ],
    "treatment_plan": [
        "let's talk about",
        "next steps",
        "treatment plan",
        "goals",
        "follow up",
        "next appointment",
    ],
}
