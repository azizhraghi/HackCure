import asyncio
import os
import json
from dotenv import load_dotenv

# Ensure Mistral API Key is available
load_dotenv()
if not os.getenv("MISTRAL_API_KEY"):
    print("❌ ERROR: MISTRAL_API_KEY is not set in backend/.env")
    exit(1)

from app.ai.graphs.symptom_graph import symptom_graph

def test_symptom_extraction():
    print("=" * 60)
    print("🏥 TEST: SYMPTOM UNDERSTANDING & WARNING DETECTION")
    print("=" * 60)
    
    # Test cases:
    # 1. Clear emergency (chest pain)
    # 2. Warning but high pain (EVA=8)
    # 3. Simple recovery check-in
    
    test_cases = [
        {
            "id": "1 (Emergency)",
            "raw_text": "J'ai une douleur thoracique et je me sens mal.",
            "emoji_code": "very_unwell",
            "pain_score": 6
        },
        {
            "id": "2 (Warning - High Pain)",
            "raw_text": "Mon genou est gonflé et la douleur augmente beaucoup.",
            "emoji_code": "unwell",
            "pain_score": 8
        },
        {
            "id": "3 (Normal Check-in)",
            "raw_text": "Je vais bien aujourd'hui, j'ai fait mes exercices. Pas de fièvre.",
            "emoji_code": "good",
            "pain_score": 2
        }
    ]
    
    for tc in test_cases:
        print(f"\n▶️ Running Test Case: {tc['id']}")
        print(f"Message: '{tc['raw_text']}'")
        print(f"Pain: {tc['pain_score']}/10, Emoji: {tc['emoji_code']}")
        
        initial_state = {
            "raw_text": tc["raw_text"],
            "emoji_code": tc["emoji_code"],
            "pain_score": tc["pain_score"],
            "deterministic_warning": False,
            "deterministic_emergency": False,
            "extracted_data": None,
            "errors": []
        }
        
        result = symptom_graph.invoke(initial_state)
        
        # Print outputs
        print("\n--- Results ---")
        if result.get("deterministic_emergency"):
            print("🚨 DETERMINISTIC TRIGGER: EMERGENCY DETECTED (Forward directly to D3)")
        elif result.get("deterministic_warning"):
            print("⚠️ DETERMINISTIC TRIGGER: WARNING DETECTED (Alert Care Team)")
        else:
            print("✅ No deterministic alerts.")
            
        extracted = result.get("extracted_data")
        if extracted:
            print("\n🤖 LLM Structured Extraction:")
            print(json.dumps(extracted.model_dump(), indent=2, ensure_ascii=False))
        elif result.get("errors"):
            print(f"❌ LLM Extraction Errors: {result['errors']}")
            
        print("-" * 40)

if __name__ == "__main__":
    test_symptom_extraction()
