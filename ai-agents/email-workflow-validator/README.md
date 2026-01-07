# n8n Email Workflow Validator

Python validation script for testing n8n email categorization workflows. Sends test emails via SMTP, waits for n8n processing, then validates correct routing by checking IMAP folder placement.

## Overview

This tool validates that n8n workflows correctly categorize and route emails by:
1. **Sending** test emails with embedded tracking UUIDs
2. **Waiting** for n8n to process and route emails to folders
3. **Validating** email locations via IMAP folder inspection
4. **Reporting** accuracy metrics (precision, recall, F1, confusion matrix)

## Features

- ✅ **RFC4122 UUID tracking** - Unique identifiers embedded in headers and body
- ✅ **IMAP folder validation** - Checks email routing to correct folders
- ✅ **Sklearn-based metrics** - Reuses categorization framework's accuracy calculations
- ✅ **Rich console output** - Progress bars, tables, color-coded results
- ✅ **JSON/CSV export** - Detailed reports with per-email validation results
- ✅ **Configurable wait time** - Adjust for n8n processing speed
- ✅ **Optional cleanup** - Delete test emails after validation
- ✅ **Health checks** - Validate SMTP/IMAP connectivity before running

## Architecture

Extends the existing `categorization/` prompt testing framework:
- Reuses `Email`, `ValidationReport`, `Metrics` Pydantic models
- Extends `Validator` class for workflow-specific validation
- Mirrors CLI/config/output patterns from `prompt-tester`

## Installation

```bash
cd ai-agents/email-workflow-validator
pip install -e .
```

This installs the `workflow-validator` CLI command.

## Configuration

### 1. Create/Edit `workflow_validator/config/settings.yaml`

```yaml
imap:
  host: "imap.example.com"
  port: 993
  username: "test-inbox@example.com"
  password: "${IMAP_PASSWORD}"
  use_ssl: true
  mailbox: "INBOX"

smtp:
  host: "smtp.example.com"
  port: 587
  username: "test-sender@example.com"
  password: "${SMTP_PASSWORD}"
  use_tls: true
  from_address: "test-sender@example.com"

folder_mappings:
  - folder_name: "INBOX.Contract_Submission"
    category: "contract_submission"
  - folder_name: "INBOX.International_Questions"
    category: "international_office_question"
  - folder_name: "INBOX.Postponement_Requests"
    category: "internship_postponement"
  - folder_name: "INBOX.Uncategorized"
    category: "uncategorized"

validation:
  wait_time_seconds: 60
  cleanup_after_test: true
  uuid_storage_path: "results/uuid_mapping.json"
```

### 2. Set Environment Variables

```bash
# Required: IMAP and SMTP passwords
export IMAP_PASSWORD="your-imap-password"
export SMTP_PASSWORD="your-smtp-password"
```

**Security Note:** Never commit passwords to git. Use environment variables or secrets management.

## Usage

### Run Full Validation

```bash
workflow-validator validate --test-inbox test@example.com
```

This will:
1. Load 100 test emails from `../categorization/test_data/dummy_emails.json`
2. Send them with UUIDs to `test@example.com`
3. Wait 60 seconds (configurable)
4. Check IMAP folders for correct routing
5. Generate accuracy report
6. Export results to `results/`
7. Delete test emails (optional)

### Common Options

```bash
# Custom wait time (2 minutes)
workflow-validator validate --test-inbox test@example.com -w 120

# Keep emails for manual inspection
workflow-validator validate --test-inbox test@example.com --no-cleanup

# Use different dataset
workflow-validator validate --test-inbox test@example.com -d custom_emails.json

# Verbose output
workflow-validator validate --test-inbox test@example.com -v

# Custom config file
workflow-validator validate --test-inbox test@example.com -c custom_config.yaml
```

### Test Connections

```bash
workflow-validator check-connection
```

Validates SMTP and IMAP connectivity before running full validation.

### Find Specific Email

```bash
workflow-validator find-email 550e8400-e29b-41d4-a716-446655440000
```

Debug command to locate a specific test email by UUID.

## Folder Mapping

The tool maps IMAP folders to email categories based on `folder_mappings` in config:

| IMAP Folder | Category |
|-------------|----------|
| `INBOX.Contract_Submission` | `contract_submission` |
| `INBOX.International_Questions` | `international_office_question` |
| `INBOX.Postponement_Requests` | `internship_postponement` |
| `INBOX.Uncategorized` | `uncategorized` |

**Adjust folder names** in `settings.yaml` to match your n8n workflow's IMAP folder structure.

### Common IMAP Folder Formats

- **Standard IMAP:** `INBOX.Subfolder`
- **Gmail:** `[Gmail]/Label_Name` or `Label_Name`
- **Courier:** `INBOX/Subfolder`

## UUID Embedding Strategy

For reliable email tracking, UUIDs are embedded in **two locations**:

1. **Custom Header** (Primary)
   ```
   X-Test-UUID: 550e8400-e29b-41d4-a716-446655440000
   ```

2. **Body Footer** (Fallback)
   ```
   [Original email body]

   [TEST-ID: 550e8400-e29b-41d4-a716-446655440000]
   ```

The IMAP client searches both locations to handle servers that strip custom headers.

## Output

### Console Output

```
Running health checks...
✓ SMTP server accessible (smtp.example.com)
✓ IMAP server accessible (imap.example.com)

Loaded 100 test emails

Phase 1: Sending test emails
✓ Sent 100/100 emails

Phase 2: Waiting 60s for n8n processing
✓ Wait complete

Phase 3: Validating email routing
✓ Found 98/100 emails
⚠ 2 emails not found

Validation Results
Overall Accuracy: 94.0%
Correct: 92/98  Incorrect: 6/98
Sent: 100  Found: 98  Not Found: 2

Per-Category Metrics
┌─────────────────────────────┬───────────┬────────┬────────┬─────────┐
│ Category                    │ Precision │ Recall │ F1     │ Support │
├─────────────────────────────┼───────────┼────────┼────────┼─────────┤
│ contract_submission         │ 0.97      │ 0.93   │ 0.95   │ 28      │
│ international_office_...    │ 0.90      │ 0.95   │ 0.92   │ 20      │
│ internship_postponement     │ 0.92      │ 0.92   │ 0.92   │ 11      │
│ uncategorized               │ 0.94      │ 0.94   │ 0.94   │ 39      │
└─────────────────────────────┴───────────┴────────┴────────┴─────────┘

Misrouted Emails
  • email_015: contract_submission → uncategorized (Found in folder: INBOX.Uncategorized)
  • email_042: international_office_question → uncategorized (Found in folder: INBOX.Uncategorized)
  ...

Results saved to:
  • JSON: results/workflow_validation_20260107_143025.json
  • CSV: results/email_locations_20260107_143025.csv

Phase 4: Cleaning up test emails
✓ Deleted 100 test emails
```

### JSON Output (`results/workflow_validation_*.json`)

```json
{
  "overall_accuracy": 0.94,
  "total_emails": 98,
  "correct_predictions": 92,
  "incorrect_predictions": 6,
  "per_category_metrics": {
    "contract_submission": {
      "precision": 0.97,
      "recall": 0.93,
      "f1_score": 0.95,
      "support": 28
    },
    ...
  },
  "confusion_matrix": [[26, 0, 0, 2], ...],
  "email_locations": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "email_id": "email_001",
      "found_in_folder": "INBOX.Contract_Submission",
      "expected_category": "contract_submission",
      "predicted_category": "contract_submission",
      "is_correct": true,
      "validation_timestamp": "2026-01-07T14:30:45.123456"
    },
    ...
  ],
  "emails_not_found": ["uuid-str-1", "uuid-str-2"],
  "total_sent": 100,
  "total_found": 98,
  "wait_time_seconds": 60
}
```

### CSV Output (`results/email_locations_*.csv`)

```csv
uuid,email_id,found_in_folder,expected_category,predicted_category,is_correct,validation_timestamp
550e8400-e29b-41d4-a716-446655440000,email_001,INBOX.Contract_Submission,contract_submission,contract_submission,True,2026-01-07T14:30:45
...
```

## Test Data

Uses the same 100 test emails from the categorization framework:
- Path: `../categorization/test_data/dummy_emails.json`
- Distribution: 30 contract submissions, 21 international questions, 12 postponements, 37 uncategorized
- Includes edge cases (English emails, minimal content, multi-intent)

## Troubleshooting

### "SMTP server not accessible"
- Check `smtp.host`, `smtp.port`, `smtp.username` in config
- Verify `SMTP_PASSWORD` environment variable is set
- Try telnet: `telnet smtp.example.com 587`
- Check firewall/network restrictions

### "IMAP server not accessible"
- Check `imap.host`, `imap.port`, `imap.username` in config
- Verify `IMAP_PASSWORD` environment variable is set
- Ensure IMAP is enabled on email account
- Try telnet: `telnet imap.example.com 993`

### "Emails not found"
- **n8n not running:** Check n8n workflow is active
- **Insufficient wait time:** Increase with `-w 120` (2 minutes)
- **Wrong folder mappings:** Check folder names match n8n output
- **UUID stripped:** Check email body for `[TEST-ID: ...]` footer

### "Environment variable not set"
```bash
# Set passwords before running
export IMAP_PASSWORD="your-password"
export SMTP_PASSWORD="your-password"
```

### "Invalid configuration"
- Validate YAML syntax (indentation, colons, quotes)
- Check all required fields are present
- Test config: `workflow-validator check-connection`

## Development

### Project Structure

```
workflow_validator/
├── cli.py                # CLI entry point
├── config/
│   ├── settings.yaml     # Default configuration
│   └── manager.py        # Config loader with env vars
├── data/
│   ├── schemas.py        # Pydantic models
│   └── loader.py         # Email data loading
├── email/
│   ├── smtp_client.py    # Email sending
│   └── imap_client.py    # Email retrieval
├── core/
│   ├── sender.py         # Send orchestration
│   ├── validator.py      # Validation logic
│   └── uuid_tracker.py   # UUID mapping
└── output/
    ├── formatter.py      # Console display
    └── exporter.py       # JSON/CSV export
```

### Running Tests

```bash
# Format code
black workflow_validator/

# Type checking
mypy workflow_validator/

# Unit tests (TODO)
pytest tests/
```

## Integration with n8n

### Expected n8n Workflow

1. **Email Trigger** - Monitor test inbox for incoming emails
2. **Categorization** - Call LLM or prompt-based categorization
3. **Routing** - Move email to folder based on category:
   - `contract_submission` → `INBOX.Contract_Submission`
   - `international_office_question` → `INBOX.International_Questions`
   - `internship_postponement` → `INBOX.Postponement_Requests`
   - `uncategorized` → `INBOX.Uncategorized`

### Workflow Setup Tips

- **Test inbox:** Use dedicated test account (not production)
- **Folder creation:** Ensure IMAP folders exist before routing
- **Error handling:** Log failed categorizations for debugging
- **Timing:** Adjust wait time based on workflow speed

## Design Rationale

1. **Separate module** - Distinct from prompt testing (different purpose)
2. **Extend existing Validator** - Reuse sklearn metrics calculation
3. **Import existing schemas** - Share Email/ValidationReport definitions
4. **UUID dual strategy** - Header + body for reliability across mail servers
5. **Folder mapping** - Configurable for different n8n setups
6. **Optional cleanup** - Keep emails for debugging if needed

## Related Tools

- **[prompt-tester](../categorization/)** - Test LLM categorization prompts
- **n8n workflows** - Orchestrate email processing (planned)

## License

Part of the Praktikantenamt AI-Assistant project.

## Contact

For issues or questions, refer to the main project README.
