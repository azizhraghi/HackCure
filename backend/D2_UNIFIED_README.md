# SurgiGuard AI — Developer 2 Unified Backend
## Recovery Protocols (D2A) + Knowledge Assistants (D2B)

> **Branch: `dev/d2-unified`** — ready for D1 & D3 integration.  
> ⚠️ Do NOT merge directly into `main`.

---

## Architecture Overview

```
Patient Mobile App → POST /v1/documents/upload (PDF / JPEG / PNG)
                   → POST /v1/documents/complete (fill missing fields)
                   → POST /v1/checkin (daily symptom check-in)
                   → POST /v1/assistant/chat (RAG assistant)
                          │
    ┌──────────────────────┼──────────────────────────┐
    │                      │                          │
    ▼                      ▼                          ▼
 D2A — Protocol         D2A — Safety              D2B — RAG
 Compiler                Graph                    Assistant
 ─────────────          ──────────                ──────────
 OCR Service            Allergy Check             Vectorstore
 (PyMuPDF +             Drug Interaction          Semantic Chunking
  Pixtral VLM)          Rules Engine              Memory + Reflection
 LLM Extraction         Risk Assessment           Guardrails
 20+ clinical fields    asa+bmi+smoking           Output Validator
 missing_fields[]       → SAFE/WARNING/BLOCKED    → Grounded answers
```

---

## D2A — Protocol Compiler (your work)

| Component | File | Description |
|-----------|------|-------------|
| **OCR Service** | `app/services/ocr_service.py` | PyMuPDF (native PDF) + Pixtral VLM (scanned/image) |
| **Protocol Graph** | `app/ai/graphs/protocol_graph.py` | LLM extraction → 20+ clinical fields |
| **Safety Graph** | `app/ai/graphs/safety_graph.py` | Deterministic allergy + interaction checker |
| **Schema** | `app/schemas/protocol.py` | `ExtractedProtocol` with auto-BMI, missing_fields, is_high_risk |
| **API Upload** | `app/api/v1/documents.py` | Upload PDF/JPEG/PNG + Complete missing fields |
| **API Check-in** | `app/api/v1/checkin.py` | Daily symptom check-in → symptoms.structured event |

### Extracted Fields (20+)

**Patient Identity:** lastname, firstname, dob, age, sex  
**Anthropometry:** height_cm, weight_kg, bmi_kg_m2 (auto-computed)  
**Risk Factors:** smoking_status, diabetes, hypertension, cardiac_history, renal_insufficiency, hepatic_insufficiency, anticoagulated_before_surgery  
**Surgical Context:** surgery_type, surgery_date, discharge_date, hospital_name, anesthesia_type, asa_score, blood_type  
**Medical History:** comorbidities[], previous_surgeries[], known_allergies[]  
**Medications:** DCI, commercial_name, dosage_mg, frequency, duration, route, drug_class, antibiotic_family, confidence score  
**Follow-up:** physical_restrictions[], followup_appointments[], general_instructions

### OCR Strategy
- **PDF natif** → PyMuPDF (0 API, ~50ms)
- **PDF scanné** (page < 40 mots) → render PNG → Pixtral-12b VLM
- **Image directe** (JPEG/PNG from camera) → Pixtral-12b VLM directly

---

## D2B — RAG Assistant (teammate's work)

| Component | File | Description |
|-----------|------|-------------|
| **Assistant Graph** | `app/ai/graphs/assistant_graph.py` | Conversational RAG with Groq, memory & self-reflection |
| **Symptom Graph** | `app/ai/graphs/symptom_graph.py` | Structured symptom extraction |
| **Vectorstore** | `app/ai/rag/vectorstore.py` | Semantic chunking + embedding |
| **Retriever** | `app/ai/rag/retriever.py` | Scoped document retrieval |
| **Guardrails** | `app/ai/guardrails/` | Input sanitizer + output validator |
| **Chat API** | `app/api/v1/chat.py` | Patient/caregiver chat endpoint |
| **Config** | `app/config.py` | Centralized configuration |

---

## API Endpoints (Unified)

| Method | Endpoint | Owner | Description |
|--------|----------|-------|-------------|
| `POST` | `/v1/documents/upload` | D2A | Upload PDF/JPEG/PNG → OCR + Extract + Safety |
| `POST` | `/v1/documents/complete` | D2A | Fill missing fields → re-run safety |
| `POST` | `/v1/checkin` | D2A | Daily symptom check-in |
| `POST` | `/v1/assistant/chat` | D2B | RAG assistant chat |
| `GET`  | `/docs` | FastAPI | Interactive API documentation |

---

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # Add your MISTRAL_API_KEY
python -m uvicorn main:app --reload
```

## Testing

```bash
# Full pipeline test (OCR → Extract → Safety)
python test_full_pipeline.py

# OCR only
python test_ocr.py

# Assistant test
python test_assistant.py

# Open test UI in browser
# → backend/test_ui.html
```

## Events Published (for D1 & D3 consumption)

| Event Type | Producer | Schema |
|------------|----------|--------|
| `symptoms.structured` | D2 | mood_label, pain_score, items[], warning_answers[] |
| `protocol.activated` | D2 | protocol_id, version, approval_id, content_hash |
| `medication.reported` | D2 | prescription_id, reported_status, reporter_id |

---

## Integration Points for D1 & D3

### D1 (Recovery Twin) consumes:
- `ExtractedProtocol` → patient demographics, surgery context, risk factors
- `symptoms.structured` → daily check-in data for trend analysis

### D3 (Safety Coordinator) consumes:
- `SafetyReport` → alerts (CRITICAL/WARNING/INFO) for escalation
- `symptoms.structured` → warning signs for emergency lane
- `missing_fields[]` → track data completeness

---

**Status: ✅ Integration-ready for D1 & D3**
