"""Generate the FICTIONAL sample discharge summary used by the document demo.

    python -m seed.make_sample_docs      (writes seed/documents/sarah_discharge_summary.pdf)

Not a real patient, not real clinical advice.
"""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).parent / "documents"

SECTIONS = [
    ("", [
        "St. Joseph Medical Center - Department of Orthopedic Surgery",
        "FICTIONAL DOCUMENT FOR A HACKATHON DEMO - NOT A REAL PATIENT",
    ]),
    ("DISCHARGE SUMMARY", [
        "Patient: Sarah Miller    Age: 64    Sex: F",
        "Procedure: Total knee replacement (arthroplasty), RIGHT knee",
        "Date of surgery: 06/10/2026    Date of discharge: 08/10/2026",
        "Surgeon: Dr. Elena Ruiz",
        "Allergies: Penicillin (rash)",
        "Course: uncomplicated. Mobilised day 1 with crutches. Wound dry at discharge.",
    ]),
    ("MEDICATIONS AT DISCHARGE", [
        "1. Paracetamol 1 g by mouth at 08:00, 14:00 and 20:00 for pain (maximum 4 g per day).",
        "2. Celecoxib 200 mg by mouth once daily at 09:00 with food (anti-inflammatory).",
        "3. Pantoprazole 20 mg by mouth once daily at 08:00 (stomach protection).",
        "4. Enoxaparin 40 mg subcutaneous injection once daily at 20:00 for 14 days (prevention of blood clots).",
        "5. Cefuroxime 500 mg by mouth three times daily at 08:00, 14:00 and 20:00 for 7 days (antibiotic).",
        "If a dose is missed: do not take two doses together; inform the care team.",
        "Do not take ibuprofen or other NSAIDs in addition to celecoxib unless the surgeon agrees.",
    ]),
    ("ACTIVITY", [
        "Weight bearing as tolerated with two crutches for 14 days.",
        "No driving for at least 4 weeks.",
        "Keep the leg elevated when resting; ice 15-20 minutes after exercises.",
    ]),
    ("REHABILITATION EXERCISES", [
        "Knee bends 2 x 10, morning (09:30) and evening (18:00).",
        "Straight-leg raises 2 x 10, morning (09:30) and evening (18:00).",
        "Ankle pumps 3 x 15, at 09:30, 13:00 and 18:00.",
    ]),
    ("WOUND CARE", [
        "Waterproof dressing: showering allowed with the dressing on. No bath or swimming until staples are removed.",
        "Do not change the dressing unless instructed. Daily wound photo in the SurgiGuard app.",
    ]),
    ("FOLLOW-UP APPOINTMENTS", [
        "Physiotherapy: 14/10/2026 at 15:00.",
        "Staple removal: 16/10/2026 at 09:00.",
        "Follow-up with Dr. Ruiz: 20/10/2026 at 10:30.",
    ]),
    ("WARNING SIGNS - contact the surgeon's office the same day", [
        "Fever over 38 C, spreading redness, increasing warmth or swelling, drainage or bad smell from the wound,",
        "pain that keeps increasing.",
    ]),
    ("EMERGENCY - call 112 immediately", [
        "Sudden shortness of breath or chest pain, calf pain or swelling in either leg, fainting, heavy bleeding.",
    ]),
]


def build() -> Path:
    OUT.mkdir(exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    for title, lines in SECTIONS:
        if title:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in lines:
            pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
    path = OUT / "sarah_discharge_summary.pdf"
    pdf.output(str(path))
    return path


if __name__ == "__main__":
    print(build())
