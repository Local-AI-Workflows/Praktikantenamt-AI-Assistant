# Setup Overview

Visual guide to the email flow and configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  YOUR GMAIL (SENDER)                                        │
│  • Sends 100 test emails                                    │
│  • Uses Gmail SMTP: smtp.gmail.com:587                      │
│  • Requires App Password                                    │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Send 100 emails via SMTP
                      │ Each with embedded UUID
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  TEST INBOX (RECEIVER)                                      │
│  • Receives test emails                                     │
│  • n8n monitors this inbox                                  │
│  • Can be any email provider (Gmail, Outlook, etc.)         │
│                                                             │
│  INBOX/                                                     │
│  ├── Contract_Submission/      ◄── n8n routes here         │
│  ├── International_Questions/                               │
│  ├── Postponement_Requests/                                 │
│  └── Uncategorized/                                         │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Validate via IMAP
                      │ Check which folder each email landed in
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  VALIDATION SCRIPT                                          │
│  • Connects to test inbox via IMAP                          │
│  • Searches for UUIDs                                       │
│  • Maps folder → category                                   │
│  • Calculates accuracy                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Two Email Accounts Setup

### Account 1: Your Gmail (SENDER)

**Purpose:** Sends test emails
**Protocol:** SMTP
**Config section:** `smtp`

```yaml
smtp:
  host: "smtp.gmail.com"
  port: 587
  username: "your-gmail@gmail.com"
  password: "${GMAIL_APP_PASSWORD}"
  from_address: "your-gmail@gmail.com"
```

**Required:**
- Gmail App Password (16 characters)
- 2-Step Verification enabled

**Environment variable:**
```bash
export GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
```

### Account 2: Test Inbox (RECEIVER)

**Purpose:** Receives emails, n8n routes them, validation checks folders
**Protocol:** IMAP
**Config section:** `imap`

```yaml
imap:
  host: "imap.example.com"  # Your test inbox IMAP server
  port: 993
  username: "test-inbox@example.com"
  password: "${IMAP_PASSWORD}"
```

**Can be:**
- Another Gmail account
- Outlook/Office365
- University email
- Any email provider with IMAP access

**Environment variable:**
```bash
export IMAP_PASSWORD="your-test-inbox-password"
```

## Email Flow Example

```
1. Script sends email:
   From: your-gmail@gmail.com
   To: test-inbox@example.com
   Subject: Praktikumsvertrag zur Unterschrift
   X-Test-UUID: 550e8400-...
   Body: [German email content]
         [TEST-ID: 550e8400-...]

2. Email arrives in test inbox:
   test-inbox@example.com/INBOX/

3. n8n processes:
   • Reads email from INBOX
   • Categorizes with LLM
   • Moves to subfolder based on category
   test-inbox@example.com/INBOX/Contract_Submission/

4. Script validates:
   • Searches test inbox via IMAP
   • Finds email in INBOX/Contract_Submission
   • Maps folder → "contract_submission"
   • Compares with expected: "contract_submission"
   • Result: ✓ Correct!
```

## Why Two Accounts?

**Option 1: Two separate accounts (RECOMMENDED)**
- ✅ Clean separation of concerns
- ✅ Gmail for sending (reliable SMTP)
- ✅ Test inbox for receiving (isolated from personal email)
- ✅ n8n doesn't interfere with your personal Gmail

**Option 2: Same Gmail for both (possible but not ideal)**
- ⚠️ n8n would process your personal emails too
- ⚠️ Risk of moving personal emails to wrong folders
- ⚠️ Harder to isolate test environment

## Configuration Checklist

- [ ] 1. **Gmail (Sender)**
  - [ ] Enable 2-Step Verification
  - [ ] Generate App Password
  - [ ] Copy password to `GMAIL_APP_PASSWORD` env var
  - [ ] Update `smtp.username` in settings.yaml

- [ ] 2. **Test Inbox (Receiver)**
  - [ ] Get IMAP server details (host, port)
  - [ ] Ensure IMAP is enabled
  - [ ] Copy password to `IMAP_PASSWORD` env var
  - [ ] Update `imap.host` and `imap.username` in settings.yaml

- [ ] 3. **Folder Mappings**
  - [ ] Check n8n output folder names
  - [ ] Update `folder_mappings` in settings.yaml
  - [ ] Match IMAP folder format (e.g., `INBOX.Subfolder` vs `Subfolder`)

- [ ] 4. **Test Connection**
  - [ ] Run: `workflow-validator check-connection`
  - [ ] Verify both SMTP and IMAP succeed

## Common Setups

### Gmail → Gmail
```yaml
smtp:
  host: "smtp.gmail.com"
  username: "sender@gmail.com"
imap:
  host: "imap.gmail.com"
  username: "testinbox@gmail.com"
```

### Gmail → Outlook
```yaml
smtp:
  host: "smtp.gmail.com"
  username: "sender@gmail.com"
imap:
  host: "outlook.office365.com"
  username: "testinbox@outlook.com"
```

### Gmail → University Email
```yaml
smtp:
  host: "smtp.gmail.com"
  username: "sender@gmail.com"
imap:
  host: "imap.uni-example.de"
  username: "testinbox@uni-example.de"
```

## Testing

### Step 1: Test SMTP (Gmail)
```bash
workflow-validator check-connection
```
Should show: `✓ SMTP connection successful`

If fails:
- Check `GMAIL_APP_PASSWORD` is set
- Verify App Password is correct (16 chars)
- Ensure 2-Step Verification is enabled
- Check firewall allows outbound port 587

### Step 2: Test IMAP (Test Inbox)
```bash
workflow-validator check-connection
```
Should show: `✓ IMAP connection successful`

If fails:
- Check `IMAP_PASSWORD` is set
- Verify IMAP is enabled on account
- Check host/port are correct
- Ensure firewall allows outbound port 993

### Step 3: Send Test Emails
```bash
workflow-validator validate --test-inbox testinbox@example.com -w 120 --no-cleanup
```

Check:
- Emails arrive in test inbox
- n8n processes them
- Emails move to correct folders
- Script finds them and validates

## Troubleshooting

### "SMTP connection failed"
- **Cause:** Gmail App Password issue
- **Fix:** Regenerate App Password at https://myaccount.google.com/apppasswords
- **Check:** `echo $GMAIL_APP_PASSWORD` shows 16 characters

### "IMAP connection failed"
- **Cause:** Test inbox credentials or IMAP disabled
- **Fix:** Enable IMAP in email settings
- **Check:** Try connecting with email client (Thunderbird, Outlook)

### "Emails not found"
- **Cause:** n8n not moving emails to folders
- **Fix:** Check n8n workflow is running and routing correctly
- **Debug:** Use `--no-cleanup` to keep emails and check manually

## Security Notes

- **Never commit passwords** - Use environment variables only
- **App Passwords** - Easier to revoke than your main password
- **Test account** - Use dedicated test inbox, not personal email
- **Folder mappings** - Review before running to avoid moving real emails
