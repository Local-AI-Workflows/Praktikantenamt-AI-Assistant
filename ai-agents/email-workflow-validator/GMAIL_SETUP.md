# Gmail-Only Setup (Testing Mode)

Quick setup guide for testing with a single Gmail account.

## Current Configuration

✅ **SMTP (Sender):** spammer1966@gmail.com
✅ **IMAP (Receiver):** spammer1966@gmail.com (same account)
✅ **Result:** Emails sent to yourself for testing

## Step-by-Step Setup

### 1. Generate Gmail App Password

**Prerequisites:**
- 2-Step Verification must be enabled

**Steps:**

1. Go to: https://myaccount.google.com/security
2. Find "2-Step Verification" → Enable if not already
3. Go to: https://myaccount.google.com/apppasswords
4. Select:
   - App: **Mail**
   - Device: **Windows Computer** (or your device)
5. Click **Generate**
6. Copy the 16-character password (format: `abcd efgh ijkl mnop`)

### 2. Create .env File

```bash
cd ai-agents/email-workflow-validator
cp .env.template .env
```

Edit `.env` and add your App Password (remove spaces):

```ini
GMAIL_APP_PASSWORD=abcdefghijklmnop
```

### 3. Enable IMAP in Gmail

1. Open Gmail → Settings (gear icon) → See all settings
2. Go to **Forwarding and POP/IMAP** tab
3. Find **IMAP access**
4. Select **Enable IMAP**
5. Click **Save Changes**

### 4. Create Gmail Labels (Optional for n8n)

If you want to test n8n routing, create these labels in Gmail:

1. In Gmail, click **More** in sidebar
2. Click **Create new label**
3. Create labels:
   - `Contract_Submission`
   - `International_Questions`
   - `Postponement_Requests`
   - `Uncategorized`

**Note:** n8n will need to move emails to these labels based on categorization.

### 5. Test Connection

```bash
cd ai-agents/email-workflow-validator
pip install -e .
workflow-validator check-connection
```

**Expected output:**
```
✓ SMTP connection successful
✓ IMAP connection successful
```

### 6. Run Validation

```bash
workflow-validator validate --test-inbox spammer1966@gmail.com
```

This will:
1. Send 100 emails to yourself (spammer1966@gmail.com)
2. Wait 60 seconds
3. Check your inbox via IMAP
4. Look for emails in labels (if n8n moved them)
5. Generate accuracy report

## What Happens

```
spammer1966@gmail.com (YOU)
        │
        │ [Send 100 emails via SMTP]
        ▼
spammer1966@gmail.com (YOUR INBOX)
        │
        │ [n8n monitors inbox]
        │ [Categorizes emails]
        │ [Moves to labels]
        ▼
Gmail Labels:
├── Contract_Submission (30 emails)
├── International_Questions (21 emails)
├── Postponement_Requests (12 emails)
└── Uncategorized (37 emails)
        │
        │ [Script validates via IMAP]
        ▼
Validation Report
✓ Accuracy: 94%
```

## Troubleshooting

### "SMTP connection failed"

**Cause:** Invalid App Password or 2-Step not enabled

**Fix:**
1. Check 2-Step Verification is enabled
2. Regenerate App Password
3. Copy without spaces to `.env`
4. Verify: `cat .env` shows `GMAIL_APP_PASSWORD=abcd...` (16 chars, no spaces)

### "IMAP connection failed"

**Cause:** IMAP not enabled in Gmail

**Fix:**
1. Gmail Settings → Forwarding and POP/IMAP
2. Enable IMAP
3. Save Changes
4. Wait ~5 minutes for changes to propagate
5. Try again: `workflow-validator check-connection`

### "Emails not found"

**Cause:** n8n not running or labels don't exist

**Expected for initial test:**
- Without n8n running, emails stay in INBOX
- Script will report "found in INBOX" but categories won't match
- This is normal! n8n needs to be set up to move emails

**To actually test routing:**
1. Set up n8n workflow to monitor spammer1966@gmail.com
2. Configure n8n to move emails to labels based on category
3. Run validator again

### "Environment variable GMAIL_APP_PASSWORD not set"

**Cause:** `.env` file doesn't exist or is empty

**Fix:**
```bash
# Check if .env exists
ls -la .env

# If not, copy template
cp .env.template .env

# Edit and add password
nano .env
```

## Gmail Rate Limits

Gmail has sending limits:
- **500 emails/day** for free accounts
- **2000 emails/day** for Google Workspace

**Solution for testing:**
- Use smaller dataset: `-d quick_test.json` (if you create one)
- Or test with first 10-20 emails only
- Or wait 24 hours between full runs

## Switching to Separate Test Inbox Later

When you get separate test inbox credentials:

1. Update `settings.yaml`:
```yaml
imap:
  host: "imap.test-provider.com"
  username: "test-inbox@test-provider.com"
  password: "${IMAP_PASSWORD}"
```

2. Update `.env`:
```ini
GMAIL_APP_PASSWORD=your-gmail-app-password
IMAP_PASSWORD=test-inbox-password
```

3. Update folder mappings to match test inbox format:
```yaml
folder_mappings:
  - folder_name: "INBOX.Contract_Submission"  # Or whatever format
```

## Security Note

⚠️ **App Password Security:**
- App Passwords can access your entire Gmail account
- Treat like a regular password
- If compromised, revoke at: https://myaccount.google.com/apppasswords
- Never commit `.env` to git (already gitignored)

✅ **Best Practice:**
- Use separate Gmail for testing (not your main account)
- Or use separate test inbox (when you get credentials)
- App Passwords easier to revoke than changing main password

## Next Steps

1. ✅ Generate App Password
2. ✅ Create `.env` file
3. ✅ Enable IMAP
4. ✅ Test connection
5. ⏳ Set up n8n workflow (separate task)
6. ⏳ Run full validation

Your validator is ready to test! 🚀
