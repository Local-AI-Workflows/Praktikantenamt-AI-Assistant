# Quick Start Guide

Get the n8n email workflow validator running in 5 minutes.

## Prerequisites

- Python 3.10+
- **Gmail account** (for sending test emails)
- **Test inbox** (separate email account where n8n receives/routes emails)
- n8n workflow set up and running

## Step 1: Install

```bash
cd ai-agents/email-workflow-validator
pip install -e .
```

## Step 2: Configure

Edit `workflow_validator/config/settings.yaml`:

```yaml
# SENDER: Your Gmail (sends 100 test emails)
smtp:
  host: "smtp.gmail.com"  # Fixed for Gmail
  username: "your-gmail@gmail.com"  # Your Gmail address
  from_address: "your-gmail@gmail.com"

# RECEIVER: Test inbox (where n8n receives and routes emails)
imap:
  host: "imap.example.com"  # Your test inbox IMAP server
  username: "test-inbox@example.com"  # Your test inbox email

folder_mappings:
  - folder_name: "INBOX.Contract_Submission"  # Adjust to match n8n folders
    category: "contract_submission"
  # ... (adjust folder names to match your n8n setup)
```

## Step 3: Set Passwords (in .env file)

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.template .env

# Edit with your credentials
nano .env  # or use your favorite editor
```

Add your passwords to `.env`:

```ini
# Gmail App Password (NOT your regular Gmail password!)
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Test inbox password
IMAP_PASSWORD=test-inbox-password
```

**✅ The .env file is gitignored** - your secrets are safe!

### How to Get Gmail App Password

1. Enable 2-Step Verification: [Google Account Security](https://myaccount.google.com/security)
2. Generate App Password: [App Passwords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and your device
4. Copy the 16-character password (format: `xxxx-xxxx-xxxx-xxxx`)
5. Add to `.env` file as `GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx`

## Step 4: Test Connection

```bash
workflow-validator check-connection
```

Expected output:
```
✓ SMTP connection successful
✓ IMAP connection successful
```

## Step 5: Run Validation

```bash
workflow-validator validate --test-inbox test@gmail.com
```

This will:
1. Send 100 test emails
2. Wait 60 seconds
3. Validate routing
4. Show accuracy report

## Expected Results

```
Phase 1: Sending test emails
✓ Sent 100/100 emails

Phase 2: Waiting 60s for n8n processing
✓ Wait complete

Phase 3: Validating email routing
✓ Found 98/100 emails

Validation Results
Overall Accuracy: 94.0%
```

## Troubleshooting

### Connection Failed?

```bash
# Check IMAP manually
telnet imap.gmail.com 993

# Check SMTP manually
telnet smtp.gmail.com 587
```

### Emails Not Found?

- Check n8n workflow is running
- Increase wait time: `workflow-validator validate --test-inbox test@gmail.com -w 120`
- Check folder names match n8n output

### Gmail-Specific Setup

1. Enable IMAP: Gmail Settings → Forwarding and POP/IMAP → Enable IMAP
2. Create App Password: Google Account → Security → 2-Step Verification → App passwords
3. Use labels as folders: `folder_name: "label_name"` (no INBOX prefix)

## Next Steps

- Adjust wait time for your n8n speed
- Customize folder mappings
- Review detailed results in `results/` directory
- Keep emails for inspection: `--no-cleanup` flag

## Common Commands

```bash
# Basic validation
workflow-validator validate --test-inbox test@example.com

# With custom wait time
workflow-validator validate --test-inbox test@example.com -w 120

# Keep emails (don't delete)
workflow-validator validate --test-inbox test@example.com --no-cleanup

# Verbose output
workflow-validator validate --test-inbox test@example.com -v

# Find specific email
workflow-validator find-email 550e8400-e29b-41d4-a716-446655440000
```

## Need Help?

See [README.md](README.md) for full documentation.
