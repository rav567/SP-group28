from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    abort,
)
from cryptography.fernet import Fernet
import hashlib
import json
import re
import time
import secrets

BASE = Path(__file__).parent
SECURE_DIR = BASE / "secure_records"
EXPORT_DIR = BASE / "redacted_exports"
LOG_DIR = BASE / "audit_logs"
KEY_FILE = BASE / "master.key"
USERS_FILE = BASE / "users.json"
ACCESS_LOG = LOG_DIR / "access_log.json"
MONITOR_LOG = LOG_DIR / "monitor_log.json"

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _append_log(path: Path, event: dict):
    logs = []
    if path.exists():
        try:
            logs = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logs = []
    logs.append(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(logs, indent=2), encoding="utf-8")


def log_access(event: dict):
    _append_log(ACCESS_LOG, event)


def log_monitor(event: dict):
    _append_log(MONITOR_LOG, event)


def run_malware_scan():
    """Mirror of malware_monitor.py: look for .locked files in the secure store."""
    suspicious = []
    if SECURE_DIR.exists():
        suspicious = sorted(p.name for p in SECURE_DIR.rglob("*.locked"))
    return suspicious


def read_log(path: Path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def list_encrypted_files():
    if not SECURE_DIR.exists():
        return []
    return sorted(SECURE_DIR.rglob("*.enc"))


def decrypt_file(file_path: Path) -> str:
    key = KEY_FILE.read_bytes()
    fernet = Fernet(key)
    return fernet.decrypt(file_path.read_bytes()).decode()


def redact_pii(text: str) -> str:
    text = re.sub(r"Name:\s.*", "Name: [REDACTED]", text)
    text = re.sub(r"DOB:\s.*", "DOB: [REDACTED]", text)
    text = re.sub(r"NHS Number:\s.*", "NHS Number: [REDACTED]", text)
    text = re.sub(r"Patient ID:\s.*", "Patient ID: [REDACTED]", text)
    return text


def current_user():
    if "username" not in session:
        return None
    return {"username": session["username"], "role": session["role"]}


def require_login():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    return None


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        mfa_code = request.form.get("mfa_code", "").strip()
        users = load_users()

        if (
            username in users
            and hash_password(password) == users[username]["password_hash"]
            and mfa_code == users[username]["mfa_code"]
        ):
            session["username"] = username
            session["role"] = users[username]["role"]
            log_access({
                "timestamp": now_str(),
                "event": "login_success",
                "user": username,
                "role": users[username]["role"],
            })
            return redirect(url_for("dashboard"))

        log_access({
            "timestamp": now_str(),
            "event": "failed_login",
            "attempted_user": username or "(blank)",
        })
        error = "Sign-in failed. Check your username, password and MFA code."
    return render_template("defence_login.html", error=error)


@app.route("/logout")
def logout():
    user = current_user()
    if user:
        log_access({
            "timestamp": now_str(),
            "event": "logout",
            "user": user["username"],
            "role": user["role"],
        })
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    guard = require_login()
    if guard:
        return guard

    files = list_encrypted_files()
    return render_template(
        "defence_dashboard.html",
        user=current_user(),
        files=[f.name for f in files],
    )


@app.route("/record/<path:filename>")
def record(filename):
    guard = require_login()
    if guard:
        return guard

    user = current_user()
    target = None
    for f in list_encrypted_files():
        if f.name == filename:
            target = f
            break
    if target is None:
        abort(404)

    if user["role"] not in {"doctor", "admin"}:
        log_access({
            "timestamp": now_str(),
            "user": user["username"],
            "role": user["role"],
            "event": "unauthorised_access_attempt",
            "file": target.name,
        })
        return render_template("defence_access_denied.html", user=user, file=target.name), 403

    plaintext = decrypt_file(target)
    ciphertext_preview = target.read_bytes()[:96].hex()

    log_access({
        "timestamp": now_str(),
        "user": user["username"],
        "role": user["role"],
        "event": "record_accessed",
        "file": target.name,
    })

    return render_template(
        "defence_record.html",
        user=user,
        file=target.name,
        plaintext=plaintext,
        ciphertext_preview=ciphertext_preview,
        ciphertext_size=target.stat().st_size,
    )


@app.route("/research-export", methods=["GET", "POST"])
def research_export():
    guard = require_login()
    if guard:
        return guard

    user = current_user()
    generated = False
    pairs = []

    if request.method == "POST":
        EXPORT_DIR.mkdir(exist_ok=True)
        for enc in list_encrypted_files():
            plaintext = decrypt_file(enc)
            redacted = redact_pii(plaintext)
            out_name = enc.stem.replace(".txt", "") + "_redacted.txt"
            (EXPORT_DIR / out_name).write_text(redacted, encoding="utf-8")
        log_access({
            "timestamp": now_str(),
            "user": user["username"],
            "role": user["role"],
            "event": "research_export_generated",
        })
        generated = True

    for enc in list_encrypted_files():
        try:
            original = decrypt_file(enc)
        except Exception:
            continue
        redacted = redact_pii(original)
        pairs.append({
            "file": enc.name,
            "original": original,
            "redacted": redacted,
        })

    exported = []
    if EXPORT_DIR.exists():
        exported = sorted(p.name for p in EXPORT_DIR.glob("*.txt"))

    return render_template(
        "defence_research_export.html",
        user=user,
        pairs=pairs,
        exported=exported,
        generated=generated,
    )


@app.route("/research-export/download/<path:filename>")
def download_redacted(filename):
    guard = require_login()
    if guard:
        return guard
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)


@app.route("/audit", methods=["GET", "POST"])
def audit():
    guard = require_login()
    if guard:
        return guard

    user = current_user()
    if user["role"] != "admin":
        log_access({
            "timestamp": now_str(),
            "user": user["username"],
            "role": user["role"],
            "event": "unauthorised_access_attempt",
            "file": "security_console",
        })
        return render_template(
            "defence_access_denied.html", user=user, file="Security Console"
        ), 403

    scan_result = None
    if request.method == "POST" and request.form.get("action") == "scan":
        threats = run_malware_scan()
        if threats:
            for name in threats:
                log_monitor({
                    "timestamp": now_str(),
                    "event": "malware_alert",
                    "file": name,
                    "triggered_by": user["username"],
                })
        else:
            log_monitor({
                "timestamp": now_str(),
                "event": "monitor_scan_clean",
                "triggered_by": user["username"],
            })
        scan_result = {
            "timestamp": now_str(),
            "threats": threats,
            "clean": not threats,
        }

    access_events = list(reversed(read_log(ACCESS_LOG)))
    monitor_events = list(reversed(read_log(MONITOR_LOG)))

    return render_template(
        "defence_audit.html",
        user=user,
        access_events=access_events,
        monitor_events=monitor_events,
        scan_result=scan_result,
    )


LOG_DIR.mkdir(exist_ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False)
