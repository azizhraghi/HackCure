import re
from typing import Tuple, List

FORBIDDEN_PHRASES = [
    r"diagnosed", r"you have", r"stop taking", r"take extra",
    r"safe to", r"healed", r"no need to worry", r"vous avez", r"arrêtez de prendre",
    r"prenez plus", r"sans danger", r"guéri", r"ne vous inquiétez pas",
    r"diagnostic"
]

def validate_output(text: str, context_documents: List[str]) -> Tuple[str, bool, List[str]]:
    """
    Returns (validated_text, escalate_flag, citations)
    Checks for dangerous claims and enforces [ESCALATE] logic.
    """
    escalate = False
    
    # Check for forbidden phrases
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            # We don't block entirely, but we flag for escalation and append a safety warning
            escalate = True
            text += "\n[Avertissement de sécurité : Ce message a été généré par IA et nécessite une validation médicale.]"
            break
            
    if "[ESCALATE]" in text:
        escalate = True
        text = text.replace("[ESCALATE]", "").strip()
        
    # Extract citations [Source X]
    citations = re.findall(r"\[Source.*?\]", text)
    
    return text, escalate, citations
