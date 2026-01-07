# Secrets Management

How to securely configure your passwords using the `.env` file.

## Overview

Instead of exporting environment variables every time, this project uses a **`.env` file** to store your secrets locally. The `.env` file is:

✅ **Gitignored** - Never committed to version control
✅ **Local only** - Stays on your machine
✅ **Easy to edit** - Simple key=value format

## Setup

### Step 1: Copy the Template

```bash
cd ai-agents/email-workflow-validator
cp .env.template .env
```

### Step 2: Edit the .env File

Open `.env` in your editor:

```bash
nano .env
# or
code .env
# or
vim .env
```

### Step 3: Add Your Credentials

Replace the placeholder values:

```ini
# Gmail App Password (NOT your regular Gmail password!)
# Get from: https://myaccount.google.com/apppasswords
GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop

# Test inbox password
# Your test inbox IMAP password
IMAP_PASSWORD=your-actual-test-inbox-password
```

### Step 4: Save and Test

```bash
# Test that secrets are loaded correctly
workflow-validator check-connection
```

Expected output:
```
✓ SMTP connection successful
✓ IMAP connection successful
```

## File Structure

```
ai-agents/email-workflow-validator/
├── .env.template       ✅ Committed to git (safe - no secrets)
├── .env                ❌ Gitignored (contains secrets)
├── .gitignore          ✅ Protects .env from being committed
└── workflow_validator/
    └── config/
        ├── settings.yaml  ✅ References ${GMAIL_APP_PASSWORD} and ${IMAP_PASSWORD}
        └── manager.py     ✅ Loads .env file automatically
```

## How It Works

1. **Template committed**: `.env.template` shows required variables (no actual secrets)
2. **You create .env**: Copy template and add real passwords
3. **Auto-loaded**: `ConfigManager` automatically loads `.env` on startup
4. **Variables replaced**: `${GMAIL_APP_PASSWORD}` in YAML → actual password from `.env`

## Security Features

### ✅ Gitignore Protection

The `.gitignore` ensures `.env` is **never committed**:

```gitignore
# .gitignore
.env              # Actual secrets file (ignored)
!.env.template    # Template without secrets (committed)
```

### ✅ No Command History

Unlike `export` commands, your secrets don't appear in:
- Shell history (`~/.bash_history`)
- Command logs
- Terminal scrollback

### ✅ Centralized Management

All secrets in one place:
```
.env file only
├── GMAIL_APP_PASSWORD
└── IMAP_PASSWORD
```

Instead of scattered across terminal sessions.

## Getting Gmail App Password

### Prerequisites
1. **2-Step Verification** must be enabled
2. Go to: https://myaccount.google.com/security

### Generate App Password

1. Visit: https://myaccount.google.com/apppasswords
2. Select "Mail" as the app
3. Select your device (e.g., "Windows Computer")
4. Click "Generate"
5. Copy the 16-character password (format: `xxxx-xxxx-xxxx-xxxx`)
6. Add to `.env` as `GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx`

**Note:** Remove spaces from the password when adding to `.env`
- Google shows: `abcd efgh ijkl mnop`
- In .env use: `GMAIL_APP_PASSWORD=abcdefghijklmnop`

## Environment Variable Priority

The configuration system loads secrets in this order (later overrides earlier):

1. **Code defaults** (in `schemas.py`)
2. **YAML config** (`settings.yaml`)
3. **`.env` file** (loaded by `python-dotenv`)
4. **System environment variables** (traditional `export`)

This means:
- `.env` file is convenient for local development
- System env vars can override for CI/CD or production
- Both work seamlessly together

## Troubleshooting

### "Environment variable GMAIL_APP_PASSWORD not set"

**Cause:** `.env` file doesn't exist or is empty

**Fix:**
```bash
# Check if .env exists
ls -la .env

# If not, copy template
cp .env.template .env

# Edit and add your password
nano .env
```

### "SMTP connection failed" (Gmail)

**Cause:** Invalid App Password

**Fix:**
1. Verify 2-Step Verification is enabled
2. Regenerate App Password at https://myaccount.google.com/apppasswords
3. Update `.env` with new password
4. Ensure no spaces in password

### "IMAP connection failed" (Test inbox)

**Cause:** Wrong test inbox password or IMAP disabled

**Fix:**
1. Verify IMAP is enabled in email account settings
2. Check password is correct
3. Try logging in via email client (Thunderbird, Outlook)

### ".env file not being read"

**Cause:** Wrong location

**Fix:** Ensure `.env` is in project root:
```bash
ai-agents/email-workflow-validator/.env  ✅ Correct
ai-agents/email-workflow-validator/workflow_validator/.env  ❌ Wrong
```

The `ConfigManager` looks for `.env` at:
```python
Path(__file__).parent.parent.parent / ".env"
# From: workflow_validator/config/manager.py
# Up 3 levels to: ai-agents/email-workflow-validator/.env
```

## Checking Loaded Variables

Debug what variables are loaded:

```python
# In Python shell
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path("ai-agents/email-workflow-validator/.env")
load_dotenv(env_path)

# Check if loaded
print(f"GMAIL_APP_PASSWORD: {os.getenv('GMAIL_APP_PASSWORD')[:4]}****")  # First 4 chars
print(f"IMAP_PASSWORD: {'SET' if os.getenv('IMAP_PASSWORD') else 'NOT SET'}")
```

## Alternative: System Environment Variables

If you prefer traditional exports, they still work:

```bash
export GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export IMAP_PASSWORD="your-password"
workflow-validator validate --test-inbox test@example.com
```

System env vars override `.env` file if both are set.

## Best Practices

✅ **DO:**
- Keep `.env` in project root
- Use `.env.template` as reference
- Add comments in `.env` for clarity
- Regenerate passwords if compromised

❌ **DON'T:**
- Commit `.env` to git
- Share `.env` file publicly
- Use real Gmail password (use App Password)
- Store production secrets in `.env` (use secure vault)

## CI/CD Integration

For automated testing (GitHub Actions, etc.):

```yaml
# .github/workflows/test.yml
env:
  GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
  IMAP_PASSWORD: ${{ secrets.IMAP_PASSWORD }}
```

GitHub Secrets → Environment Variables → Code (same variable names)

## Summary

```
┌─────────────────────────────────────────┐
│ .env.template (committed)               │
│   GMAIL_APP_PASSWORD=xxxx-xxxx-...      │
│   IMAP_PASSWORD=your-password           │
└─────────────────────────────────────────┘
              │
              │ cp .env.template .env
              ▼
┌─────────────────────────────────────────┐
│ .env (gitignored)                       │
│   GMAIL_APP_PASSWORD=real-password      │
│   IMAP_PASSWORD=real-test-password      │
└─────────────────────────────────────────┘
              │
              │ load_dotenv()
              ▼
┌─────────────────────────────────────────┐
│ Environment Variables (in memory)       │
│   os.getenv('GMAIL_APP_PASSWORD')       │
│   os.getenv('IMAP_PASSWORD')            │
└─────────────────────────────────────────┘
              │
              │ ConfigManager._replace_env_vars()
              ▼
┌─────────────────────────────────────────┐
│ settings.yaml                           │
│   password: ${GMAIL_APP_PASSWORD}       │
│            ↓ (replaced)                 │
│   password: "real-password"             │
└─────────────────────────────────────────┘
```

Your secrets are safe and easy to manage! 🔒
