"""Scripted scenario for CHW Copilot demo (offline, deterministic)."""

from __future__ import annotations

GUIDELINE_STAGES = [
    "Memory Map",
    "Danger Signs",
    "Breathing",
    "Triage",
    "Referral Packet",
    "Follow-up",
]

SCENARIO_STEPS = [
    {
        "id": 0,
        "speaker": "SYSTEM",
        "trace": "Memory Map",
        "text": "Morning route. Offline village. Many households to visit. Let's review follow-ups.",
    },
    {
        "id": 1,
        "speaker": "SYSTEM",
        "trace": "Memory Map",
        "text": "Select an urgent follow-up child to review history.",
    },
    {
        "id": 2,
        "speaker": "CHW",
        "trace": "Danger Signs",
        "text": "No internet here. The 2-year-old still has fever and cough. The caregiver says the child is very tired.",
        "updates": {
            "age_months": 24,
            "symptoms": ["fever", "cough", "lethargy"],
        },
    },
    {
        "id": 3,
        "speaker": "COPILOT",
        "trace": "Danger Signs",
        "text": "I can work offline. We'll follow a guideline-based triage flow. First: general danger signs.",
    },
    {
        "id": 4,
        "speaker": "COPILOT",
        "trace": "Danger Signs",
        "text": "Any seizures now or earlier today?",
    },
    {
        "id": 5,
        "speaker": "CHW",
        "trace": "Danger Signs",
        "text": "No seizures.",
        "updates": {"seizures": False},
    },
    {
        "id": 6,
        "speaker": "COPILOT",
        "trace": "Danger Signs",
        "text": "Unable to drink/breastfeed, or vomiting everything?",
    },
    {
        "id": 7,
        "speaker": "CHW",
        "trace": "Danger Signs",
        "text": "Still hard to drink. Vomited after water.",
        "updates": {
            "unable_to_drink": True,
            "vomiting_everything": True,
            "danger_sign": True,
        },
    },
    {
        "id": 8,
        "speaker": "COPILOT",
        "trace": "Breathing",
        "text": "That's a danger sign. Next: breathing assessment.",
    },
    {
        "id": 9,
        "speaker": "COPILOT",
        "trace": "Breathing",
        "text": "Count breaths for 1 minute. (Demo timer)",
        "ui_event": "show_timer",
        "timer_seconds": 5,
    },
    {
        "id": 10,
        "speaker": "CHW",
        "trace": "Breathing",
        "text": "Respiratory rate is 52 per minute.",
        "updates": {"rr": 52},
    },
    {
        "id": 11,
        "speaker": "COPILOT",
        "trace": "Breathing",
        "text": "Fast breathing for age. Do you see chest indrawing?",
    },
    {
        "id": 12,
        "speaker": "CHW",
        "trace": "Breathing",
        "text": "Yes.",
        "updates": {"chest_indrawing": True},
    },
    {
        "id": 13,
        "speaker": "COPILOT",
        "trace": "Triage",
        "text": "Structured summary:\n- danger sign: unable to drink / vomiting\n- RR 52\n- chest indrawing: yes",
        "triage_update": {
            "classification": "URGENT REFERRAL",
            "color": "red",
            "reasons": ["Danger sign present", "Respiratory distress"],
        },
    },
    {
        "id": 14,
        "speaker": "COPILOT",
        "trace": "Follow-up",
        "text": (
            "Next actions:\n"
            "- Arrange transport / referral now.\n"
            "- Keep the child warm and monitored.\n"
            "- Provide pre-referral care per local protocol and supervisor direction.\n"
            "- Prepare handoff notes.\n\n"
            "Caregiver message: Your child may be very sick. We need to go to the clinic/hospital now."
        ),
        "next_actions": [
            "Arrange transport / referral now.",
            "Keep the child warm and monitored.",
            "Provide pre-referral care per local protocol and supervisor direction.",
            "Prepare handoff notes.",
        ],
        "caregiver_message": "Your child may be very sick. We need to go to the clinic/hospital now.",
    },
    {
        "id": 15,
        "speaker": "COPILOT",
        "trace": "Referral Packet",
        "text": (
            "Referral Packet (SBAR):\n"
            "Situation: 2-year-old, fever+cough, lethargic, offline village\n"
            "Background: onset today, unable to drink, vomiting, RR 52, chest indrawing\n"
            "Assessment: urgent referral needed\n"
            "Recommendation: immediate evaluation at facility"
        ),
        "ui_event": "show_referral",
        "referral_packet": (
            "Situation: 2-year-old, fever+cough, lethargic, offline village\n"
            "Background: onset today, unable to drink, vomiting, RR 52, chest indrawing\n"
            "Assessment: urgent referral needed\n"
            "Recommendation: immediate evaluation at facility"
        ),
    },
    {
        "id": 16,
        "speaker": "COPILOT",
        "trace": "Follow-up",
        "text": "Compared to the last visit: RR 58 → 52 (improving), but danger signs persist.",
        "updates": {"rr_delta": -6, "trend": "improving_but_high_risk"},
    },
    {
        "id": 17,
        "speaker": "SYSTEM",
        "trace": "Follow-up",
        "text": "On-device: simulated • TTFT: 0.9s (mock) • 12 tok/s (mock) • No data leaves device (simulated)\nDemo complete ✅",
        "ui_event": "show_metrics",
        "metrics": [
            "On-device: simulated",
            "TTFT: 0.9s (mock)",
            "12 tok/s (mock)",
            "No data leaves device (simulated)",
        ],
    },
]
