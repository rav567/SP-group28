from pathlib import Path
from cryptography.fernet import Fernet
import re

BASE = Path.home() / "defence_coursework"
SECURE_DIR = BASE / "secure_records"
EXPORT_DIR = BASE / "redacted_exports"
KEY_FILE = BASE / "master.key"

def decrypt_file(file_path):
    key = KEY_FILE.read_bytes()
    fernet = Fernet(key)
    return fernet.decrypt(file_path.read_bytes()).decode()

def redact_pii(text: str) -> str:
    text = re.sub(r"Name:\s.*", "Name: [REDACTED]", text)
    text = re.sub(r"DOB:\s.*", "DOB: [REDACTED]", text)
    text = re.sub(r"NHS Number:\s.*", "NHS Numer: [REDACTED]", text)
    text = re.sub(r"Patient ID:\s.*", "Patient ID: [REDACTED]", text)
    return text

def main():
    EXPORT_DIR.mkdir(exist_ok=True)
    for file in SECURE_DIR.rglob("*.enc"):
        content = decrypt_file(file)
        redacted = redact_pii(content)
        output_name = file.stem.replace(".txt", "") + "_redacted.txt"
        (EXPORT_DIR / output_name).write_text(redacted, encoding="utf-8")
    print("Redacted AI-safe exports created")

if __name__ == "__main__":
    main()
