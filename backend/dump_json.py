"""Génère le JSON complet du pipeline D2A sur le PDF de test."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ocr_service import extract_text_from_pdf
from app.ai.graphs.protocol_graph import protocol_graph, ProtocolState
from app.ai.graphs.safety_graph import safety_graph, SafetyState

pdf = Path("documents/ordonnance_post_ptg_safe.pdf")
print("OCR en cours...", file=sys.stderr)
ocr = extract_text_from_pdf(pdf)

proto_result = protocol_graph.invoke({
    "document_text": ocr.full_text,
    "source_file": pdf.name,
    "word_count": ocr.word_count,
    "extracted_data": None,
    "errors": [],
    "low_confidence": False,
})
extracted = proto_result.get("extracted_data")

safety_result = safety_graph.invoke({
    "extracted_protocol": extracted,
    "patient_allergies": ["pénicilline"],
    "safety_report": None,
    "deterministic_alerts": [],
    "needs_llm_check": False,
})
report = safety_result.get("safety_report")

output = {
    "status": report.status if report else "SAFE",
    "ocr_method": ocr.method,
    "word_count": ocr.word_count,
    "extraction": extracted.model_dump() if extracted else None,
    "safety_report": report.model_dump() if report else None,
    "missing_fields": [f.model_dump() for f in extracted.missing_fields] if extracted else [],
    "errors": proto_result.get("errors", []),
}
print(json.dumps(output, ensure_ascii=False, indent=2))
