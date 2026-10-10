import re
import bleach
from typing import Tuple, List

INJECTION_PATTERNS = [
    r"ignore (previous|above|all) instructions",
    r"you are now",
    r"pretend (to be|you are)",
    r"system\s*:", 
    r"<\|.*\|>",
    r"ADMIN\s*MODE",
    r"reveal.*prompt",
    r"show.*system.*message",
    r"forget.*rules",
    r"override.*safety",
]

def sanitize_input(text: str) -> Tuple[str, List[str]]:
    """Returns (cleaned_text, detected_threats)"""
    threats = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            threats.append(f"Potential injection: {pattern}")
    
    # Strip HTML and scripts
    cleaned = bleach.clean(text, strip=True)
    return cleaned, threats
