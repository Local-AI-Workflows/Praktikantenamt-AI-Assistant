#!/usr/bin/env python
"""Quick test for folder parsing."""

import sys
sys.path.insert(0, '.')

from workflow_validator.email.imap_client import IMAPClient
from workflow_validator.config.manager import ConfigManager

cm = ConfigManager()
cfg = cm.load_config()
ic = IMAPClient(cfg.imap)
ic.connect()

# Get raw response
status, folders_raw = ic.connection.list()
print("Raw folders:")
for folder_bytes in folders_raw:
    folder_str = folder_bytes.decode('utf-8', errors='ignore')
    print(f"  Raw: {repr(folder_str)}")
    
    # Test parsing
    parts = folder_str.split('"')
    print(f"    Parts: {parts}")
    if len(parts) >= 5:
        folder_name = parts[-2]
        print(f"    Parsed: {folder_name}")
    print()

print("\nUsing list_folders():")
folders = ic.list_folders()
for f in folders:
    print(f"  • {f}")

ic.disconnect()
