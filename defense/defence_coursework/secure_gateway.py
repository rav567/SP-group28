from pathlib import Path
from cryptography.fernet import Fernet
import json
import hashlib
import time

BASE = Path.home() / "defence_coursework"
SECURE_DIR = BASE / "secure_records"
LOG_FILE = BASE / "audit_logs" / "access_log.json"
KEY_FILE = BASE / "master.key"
USERS_FILE = BASE / "users.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))

def log_event(event: dict):
    logs = []
    if LOG_FILE.exists():
        logs = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    logs.append(event)
    LOG_FILE.write_text(json.dumps(logs, indent=2), encoding="utf-8")

def authenticate():
    users = load_users()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    mfa_code = input("MFA Code: ").strip()

    if username not in users:
        print("Access denied.")
        return None

    user = users[username]
    if hash_password(password) != user["password_hash"]:
        print("Access denied.")
        return None

    if mfa_code != user["mfa_code"]:
        print("Access denied,")
        return None
    return username, user["role"]

def list_files():
    return sorted(SECURE_DIR.rglob("*enc"))

def decrypt_file(file_path):
    key = KEY_FILE.read_bytes()
    fernet = Fernet(key)
    return fernet.decrypt(file_path.read_bytes()).decode()

def main():
    auth = authenticate()
    if not auth:
       log_event({
           "timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),
           "event": "failed_login"
       })
       return

    username, role = auth
    print(f"Login successful. Role: {role}")

    files = list_files()

    if not files:
       print("No encrypted records found.")
       log_event({
          "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
          "user": username,
          "role": role,
          "event": "no_records_found"
       })
       return

    for idx, file in enumerate(files, start=1):
        print(f"{idx}. {file.name}")

    choice = int(input("Choose file number to open: ")) - 1
    selected = files[choice]

    if role not in {"doctor", "admin"}:
        print("You do not have permission to access patient records.")
        log_event({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": username,
            "role": role,
            "event": "unauthorised_access_attempt",
            "file": selected.name
        })
        return

    content = decrypt_file(selected)
    print("\n --- RECORD CONTENT ---")
    print(content)

    log_event({
        "timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),
        "user": username,
        "role": role,
        "event": "record_accessed",
        "file": selected.name
    })

if __name__ == "__main__":
    main()
