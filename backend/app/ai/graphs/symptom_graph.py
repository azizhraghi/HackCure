from typing import TypedDict, Optional, List
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas.symptom import SymptomExtractionResult
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv
import re

from app.config import settings, get_chat_llm, get_active_provider

WARNING_KEYWORDS_FR = [
    "fièvre", "rougeur", "gonflement", "écoulement", "odeur",
    "douleur qui augmente", "plaie", "infection",
]
EMERGENCY_KEYWORDS_FR = [
    "essoufflement", "douleur thoracique", "douleur poitrine",
    "mollet gonflé", "malaise", "évanouissement", "perte de connaissance",
    "embolie", "caillot",
]

class SymptomState(TypedDict):
    raw_text: str
    emoji_code: str
    pain_score: int
    deterministic_warning: bool
    deterministic_emergency: bool
    extracted_data: Optional[SymptomExtractionResult]
    errors: List[str]

llm = get_chat_llm(temperature=0.0)
parser = PydanticOutputParser(pydantic_object=SymptomExtractionResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Extract medical symptoms from the patient's message.\n\nOUTPUT FORMAT:\n{format_instructions}\n\nRULES:\n1. 'No fever' means assertion='absent'.\n2. 'I don't know if I have a fever' means assertion='unknown'.\n3. An EVA pain score >= 7 is 'severe'."),
    ("user", "Text: {raw_text}\nEmoji: {emoji_code}\nPain Score (EVA): {pain_score}/10")
])

extraction_chain = prompt | llm | parser

def check_deterministic_warnings(state: SymptomState):
    text = state.get("raw_text", "").lower()
    pain = state.get("pain_score", 0)
    
    is_warning = False
    is_emergency = False
    
    if pain >= 7:
        is_warning = True
        
    for kw in EMERGENCY_KEYWORDS_FR:
        if kw in text:
            is_emergency = True
            break
            
    for kw in WARNING_KEYWORDS_FR:
        if kw in text:
            is_warning = True
            break
            
    return {"deterministic_warning": is_warning, "deterministic_emergency": is_emergency}

def extract_symptoms(state: SymptomState):
    if get_active_provider() == "offline":
        return {"extracted_data": None}

    try:
        result = extraction_chain.invoke({
            "raw_text": state["raw_text"],
            "emoji_code": state["emoji_code"],
            "pain_score": state["pain_score"],
            "format_instructions": parser.get_format_instructions()
        })
        return {"extracted_data": result}
    except Exception as e:
        return {"errors": [str(e)]}

builder = StateGraph(SymptomState)
builder.add_node("check_deterministic", check_deterministic_warnings)
builder.add_node("extract_llm", extract_symptoms)

builder.set_entry_point("check_deterministic")
builder.add_edge("check_deterministic", "extract_llm")
builder.add_edge("extract_llm", END)

symptom_graph = builder.compile()
