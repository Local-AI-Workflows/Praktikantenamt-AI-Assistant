# Validation Workflow

Visual guide to how the validation script works.

## 4-Phase Workflow

```
┌─────────────────────────────────────────────────────────┐
│  workflow-validator validate --test-inbox test@test.de │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  INITIALIZATION                 │
        │  • Load config (YAML + env)     │
        │  • Health check SMTP/IMAP       │
        │  • Load 100 test emails         │
        └─────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  PHASE 1: SEND EMAILS           │
        │                                 │
        │  For each email:                │
        │  1. Generate UUID (uuid4)       │
        │  2. Embed in header + body      │
        │  3. Send via SMTP               │
        │  4. Track mapping (JSON)        │
        │                                 │
        │  Result: 100 emails sent        │
        └─────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  PHASE 2: WAIT FOR n8n          │
        │                                 │
        │  Sleep 60s (configurable)       │
        │  Progress bar: 1/60 ... 60/60   │
        │                                 │
        │  n8n workflow processes:        │
        │  • Categorize emails            │
        │  • Route to folders             │
        └─────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  PHASE 3: VALIDATE ROUTING      │
        │                                 │
        │  1. Connect IMAP                │
        │  2. List folders (4 expected)   │
        │  3. For each UUID:              │
        │     • Search all folders        │
        │     • Find location             │
        │     • Map folder → category     │
        │     • Compare vs expected       │
        │                                 │
        │  Result: 98 found, 2 missing    │
        └─────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  PHASE 4: REPORT & CLEANUP      │
        │                                 │
        │  1. Calculate metrics (sklearn) │
        │     • Accuracy: 94%             │
        │     • Per-category: P/R/F1      │
        │     • Confusion matrix          │
        │  2. Display results (Rich)      │
        │  3. Export JSON/CSV             │
        │  4. Delete test emails (opt)    │
        └─────────────────────────────────┘
                          │
                          ▼
                   ✅ Complete!
```

## Email Flow

```
Test Email (JSON)
      │
      │ [UUID Generated]
      ▼
UUID: 550e8400-e29b-41d4-a716-446655440000
      │
      │ [Embed in Email]
      ▼
┌─────────────────────────────────────┐
│ From: student@haw.de                │
│ To: test@test.de                    │
│ Subject: Praktikumsvertrag ...      │
│ X-Test-UUID: 550e8400-...           │  ◄── Custom Header
│                                     │
│ Sehr geehrtes Praktikantenamt,      │
│ ...                                 │
│                                     │
│ [TEST-ID: 550e8400-e29b-...]        │  ◄── Body Footer
└─────────────────────────────────────┘
      │
      │ [Send via SMTP]
      ▼
  Test Inbox
      │
      │ [n8n processes]
      ▼
n8n Workflow:
  1. Categorize (LLM)
  2. Route to folder
      │
      │ [Move to folder]
      ▼
INBOX.Contract_Submission  ◄── Email lands here
      │
      │ [IMAP search by UUID]
      ▼
Validation:
  Found in: INBOX.Contract_Submission
  Expected: contract_submission
  Predicted: contract_submission
  ✅ Correct!
```

## Folder Mapping

```
┌────────────────────────────────────────────────────────┐
│  IMAP Folders (n8n output)  →  Categories (expected)  │
├────────────────────────────────────────────────────────┤
│  INBOX.Contract_Submission  →  contract_submission     │
│  INBOX.International_...    →  international_office... │
│  INBOX.Postponement_Req...  →  internship_postponement│
│  INBOX.Uncategorized        →  uncategorized          │
└────────────────────────────────────────────────────────┘

Configuration: workflow_validator/config/settings.yaml

folder_mappings:
  - folder_name: "INBOX.Contract_Submission"
    category: "contract_submission"
  ...
```

## UUID Tracking

```
UUID Mapping (results/uuid_mapping.json):

{
  "550e8400-e29b-41d4-a716-446655440000": {
    "email_id": "email_001",
    "expected_category": "contract_submission",
    "sent_timestamp": "2026-01-07T14:25:30.123456",
    "subject": "Praktikumsvertrag zur Unterschrift",
    "sender": "max.mueller@htwg-konstanz.de"
  },
  ...
}

Used for:
• Matching sent emails with found emails
• Debugging (find which email has which UUID)
• Audit trail
```

## Validation Metrics

```
From sklearn:
  y_true = [expected_category for each email]
  y_pred = [predicted_category from folder]

accuracy_score(y_true, y_pred)
  → 94.0%

precision_recall_fscore_support(y_true, y_pred)
  → Per-category: P/R/F1

confusion_matrix(y_true, y_pred)
  → 4x4 matrix showing misclassifications

Reuses existing Validator class from categorization/
```

## Error Handling

```
┌─────────────────────────────────────┐
│  Potential Errors                   │
├─────────────────────────────────────┤
│  ✗ SMTP connection failed           │
│    → Check host/port/credentials    │
│    → Fail fast, clear error message │
│                                     │
│  ✗ Email not found after wait       │
│    → Report in emails_not_found[]   │
│    → Continue with other emails     │
│    → Suggest: increase wait time    │
│                                     │
│  ✗ Email in unexpected folder       │
│    → Map to "uncategorized"         │
│    → Report as misclassified        │
│    → Show in misrouted emails list  │
└─────────────────────────────────────┘
```

## Output Structure

```
results/
├── workflow_validation_20260107_143025.json
│   └── Full report: metrics, locations, misroutes
│
├── email_locations_20260107_143025.csv
│   └── Per-email: uuid, folder, expected, predicted
│
└── uuid_mapping.json
    └── UUID → email metadata for debugging
```

## Command Variants

```bash
# Basic (60s wait, cleanup enabled)
workflow-validator validate --test-inbox test@test.de

# Custom wait time
workflow-validator validate --test-inbox test@test.de -w 120
                                                         ▲
                                                    2 minutes

# Keep emails (no cleanup)
workflow-validator validate --test-inbox test@test.de --no-cleanup
                                                        ▲
                                                   don't delete

# Verbose (show each email)
workflow-validator validate --test-inbox test@test.de -v
                                                        ▲
                                                   detailed

# Custom dataset
workflow-validator validate --test-inbox test@test.de -d quick_test.json
                                                        ▲
                                                   20 emails only
```

## Architecture Decisions

### Why UUID in both header AND body?
- Some mail servers strip custom headers
- Body footer is always preserved
- Search tries header first (faster), falls back to body

### Why wait instead of polling?
- Simpler implementation
- Configurable for different n8n speeds
- Avoids IMAP rate limiting

### Why sklearn for metrics?
- Reuses existing Validator class
- Industry-standard calculations
- Consistency with prompt-tester tool

### Why folder mapping vs direct category?
- n8n folder names may differ across setups
- Allows Gmail labels, Exchange folders, etc.
- Configurable without code changes
