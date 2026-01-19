"""
Test data corrections for known labeling errors.
Applies corrections without modifying the original test data files.
"""

# Mapping of email IDs to their correct expected_category
# These are corrections for known labeling errors in dummy_emails.json
CATEGORY_CORRECTIONS = {
    "email_015": "uncategorized",  # Follow-up on contract (not a submission)
    "email_022": "uncategorized",  # Question about contract requirements
    "email_028": "uncategorized",  # Technical issue with upload
    "email_040": "uncategorized",  # Request for help finding internship
    "email_049": "uncategorized",  # Question about contract extension
    "email_054": "uncategorized",  # Resubmission of corrected contract (follow-up)
    "email_060": "uncategorized",  # Question about extension possibility
    "email_070": "uncategorized",  # Question about extension of ongoing internship
    "email_076": "uncategorized",  # Question about contract duration before submission
    "email_078": "uncategorized",  # Question about extending ongoing internship
    "email_080": "uncategorized",  # Technical issue with portal (not submission)
    "email_090": "uncategorized",  # Follow-up on previous issue
    "email_094": "uncategorized",  # Administrative question
    "email_100": "uncategorized",  # Unclear category based on content
}


def apply_corrections(emails: list) -> list:
    """
    Apply test data corrections to email list.
    
    Args:
        emails: List of email dictionaries with 'id' and 'expected_category' fields
        
    Returns:
        List with corrected expected_category values
    """
    corrected_emails = []
    for email in emails:
        email_copy = email.copy()
        email_id = email.get("id")
        
        if email_id in CATEGORY_CORRECTIONS:
            email_copy["expected_category"] = CATEGORY_CORRECTIONS[email_id]
        
        corrected_emails.append(email_copy)
    
    return corrected_emails
