"""
Génère des PDFs médicaux réalistes pour les tests du pipeline D2A.
Les documents suivent les standards français (ordonnance sécurisée, DCI obligatoire).
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "documents")
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

# --- Custom Styles ---
style_title = ParagraphStyle("title", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4)
style_subtitle = ParagraphStyle("subtitle", fontSize=10, fontName="Helvetica", alignment=TA_CENTER, spaceAfter=2, textColor=colors.grey)
style_section = ParagraphStyle("section", fontSize=10, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a3c6b"))
style_body = ParagraphStyle("body", fontSize=9, fontName="Helvetica", spaceAfter=2, leading=14)
style_small = ParagraphStyle("small", fontSize=7, fontName="Helvetica", textColor=colors.grey, spaceAfter=2)
style_warning = ParagraphStyle("warning", fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#c0392b"), spaceBefore=6)
style_right = ParagraphStyle("right", fontSize=9, fontName="Helvetica", alignment=TA_RIGHT)


def build_header_table(surgeon_name, rpps, speciality, etablissement, address):
    """Tableau d'en-tête standard ordonnance FR"""
    left = f"<b>{surgeon_name}</b><br/>{speciality}<br/>N° RPPS : {rpps}"
    right = f"<b>{etablissement}</b><br/>{address}"
    data = [[Paragraph(left, style_body), Paragraph(right, style_right)]]
    t = Table(data, colWidths=[9*cm, 9*cm])
    t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    return t


def generate_ordonnance_normale():
    """Ordonnance post-PTG sûre — cas de Sarah Miller"""
    path = os.path.join(OUTPUT_DIR, "ordonnance_post_ptg_safe.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(build_header_table(
        surgeon_name="Dr. Elena Ruiz", rpps="10012345678",
        speciality="Chirurgie Orthopédique et Traumatologique",
        etablissement="St. Joseph Medical Center",
        address="12 Rue du Général Faidherbe, 75012 Paris"
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3c6b"), spaceAfter=8))
    story.append(Paragraph("ORDONNANCE MÉDICALE", style_title))
    story.append(Paragraph("Ordonnance sécurisée — Document non reproductible", style_subtitle))
    story.append(Spacer(1, 0.3*cm))

    # Patient Info
    patient_data = [
        ["Patient :", "MILLER Sarah", "Date de naissance :", "15/03/1961"],
        ["Date :", "04/06/2025", "Allergie connue :", "PÉNICILLINE ⚠️"],
        ["Motif :", "Suites opératoires PTG Droite (J0)", "", ""]
    ]
    t = Table(patient_data, colWidths=[3*cm, 6*cm, 4*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0f4fa")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#1a3c6b")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("PRESCRIPTION", style_section))

    meds = [
        {
            "num": "1",
            "dci": "PARACÉTAMOL",
            "commercial": "(Doliprane®)",
            "dosage": "1 g",
            "forme": "Comprimé effervescent",
            "posologie": "1 comprimé MATIN, MIDI et SOIR",
            "duree": "14 jours ou selon douleur (EVA ≤ 4)",
            "note": "⚠️ Ne pas dépasser 4 g / 24h — Antalgique Palier 1",
            "classe": "Analgésique/Antipyrétique"
        },
        {
            "num": "2",
            "dci": "CÉLÉCOXIB",
            "commercial": "(Celebrex® 200mg)",
            "dosage": "200 mg",
            "forme": "Gélule",
            "posologie": "1 gélule le MATIN au milieu du repas",
            "duree": "14 jours",
            "note": "Prendre IMPÉRATIVEMENT au milieu du repas. Pas d'AINS supplémentaire.",
            "classe": "Anti-inflammatoire (AINS COX-2 sélectif)"
        },
        {
            "num": "3",
            "dci": "PANTOPRAZOLE",
            "commercial": "(Inexium® 20mg)",
            "dosage": "20 mg",
            "forme": "Comprimé gastro-résistant",
            "posologie": "1 comprimé le MATIN À JEUN",
            "duree": "14 jours",
            "note": "Gastroprotection — À prendre avant le Célécoxib.",
            "classe": "Inhibiteur de la pompe à protons (IPP)"
        },
        {
            "num": "4",
            "dci": "ÉNOXAPARINE SODIQUE",
            "commercial": "(Lovenox® 4000 UI/0.4mL)",
            "dosage": "4000 UI (40 mg/0.4 mL)",
            "forme": "Solution injectable SC",
            "posologie": "1 injection SOUS-CUTANÉE le SOIR",
            "duree": "14 jours — Prophylaxie thrombo-embolique",
            "note": "⚠️ Injection sous-cutanée — Alterner flanc gauche/droit. Surveillance plaquettes.",
            "classe": "Anticoagulant (HBPM)"
        }
    ]

    for m in meds:
        med_data = [
            [Paragraph(f"<b>{m['num']}. {m['dci']}</b> {m['commercial']} — {m['dosage']}", style_body),
             Paragraph(f"<i>Classe : {m['classe']}</i>", style_small)],
            [Paragraph(f"Forme : {m['forme']}", style_body), ""],
            [Paragraph(f"Posologie : <b>{m['posologie']}</b>", style_body), ""],
            [Paragraph(f"Durée : {m['duree']}", style_body), ""],
            [Paragraph(m['note'], style_warning if "⚠️" in m['note'] else style_body), ""]
        ]
        t = Table(med_data, colWidths=[12*cm, 6*cm])
        t.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#1a3c6b")),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dde8f5")),
            ("PADDING", (0,0), (-1,-1), 4),
            ("SPAN", (0,1), (1,1)),
            ("SPAN", (0,2), (1,2)),
            ("SPAN", (0,3), (1,3)),
            ("SPAN", (0,4), (1,4)),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.25*cm))

    story.append(Paragraph("CONTRE-INDICATIONS ABSOLUES", style_section))
    story.append(Paragraph(
        "NE PAS PRENDRE : Ibuprofène, Kétoprofène, Aspirine ou tout AINS sans avis médical. "
        "Pas de conduite automobile pendant le traitement analgésique fort.",
        style_body
    ))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Signature et cachet du médecin :", style_body))
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("Dr. Elena Ruiz — Paris, le 04/06/2025", style_body))
    story.append(Paragraph("Ordonnance valable 3 mois à compter de la date de rédaction.", style_small))

    doc.build(story)
    print(f"✅ Généré : {path}")
    return path


def generate_ordonnance_avec_conflit():
    """
    Ordonnance INTENTIONNELLEMENT DANGEREUSE pour tester l'Agent de Sécurité.
    Patient : Sarah Miller (allergie Pénicilline) + prescription d'Amoxicilline (béta-lactamine).
    Résultat attendu du Safety Checker : BLOCKED — Allergie détectée.
    """
    path = os.path.join(OUTPUT_DIR, "ordonnance_conflit_allergie.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(build_header_table(
        surgeon_name="Dr. Marc Bernard", rpps="10098765432",
        speciality="Médecine Générale",
        etablissement="Cabinet Médical Voltaire",
        address="55 Rue Voltaire, 75011 Paris"
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#c0392b"), spaceAfter=8))
    story.append(Paragraph("ORDONNANCE MÉDICALE", style_title))
    story.append(Spacer(1, 0.3*cm))

    patient_data = [
        ["Patient :", "MILLER Sarah", "Date de naissance :", "15/03/1961"],
        ["Date :", "10/06/2025", "Allergie connue :", "PÉNICILLINE ⚠️"],
        ["Motif :", "Suspicion d'infection cutanée post-opératoire", "", ""]
    ]
    t = Table(patient_data, colWidths=[3*cm, 6*cm, 4*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#fdf0ef")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#c0392b")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey), ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("PRESCRIPTION", style_section))

    # DANGER: Amoxicilline = Béta-lactamine = Famille Pénicilline
    conflict_med = [
        [Paragraph("<b>1. AMOXICILLINE</b> (Clamoxyl® 1g) — 1 g", style_body),
         Paragraph("<i>Classe : Antibiotique béta-lactamine (famille Pénicilline)</i>", style_small)],
        [Paragraph("Forme : Comprimé dispersible", style_body), ""],
        [Paragraph("Posologie : <b>1 comprimé MATIN et SOIR au cours du repas</b>", style_body), ""],
        [Paragraph("Durée : 7 jours", style_body), ""],
    ]
    t = Table(conflict_med, colWidths=[12*cm, 6*cm])
    t.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#c0392b")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#fad9d7")),
        ("PADDING", (0,0), (-1,-1), 4),
        ("SPAN", (0,1), (1,1)), ("SPAN", (0,2), (1,2)), ("SPAN", (0,3), (1,3)),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(
        "⚠️ CE DOCUMENT EST UN DOCUMENT DE TEST — L'amoxicilline est une béta-lactamine "
        "contre-indiquée chez les patients allergiques à la pénicilline. "
        "Ce cas doit être BLOQUÉ par le Safety Checker IA.",
        style_warning
    ))

    doc.build(story)
    print(f"✅ Généré : {path}")
    return path


def generate_compte_rendu_operatoire():
    """Compte-rendu opératoire post-PTG — pour tester l'extraction de restrictions physiques"""
    path = os.path.join(OUTPUT_DIR, "compte_rendu_operatoire_ptg.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(build_header_table(
        surgeon_name="Dr. Elena Ruiz", rpps="10012345678",
        speciality="Chirurgie Orthopédique — St. Joseph Medical Center",
        etablissement="St. Joseph Medical Center", address="12 Rue du Général Faidherbe, 75012 Paris"
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a3c6b"), spaceAfter=8))
    story.append(Paragraph("COMPTE-RENDU OPÉRATOIRE", style_title))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["Patient :", "MILLER Sarah (née le 15/03/1961)"],
        ["Date d'intervention :", "04/06/2025 — 08h30 à 10h45"],
        ["Chirurgien :", "Dr. Elena Ruiz"],
        ["Anesthésiste :", "Dr. Thomas Leblanc"],
        ["Type d'anesthésie :", "Rachianesthésie (ALR)"],
        ["Intervention :", "Prothèse Totale du Genou (PTG) Droite — Cimentée"],
        ["Indication :", "Gonarthrose tricompartimentale droite invalidante — échec traitement médical"],
    ]
    t = Table(info_data, colWidths=[5.5*cm, 12.5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9), ("PADDING", (0,0), (-1,-1), 4),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0f4fa")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#1a3c6b")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("DÉROULEMENT OPÉRATOIRE", style_section))
    story.append(Paragraph(
        "Installation en décubitus dorsal. Garrot pneumatique à la racine de cuisse droite gonflé à 300 mmHg. "
        "Voie d'abord antérieure para-patellaire médiale. Arthrotomie. Excision des ménisques et du LCA. "
        "Coupes osseuses fémorales et tibiales réalisées aux ancillaires conventionnels. "
        "Pose d'une prothèse totale <b>cimentée bicompartimentale</b> (modèle NexGen, Zimmer Biomet). "
        "Taille prothèse fémur : E — Taille tibia : 4 — Épaisseur insert : 10 mm. "
        "Rotule non resurfacée mais dénervée (électrocoagulation). "
        "Lavage articulaire abondant au sérum physiologique. "
        "Fermeture plan par plan. Pose d'un redon intra-articulaire. Pansement compressif.",
        style_body
    ))

    story.append(Paragraph("CONSIGNES POST-OPÉRATOIRES IMMÉDIATES", style_section))
    consignes = [
        "Appui total autorisé immédiatement avec 2 béquilles — OBLIGATOIRE",
        "Pas de conduite automobile avant J+28 minimum",
        "Kinésithérapie débutant à J+1 (flexion passive progressive)",
        "Ablation du redon à J+1",
        "Ablation agrafes à J+14",
        "Prophylaxie anti-thrombotique par HBPM : 14 jours",
        "Consultation de contrôle à 6 semaines post-op avec radio de contrôle",
    ]
    for c in consignes:
        story.append(Paragraph(f"• {c}", style_body))

    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph("Dr. Elena Ruiz — Paris, le 04/06/2025", style_body))

    doc.build(story)
    print(f"✅ Généré : {path}")
    return path


if __name__ == "__main__":
    print("📄 Génération des PDFs médicaux de test...")
    generate_ordonnance_normale()
    generate_ordonnance_avec_conflit()
    generate_compte_rendu_operatoire()
    print("\n✅ Tous les PDFs sont dans backend/documents/")
    print("   - ordonnance_post_ptg_safe.pdf      → Ordonnance normale (doit être SAFE)")
    print("   - ordonnance_conflit_allergie.pdf    → Ordonnance dangereuse (doit être BLOCKED)")
    print("   - compte_rendu_operatoire_ptg.pdf    → Compte-rendu opératoire")
