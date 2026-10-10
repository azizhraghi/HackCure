from typing import TypedDict, Optional
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas.protocol import ExtractedProtocol
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest") # Using small for fast structured output

class ProtocolState(TypedDict):
    document_text: str
    extracted_data: Optional[ExtractedProtocol]
    errors: list[str]

llm = ChatMistralAI(model=MISTRAL_MODEL, mistral_api_key=MISTRAL_API_KEY, temperature=0.1)

parser = PydanticOutputParser(pydantic_object=ExtractedProtocol)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a medical document parser for a French postoperative recovery system.\nExtract ONLY what is explicitly written in the document.\n\nOUTPUT FORMAT:\n{format_instructions}\n\nRULES:\n1. Extract medication EXACTLY as written (DCI, dose, frequency)\n2. Do NOT invent timing if not specified\n3. Do NOT add medications not in the document\n4. Preserve original French medical terms."),
    ("user", "DOCUMENT:\n{document_text}")
])

extraction_chain = prompt | llm | parser

def extract_protocol(state: ProtocolState):
    try:
        # Note: Mistral large/small supports JSON mode, but standard tool calling is safer if available. We use standard Pydantic parser here.
        result = extraction_chain.invoke({
            "document_text": state["document_text"],
            "format_instructions": parser.get_format_instructions()
        })
        return {"extracted_data": result, "errors": state.get("errors", [])}
    except Exception as e:
        errors = state.get("errors", [])
        errors.append(f"Extraction failed: {str(e)}")
        return {"errors": errors}

def validate_protocol(state: ProtocolState):
    data = state.get("extracted_data")
    errors = state.get("errors", [])
    if data:
        # Deterministic checks
        if not data.medications:
            errors.append("No medications found in document.")
    return {"errors": errors}

# Build LangGraph
builder = StateGraph(ProtocolState)
builder.add_node("extract", extract_protocol)
builder.add_node("validate", validate_protocol)

builder.set_entry_point("extract")
builder.add_edge("extract", "validate")
builder.add_edge("validate", END)

protocol_graph = builder.compile()
