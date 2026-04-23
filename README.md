# SP-group28 — Hospital Cyber-Attack & Defence Simulation

ELEC0138 Security and Privacy Coursework — UCL

This project simulates a full cyber-attack kill-chain against a fictional NHS Trust hospital network and demonstrates a set of corresponding defences. Everything runs across three VMs (host macOS, Ubuntu target, Kali attacker) using Docker containers as the hospital infrastructure.

The simulation covers two independent attack scenarios and a defence dashboard:

| Component | Location | Description |
|-----------|----------|-------------|
| **Combined Ransomware Attack** | `attack/combined/` | End-to-end phishing → reconnaissance → SSH deployment → Fernet ransomware with lateral movement across three hospital containers |
| **Botnet / DDoS Attack** | `attack/botnet-ddos_coursework/` | Mirai-style four-phase DDoS (SYN, UDP, DNS, ICMP floods) against EHR and IoMT systems, with Snort IPS detection |
| **Defence Dashboard** | `defense/defence_coursework/` | Flask web app with MFA login, role-based access control, encrypted record viewing, PII redaction for research exports, audit logging, and malware scanning |

---

## Architecture

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────────────────────┐
│   macOS Host │──SSH──▶│   Kali VM        │──SSH──▶│   Ubuntu VM (Docker Host)        │
│  (launch.sh) │       │  (run_attack.py) │       │                                  │
└──────────────┘       └──────────────────┘       │  ┌────────────┐  10.10.10.10:22  │
                                                  │  │ EHR Server │  (port 2222)     │
                                                  │  └────────────┘                  │
                                                  │  ┌────────────┐  10.10.10.11:22  │
                                                  │  │ IoT Gateway│  (port 2223)     │
                                                  │  └────────────┘                  │
                                                  │  ┌────────────┐  10.10.10.12:22  │
                                                  │  │Staff Portal│  (port 2224)     │
                                                  │  └────────────┘                  │
                                                  └──────────────────────────────────┘
```

---

## Prerequisites

### VMs

| VM | OS | Role |
|----|----|------|
| **Ubuntu** | Ubuntu 24.04 (VMware) | Docker host — runs the three hospital containers |
| **Kali** | Kali Linux (VMware) | Attacker machine — runs the attack scripts |
| **macOS** | macOS (host) | Optional orchestrator — runs `launch.sh` to automate everything |

All VMs must be on the same Host-Only network and have SSH enabled.

### Software Versions

| Tool | Version | Where |
|------|---------|-------|
| Docker / Docker Compose | Latest | Ubuntu VM |
| Python | 3.11+ | All VMs |
| Snort | 2.9.20 | Ubuntu VM (DDoS scenario only) |
| Scapy | 2.5.0 | Ubuntu VM (DDoS scenario only) |
| nmap | Latest | Kali VM |
| Flask | Latest | Kali VM + Defence host |
| Paramiko | Latest | Kali VM |
| cryptography | Latest | Kali VM + Docker containers |

### Python Dependencies

On **Kali** (attack):

```bash
python3 -m pip install flask paramiko cryptography --break-system-packages
```

On the machine running the **defence dashboard**:

```bash
python3 -m pip install flask cryptography --break-system-packages
```

On **Ubuntu** (DDoS scenario):

```bash
sudo apt install snort python3-scapy python3-flask nmap hydra -y
```

---

## Dataset

Patient data comes from the [Synthea](https://synthetichealth.github.io/synthea/) synthetic patient dataset (`data/synthea_sample_data_csv_apr2020.zip`). The script `data/trim_synthea.py` samples 10 patients and generates trimmed EHR, IoT, and portal data bundles used by the Docker containers.

---

## Running the Combined Ransomware Attack

### Option A — Fully Automated (from macOS)

```bash
cd attack/combined
./launch.sh <UBUNTU_IP> <KALI_IP>
```

This single command will:
1. Check connectivity to both VMs
2. Install Docker on Ubuntu if needed
3. Copy Docker files to Ubuntu and build the three hospital containers
4. Copy the attack files to Kali and install Python dependencies
5. Run the full attack (phishing → recon → deploy → ransomware)
6. Verify all files are encrypted and save results locally

### Option B — Manual (from Kali)

**1. Build the target containers on Ubuntu:**

```bash
cd ~/docker
docker compose up -d --build
```

**2. Run the attack from Kali:**

```bash
cd ~/combined
python3 run_attack.py <UBUNTU_IP>
```

**3. When the phishing page appears, open the URL in a browser and enter:**
- Username: `ehradmin`
- Password: `Hospital2024!`

Phases 1–3 run automatically after credential submission.

**4. Verify the damage:**

```bash
ssh -p 2222 ehradmin@<UBUNTU_IP> "ls /opt/hospital-data/"
ssh -p 2223 ehradmin@<UBUNTU_IP> "ls /opt/hospital-data/"
ssh -p 2224 ehradmin@<UBUNTU_IP> "ls /opt/hospital-data/"
```

All files should be `.enc` with a `RANSOM_NOTE.txt`.

### Reset the Lab

On Ubuntu:

```bash
cd ~/docker
docker compose down && docker compose up -d --build
```

---

## Running the DDoS / Botnet Attack

Run everything on the **Ubuntu VM** in separate terminals:

```bash
# Terminal 1 — EHR Server
cd attack/botnet-ddos_coursework && python3 ehr_server.py

# Terminal 2 — IoMT Devices
cd attack/botnet-ddos_coursework && python3 iomt_devices.py

# Terminal 3 — SOC Dashboard
cd attack/botnet-ddos_coursework && python3 dashboard.py

# Terminal 4 — Snort IPS
sudo snort -A console -c /etc/snort/snort.conf -i lo

# Terminal 5 — Launch Attack
cd attack/botnet-ddos_coursework && sudo python3 scapy_attacks.py
```

---

## Running the Defence Dashboard

```bash
cd defense/defence_coursework
python3 defence_dashboard.py
```

Open `http://127.0.0.1:5050` in a browser. User credentials and MFA codes are in `defense/defence_coursework/users.json`.

The dashboard provides:
- **Login** with password + MFA verification
- **Record Viewer** — decrypts `.enc` patient files (doctor/admin only)
- **Research Export** — generates PII-redacted copies for researchers
- **Audit Console** — access logs, monitor logs, and on-demand malware scan (admin only)

---

## Project Structure

```
SP-group28/
├── attack/
│   ├── combined/                 # Ransomware kill-chain
│   │   ├── run_attack.py         # Attack orchestrator (phases 0-2)
│   │   ├── launch.sh             # Mac automation script
│   │   ├── phases/
│   │   │   ├── phase0_phishing.py    # Fake NHS login page
│   │   │   ├── phase1_recon.py       # nmap reconnaissance
│   │   │   ├── phase2_deploy.py      # SSH payload deployment
│   │   │   └── phase3_ransomware.py  # Fernet encryption + lateral movement
│   │   ├── docker/
│   │   │   ├── Dockerfile
│   │   │   ├── docker-compose.yml
│   │   │   └── trimmed_data/         # Hospital data for containers
│   │   └── utils/
│   │       ├── logger.py
│   │       └── decrypt_all.py
│   └── botnet-ddos_coursework/   # DDoS simulation
│       ├── scapy_attacks.py
│       ├── ehr_server.py
│       ├── iomt_devices.py
│       ├── dashboard.py
│       └── local.rules           # Snort IPS rules
├── defense/
│   └── defence_coursework/
│       ├── defence_dashboard.py  # Flask defence web app
│       ├── setup_defence.py      # One-time encryption setup
│       ├── secure_gateway.py     # CLI gateway
│       ├── malware_monitor.py    # CLI malware scanner
│       ├── ai_redaction_guard.py # PII redaction tool
│       ├── users.json            # User credentials + MFA
│       ├── master.key            # Fernet encryption key
│       ├── templates/            # HTML templates
│       ├── secure_records/       # Encrypted patient files
│       ├── redacted_exports/     # PII-redacted outputs
│       └── audit_logs/           # Access + monitor logs
└── data/
    ├── csv/                      # Full Synthea dataset
    ├── trim_synthea.py           # Trimming script
    └── trimmed_data/             # Trimmed EHR/IoT/portal data
```

---

## Documents

- [Project Plan](https://docs.google.com/document/d/1o-6iaIsaD5YcRFzfXixdx0XFna_Ku-syhJL-sy6JT70/edit?usp=sharing)
- [Report](https://docs.google.com/document/d/1-01H5CRUdGoB3iFYDgK9ss33LVSrljJ8NHmLCTc5u2E/edit?usp=sharing)
- [Threat Model](https://docs.google.com/document/d/1ktMEwr9hJ5eSsMqKGv9q4kKmk5b1CornFN5OHGUXWcw/edit?tab=t.0)
