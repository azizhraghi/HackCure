# 🏥 SurgiGuard AI — D2A : Moteur d'Extraction Médicale Autonome
## Plan Final & Critique — Réaliste pour Jury Médical

---

## ⚠️ Critique du Plan Précédent (Ce Qui Était Mauvais)

Le plan précédent avait 3 erreurs critiques :

1. **"Sans validation humaine"** — DANGEREUX et médicallement irresponsable. Aucun jury médical ne validera un système où une IA pose des actes médicaux sans supervision. On va inverser ça : notre force c'est justement de montrer que l'IA **AIDE** le médecin, pas qu'elle le **REMPLACE**.

2. **Pas de vraies données** — On n'a pas de PDFs d'hôpital réels. On va générer des PDFs réalistes crédibles (il n'y a pas besoin de vrais PDFs d'hôpital pour une démo hackathon, mais ils doivent être médicalement irréprochables).

3. **Architecture trop simple** — Le "conflict_resolver" était trop vague. On va coder des règles réelles et médicalement correctes.

---

## 🎯 Nouvel Objectif : Ce que le Jury Médical verra

> **"L'IA lit le dossier de sortie du patient, structure les informations, détecte les risques potentiels (allergies, interactions médicamenteuses), et présente tout cela avec un niveau de confiance, pour qu'un médecin puisse valider en 30 secondes plutôt qu'en 10 minutes."**

L'IA ne remplace pas le médecin. Elle lui fait gagner du temps et sécurise sa prise de décision. C'est ce message qui va convaincre le jury.

---

## 📄 Étape 0 : Générer des Données Médicales Réalistes (URGENT)

On ne cherche pas de vrais PDFs. On génère les nôtres, mais ils doivent être médicalement parfaits.

**Quels documents générer :**
- `ordonnance_post_ptg.pdf` — Ordonnance post-Prothèse Totale du Genou (cas de Sarah Miller). Les médicaments inclus : Paracétamol 1g, Célécoxib 200mg, Lovenox 4000UI, Pantoprazole 20mg.
- `compte_rendu_ptg.pdf` — Compte-rendu opératoire fictif mais réaliste.
- `protocole_kine_ptg.pdf` — Protocole de rééducation sur 6 semaines.
- `ordonnance_avec_conflit.pdf` — Une ordonnance de test intentionnellement "dangereuse" (Amoxicilline prescrit à un patient allergique à la Pénicilline) pour tester notre Agent de Sécurité.

**Outils :** On utilise `reportlab` (Python) pour générer ces PDFs proprement et rapidement.

---

## 🏗️ Architecture Finale : 4 Couches Propres

```
PDF entrant
    │
    ▼
┌─────────────────────────┐
│  SERVICE 1 : OCR Layer  │  ← PyMuPDF (natif) / Tesseract (scan)
│  Extrait le texte brut  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  AGENT 1 : Structure Extractor (LangGraph)  │  ← Mistral + Pydantic
│  JSON structuré + Confidence Score par champ│
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  AGENT 2 : Medical Safety Checker           │  ← Règles Déterministes + LLM
│  Croise les médicaments avec :              │
│  • Allergies du patient                     │
│  • Interactions entre médicaments prescrits │
│  • Doses (min/max selon le poids/âge)       │
└────────────┬────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  RÉSULTAT : ProtocolReport JSON      │
│  • status: SAFE / WARNING / BLOCKED  │
│  • confidence_score: 0-100%          │
│  • alerts: [...] si risques          │
│  • extracted_data: {...} médicaments │
└──────────────────────────────────────┘
             │
             ▼
    API : POST /v1/documents/upload
    → Stockage SQLite
    → Retour JSON au frontend
```

---

## 📋 Étapes de Code Détaillées

### ✅ Étape 1 : Générer les PDFs de Test Réalistes
**Fichier à créer :** `backend/seed/generate_pdfs.py`
- Utiliser `reportlab` pour générer `ordonnance_post_ptg.pdf` et `ordonnance_avec_conflit.pdf`.
- Les deux fichiers seront placés dans `backend/documents/`.
- **Test de validation :** Ouvrir les PDFs et vérifier qu'ils ressemblent à une vraie ordonnance médicale française (tampon médecin, RPPS, DCI des médicaments).

### ✅ Étape 2 : Service OCR (Extraction du Texte Brut)
**Fichier à créer :** `backend/app/services/ocr_service.py`
- Stratégie 1 (PyMuPDF) : Pour les PDFs avec texte natif (le cas de nos PDFs générés).
- Stratégie 2 (Tesseract) : Fallback si PyMuPDF retourne moins de 50 mots (signe que c'est un scan).
- **Sortie :** Dictionnaire `{page_number: text_content}`.
- **Test de validation (`test_ocr.py`):** Lire `ordonnance_post_ptg.pdf` et vérifier que les mots "Paracétamol", "Célécoxib" et le nom du patient apparaissent dans le texte extrait.

### ✅ Étape 3 : Améliorer l'Agent Extracteur (LangGraph Agent 1)
**Fichier à modifier :** `backend/app/ai/graphs/protocol_graph.py`

**Amélioration du Schéma Pydantic :**
```
MedicationSchema {
  dci: str                  # Nom générique (ex: "paracétamol")
  commercial_name: str      # Nom commercial (ex: "Doliprane")
  dosage_mg: float          # Dose en mg (ex: 1000)
  frequency_per_day: int    # Nb prises par jour (ex: 3)
  duration_days: int        # Durée traitement en jours (ex: 14)
  route: str                # "oral", "injectable", "topique"
  special_instructions: str # "avec repas", etc.
  confidence: float         # Score entre 0.0 et 1.0
}

ExtractedProtocol {
  medications: List[MedicationSchema]
  physical_restrictions: List[str]     # "Pas de conduite", "Béquilles"
  followup_appointments: List[date]    # Rendez-vous de suivi
  global_confidence: float             # Moyenne des scores
  extraction_notes: str               # Si l'IA est incertaine sur qqch
}
```

**Règle de Guardrail :** Si `global_confidence < 0.90` → ne pas enregistrer, lever une alerte.
**Test de validation :** Passer le texte brut de `ordonnance_post_ptg.pdf` et vérifier que les 4 médicaments sont extraits avec une confiance > 0.90.

### ✅ Étape 4 : L'Agent de Sécurité Médicale (LangGraph Agent 2)
**Fichier à créer :** `backend/app/ai/graphs/safety_checker.py`

Cet agent fonctionne en **deux niveaux** pour être médicalement rigoureux :

**Niveau 1 — Règles Déterministes (rapide, 100% fiable) :**
- Dictionnaire des classes d'antibiotiques (béta-lactamines = Pénicilline + Amoxicilline + Augmentin). Si patient allergique à la Pénicilline ET un médicament de cette classe est prescrit → BLOCKED immédiatement, sans LLM.
- Vérification des associations médicamenteuses AINS + Anticoagulant (Célécoxib + Lovenox dans notre cas) → WARNING car risque hémorragique.

**Niveau 2 — Vérification LLM (pour les cas complexes) :**
- Pour tout ce que les règles ne couvrent pas, on envoie à Mistral avec le prompt : "Voici la liste de médicaments prescrits et le profil du patient. Y a-t-il des contre-indications formelles ou des interactions médicamenteuses à signaler ? Réponds uniquement par un JSON structuré."

**Sortie de l'Agent :**
```
SafetyReport {
  status: "SAFE" | "WARNING" | "BLOCKED"
  alerts: [
    { severity: "CRITICAL", message: "Allergie Pénicilline détectée avec Amoxicilline prescrit." },
    { severity: "WARNING", message: "Association AINS + Anticoagulant : Surveillance hémorragique renforcée." }
  ]
}
```

**Test de validation (`test_safety.py`):** Passer l'ordonnance avec conflit (Amoxicilline + patient allergique) et vérifier que le status est "BLOCKED".

### ✅ Étape 5 : Connecter les Agents (LangGraph Complet)
**Fichier à modifier :** `backend/app/ai/graphs/protocol_graph.py`
```
Nœuds du graphe :
  [ocr] → [extract] → (si confidence < 0.9 → [error]) → [safety_check] → [save_to_db]
```

### ✅ Étape 6 : Endpoint API Final
**Fichier à créer :** `backend/app/api/v1/documents.py`
- `POST /v1/documents/upload` : Reçoit le PDF + l'ID patient, lance le pipeline complet, retourne le `ProtocolReport`.
- `GET /v1/documents/{protocol_id}` : Retourne le protocole sauvegardé.

---

## 🧪 Stratégie de Test pour le Jury

| Test | Input | Résultat Attendu | Ce que ça démontre |
|------|-------|-------------------|--------------------|
| `test_ocr.py` | `ordonnance_post_ptg.pdf` | Les 4 médicaments sont dans le texte | Notre lecture de PDF marche |
| `test_extract.py` | Texte brut de l'ordonnance | JSON structuré, confiance > 90% | Notre IA lit les données correctement |
| `test_safety_ok.py` | Ordonnance normale | Status = SAFE | Le cas nominal fonctionne |
| `test_safety_blocked.py` | Ordonnance Amoxicilline + allergie Pénicilline | Status = BLOCKED, alerte critique | Notre garde-fou de sécurité fonctionne |
| `test_pipeline_end2end.py` | PDF → API → JSON final | ProtocolReport complet en sortie | Tout le système fonctionne de A à Z |

---

## 🗣️ Message Clé pour le Jury Médical

> *"Notre système ne prescrit rien. Il lit, structure, et alerte. Le médecin garde le contrôle total. Mais grâce à notre moteur IA, il voit en 10 secondes si une ordonnance est sûre pour ce patient précis, au lieu de passer 10 minutes à croiser les informations manuellement."*

C'est ce message-là qui va séduire un jury médical.
