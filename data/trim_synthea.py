#!/usr/bin/env python3
"""
trim_synthea.py — Cuts the full Synthea dataset down to 10 patients and
generates synthetic IoT + staff-portal data for the Docker containers.
"""

import os
import json
import random
import secrets
import string
from datetime import datetime, timedelta

import pandas as pd

SEED = 42
random.seed(SEED)

SRC_DIR = os.path.join(os.path.dirname(__file__), "data", "csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "trimmed_data")

EHR_DIR = os.path.join(OUT_DIR, "ehr_data")
IOT_DIR = os.path.join(OUT_DIR, "iot_data")
PORTAL_DIR = os.path.join(OUT_DIR, "portal_data")

N_PATIENTS = 10
OBS_LIMIT = 500


# ── helpers ──────────────────────────────────────────────────────────────────

def ensure_dirs():
    for d in (EHR_DIR, IOT_DIR, PORTAL_DIR):
        os.makedirs(d, exist_ok=True)


def pick_patients() -> list[str]:
    df = pd.read_csv(os.path.join(SRC_DIR, "patients.csv"))
    sample = df.sample(n=N_PATIENTS, random_state=SEED)
    return sample["Id"].tolist()


def filter_and_save(filename: str, patient_ids: list[str], dest_dir: str,
                    patient_col: str = "PATIENT", limit: int | None = None):
    src = os.path.join(SRC_DIR, filename)
    df = pd.read_csv(src)
    filtered = df[df[patient_col].isin(patient_ids)]
    if limit and len(filtered) > limit:
        filtered = filtered.sample(n=limit, random_state=SEED)
    out = os.path.join(dest_dir, filename)
    filtered.to_csv(out, index=False, encoding="utf-8")
    return len(filtered)


# ── EHR data (real Synthea, trimmed to 10 patients) ─────────────────────────

def build_ehr(patient_ids: list[str]):
    print("\n── EHR Server ──")

    patients = pd.read_csv(os.path.join(SRC_DIR, "patients.csv"))
    patients = patients[patients["Id"].isin(patient_ids)]
    patients.to_csv(os.path.join(EHR_DIR, "patients.csv"), index=False, encoding="utf-8")
    print(f"  patients.csv         {len(patients):>5} rows")

    for fname, limit in [
        ("conditions.csv", None),
        ("medications.csv", None),
        ("observations.csv", OBS_LIMIT),
        ("encounters.csv", None),
        ("allergies.csv", None),
    ]:
        n = filter_and_save(fname, patient_ids, EHR_DIR, limit=limit)
        print(f"  {fname:<22} {n:>5} rows")


# ── IoT Gateway (generated) ─────────────────────────────────────────────────

def build_iot(patient_ids: list[str]):
    print("\n── IoT Gateway ──")

    monitors = [f"IOT-PM-{i:03d}" for i in range(1, 11)]
    pumps = [f"IOT-IP-{i:03d}" for i in range(1, 6)]
    ventilators = [f"IOT-VT-{i:03d}" for i in range(1, 4)]

    monitor_patient = dict(zip(monitors, patient_ids))
    pump_patient = dict(zip(pumps, patient_ids[:5]))
    vent_patient = dict(zip(ventilators, patient_ids[:3]))

    device_patient = {**monitor_patient, **pump_patient, **vent_patient}
    device_type = {}
    for d in monitors:
        device_type[d] = "Patient Monitor"
    for d in pumps:
        device_type[d] = "Infusion Pump"
    for d in ventilators:
        device_type[d] = "Ventilator"

    all_devices = monitors + pumps + ventilators

    metric_specs = {
        "Patient Monitor": [
            ("HeartRate", "bpm", 55, 110),
            ("SpO2", "%", 88, 100),
            ("SystolicBP", "mmHg", 100, 180),
            ("DiastolicBP", "mmHg", 60, 100),
            ("Temperature", "C", 36.0, 39.5),
        ],
        "Infusion Pump": [
            ("FlowRate", "mL/hr", 50, 500),
        ],
        "Ventilator": [
            ("TidalVolume", "mL", 300, 600),
        ],
    }

    start = datetime(2025, 1, 8, 6, 0, 0)
    rows = []
    for i in range(500):
        ts = start + timedelta(minutes=5 * i)
        dev = random.choice(all_devices)
        dtype = device_type[dev]
        metric_name, unit, lo, hi = random.choice(metric_specs[dtype])

        if isinstance(lo, float):
            value = round(random.uniform(lo, hi), 1)
        else:
            value = random.randint(lo, hi)

        frac = (value - lo) / (hi - lo) if hi != lo else 0.5
        if frac > 0.92 or frac < 0.08:
            status = random.choices(["Critical", "Warning"], weights=[0.6, 0.4])[0]
        elif frac > 0.82 or frac < 0.15:
            status = random.choices(["Warning", "Normal"], weights=[0.4, 0.6])[0]
        else:
            status = "Normal"

        rows.append({
            "Timestamp": ts.isoformat(),
            "DeviceID": dev,
            "DeviceType": dtype,
            "PatientID": device_patient[dev],
            "Metric": metric_name,
            "Value": value,
            "Unit": unit,
            "Status": status,
        })

    pd.DataFrame(rows).to_csv(
        os.path.join(IOT_DIR, "telemetry.csv"), index=False, encoding="utf-8"
    )
    print(f"  telemetry.csv        {len(rows):>5} rows")

    locations = [
        "Ward A - Bed 1", "Ward A - Bed 2", "Ward A - Bed 3",
        "Ward B - Bed 1", "Ward B - Bed 2", "ICU - Bay 1",
        "ICU - Bay 2", "ICU - Bay 3", "ICU - Bay 4",
        "Respiratory Unit - Bed 1", "Respiratory Unit - Bed 2",
        "Emergency - Bay 1", "Emergency - Bay 2",
        "Cardiology - Bed 1", "Cardiology - Bed 2",
        "Oncology - Bed 1", "Oncology - Bed 2", "Oncology - Bed 3",
    ]
    manufacturers = ["Philips", "GE Healthcare", "Medtronic", "Dräger", "Baxter"]
    reg_rows = []
    for dev in all_devices:
        reg_rows.append({
            "DeviceID": dev,
            "DeviceType": device_type[dev],
            "Location": random.choice(locations),
            "PatientID": device_patient[dev],
            "Firmware": f"v{random.randint(2, 5)}.{random.randint(0, 9)}.{random.randint(0, 15)}",
            "LastPatched": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "Manufacturer": random.choice(manufacturers),
        })
    pd.DataFrame(reg_rows).to_csv(
        os.path.join(IOT_DIR, "device_registry.csv"), index=False, encoding="utf-8"
    )
    print(f"  device_registry.csv  {len(reg_rows):>5} rows")


# ── Staff Portal (generated) ─────────────────────────────────────────────────

STAFF = [
    ("S-001", "Dr James Whitfield",    "Consultant",    "Cardiology",    "Full"),
    ("S-002", "Dr Priya Sharma",       "Registrar",     "Oncology",      "Full"),
    ("S-003", "Dr Mohammed Al-Rashid",  "SHO",           "Emergency",     "Standard"),
    ("S-004", "Dr Emily Chen",         "FY2",           "Respiratory",   "Standard"),
    ("S-005", "Sarah Thompson",        "Ward Sister",   "Orthopaedics",  "Standard"),
    ("S-006", "Michael O'Brien",       "Staff Nurse",   "Cardiology",    "Standard"),
    ("S-007", "Fatima Begum",          "Staff Nurse",   "Oncology",      "Standard"),
    ("S-008", "David Williams",        "Practice Nurse", "Respiratory",  "Standard"),
    ("S-009", "Rachel Hughes",         "HCA",           "Emergency",     "Basic"),
    ("S-010", "Daniel Okonkwo",        "HCA",           "Orthopaedics",  "Basic"),
    ("S-011", "Dr Laura Mitchell",     "Consultant",    "Respiratory",   "Full"),
    ("S-012", "Karen Singh",           "Staff Nurse",   "Emergency",     "Standard"),
]


def build_portal(patient_ids: list[str]):
    print("\n── Staff Portal ──")

    staff_rows = []
    for sid, name, role, dept, level in STAFF:
        first = name.replace("Dr ", "").split()[0].lower()
        last = name.replace("Dr ", "").split()[-1].lower()
        staff_rows.append({
            "StaffID": sid,
            "Name": name,
            "Role": role,
            "Department": dept,
            "AccessLevel": level,
            "Email": f"{first}.{last}@nhs-hospital.invalid",
        })
    pd.DataFrame(staff_rows).to_csv(
        os.path.join(PORTAL_DIR, "staff_directory.csv"), index=False, encoding="utf-8"
    )
    print(f"  staff_directory.csv  {len(staff_rows):>5} rows")

    actions = ["LOGIN", "LOGOUT", "VIEW", "UPDATE", "PRINT", "EXPORT"]
    action_weights = [15, 10, 40, 20, 10, 5]
    base = datetime(2025, 1, 8, 7, 0, 0)
    log_rows = []
    for _ in range(50):
        ts = base + timedelta(minutes=random.randint(0, 720))
        staff_id = random.choice([s[0] for s in STAFF])
        action = random.choices(actions, weights=action_weights)[0]
        resource = random.choice(patient_ids)
        ip = f"10.10.10.{random.randint(50, 60)}"
        log_rows.append({
            "Timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "StaffID": staff_id,
            "Action": action,
            "Resource": resource,
            "IPAddress": ip,
        })
    log_rows.sort(key=lambda r: r["Timestamp"])
    pd.DataFrame(log_rows).to_csv(
        os.path.join(PORTAL_DIR, "access_log.csv"), index=False, encoding="utf-8"
    )
    print(f"  access_log.csv       {len(log_rows):>5} rows")

    def fake_jwt():
        return "eyJ" + "".join(random.choices(string.ascii_letters + string.digits + "_-", k=80))

    tokens = []
    for staff_id in [s[0] for s in STAFF[:5]]:
        tokens.append({
            "staff_id": staff_id,
            "token": fake_jwt(),
            "expires": (datetime(2025, 1, 8, 19, 0, 0)
                        + timedelta(hours=random.randint(1, 8))).isoformat(),
        })
    with open(os.path.join(PORTAL_DIR, "session_tokens.json"), "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    print(f"  session_tokens.json  {len(tokens):>5} entries")


# ── summary ──────────────────────────────────────────────────────────────────

def print_summary():
    print("\n── Summary ──")
    for label, folder in [("EHR Server", EHR_DIR),
                          ("IoT Gateway", IOT_DIR),
                          ("Staff Portal", PORTAL_DIR)]:
        files = os.listdir(folder)
        total = sum(os.path.getsize(os.path.join(folder, f)) for f in files)
        print(f"  {label:<14}  {len(files)} files  {total / 1024:.1f} KB")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(folder, f))
            print(f"    {f:<28} {size / 1024:>7.1f} KB")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ensure_dirs()
    patient_ids = pick_patients()
    print(f"Selected {len(patient_ids)} patients:")
    for pid in patient_ids:
        print(f"  {pid}")

    build_ehr(patient_ids)
    build_iot(patient_ids)
    build_portal(patient_ids)
    print_summary()


if __name__ == "__main__":
    main()
