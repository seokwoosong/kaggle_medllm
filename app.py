
from __future__ import annotations

import math
import random
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import folium
import streamlit as st
from streamlit_folium import st_folium

from assets.patients import PATIENTS, get_patient_by_id
from assets.scenario import SCENARIO_STEPS

APP_TABS = ["Home", "Triage", "Handoff"]
TRIAGE_STAGES = ["Danger Signs", "Breathing", "Triage", "Referral Packet", "Follow-up"]
HOME_FILTERS = ["All", "Urgent", "Due today", "New visits", "Overdue"]
WORKLOAD_KPIS = [
    ("Assigned households", "145"),
    ("Follow-ups due this week", "28"),
    ("Due today", "12"),
    ("Urgent today", "2"),
    ("Showing", "Top 6 (prioritized)"),
]


def load_css() -> None:
    css = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def badge(text: str, color: str) -> str:
    return f"<span class='pill pill-{color}'>{text}</span>"


def status_color(status: str) -> str:
    if status == "urgent follow-up":
        return "red"
    if status == "normal follow-up":
        return "yellow"
    return "blue"


def default_patient_state(patient: dict[str, Any]) -> dict[str, Any]:
    return {
        "patient_id": patient["id"],
        "age_months": patient.get("age_months"),
        "symptoms": [],
        "seizures": None,
        "unable_to_drink": None,
        "vomiting_everything": None,
        "danger_sign": False,
        "rr": None,
        "chest_indrawing": None,
        "rr_delta": None,
        "trend": None,
        "last_visit_summary": patient.get("last_visit_summary"),
    }


def initial_triage() -> dict[str, Any]:
    return {
        "classification": "Pending",
        "color": "yellow",
        "reasons": ["Awaiting guideline steps"],
    }


def generate_dummy_patients(base_patients: list[dict[str, Any]], n: int = 18, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    ref_date = date(2026, 2, 14)

    first_names = [
        "Safa",
        "Imani",
        "Kito",
        "Ayo",
        "Nia",
        "Tari",
        "Mosi",
        "Zuri",
        "Kena",
        "Lela",
        "Pendo",
        "Ari",
        "Jabari",
        "Nala",
        "Rafi",
        "Tamu",
        "Eshe",
        "Moyo",
    ]
    last_initials = [
        "Q.", "W.", "E.", "R.", "T.", "Y.", "U.", "I.", "O.",
        "P.", "A.", "S.", "D.", "F.", "G.", "H.", "J.", "K.",
    ]
    avatars = ["🧒", "👦", "👧", "🧑", "👶"]

    dummies: list[dict[str, Any]] = []
    categories = ["due_today", "overdue", "new_visit", "due_week"]
    weights = [0.35, 0.30, 0.20, 0.15]

    for i in range(n):
        template = base_patients[i % len(base_patients)]
        due_category = rng.choices(categories, weights=weights, k=1)[0]

        overdue_days = rng.randint(1, 5) if due_category == "overdue" else 0
        is_new = due_category == "new_visit"
        due_today = due_category == "due_today"
        due_this_week = due_category in {"due_today", "overdue", "due_week"}
        follow_up_due = due_this_week

        urgent = (due_category in {"overdue", "due_today"} and rng.random() < 0.38) or (i % 11 == 0)
        status = "urgent follow-up" if urgent else ("new visit" if is_new else "normal follow-up")

        rr_last = None if is_new else rng.randint(34, 62)
        rr_curr = None if rr_last is None else max(26, rr_last + rng.randint(-7, 4))

        if is_new:
            last_visit_date = None
            last_visit_summary = "No prior visit. New household in catchment."
            last_visit_fields: dict[str, Any] = {}
            current_seed: dict[str, Any] = {}
        else:
            last_visit_date = (ref_date - timedelta(days=rng.randint(1, 12))).isoformat()
            danger_last = urgent and rng.random() < 0.55
            indrawing_last = urgent and rng.random() < 0.45
            last_visit_summary = (
                "Recent respiratory follow-up. "
                "Continue close reassessment based on local protocol."
            )
            last_visit_fields = {
                "rr": rr_last,
                "danger_sign": danger_last,
                "unable_to_drink": danger_last,
                "vomiting_everything": danger_last and rng.random() < 0.5,
                "chest_indrawing": indrawing_last,
            }
            current_seed = {
                "rr": rr_curr,
                "danger_sign": danger_last if due_category != "due_week" else False,
                "unable_to_drink": danger_last and rng.random() < 0.75,
                "vomiting_everything": danger_last and rng.random() < 0.45,
                "chest_indrawing": indrawing_last and rng.random() < 0.7,
            }

        protocol_followup_due = follow_up_due or urgent
        facility_referral_pending = urgent or (due_category == "overdue" and rng.random() < 0.5)

        name = f"{first_names[i % len(first_names)]} {last_initials[i % len(last_initials)]}"
        lat = template["lat"] + rng.uniform(-0.0125, 0.0125)
        lon = template["lon"] + rng.uniform(-0.0125, 0.0125)

        dummies.append(
            {
                "id": f"d{i + 1:03d}",
                "pseudonym": name,
                "age_months": rng.randint(8, 48),
                "avatar": avatars[i % len(avatars)],
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "last_visit_date": last_visit_date,
                "last_visit_summary": last_visit_summary,
                "last_visit_fields": last_visit_fields,
                "current_visit_seed": current_seed,
                "follow_up_due": follow_up_due,
                "status": status,
                "due_category": due_category,
                "overdue_days": overdue_days,
                "due_today": due_today,
                "due_this_week": due_this_week,
                "facility_referral_pending": facility_referral_pending,
                "protocol_followup_due": protocol_followup_due,
                "is_dummy": True,
            }
        )

    return dummies


def all_patients() -> list[dict[str, Any]]:
    return PATIENTS + st.session_state.dummy_patients


def get_patient_by_id_any(patient_id: str) -> dict[str, Any] | None:
    real = get_patient_by_id(patient_id)
    if real:
        return real
    for patient in st.session_state.dummy_patients:
        if patient["id"] == patient_id:
            return patient
    return None

def patient_meta(patient: dict[str, Any]) -> dict[str, Any]:
    due_category = patient.get("due_category")
    overdue_days = int(patient.get("overdue_days", 0) or 0)

    is_new = bool(patient.get("status") == "new visit" or patient.get("last_visit_date") is None or due_category == "new_visit")
    is_urgent = patient.get("status") == "urgent follow-up"

    if due_category == "due_today":
        due_today = True
    elif due_category == "overdue":
        due_today = False
    else:
        due_today = bool(patient.get("follow_up_due", False) and not is_new and overdue_days == 0)

    overdue = due_category == "overdue" or overdue_days > 0
    due_this_week = bool(patient.get("due_this_week", patient.get("follow_up_due", False) or due_today or overdue))

    protocol_due = bool(patient.get("protocol_followup_due", patient.get("follow_up_due", False) or due_today or overdue))
    referral_pending = bool(patient.get("facility_referral_pending", is_urgent))

    return {
        "is_new": is_new,
        "is_urgent": is_urgent,
        "due_today": due_today,
        "overdue": overdue,
        "overdue_days": overdue_days,
        "due_this_week": due_this_week,
        "protocol_due": protocol_due,
        "referral_pending": referral_pending,
    }


def patient_badges(patient: dict[str, Any]) -> list[tuple[str, str]]:
    meta = patient_meta(patient)
    badges: list[tuple[str, str]] = []

    if meta["overdue"]:
        badges.append((f"Overdue {meta['overdue_days']} days", "red"))
    if meta["referral_pending"]:
        badges.append(("Facility referral pending", "yellow"))
    if meta["protocol_due"]:
        badges.append(("Follow-up due (per local protocol)", "blue"))
    if meta["is_new"] and not badges:
        badges.append(("New visit", "gray"))

    return badges


def patient_priority(patient: dict[str, Any]) -> int:
    meta = patient_meta(patient)
    score = 0

    if meta["is_urgent"]:
        score += 80
    if meta["overdue"]:
        score += 60 + min(meta["overdue_days"], 7)
    if meta["due_today"]:
        score += 40
    if meta["due_this_week"]:
        score += 20
    if meta["referral_pending"]:
        score += 14
    if meta["protocol_due"]:
        score += 8
    if meta["is_new"]:
        score += 4

    return score


def matches_home_filter(patient: dict[str, Any], filter_name: str) -> bool:
    meta = patient_meta(patient)

    if filter_name == "Urgent":
        return meta["is_urgent"]
    if filter_name == "Due today":
        return meta["due_today"]
    if filter_name == "New visits":
        return meta["is_new"]
    if filter_name == "Overdue":
        return meta["overdue"]
    return True


def ordered_home_patients(filter_name: str) -> tuple[list[dict[str, Any]], bool]:
    ranked = sorted(all_patients(), key=lambda p: (-patient_priority(p), p["pseudonym"]))

    if filter_name == "All":
        return ranked, False

    matched = [patient for patient in ranked if matches_home_filter(patient, filter_name)]
    matched_ids = {patient["id"] for patient in matched}
    remainder = [patient for patient in ranked if patient["id"] not in matched_ids]
    fill_used = len(matched) < 6

    return matched + remainder, fill_used


def reset_demo_state(keep_patient: bool = True) -> None:
    selected = st.session_state.selected_patient_id if keep_patient else PATIENTS[0]["id"]
    patient = get_patient_by_id_any(selected) or all_patients()[0]

    st.session_state.selected_patient_id = patient["id"]
    st.session_state.step_idx = -1
    st.session_state.messages = []
    st.session_state.patient_state = default_patient_state(patient)
    st.session_state.guideline_trace_step = "Memory Map"
    st.session_state.triage_result = initial_triage()
    st.session_state.demo_running = False
    st.session_state.demo_complete = False
    st.session_state.next_actions = []
    st.session_state.caregiver_message = ""
    st.session_state.referral_packet = ""
    st.session_state.show_referral = False
    st.session_state.show_metrics = False
    st.session_state.metrics_badges = []
    st.session_state.timer_end = None


def ensure_state() -> None:
    if "dummy_patients" not in st.session_state:
        st.session_state.dummy_patients = generate_dummy_patients(PATIENTS, n=18, seed=42)

    if "selected_patient_id" not in st.session_state:
        st.session_state.selected_patient_id = PATIENTS[0]["id"]

    all_ids = {patient["id"] for patient in all_patients()}
    if st.session_state.selected_patient_id not in all_ids:
        st.session_state.selected_patient_id = PATIENTS[0]["id"]

    if "compare_patient_a_id" not in st.session_state:
        st.session_state.compare_patient_a_id = PATIENTS[0]["id"]
    if "compare_patient_b_id" not in st.session_state:
        st.session_state.compare_patient_b_id = PATIENTS[1]["id"]
    if "speed" not in st.session_state:
        st.session_state.speed = 0.6
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Home"
    if "home_filter" not in st.session_state:
        st.session_state.home_filter = "All"
    if "home_show_more" not in st.session_state:
        st.session_state.home_show_more = False
    if "step_idx" not in st.session_state:
        reset_demo_state(keep_patient=True)


def set_active_tab(tab: str) -> None:
    if tab not in APP_TABS:
        return
    st.session_state.active_tab = tab
    st.rerun()


def generate_copilot_reply(context: dict[str, Any]) -> str:
    """Placeholder for future MedGemma integration.

    This demo intentionally returns scripted text only.
    """
    return context.get("text", "")


def role_for_speaker(speaker: str) -> str:
    return "user" if speaker == "CHW" else "assistant"


def apply_step(step: dict[str, Any]) -> None:
    text = step.get("text", "")
    if step.get("speaker") == "COPILOT":
        text = generate_copilot_reply(step)

    st.session_state.messages.append(
        {
            "speaker": step["speaker"],
            "text": text,
            "trace": step.get("trace", st.session_state.guideline_trace_step),
        }
    )

    st.session_state.guideline_trace_step = step.get("trace", st.session_state.guideline_trace_step)

    for key, value in step.get("updates", {}).items():
        st.session_state.patient_state[key] = value

    if step.get("triage_update"):
        st.session_state.triage_result = step["triage_update"]

    if step.get("next_actions"):
        st.session_state.next_actions = step["next_actions"]

    if step.get("caregiver_message"):
        st.session_state.caregiver_message = step["caregiver_message"]

    if step.get("referral_packet"):
        st.session_state.referral_packet = step["referral_packet"]

    ui_event = step.get("ui_event")
    if ui_event == "show_timer":
        st.session_state.timer_end = time.time() + float(step.get("timer_seconds", 5))
    elif ui_event == "show_referral":
        st.session_state.show_referral = True
    elif ui_event == "show_metrics":
        st.session_state.show_metrics = True
        st.session_state.metrics_badges = step.get("metrics", [])

    if step["id"] == SCENARIO_STEPS[-1]["id"]:
        st.session_state.demo_complete = True
        st.session_state.demo_running = False

    st.session_state.step_idx += 1

def timer_active() -> bool:
    end = st.session_state.timer_end
    return bool(end and time.time() < end)


def typing_delay(speed: float) -> float:
    return max(0.3, min(0.8, speed))


def maybe_apply_next_step() -> str:
    next_idx = st.session_state.step_idx + 1
    if next_idx >= len(SCENARIO_STEPS):
        st.session_state.demo_complete = True
        st.session_state.demo_running = False
        return "done"

    step = SCENARIO_STEPS[next_idx]

    # Wait for demo timer before applying RR step.
    if step["id"] == 10 and timer_active():
        return "wait_timer"

    if step["speaker"] == "COPILOT":
        with st.spinner("Copilot is typing..."):
            time.sleep(typing_delay(st.session_state.speed))

    apply_step(step)
    return "applied"


def compute_deltas(last_fields: dict[str, Any], current_fields: dict[str, Any]) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    rr_last = last_fields.get("rr") if last_fields else None
    rr_curr = current_fields.get("rr")
    if rr_last is not None and rr_curr is not None:
        deltas["rr_delta"] = rr_curr - rr_last
    else:
        deltas["rr_delta"] = None

    for key in ["danger_sign", "unable_to_drink", "vomiting_everything", "chest_indrawing"]:
        if last_fields and key in last_fields and current_fields.get(key) is not None:
            deltas[key] = f"{last_fields.get(key)} -> {current_fields.get(key)}"
        else:
            deltas[key] = "n/a"
    return deltas


def bool_text(value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Unknown"


def current_patient() -> dict[str, Any]:
    return get_patient_by_id_any(st.session_state.selected_patient_id) or all_patients()[0]


def render_phone_header() -> None:
    st.markdown(
        (
            "<div class='phone-header-wrap'>"
            "<div class='phone-notch'></div>"
            "<div class='phone-topbar'><span>10:28</span><span>VoLTE  5G  87%</span></div>"
            "<div class='phone-header'>"
            "<div class='status-row'>"
            + badge("No Signal", "gray")
            + badge("Offline Mode", "gray")
            + badge("On-device (simulated)", "blue")
            + "</div>"
            "<div class='status-row'>"
            + badge("DEMO ONLY", "red")
            + badge("Not medical advice", "red")
            + badge("Guideline-based support concept", "yellow")
            + "</div></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_workload_kpis() -> None:
    cards = []
    for idx, (label, value) in enumerate(WORKLOAD_KPIS):
        full = " kpi-card-full" if idx == len(WORKLOAD_KPIS) - 1 else ""
        cards.append(
            "<div class='kpi-card" + full + "'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            "</div>"
        )

    st.markdown("<div class='workload-kpi-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_home_filters() -> None:
    st.markdown("### Prioritization Filters")
    cols = st.columns(len(HOME_FILTERS))

    for idx, option in enumerate(HOME_FILTERS):
        with cols[idx]:
            button_type = "primary" if st.session_state.home_filter == option else "secondary"
            if st.button(option, key=f"home_filter_{option}", use_container_width=True, type=button_type):
                if st.session_state.home_filter != option:
                    st.session_state.home_filter = option
                    st.session_state.home_show_more = False
                    st.rerun()


def followup_item(patient: dict[str, Any], rank: int, is_top_priority: bool) -> None:
    selected_cls = "selected" if patient["id"] == st.session_state.selected_patient_id else ""
    rank_cls = "top-rank" if is_top_priority else "extra-rank"
    st.markdown(f"<div class='followup-item {selected_cls}'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 5, 2])
    with c1:
        st.markdown(f"<div class='avatar'>{patient['avatar']}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<span class='rank-pill {rank_cls}'>#{rank}</span> **{patient['pseudonym']}**", unsafe_allow_html=True)
        date_text = patient.get("last_visit_date") or "No prior visit"
        st.caption(f"Last visit: {date_text}")
        badges_html = "".join(badge(text, color) for text, color in patient_badges(patient))
        if badges_html:
            st.markdown(f"<div class='patient-badge-row'>{badges_html}</div>", unsafe_allow_html=True)

    with c3:
        st.markdown(badge(patient["status"], status_color(patient["status"])), unsafe_allow_html=True)
        if st.button("Select", key=f"select_{patient['id']}", use_container_width=True):
            st.session_state.selected_patient_id = patient["id"]
            reset_demo_state(keep_patient=True)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def nearest_patient(lat: float, lon: float, patients: list[dict[str, Any]]) -> str | None:
    best_id = None
    best_dist = 999.0
    for patient in patients:
        dist = math.hypot(patient["lat"] - lat, patient["lon"] - lon)
        if dist < best_dist:
            best_dist = dist
            best_id = patient["id"]
    if best_dist < 0.012:
        return best_id
    return None

def render_map(map_patients: list[dict[str, Any]], highlighted_ids: set[str]) -> None:
    st.markdown("### Memory Map")
    st.caption(f"Catchment view: {len(map_patients)} households. Highlighted markers are the current Top 6.")

    center_lat = sum(p["lat"] for p in map_patients) / len(map_patients)
    center_lon = sum(p["lon"] for p in map_patients) / len(map_patients)

    try:
        fmap = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles="OpenStreetMap",
            control_scale=False,
            prefer_canvas=True,
        )

        for patient in map_patients:
            is_selected = patient["id"] == st.session_state.selected_patient_id
            is_highlighted = patient["id"] in highlighted_ids

            if is_selected:
                border = "#b32020"
                size = 30
                opacity = 1.0
            elif is_highlighted:
                border = "#2e5b88"
                size = 26
                opacity = 0.96
            else:
                border = "#97a8ba"
                size = 20
                opacity = 0.78

            summary_badges = patient_badges(patient)
            badge_preview = summary_badges[0][0] if summary_badges else "Routine check"
            popup = f"{patient['avatar']} {patient['pseudonym']} ({patient['status']})<br/>{badge_preview}"
            icon_html = (
                f"<div style='width:{size}px;height:{size}px;border-radius:50%;"
                f"border:3px solid {border};background:#fff9f1;display:flex;opacity:{opacity};"
                "align-items:center;justify-content:center;font-size:14px;'>"
                f"{patient['avatar']}</div>"
            )
            folium.Marker(
                location=[patient["lat"], patient["lon"]],
                tooltip=patient["pseudonym"],
                popup=popup,
                icon=folium.DivIcon(html=icon_html),
            ).add_to(fmap)

        map_key = (
            f"map_{st.session_state.selected_patient_id}_"
            f"{st.session_state.home_filter}_{int(st.session_state.home_show_more)}"
        )
        data = st_folium(fmap, width=350, height=260, key=map_key)
        clicked = data.get("last_object_clicked") if isinstance(data, dict) else None
        if clicked and clicked.get("lat") is not None and clicked.get("lng") is not None:
            candidate = nearest_patient(clicked["lat"], clicked["lng"], map_patients)
            if candidate and candidate != st.session_state.selected_patient_id:
                st.session_state.selected_patient_id = candidate
                reset_demo_state(keep_patient=True)
                st.rerun()
    except Exception:
        st.warning("Map rendering fallback: showing catchment table.")
        st.dataframe(
            [
                {
                    "patient": p["pseudonym"],
                    "status": p["status"],
                    "lat": p["lat"],
                    "lon": p["lon"],
                }
                for p in map_patients
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_last_visit_summary(patient: dict[str, Any]) -> None:
    st.markdown("### Last Visit Summary")
    date_text = patient.get("last_visit_date") or "No prior visit"
    summary = patient.get("last_visit_summary") or "No prior visit summary"
    badges_html = "".join(badge(text, color) for text, color in patient_badges(patient))

    st.markdown(
        (
            "<div class='summary-card'>"
            f"<strong>{patient['pseudonym']}</strong><br/>"
            f"Last visit: {date_text}<br/>"
            f"{summary}"
            f"<div class='patient-badge-row'>{badges_html}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_patient_card(patient: dict[str, Any]) -> None:
    p = st.session_state.patient_state
    with st.expander("Patient Card (Structured)", expanded=True):
        st.markdown(f"- Pseudonym: **{patient['pseudonym']}**")
        st.markdown(f"- Age (months): **{p.get('age_months') or patient.get('age_months') or '-'}**")
        st.markdown(f"- Symptoms: **{', '.join(p.get('symptoms') or []) or '-'}**")
        st.markdown(f"- Danger sign: **{bool_text(p.get('danger_sign'))}**")
        st.markdown(f"- RR: **{p.get('rr') if p.get('rr') is not None else '-'}**")
        st.markdown(f"- Chest indrawing: **{bool_text(p.get('chest_indrawing'))}**")
        st.markdown(f"- Last visit summary: **{patient.get('last_visit_summary') or 'No prior visit'}**")


def render_guideline_trace() -> None:
    with st.expander("Guideline Trace", expanded=True):
        chips = []
        active_trace = st.session_state.guideline_trace_step
        for stage in TRIAGE_STAGES:
            active = "active" if stage == active_trace else ""
            chips.append(f"<span class='trace-chip {active}'>{stage}</span>")
        st.markdown("".join(chips), unsafe_allow_html=True)


def render_chat() -> None:
    st.markdown("### CHW Copilot Chat")

    for message in st.session_state.messages:
        role = role_for_speaker(message["speaker"])
        avatar = "🧑‍⚕️" if message["speaker"] == "CHW" else ("🤖" if message["speaker"] == "COPILOT" else "🧭")
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["text"])

    if timer_active() and st.session_state.step_idx >= 9:
        remaining = max(0, int(math.ceil(st.session_state.timer_end - time.time())))
        st.info(f"Breathing timer (simulated): {remaining}s remaining")
        progress = (5 - min(5, remaining)) / 5
        st.progress(progress)

    if st.session_state.demo_complete:
        st.success("Demo complete")


def render_triage_controls() -> None:
    st.markdown("<div class='triage-controls-wrap'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Play demo", use_container_width=True, key="triage_play"):
            st.session_state.demo_running = True
            st.rerun()
    with c2:
        if st.button("Next step", use_container_width=True, key="triage_next"):
            result = maybe_apply_next_step()
            if result == "wait_timer":
                st.info("Timer running. Next step unlocks when timer completes.")
            st.rerun()
    with c3:
        if st.button("Reset", use_container_width=True, key="triage_reset"):
            reset_demo_state(keep_patient=True)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_triage_result() -> None:
    triage = st.session_state.triage_result
    color_cls = {
        "red": "triage-red",
        "yellow": "triage-yellow",
        "green": "triage-green",
    }.get(triage.get("color", "yellow"), "triage-yellow")
    reasons = "<br/>".join(f"- {r}" for r in triage.get("reasons", []))
    st.markdown(
        (
            f"<div class='triage-card {color_cls}'>"
            f"Classification: {triage.get('classification', 'Pending')}<br/>"
            f"Reasons:<br/>{reasons}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_next_actions() -> None:
    actions = st.session_state.next_actions
    if actions:
        for item in actions:
            st.checkbox(item, value=False, disabled=True)
    else:
        st.caption("Checklist appears in Act 2.")


def render_referral_packet() -> None:
    if st.session_state.show_referral and st.session_state.referral_packet:
        st.code(st.session_state.referral_packet, language="text")
        if st.button("Copy referral summary (manual copy)", use_container_width=True, key="copy_sbar"):
            st.toast("Copy manually from the SBAR text box.")
    else:
        st.caption("Referral packet appears at Step 15.")


def render_continuity_block(patient: dict[str, Any]) -> None:
    p = st.session_state.patient_state
    last_fields = patient.get("last_visit_fields", {})
    delta = compute_deltas(last_fields, p)

    st.markdown("### Continuity & History")
    st.markdown("**Last visit vs current visit**")
    st.write(
        {
            "RR last": last_fields.get("rr"),
            "RR current": p.get("rr"),
            "danger_sign last": last_fields.get("danger_sign"),
            "danger_sign current": p.get("danger_sign"),
            "chest_indrawing last": last_fields.get("chest_indrawing"),
            "chest_indrawing current": p.get("chest_indrawing"),
        }
    )

    rr_last = last_fields.get("rr")
    rr_curr = p.get("rr")
    if rr_last is not None and rr_curr is not None:
        st.info(f"Delta: RR {rr_last} -> {rr_curr} ({rr_curr - rr_last:+d})")
    else:
        st.info("Delta: RR data not complete yet.")

    st.caption(f"Detail deltas: {delta}")

    if p.get("danger_sign"):
        st.warning("Follow-up reminder: danger signs persist, keep urgent follow-up active.")


def render_top_nav() -> None:
    st.markdown("<div class='top-nav-wrap'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "Home",
            key="tab_home_top",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Home" else "secondary",
        ):
            set_active_tab("Home")
    with c2:
        if st.button(
            "Triage",
            key="tab_triage_top",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Triage" else "secondary",
        ):
            set_active_tab("Triage")
    with c3:
        if st.button(
            "Handoff",
            key="tab_handoff_top",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Handoff" else "secondary",
        ):
            set_active_tab("Handoff")

    st.markdown("</div>", unsafe_allow_html=True)


def render_bottom_nav() -> None:
    st.markdown("<div class='bottom-nav-wrap'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button(
            "Home",
            key="tab_home",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Home" else "secondary",
        ):
            set_active_tab("Home")
    with c2:
        if st.button(
            "Triage",
            key="tab_triage",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Triage" else "secondary",
        ):
            set_active_tab("Triage")
    with c3:
        if st.button(
            "Handoff",
            key="tab_handoff",
            use_container_width=True,
            type="primary" if st.session_state.active_tab == "Handoff" else "secondary",
        ):
            set_active_tab("Handoff")

    st.markdown("</div>", unsafe_allow_html=True)


def score_urgency(patient: dict[str, Any], current_fields: dict[str, Any] | None = None) -> int:
    score = 0
    if patient.get("status") == "urgent follow-up":
        score += 2
    fields = current_fields or patient.get("current_visit_seed", {})
    if fields.get("danger_sign"):
        score += 2
    if fields.get("chest_indrawing"):
        score += 1
    if (fields.get("rr") or 0) >= 50:
        score += 1
    return score


def mini_compare_card(patient: dict[str, Any], title: str, current_override: dict[str, Any] | None = None) -> None:
    last = patient.get("last_visit_fields", {})
    current = current_override if current_override is not None else patient.get("current_visit_seed", {})
    st.markdown(f"**{title}: {patient['pseudonym']}**")

    if not patient.get("last_visit_date"):
        st.caption("No prior visit")
    else:
        st.caption(f"Last visit: {patient['last_visit_date']}")

    rr_last = last.get("rr")
    rr_curr = current.get("rr")
    if rr_last is not None and rr_curr is not None:
        rr_delta = rr_curr - rr_last
        rr_delta_text = f"{rr_delta:+d}"
    else:
        rr_delta_text = "n/a"

    st.write(
        {
            "RR last": rr_last,
            "RR current": rr_curr,
            "Delta": rr_delta_text,
            "Danger sign": current.get("danger_sign", "n/a"),
            "Chest indrawing": current.get("chest_indrawing", "n/a"),
        }
    )


def render_compare_view() -> None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Compare Patients")

    options = {p["pseudonym"]: p["id"] for p in PATIENTS}
    name_by_id = {v: k for k, v in options.items()}

    a_name = st.sidebar.selectbox(
        "Patient A",
        list(options.keys()),
        index=list(options.values()).index(st.session_state.compare_patient_a_id),
    )
    b_name = st.sidebar.selectbox(
        "Patient B",
        list(options.keys()),
        index=list(options.values()).index(st.session_state.compare_patient_b_id),
    )

    st.session_state.compare_patient_a_id = options[a_name]
    st.session_state.compare_patient_b_id = options[b_name]

    pa = get_patient_by_id(st.session_state.compare_patient_a_id)
    pb = get_patient_by_id(st.session_state.compare_patient_b_id)
    if not pa or not pb:
        return

    with st.sidebar.expander("Comparison snapshot", expanded=True):
        a_current = st.session_state.patient_state if pa["id"] == st.session_state.selected_patient_id else pa.get("current_visit_seed", {})
        b_current = st.session_state.patient_state if pb["id"] == st.session_state.selected_patient_id else pb.get("current_visit_seed", {})

        col_a, col_b = st.columns(2)
        with col_a:
            mini_compare_card(pa, "A", a_current)
        with col_b:
            mini_compare_card(pb, "B", b_current)

        score_a = score_urgency(pa, a_current)
        score_b = score_urgency(pb, b_current)
        if score_a > score_b:
            hint = f"Most urgent today: {name_by_id[pa['id']]}"
        elif score_b > score_a:
            hint = f"Most urgent today: {name_by_id[pb['id']]}"
        else:
            hint = "Most urgent today: tie (both need close review)"
        st.markdown(badge(hint, "red"), unsafe_allow_html=True)

def render_sidebar_controls() -> None:
    st.sidebar.markdown("## Controls")

    patient_pool = all_patients()
    labels = [f"{p['pseudonym']} ({p['id']})" for p in patient_pool]
    ids = [p["id"] for p in patient_pool]

    if st.session_state.selected_patient_id not in ids:
        st.session_state.selected_patient_id = ids[0]

    selected_label = st.sidebar.selectbox(
        "Patient selector",
        labels,
        index=ids.index(st.session_state.selected_patient_id),
    )
    selected_id = selected_label.split("(")[-1].replace(")", "")

    if selected_id != st.session_state.selected_patient_id:
        st.session_state.selected_patient_id = selected_id
        reset_demo_state(keep_patient=True)
        st.sidebar.info("Patient changed. Scenario reset for this patient.")
        st.rerun()

    st.session_state.speed = st.sidebar.slider("Speed", 0.2, 1.5, float(st.session_state.speed), 0.1)

    if st.sidebar.button("Reset scenario", use_container_width=True):
        reset_demo_state(keep_patient=True)
        st.rerun()

    render_compare_view()


def render_home_tab(patient: dict[str, Any]) -> None:
    render_workload_kpis()
    render_home_filters()

    ordered, fill_used = ordered_home_patients(st.session_state.home_filter)
    top_six = ordered[:6]

    visible_limit = 24 if st.session_state.home_show_more else 6
    visible_patients = ordered[:visible_limit]

    st.markdown("### Top 6 prioritized for today")
    if st.session_state.home_filter != "All" and fill_used:
        st.caption("Not enough matches; showing additional prioritized visits.")

    for idx, listed_patient in enumerate(visible_patients, start=1):
        followup_item(listed_patient, rank=idx, is_top_priority=idx <= 6)

    extra_available = max(0, min(18, len(ordered) - 6))
    if extra_available > 0:
        label = f"Show more (+{extra_available})" if not st.session_state.home_show_more else "Show less"
        if st.button(label, use_container_width=True, key="home_show_more_btn"):
            st.session_state.home_show_more = not st.session_state.home_show_more
            st.rerun()

    highlighted_ids = {p["id"] for p in top_six}
    render_map(all_patients(), highlighted_ids=highlighted_ids)

    render_last_visit_summary(current_patient())

    if st.button("Start Triage", use_container_width=True, key="start_triage"):
        reset_demo_state(keep_patient=True)
        st.session_state.active_tab = "Triage"
        st.rerun()


def render_triage_tab(patient: dict[str, Any]) -> None:
    render_guideline_trace()
    render_patient_card(patient)
    render_chat()
    render_triage_controls()

    if st.session_state.demo_complete:
        if st.button("Go to Handoff", use_container_width=True, key="go_handoff"):
            set_active_tab("Handoff")


def render_handoff_tab(patient: dict[str, Any]) -> None:
    st.markdown("### Triage Result")
    render_triage_result()

    st.markdown("### Next Actions")
    render_next_actions()

    st.markdown("### Caregiver Message")
    if st.session_state.caregiver_message:
        st.info(st.session_state.caregiver_message)
    else:
        st.caption("Caregiver message appears after triage step 14.")

    st.markdown("### Referral Packet (SBAR)")
    render_referral_packet()

    render_continuity_block(patient)

    if st.session_state.show_metrics and st.session_state.metrics_badges:
        st.markdown("### Edge Metrics (simulated)")
        st.markdown("".join(badge(text, "blue") for text in st.session_state.metrics_badges), unsafe_allow_html=True)

    if st.button("Back to Home", use_container_width=True, key="back_home"):
        set_active_tab("Home")


def render_active_tab(patient: dict[str, Any]) -> None:
    if st.session_state.active_tab == "Home":
        render_home_tab(patient)
    elif st.session_state.active_tab == "Triage":
        render_triage_tab(patient)
    else:
        render_handoff_tab(patient)


def maybe_run_autoplay() -> None:
    if st.session_state.active_tab != "Triage":
        return
    if st.session_state.demo_running and not st.session_state.demo_complete:
        outcome = maybe_apply_next_step()
        if outcome == "wait_timer":
            time.sleep(0.2)
        elif outcome == "applied":
            time.sleep(st.session_state.speed)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="CHW Copilot Demo", page_icon="+", layout="centered")
    load_css()
    ensure_state()

    render_sidebar_controls()

    patient = current_patient()

    render_phone_header()
    render_top_nav()
    render_active_tab(patient)
    render_bottom_nav()

    maybe_run_autoplay()


if __name__ == "__main__":
    main()
