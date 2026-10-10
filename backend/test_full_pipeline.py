"""
Pipeline complet D2A : PDF → OCR → Extraction → Safety Check → Résultat final

Usage:
    python test_full_pipeline.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

if not os.getenv("MISTRAL_API_KEY"):
    print("ERREUR: Ajouter MISTRAL_API_KEY dans backend/.env")
    sys.exit(1)

from app.services.ocr_service import extract_text_from_pdf
from app.ai.graphs.protocol_graph import protocol_graph, ProtocolState
from app.ai.graphs.safety_graph import safety_graph, SafetyState

DOCS_DIR = os.path.join(os.path.dirname(__file__), "documents")

TEST_CASES = [
    {
        "name": "Test 1 - Ordonnance NORMALE (WARNING attendu - interaction AINS+HBPM reelle)",
        "pdf":  "ordonnance_post_ptg_safe.pdf",
        "patient_allergies": ["pénicilline"],
        "expected_status": "WARNING",  # AINS (Célécoxib) + HBPM (Lovenox) = vraie interaction médicale
    },
    {
        "name": "Test 2 - Ordonnance DANGEREUSE (doit etre BLOCKED - Allergie Amoxicilline)",
        "pdf":  "ordonnance_conflit_allergie.pdf",
        "patient_allergies": ["pénicilline"],
        "expected_status": "BLOCKED",
    },
    {
        "name": "Test 3 - Compte Rendu Operatoire (extraction restrictions physiques)",
        "pdf":  "compte_rendu_operatoire_ptg.pdf",
        "patient_allergies": ["pénicilline"],
        "expected_status": "SAFE",  # Pas de médicaments prescrits directement, juste des restrictions physiques
    },
]


def run_pipeline(pdf_filename: str, patient_allergies: list[str]) -> dict:
    pdf_path = os.path.join(DOCS_DIR, pdf_filename)

    # ── Étape 1 : OCR ──────────────────────────────────────────────────────
    print(f"  [OCR] Extraction texte de '{pdf_filename}'...")
    ocr = extract_text_from_pdf(pdf_path)
    print(f"  [OCR] Méthode: {ocr.method} | Mots: {ocr.word_count}")

    # ── Étape 2 : Agent 1 — Extraction structurée ─────────────────────────
    print(f"  [AGENT 1] Envoi à Mistral pour structuration...")
    proto_state: ProtocolState = {
        "document_text": ocr.full_text,
        "source_file": ocr.source_file,
        "word_count": ocr.word_count,
        "extracted_data": None,
        "errors": [],
        "low_confidence": False,
    }
    proto_result = protocol_graph.invoke(proto_state)
    extracted = proto_result.get("extracted_data")

    if not extracted:
        print(f"  [AGENT 1] ECHEC: {proto_result.get('errors')}")
        return {"status": "ERROR", "errors": proto_result.get("errors")}

    print(f"  [AGENT 1] Extraction OK — {len(extracted.medications)} médicaments détectés")
    print(f"  [AGENT 1] Confiance globale: {extracted.global_confidence:.0%}")
    if proto_result.get("low_confidence"):
        print(f"  [AGENT 1] AVERTISSEMENT: Confiance insuffisante")

    # ── Étape 3 : Agent 2 — Safety Check ──────────────────────────────────
    print(f"  [AGENT 2] Vérification de sécurité médicale...")
    safety_state: SafetyState = {
        "extracted_protocol": extracted,
        "patient_allergies": patient_allergies,
        "safety_report": None,
        "deterministic_alerts": [],
        "needs_llm_check": False,
    }
    safety_result = safety_graph.invoke(safety_state)
    report = safety_result.get("safety_report")

    return {
        "extracted": extracted,
        "safety_report": report,
        "ocr_method": ocr.method,
        "word_count": ocr.word_count,
        "proto_errors": proto_result.get("errors", []),
    }


def print_separator(char="─", width=60):
    print(char * width)


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  SURGIGUARD AI — PIPELINE COMPLET D2A")
    print("  OCR → Extraction → Safety Check")
    print("═" * 60)

    all_passed = True

    for tc in TEST_CASES:
        print(f"\n{'═'*60}")
        print(f"  {tc['name']}")
        print_separator()

        try:
            result = run_pipeline(tc["pdf"], tc["patient_allergies"])
        except Exception as e:
            print(f"  ERREUR FATALE: {e}")
            import traceback; traceback.print_exc()
            all_passed = False
            continue

        report = result.get("safety_report")
        extracted = result.get("extracted")

        print_separator()
        print("  RESULTATS:")

        if extracted:
            print(f"  • Type document     : {extracted.document_type}")
            print(f"  • Patient           : {extracted.patient_lastname} {extracted.patient_firstname}")
            print(f"  • Allergies (doc)   : {', '.join(extracted.known_allergies) or 'Aucune'}")
            print(f"  • Médicaments       : {len(extracted.medications)}")
            for m in extracted.medications:
                conf_icon = "✅" if m.confidence >= 0.9 else ("⚠️" if m.confidence >= 0.7 else "❌")
                print(f"    {conf_icon} {m.dci} {m.dosage_raw} — confiance {m.confidence:.0%}")
            print(f"  • Confiance globale : {extracted.global_confidence:.0%}")
            if extracted.physical_restrictions:
                print(f"  • Restrictions      : {', '.join(extracted.physical_restrictions[:2])}")

        if report:
            status_icon = {"SAFE": "✅", "WARNING": "⚠️", "BLOCKED": "🚨"}.get(report.status, "?")
            print(f"\n  STATUT FINAL: {status_icon} {report.status}")
            if report.alerts:
                for alert in report.alerts:
                    sev_icon = "🚨" if alert.severity == "CRITICAL" else ("⚠️" if alert.severity == "WARNING" else "ℹ️")
                    print(f"  {sev_icon} [{alert.severity}] {alert.message}")

        # Vérification du résultat attendu
        actual_status = report.status if report else "ERROR"
        expected = tc["expected_status"]
        match = actual_status == expected
        if not match:
            all_passed = False
        print(f"\n  Test {'PASSE ✅' if match else 'ECHOUE ❌'} "
              f"(attendu: {expected}, obtenu: {actual_status})")

    print("\n" + "═" * 60)
    print(f"  BILAN : {'TOUS LES TESTS PASSES ✅' if all_passed else 'CERTAINS TESTS ONT ECHOUE ❌'}")
    print("═" * 60 + "\n")
