# Plan de Travail Réparti (100% IA 🤖) : Developer 2A & Developer 2B

Pardon pour la confusion ! Puisque votre spécialité à tous les deux est **l'Intelligence Artificielle pure**, nous allons abandonner le Dashboard (on laissera ça à un autre membre ou on s'en passera pour se concentrer sur l'IA). 

Voici comment vous pouvez vous diviser la tâche pour construire une **IA Médicale Ultra-Intelligente et Sécurisée** en travaillant en parallèle sur deux axes majeurs :

---

## 👨‍💻 Developer 2A : Axe "OCR Avancé & Compilation des Protocoles"
*Dossiers de travail : `backend/app/ai/graphs/protocol_graph.py` et création de `backend/app/ai/ocr/`*

Votre but est de transformer des documents médicaux complexes et désordonnés en données parfaitement structurées.

**Tâches IA :**
1. **Pipeline Vision & Texte (PyMuPDF / Tesseract) :**
   - Créer un script capable de lire les vrais PDF (ordonnances, compte-rendus) et d'en extraire le texte brut de manière intelligente (gérer les tableaux de médicaments).
2. **Amélioration du `protocol_graph.py` (LangGraph) :**
   - Rendre le prompt de Mistral beaucoup plus robuste pour extraire non seulement les médicaments, mais aussi les **contre-indications**, les **exercices de kiné**, et les **scores de restriction**.
3. **Système de Confiance (Confidence Scoring) :**
   - Modifier le schéma d'extraction (`app/schemas/protocol.py`) pour que l'IA donne un pourcentage de confiance pour chaque médicament extrait. Si l'IA n'est pas sûre à 95% d'un dosage, elle doit lever un drapeau d'incertitude (OWASP GenAI - Hallucination Prevention).
4. **Agent de Résolution de Conflits :**
   - Créer un sous-agent qui vérifie si les médicaments prescrits dans l'ordonnance ne rentrent pas en conflit avec les allergies du patient (croisement de données avec un prompt spécifique).

---

## 👩‍💻 Developer 2B : Axe "Assistant RAG Intelligent & Guardrails de Sécurité"
*Dossiers de travail : `backend/app/ai/graphs/assistant_graph.py` et `backend/app/ai/rag/`*

Votre but est de créer le cerveau conversationnel (Chatbot) qui répond aux patients sans **jamais** halluciner ni donner de diagnostics.

**Tâches IA :**
1. **RAG Avancé (Vectorisation FAISS) :**
   - Actuellement, le RAG est basique. Vous devez implémenter un système de **Chunking sémantique** (découper les gros protocoles en petits morceaux pertinents) avant de les mettre dans FAISS.
2. **Mémoire Conversationnelle (LangChain Memory) :**
   - Intégrer une mémoire dans l'Assistant pour qu'il se souvienne du contexte des 5 derniers messages du patient lors d'une même session.
3. **Sécurité Anti-Hallucination & Guardrails (`output_validator.py`) :**
   - Créer un deuxième appel LLM (un Agent Critique) qui relit la réponse du premier LLM avant de l'envoyer au patient, pour vérifier qu'il ne s'improvise pas docteur ("Self-Reflection").
4. **Fusion RAG + Symptômes :**
   - Modifier `assistant_graph.py` pour qu'il analyse d'abord si la question contient un symptôme grave (ex: "J'ai mal"). Si oui, l'Assistant doit rediriger dynamiquement le flux vers le `symptom_graph.py` pour évaluer la gravité avant de répondre.

---

### Comment collaborer ce soir sans conflit ?
- **D2A** ne travaille **que** sur la partie Extraction de données (Lecture de documents -> Structuration). 
- **D2B** ne travaille **que** sur la partie Conversationnelle (Chatbot -> Base Vectorielle -> Filtres de sécurité).
- Ainsi, vous travaillez tous les deux sur des algorithmes IA complexes en LangChain/LangGraph, mais dans des fichiers séparés ! 

**Première étape pour vous deux :**
Dans le dossier `backend`, copiez le fichier `.env.example` en `.env` et mettez-y votre clé API `MISTRAL_API_KEY` pour pouvoir exécuter les scripts de tests !
