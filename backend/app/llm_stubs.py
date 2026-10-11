"""Canned LLM behaviour for LLM_MODE=stub (tests, offline demo). Deterministic, schema-valid."""

import json

from .llm import Reply, ToolCall, new_call_id, stub

ITEM_WORDS = {"pain": "pain", "fatigue": "tiredness", "mobility": "difficulty moving"}

CATEGORY_LINES = {
    "symptoms": "{name} completed the daily check-in.",
    "medications": "{name}'s medicines were logged today.",
    "vitals": "The home sensor sent readings today.",
    "wound": "{name} shared a wound photo when asked.",
    "alerts": "The care team is reviewing a change today and may call {name}.",
    "rehab": "Exercises are part of today's plan.",
    "appointments": "An appointment is coming up.",
}


@stub("checkin_clarify")
def _clarify(messages, ctx):
    word = ITEM_WORDS.get(ctx.get("item"), ctx.get("item", "this"))
    return {"text": f"Your {word} is higher than at your last check-in. Which best describes it?",
            "options": ["A bit more than usual, but I'm managing",
                        "I need to rest most of the day",
                        "I can hardly get out of bed"]}


@stub("chat")
def _chat(messages, ctx):
    if ctx.get("lang") == "French":
        return ("Je peux vous aider à comprendre votre plan de récupération. Pour toute décision médicale, "
                "parlez-en à votre équipe de soins. (réponse de démonstration)")
    return ("I can help you understand your recovery plan. For any medical decision, please check with your "
            "care team. (demo reply)")


@stub("digest")
def _digest(messages, ctx):
    name = ctx.get("first_name", "The patient")
    cats = []
    for e in ctx.get("events", []):
        if e["category"] not in cats:
            cats.append(e["category"])
    lines = [CATEGORY_LINES[c].format(name=name) for c in cats if c in CATEGORY_LINES][:4]
    summary = " ".join(lines) or f"A quiet day for {name}; nothing new was shared with you today."
    tasks = []
    if "alerts" in cats:
        tasks.append({"text": f"Stay close to {name} this evening and keep the phone nearby.", "category": "alerts"})
    if "medications" in cats:
        tasks.append({"text": f"Remind {name} about the 20:00 medicines.", "category": "medications"})
    return {"summary": summary, "tasks": tasks[:3]}


# ------------------------------------------------------------------ investigation (tool loop)

def _results(messages) -> list[tuple[str, dict]]:
    out = []
    for msg in messages:
        if msg.get("role") == "tool":
            try:
                out.append((msg.get("name"), json.loads(msg.get("content") or "{}")))
            except json.JSONDecodeError:
                out.append((msg.get("name"), {}))
    return out


def _last(results, name, pred=lambda r: True):
    return next((r for n, r in reversed(results) if n == name and pred(r)), None)


def _call(name, args):
    return Reply(content=f"Next: {name}", tool_calls=[ToolCall(new_call_id(), name, args)])


@stub("investigation")
def _investigate(messages, ctx):
    """Scripted but grounded: reads the real tool results and cites their observation ids."""
    res = _results(messages)
    done = [n for n, _ in res]
    flags = ctx.get("flags", [])
    if "never_finish" in flags:
        return _call("get_medication_context", {})
    script = [("get_vitals_trend", {"metric": "hr", "hours": 24}),
              ("get_vitals_trend", {"metric": "temp", "hours": 24}),
              ("get_symptom_checkins", {"days": 3}),
              ("get_medication_context", {}),
              ("get_wound_photos", {"n": 2}),
              ("request_wound_photo", {"reason": "Check the incision for spreading redness"})]
    if len(done) < len(script):
        return _call(*script[len(done)])
    photos = _last(res, "get_wound_photos") or {"photos": []}
    new_photo_id = ((_last(res, "request_wound_photo") or {}).get("answer") or {}).get("observation_id")
    if "compare_wound_photos" not in done and photos["photos"]:
        oldest = photos["photos"][-1]["observation_id"]
        newest = new_photo_id or photos["photos"][0]["observation_id"]
        if oldest != newest:
            return _call("compare_wound_photos", {"photo_id_a": oldest, "photo_id_b": newest})
    if "ask_followup_question" not in done:
        return _call("ask_followup_question", {"text": "Since yesterday, have you had chills or felt feverish?",
                                               "options": ["No", "Yes, a little", "Yes, a lot"]})
    return _call("finish_investigation", {"findings": _findings(res, ctx, new_photo_id)})


def _findings(res, ctx, new_photo_id):
    flags, name = ctx.get("flags", []), ctx.get("first_name", "the patient")
    hr = _last(res, "get_vitals_trend", lambda r: r.get("metric") == "hr") or {}
    temp = _last(res, "get_vitals_trend", lambda r: r.get("metric") == "temp") or {}
    checkins = _last(res, "get_symptom_checkins") or {}
    meds = _last(res, "get_medication_context") or {}
    cmp = _last(res, "compare_wound_photos") or {}
    q = _last(res, "ask_followup_question") or {}

    device, patient, missing = [], [], []
    hr_rows = [r for r in hr.get("recent_readings", []) if r["quality"] == "good"]
    if hr_rows:
        last = hr_rows[-1]
        device.append({"text": f"Heart rate {last['value'].get('value')} bpm (baseline {hr.get('baseline')}), "
                               f"24 h range {hr['summary'].get('min')}-{hr['summary'].get('max')}",
                       "observation_id": last["observation_id"], "quality": last["quality"]})
    temp_rows = [r for r in temp.get("recent_readings", []) if r["quality"] == "good"]
    if temp_rows:
        last = temp_rows[-1]
        device.append({"text": f"Temperature {last['value'].get('value')} °C (baseline {temp.get('baseline')})",
                       "observation_id": last["observation_id"], "quality": last["quality"]})
    worse = checkins.get("worsening_vs_previous") or {}
    if worse:
        items = ", ".join(f"{w['item']} {w['before']}/5 → {w['now']}/5" for w in worse.get("items", []))
        patient.append({"text": f"Check-in: {items}", "observation_id": worse["observation_id"]})
    elif checkins.get("checkins"):
        c = checkins["checkins"][-1]
        patient.append({"text": f"Check-in scores {c['scores_1_to_5']}", "observation_id": c["observation_id"]})
    for d in meds.get("not_taken", []):
        if d.get("observation_id"):
            patient.append({"text": f"{d['name']} dose at {d['scheduled_for'][11:16]} on {d['scheduled_for'][:10]} "
                                    "recorded as not taken", "observation_id": d["observation_id"]})
    if new_photo_id:
        patient.append({"text": "New wound photo taken today", "observation_id": new_photo_id})
    else:
        missing.append("No new wound photo (request not answered)")
    answer = q.get("answer") or {}
    if answer.get("observation_id"):
        patient.append({"text": f"Asked about chills/fever: \"{answer.get('text')}\"",
                        "observation_id": answer["observation_id"]})
    else:
        missing.append("Follow-up question about chills not answered")
    if meds.get("unknown"):
        missing.append(f"{len(meds['unknown'])} recent dose(s) with no answer (unknown)")
    if "bad_ids_first" in flags and not any(n == "finish_investigation" for n, _ in res):
        patient.append({"text": "Invented claim", "observation_id": "obs_doesnotexist"})

    redness = (cmp.get("comparison") or {}).get("redness_area_change_pct") if cmp.get("available") else None
    wound_txt = f", wound redness area {redness:+}% vs the day-1 photo (measured by code)" if redness is not None else ""
    hr_last = hr_rows[-1]["value"].get("value") if hr_rows else "unknown"
    temp_last = temp_rows[-1]["value"].get("value") if temp_rows else "unknown"
    n_missed = len(meds.get("not_taken", []))
    return {
        "what_changed": f"Heart rate rising to {hr_last} bpm (baseline {hr.get('baseline')}) and temperature "
                        f"{temp_last} °C over the last 24 h, with more fatigue{wound_txt}.",
        "started_at": hr_rows[0]["at"] if hr_rows else None,
        "persistent": True,
        "patient_reported": patient,
        "device_measured": device,
        "ai_interpretation": "Several small changes point in the same direction (higher heart rate, low-grade "
                             "temperature, more fatigue" + (", a missed antibiotic dose" if n_missed else "") +
                             (" and more redness around the incision" if redness else "") +
                             "). Together they may deserve a clinician review today. This is not a diagnosis.",
        "missing_or_conflicting": missing,
        "suggested_priority": "attention",
        "messages": {
            "patient": "Thank you. Your care team will look at your readings today and may call you. Keep your "
                       "phone nearby and rest. If you get short of breath, chest pain or feel faint, call 112.",
            "caregiver": f"Please check in on {name} this evening, help with rest and keep the phone close. "
                         "The care team may call.",
            "clinician": f"Day 3 after TKR: HR {hr_last} (baseline {hr.get('baseline')}), T {temp_last} °C, "
                         f"fatigue up on check-in, {n_missed} missed antibiotic dose(s){wound_txt}. "
                         "Suggest review today.",
        },
    }


# ------------------------------------------------------------------ protocol compiler

@stub("protocol")
def _protocol(messages, ctx):
    """Canned extraction of the FICTIONAL sample discharge summary (seed/documents)."""
    if "Cefuroxime" not in ctx.get("text", ""):
        return {"medications": []}
    q = "Weight bearing as tolerated with two crutches for 14 days."
    return {
        "surgery": "Total knee replacement", "side": "right", "surgery_date": "2026-10-06",
        "discharge_date": "2026-10-08", "surgeon": "Dr. Elena Ruiz", "allergies": ["Penicillin (rash)"],
        "medications": [
            {"name": "Paracetamol", "dose": "1 g", "route": "by mouth", "times": ["08:00", "14:00", "20:00"],
             "purpose": "pain", "source_quote": "Paracetamol 1 g by mouth at 08:00, 14:00 and 20:00 for pain"},
            {"name": "Celecoxib", "dose": "200 mg", "route": "by mouth", "times": ["09:00"],
             "purpose": "anti-inflammatory", "source_quote": "Celecoxib 200 mg by mouth once daily at 09:00 with food"},
            {"name": "Pantoprazole", "dose": "20 mg", "route": "by mouth", "times": ["08:00"],
             "purpose": "stomach protection", "source_quote": "Pantoprazole 20 mg by mouth once daily at 08:00"},
            {"name": "Enoxaparin", "dose": "40 mg", "route": "subcutaneous injection", "times": ["20:00"],
             "purpose": "prevention of blood clots", "duration_days": 14,
             "source_quote": "Enoxaparin 40 mg subcutaneous injection once daily at 20:00 for 14 days"},
            {"name": "Cefuroxime", "dose": "500 mg", "route": "by mouth", "times": ["08:00", "14:00", "20:00"],
             "purpose": "antibiotic", "duration_days": 7,
             "source_quote": "Cefuroxime 500 mg by mouth three times daily at 08:00, 14:00 and 20:00 for 7 days"},
        ],
        "missed_dose_instruction": "If a dose is missed: do not take two doses together; inform the care team.",
        "activity_restrictions": [{"text": q, "source_quote": q},
                                  {"text": "No driving for at least 4 weeks.", "source_quote": "No driving for at least 4 weeks."}],
        "rehab": [{"text": "Knee bends 2 x 10", "times": ["09:30", "18:00"]},
                  {"text": "Straight-leg raises 2 x 10", "times": ["09:30", "18:00"]},
                  {"text": "Ankle pumps 3 x 15", "times": ["09:30", "13:00", "18:00"]}],
        "wound_care": ["Showering allowed with the waterproof dressing on; no bath or swimming until staples are removed."],
        "appointments": [{"title": "Physiotherapy", "date": "2026-10-14", "time": "15:00"},
                         {"title": "Staple removal", "date": "2026-10-16", "time": "09:00"},
                         {"title": "Follow-up with Dr. Ruiz", "date": "2026-10-20", "time": "10:30"}],
        "warning_signs": ["Fever over 38 C", "spreading redness", "increasing warmth or swelling",
                          "drainage or bad smell from the wound", "pain that keeps increasing"],
        "emergency_signs": ["sudden shortness of breath or chest pain", "calf pain or swelling", "fainting",
                            "heavy bleeding"],
    }
