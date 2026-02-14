"""
Generate one PDF per contract from a dummy_contracts JSON dataset.

Usage:
    python test_data/generate_pdfs.py [input_json] [output_dir]

Defaults:
    input_json  = test_data/dummy_contracts_preview.json
    output_dir  = test_data/pdfs
"""

import json
import sys
from pathlib import Path

from fpdf import FPDF

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_INPUT = Path(__file__).parent / "dummy_contracts_preview.json"
DEFAULT_OUTPUT = Path(__file__).parent / "pdfs"

FONT_SIZE_BODY = 9
FONT_SIZE_SMALL = 7
LINE_H = 5          # line height in mm
MARGIN = 15         # page margin in mm


class ContractPDF(FPDF):
    """Minimal PDF wrapper with a fixed-width font for contract text."""

    def header(self) -> None:
        pass  # no automatic header

    def footer(self) -> None:
        self.set_y(-10)
        self.set_font("Courier", "I", FONT_SIZE_SMALL)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4, f"Seite {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def _make_pdf(contract_id: str, text: str, meta: dict, ground_truth: dict) -> FPDF:
    pdf = ContractPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # --- metadata strip at top ---
    pdf.set_font("Helvetica", "B", FONT_SIZE_SMALL)
    pdf.set_fill_color(230, 230, 230)
    status = ground_truth.get("expected_status", "")
    fmt = meta.get("format", "")
    difficulty = meta.get("difficulty", "")
    pdf.cell(
        0, 5,
        f"  ID: {contract_id}   |   Format: {fmt}   |   Status: {status}   |   Difficulty: {difficulty}",
        fill=True, new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(3)

    # --- contract body in monospace ---
    pdf.set_font("Courier", "", FONT_SIZE_BODY)
    # fpdf2 multi_cell handles \n natively; width=0 means full page width
    pdf.multi_cell(0, LINE_H, text, align="L")

    return pdf


def generate_pdfs(input_path: Path, output_dir: Path) -> None:
    print(f"Reading contracts from: {input_path}")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    contracts = data.get("contracts", [])
    total = len(contracts)
    print(f"Found {total} contracts — generating PDFs in: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, c in enumerate(contracts, 1):
        contract_id = c["id"]
        text = c["text"]
        meta = c.get("metadata") or {}
        gt = c.get("ground_truth") or {}

        pdf = _make_pdf(contract_id, text, meta, gt)

        out_file = output_dir / f"{contract_id}.pdf"
        pdf.output(str(out_file))

        if i % 10 == 0 or i == total:
            print(f"  [{i}/{total}] {out_file.name}")

    print(f"\nDone. {total} PDFs written to {output_dir}/")


if __name__ == "__main__":
    input_json = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    generate_pdfs(input_json, output_dir)
