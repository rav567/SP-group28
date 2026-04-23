#!/usr/bin/env python3
"""Unified JSON attack-log writer used by every phase."""

import json
import os
import time
import threading

_lock = threading.Lock()


class AttackLogger:
    """Append structured entries to a single attack_log.json file."""

    def __init__(self, log_path: str = "attack_log.json"):
        self.log_path = log_path
        self._entries: list[dict] = []

    def log(self, phase: str, action: str, details: dict | None = None,
            success: bool = True) -> dict:
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": phase,
            "action": action,
            "success": success,
            "details": details or {},
        }
        with _lock:
            self._entries.append(entry)
            self._flush()
        return entry

    def _flush(self):
        payload = {
            "attack_start": self._entries[0]["timestamp"] if self._entries else None,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_events": len(self._entries),
            "events": self._entries,
        }
        tmp = self.log_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.log_path)

    def get_entries(self) -> list[dict]:
        return list(self._entries)
