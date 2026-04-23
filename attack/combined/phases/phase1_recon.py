#!/usr/bin/env python3
"""Phase 1 — Network reconnaissance via nmap.

Wraps the logic from 01_recon.sh in Python (subprocess call).
Maps to MITRE T1046 (Network Service Discovery).
"""

import subprocess
import re

from utils.logger import AttackLogger

PORTS = "2222,2223,2224"
PORT_MAP = {
    "2222": "EHR Database Server",
    "2223": "IoT Device Gateway",
    "2224": "Staff Access Portal",
}


class Phase1Recon:
    """Run nmap against the target and return discovered services."""

    PHASE_NAME = "phase1_recon"

    def __init__(self, target_ip: str, logger: AttackLogger):
        self.target_ip = target_ip
        self.logger = logger

    def run(self) -> dict:
        print(f"\n--- Phase 1: Recon ({self.target_ip}) ---\n")

        cmd = [
            "nmap", "-n", "-Pn", "-sV",
            "-p", PORTS,
            self.target_ip,
            "-oN", "recon_results.txt",
        ]

        self.logger.log(self.PHASE_NAME, "nmap_start",
                        {"target": self.target_ip, "ports": PORTS})

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout
            print(output)
        except FileNotFoundError:
            msg = "[!] nmap not found — is it installed?"
            print(msg)
            self.logger.log(self.PHASE_NAME, "nmap_missing", success=False)
            return {"success": False, "error": msg}
        except subprocess.TimeoutExpired:
            msg = "[!] nmap timed out"
            print(msg)
            self.logger.log(self.PHASE_NAME, "nmap_timeout", success=False)
            return {"success": False, "error": msg}

        open_ports = re.findall(r"(\d+)/tcp\s+open", output)

        print("Port mapping:")
        for port, desc in PORT_MAP.items():
            status = "open" if port in open_ports else "closed/filtered"
            print(f"  {port} = {desc}  [{status}]")
        print(f"\n[*] Results saved to recon_results.txt")

        self.logger.log(self.PHASE_NAME, "nmap_complete",
                        {"open_ports": open_ports,
                         "output_file": "recon_results.txt"})

        return {
            "success": len(open_ports) > 0,
            "open_ports": open_ports,
            "target_ip": self.target_ip,
        }
