"""
Dummy PDF attachment generator for workflow validation testing.

Generates simple PDF bytes simulating a Praktikumsvertrag (internship contract).
Uses fpdf2 when available; falls back to a static minimal valid PDF otherwise.
"""


def generate_dummy_contract_pdf(
    student_name: str = "Max Mustermann",
    company_name: str = "Muster GmbH",
    start_date: str = "01.03.2026",
    end_date: str = "31.08.2026",
) -> bytes:
    """
    Generate a simple PDF simulating a Praktikumsvertrag.

    Args:
        student_name: Name of the student (appears in PDF content)
        company_name: Name of the internship company
        start_date: Internship start date (DD.MM.YYYY)
        end_date: Internship end date (DD.MM.YYYY)

    Returns:
        PDF content as bytes
    """
    try:
        return _generate_with_fpdf2(student_name, company_name, start_date, end_date)
    except ImportError:
        return _get_static_minimal_pdf()


def _generate_with_fpdf2(
    student_name: str,
    company_name: str,
    start_date: str,
    end_date: str,
) -> bytes:
    """Generate PDF using the fpdf2 library."""
    from fpdf import FPDF  # type: ignore[import]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PRAKTIKUMSVERTRAG", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)

    # Subtitle
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0, 7, "Hochschule fuer Angewandte Wissenschaften Hamburg",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.cell(0, 7, "Praktikantenamt", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)

    # Key-value rows
    rows = [
        ("Student:", student_name),
        ("Unternehmen:", company_name),
        ("Praktikumsbeginn:", start_date),
        ("Praktikumsende:", end_date),
    ]
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(55, 8, label, new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0,
        6,
        (
            "Dieser Vertrag bestaetigt das Pflichtpraktikum gemaess Studienordnung. "
            "Das Unternehmen verpflichtet sich, den Studierenden entsprechend der "
            "vereinbarten Aufgaben zu beschaeftigen."
        ),
    )

    return bytes(pdf.output())


def _get_static_minimal_pdf() -> bytes:
    """
    Return a minimal valid PDF as bytes (fallback when fpdf2 is not installed).

    This is a PDF 1.4 compliant single-page blank document.
    """
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF"
    )


def extract_email_metadata_for_pdf(subject: str, sender: str) -> dict:
    """
    Extract student/company hints from email metadata to produce a contextual PDF.

    Attempts to derive a student name from the sender address
    (e.g. max.mueller@student.haw.de → "Max Mueller").
    Falls back to generic defaults when extraction is not possible.

    Returns:
        Dict with keys: student_name, company_name, start_date, end_date
    """
    student_name = "Max Mustermann"
    if "@" in sender:
        local_part = sender.split("@")[0]
        parts = local_part.replace(".", " ").replace("_", " ").split()
        if len(parts) >= 2:
            student_name = " ".join(p.capitalize() for p in parts[:2])

    return {
        "student_name": student_name,
        "company_name": "Praktikumsbetrieb GmbH",
        "start_date": "01.03.2026",
        "end_date": "31.08.2026",
    }
