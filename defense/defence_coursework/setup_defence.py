from pathlib import Path
from cryptography.fernet import Fernet
import json
import hashlib

BASE = Path.home() / "defence_coursework"
SECURE_DIR = BASE / "secure_records"
EXPORT_DIR = BASE / "redacted_exports"
LOG_DIR = BASE / "audit_logs"
KEY_FILE = BASE / "master.key"
USERS_FILE = BASE / "users.json"

PATIENT_FILES = {
    "patient_notes/patient_001.txt":"""Patient ID: P001
Name: Harry M
DOB: 2001-12-13
Ward: General
Notes: Fever improving, waiting for blood test results.
""", 
    "patient_notes/patient_002.txt": """Patient ID: P002
Name: Faaris K
DOB: 2003-06-27
Ward: Psychiatric
Notes: Mood swings have stabilised.
""",
    "patient_notes/patient_003.txt": """Patient ID: P003
Name: Heidi M
DOB: 2003-05-10
Ward: Cardiology
Notes: Chest pain under observation.
"""
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def main():

    BASE.mkdir(exist_ok=True)
    SECURE_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    fernet = Fernet(key)

    for filename, content in PATIENT_FILES.items():
        encrypted = fernet.encrypt(content.encode())
        output_path = SECURE_DIR / (filename + ".enc")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(encrypted)

    users = {
       "doctorRK": {
           "password_hash": hash_password("doctorpassword"),
           "role": "doctor",
           "mfa_code": "246810"
       },
       "admin1": {
             "password_hash": hash_password("adminpassword"),
             "role": "admin",
             "mfa_code": "135790"
       },
       "researcher1": {
              "password_hash": hash_password("researchpassword"),
              "role": "researcher",
              "mfa_code": "112233"
       }
    }

    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
    print("Defence system setup complete.")

if __name__ == "__main__":
    main()
