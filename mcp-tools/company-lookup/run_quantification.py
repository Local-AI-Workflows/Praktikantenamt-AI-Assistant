#!/usr/bin/env python3
"""
Standalone quantification script for company lookup.

Usage:
    python run_quantification.py                    # Uses generated test data
    python run_quantification.py data/companies.xlsx  # Uses specific Excel file

This script runs a comprehensive test suite against the fuzzy matching engine
and reports accuracy metrics by category.
"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_quantification import run_quantification_report, TEST_CASES


def main():
    """Run quantification tests."""
    # Check for Excel file argument
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
        if not Path(excel_file).exists():
            print(f"Error: File not found: {excel_file}")
            sys.exit(1)
    else:
        # Create test data
        print("No Excel file specified, creating test data...")
        excel_file = create_test_data()

    print(f"\nRunning quantification on: {excel_file}")
    print(f"Test cases: {len(TEST_CASES)}")

    success = run_quantification_report(excel_file)

    if success:
        print("\n✓ Quantification PASSED (>= 70% accuracy)")
    else:
        print("\n✗ Quantification FAILED (< 70% accuracy)")

    sys.exit(0 if success else 1)


def create_test_data() -> str:
    """Create test Excel file with sample data."""
    from tempfile import NamedTemporaryFile
    from openpyxl import Workbook

    tmp = NamedTemporaryFile(suffix=".xlsx", delete=False)

    workbook = Workbook()

    # Whitelist
    ws = workbook.active
    ws.title = "Whitelist"
    ws.append(["Company Name", "Category", "Notes"])
    whitelist = [
        ("Siemens AG", "Technology", "Major German corporation"),
        ("BMW Group", "Automotive", "Car manufacturer"),
        ("SAP SE", "Software", "Enterprise software"),
        ("Volkswagen AG", "Automotive", "Auto manufacturer"),
        ("Bosch GmbH", "Technology", "Engineering company"),
        ("Deutsche Bank AG", "Finance", "Investment banking"),
        ("Deutsche Telekom AG", "Telecom", "Telecom provider"),
        ("E.ON SE", "Energy", "Energy company"),
        ("Allianz SE", "Insurance", "Insurance"),
        ("BASF SE", "Chemical", "Chemicals"),
    ]
    for company in whitelist:
        ws.append(company)

    # Blacklist
    ws2 = workbook.create_sheet("Blacklist")
    ws2.append(["Company Name", "Category", "Notes"])
    blacklist = [
        ("Fake Company GmbH", "Unknown", "Known scam"),
        ("Scam Industries Ltd", "Unknown", "Fraudulent"),
        ("Betrug & Partner KG", "Unknown", "Deceptive"),
        ("Phantomfirma SE", "Unknown", "Shell company"),
    ]
    for company in blacklist:
        ws2.append(company)

    workbook.save(tmp.name)
    print(f"Created test data: {tmp.name}")
    print(f"  Whitelist: {len(whitelist)} companies")
    print(f"  Blacklist: {len(blacklist)} companies")

    return tmp.name


if __name__ == "__main__":
    main()
