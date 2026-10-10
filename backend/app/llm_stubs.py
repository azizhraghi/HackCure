"""Canned LLM behaviour for LLM_MODE=stub (tests, offline demo). Deterministic, schema-valid."""

from .llm import stub

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
