#!/usr/bin/env python3
"""Merged decryptor — handles both .locked and .enc encrypted files.

Usage:
    python3 decrypt_all.py <key_file> <target_dir>

Example (local data):
    python3 decrypt_all.py recovery_key.key ./hospital_records

Example (inside a container):
    python3 decrypt_all.py /tmp/.ehr_key.key /opt/hospital-data
"""

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet


def decrypt_enc(filepath: Path, fernet: Fernet) -> str:
    """Decrypt a .enc file (Virus/ransomware style)."""
    original = filepath.with_suffix("")
    with open(filepath, "rb") as f:
        data = fernet.decrypt(f.read())
    with open(original, "wb") as f:
        f.write(data)
    filepath.unlink()
    return str(original)


def decrypt_locked(filepath: Path, fernet: Fernet) -> str:
    """Decrypt a .locked file (malware_coursework style)."""
    original_suffix = "".join(filepath.suffixes[:-1]) if filepath.suffix == ".locked" else filepath.suffix
    if not original_suffix:
        original = filepath.with_name(filepath.stem)
    else:
        original = filepath.with_suffix(original_suffix)

    data = fernet.decrypt(filepath.read_bytes())
    original.write_bytes(data)
    filepath.unlink()
    return str(original)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 decrypt_all.py <key_file> <target_dir>")
        sys.exit(1)

    key_path = Path(sys.argv[1])
    target_dir = Path(sys.argv[2])

    if not key_path.is_file():
        print(f"[!] Key file not found: {key_path}")
        sys.exit(1)
    if not target_dir.is_dir():
        print(f"[!] Target directory not found: {target_dir}")
        sys.exit(1)

    fernet = Fernet(key_path.read_bytes())
    print(f"[*] Loaded key from {key_path}\n")

    restored = 0

    for filepath in sorted(target_dir.rglob("*")):
        if not filepath.is_file():
            continue
        try:
            if filepath.suffix == ".enc":
                orig = decrypt_enc(filepath, fernet)
                print(f"  [RESTORED] {filepath.name} -> {os.path.basename(orig)}")
                restored += 1
            elif filepath.suffix == ".locked":
                orig = decrypt_locked(filepath, fernet)
                print(f"  [RESTORED] {filepath.name} -> {os.path.basename(orig)}")
                restored += 1
        except Exception as e:
            print(f"  [FAILED] {filepath.name}: {e}")

    for note_name in ("RANSOM_NOTE.txt", "READ_ME_RESTORE_FILES.txt"):
        note = target_dir / note_name
        if note.is_file():
            note.unlink()
            print(f"\n[*] Removed {note_name}")

    marker = Path("/tmp/.already_encrypted")
    if marker.is_file():
        marker.unlink()

    print(f"\n[*] {restored} file(s) restored.\n")


if __name__ == "__main__":
    main()
