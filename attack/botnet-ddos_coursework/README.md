# ELEC0138 - IoT DDoS/Botnet Attack Simulation and Detection
## NHS Trust - Security and Privacy Coursework

## Overview
This repository contains the attack simulation code and Snort IPS detection 
rules developed for the ELEC0138 Security and Privacy coursework at UCL. 

## Repository Structure
ELEC0138-DDoS-Botnet-Simulation/
├── README.md
├── detection/
│   └── local.rules
├── attack/
│   └── scapy_attacks.py
├── server/
│   ├── ehr_server.py
│   └── iomt_devices.py
└── dashboard/
└── dashboard.py

## Files

### detection/local.rules
Six custom Snort IPS rules using DROP mode for active packet blocking:
- SYN Flood detection (sid:1000100)
- UDP Flood detection (sid:1000101)
- DNS Flood detection (sid:1000102)
- ICMP Flood detection (sid:1000103)
- Large UDP payload detection (sid:1000104)
- DNS amplification detection (sid:1000105)

### attack/scapy_attacks.py
Python script simulating a four-phase Mirai-style botnet DDoS attack:
- Phase 1: SYN flood targeting EHR system (port 8080)
- Phase 2: UDP flood targeting hospital infrastructure
- Phase 3: DNS flood targeting hospital.nhs.uk
- Phase 4: ICMP flood targeting hospital network
- Total: 4000 packets with randomised source IPs

### server/ehr_server.py
Python HTTP server hosting the NHS Trust EHR system.
Reads Synthea synthetic patient dataset (patients.csv, conditions.csv, 
medications.csv) and displays patient records on port 8080.

### server/iomt_devices.py
Simulates six hospital IoMT devices on ports 8081-8086 and a network 
monitor dashboard on port 8087. Shows real-time device status during attack.

### dashboard/dashboard.py
Flask-based Security Operations Centre dashboard running on port 5000.
Monitors all hospital systems in real time and visualises the attack 
and defence simultaneously.

## Running the Simulation

### Prerequisites
sudo apt install snort python3-scapy python3-flask nmap hydra -y

### Start order
Terminal 1 - EHR Server:
cd server && python3 ehr_server.py

Terminal 2 - IoMT Devices:
cd server && python3 iomt_devices.py

Terminal 3 - Dashboard:
cd dashboard && python3 dashboard.py

Terminal 4 - Snort IPS:
sudo snort -A console -c /etc/snort/snort.conf -i lo

Terminal 5 - Attack:
cd attack && sudo python3 scapy_attacks.py

### Botnet Recruitment Phase
sudo nmap -sV 127.0.0.1
hydra -l testdevice -p Admin1234! ssh://127.0.0.1 -t 4 -V

## Tools Used
- Snort 2.9.20 - Intrusion Prevention System
- Scapy 2.5.0 - Packet crafting and attack simulation
- Wireshark - Network traffic analysis and preprocessing
- nmap - Network reconnaissance
- Hydra - Credential attack simulation
- Flask - Dashboard web framework
- Ubuntu 24.04 (VMware Workstation Pro)

## Dataset
- Synthea synthetic patient dataset (EHR target)
- Four module-provided pcap files analysed in Wireshark:
  - SYN.pcap (4,975 packets)
  - udp_flood.pcap (999 packets)
  - dns.pcap (1,117 packets)
  - ip_fragmented.pcap (9,077 packets)

## References
- Mandalari et al. (2025) - Protected or Porous: A Comparative Analysis 
  of Threat Detection Capability of IoT Safeguards
- Gupta and Sharma (2019) - Mitigation of DoS and Port Scan Attacks 
  Using Snort