"""Script de test rapide de l'OCR Service."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.services.ocr_service import extract_text_from_pdf

pdfs_dir = Path("documents")
if not pdfs_dir.exists():
    print("ERREUR: Dossier seed/pdfs introuvable")
    sys.exit(1)

pdfs = sorted(pdfs_dir.glob("*.pdf"))
if not pdfs:
    print("ERREUR: Aucun PDF dans seed/pdfs")
    sys.exit(1)

for pdf in pdfs:
    print("=" * 60)
    r = extract_text_from_pdf(pdf)
    print("Fichier  : " + pdf.name)
    print("Methode  : " + r.method)
    print("Mots     : " + str(r.word_count))
    print("Pages    : " + str(len(r.pages)))
    # Afficher les 5 premieres lignes non vides
    lines = [l for l in r.full_text.split("\n") if l.strip()][:5]
    print("Apercu   :")
    for l in lines:
        print("  " + l[:75])
    print()
