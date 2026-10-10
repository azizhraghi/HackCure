import re
import json
from typing import Tuple, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage

FORBIDDEN_PHRASES = [
    r"diagnosed", r"you have", r"stop taking", r"take extra",
    r"safe to", r"healed", r"no need to worry", r"vous avez", r"arrêtez de prendre",
    r"prenez plus", r"sans danger", r"guéri", r"ne vous inquiétez pas",
    r"diagnostic", r"vous souffrez de", r"je diagnostique"
]

SELF_REFLECTION_SYSTEM_PROMPT = """You are the SurgiGuard AI Medical Safety Critic.
Your role is to strictly verify that a draft response sent to a postoperative patient complies with critical safety boundaries.

MANDATORY SAFETY BOUNDARIES:
1. NO DIAGNOSIS: The assistant must NEVER diagnose, state what condition the patient has (e.g. 'c'est une infection', 'vous faites une complication'), or speculate on a pathology.
2. NO TREATMENT ALTERATION: The assistant must NEVER advise changing doses, stopping medication, or adding medications not in the approved protocol.
3. NO FALSE REASSURANCE: The assistant must NEVER claim the patient is cured ('guéri'), completely safe ('sans danger'), or dismiss concerning symptoms ('ce n'est rien').
4. CARE TEAM ESCALATION: Any serious symptoms or uncertainties MUST be directed to Dr. Ruiz / care team or emergency services.

Analyze the draft response below:
- If it violates any boundary: Rewrite it safely to remove the diagnosis/unsafe claim and instruct the patient to consult their care team. Set must_escalate=true.
- If it is completely safe and follows instructions: Keep it intact.

Respond ONLY with valid JSON in this exact structure:
{
  "is_safe": true,
  "violation_detected": null,
  "must_escalate": false,
  "verified_response": "safe text here"
}"""


def deterministic_validate(text: str) -> Tuple[str, bool, List[str]]:
    """
    Fast-path deterministic check for forbidden phrases and [ESCALATE] tag.
    """
    escalate = False

    # Check for forbidden phrases
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            escalate = True
            text += "\n[Avertissement de sécurité : Ce message a été généré par IA et nécessite une validation médicale.]"
            break

    if "[ESCALATE]" in text:
        escalate = True
        text = text.replace("[ESCALATE]", "").strip()

    # Extract citations [Source X]
    citations = re.findall(r"\[Source.*?\]", text)

    return text, escalate, citations


def validate_output_with_reflection(
    text: str,
    query: str,
    context_documents: List[str],
    critic_llm=None
) -> Tuple[str, bool, List[str], Optional[str]]:
    """
    Self-Reflection validation node:
    1. Runs fast-path deterministic regex checks.
    2. Performs an LLM critic self-reflection call to ensure NO diagnosis is posed.
    3. Returns (final_text, escalate_flag, citations, reflection_note).
    """
    base_text, base_escalate, citations = deterministic_validate(text)
    reflection_note = None

    if critic_llm is None:
        return base_text, base_escalate, citations, reflection_note

    try:
        user_prompt = f"PATIENT QUERY: {query}\n\nDRAFT RESPONSE TO EVALUATE:\n{base_text}"
        reflection_messages = [
            SystemMessage(content=SELF_REFLECTION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        critique = critic_llm.invoke(reflection_messages)
        critique_content = getattr(critique, "content", "")

        # Extract JSON from LLM response
        json_match = re.search(r"\{.*\}", critique_content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            is_safe = data.get("is_safe", True)
            must_escalate = data.get("must_escalate", False) or base_escalate
            verified_response = data.get("verified_response", base_text)
            violation = data.get("violation_detected")

            if not is_safe or violation:
                must_escalate = True
                reflection_note = f"Self-Reflection flagged: {violation}"
                final_text = verified_response
            else:
                final_text = base_text

            # Re-extract citations if updated
            new_citations = re.findall(r"\[Source.*?\]", final_text)
            return final_text, must_escalate, new_citations or citations, reflection_note

    except Exception as exc:
        # Graceful fallback: do not fail pipeline, retain deterministic check
        reflection_note = f"Self-reflection fallback: {str(exc)}"

    return base_text, base_escalate, citations, reflection_note


# Backward-compatible wrapper
def validate_output(text: str, context_documents: List[str]) -> Tuple[str, bool, List[str]]:
    return deterministic_validate(text)
