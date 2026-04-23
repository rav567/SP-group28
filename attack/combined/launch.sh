#!/bin/bash
# launch.sh — Run from your Mac. One command does everything:
#   1. Copies docker files to Ubuntu VM and builds containers
#   2. Copies attack files to Kali VM and installs dependencies
#   3. Runs the full attack from Kali
#   4. SSHs into each container to verify the damage
#   5. Saves terminal output + attack_log.json to a timestamped results folder
#
# Usage:
#   ./launch.sh <UBUNTU_IP> <KALI_IP>
#
# Example:
#   ./launch.sh 172.16.63.128 172.16.63.129
#
# Prerequisites:
#   - Both VMs running with Host-Only networking
#   - SSH enabled on Kali (sudo systemctl start ssh)
#   - Ubuntu user: hospitalserver / hospitalserver
#   - Kali user:   kali / kali

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

if [ "$#" -ne 2 ]; then
    echo -e "${RED}Usage: ./launch.sh <UBUNTU_IP> <KALI_IP>${NC}"
    echo "Example: ./launch.sh 172.16.63.128 172.16.63.129"
    exit 1
fi

UBUNTU_IP="$1"
KALI_IP="$2"

UBUNTU_USER="hospitalserver"
UBUNTU_PASS="hospitalserver"
KALI_USER="kali"
KALI_PASS="kali"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"

# ── Results folder (timestamped) ──────────────────────────────
RESULTS_BASE="/Users/yaseralharbi/Desktop/Masters/Sem 2/secutiryt and privacy/Virus-Simulation/results/auto run results"
RUN_TIMESTAMP="$(date '+%Y-%m-%d %H-%M-%S')"
RESULTS_DIR="${RESULTS_BASE}/${RUN_TIMESTAMP}"
LOG_FILE="${RESULTS_DIR}/terminal_output.txt"

mkdir -p "$RESULTS_DIR"
echo -e "${BOLD}${CYAN}Results will be saved to:${NC}"
echo -e "  ${YELLOW}${RESULTS_DIR}${NC}"
echo ""

# All output from this point is tee'd to the log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Run started: $(date)"
echo "Ubuntu IP : $UBUNTU_IP"
echo "Kali IP   : $KALI_IP"
echo ""

# Helper: save a labelled section divider in the log
log_section() {
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "  $1"
    echo "  $(date '+%H:%M:%S')"
    echo "════════════════════════════════════════════════════════"
    echo ""
}

run_ssh() {
    local user="$1" host="$2" pass="$3" cmd="$4"
    sshpass -p "$pass" ssh $SSH_OPTS "$user@$host" "$cmd"
}

run_scp() {
    local src="$1" user="$2" host="$3" pass="$4" dst="$5"
    sshpass -p "$pass" scp -r $SSH_OPTS "$src" "$user@$host:$dst"
}

# ── Check sshpass is installed on Mac ─────────────────────────
if ! command -v sshpass &>/dev/null; then
    echo -e "${RED}[!] sshpass not found. Install it:${NC}"
    echo "    brew install sshpass"
    echo ""
    echo "If brew says 'not available', use:"
    echo "    brew install hudochenkov/sshpass/sshpass"
    exit 1
fi

# ── Check connectivity ────────────────────────────────────────
log_section "STEP 0/6 — Connectivity check"
if ! ping -c 1 -W 2 "$UBUNTU_IP" &>/dev/null; then
    echo -e "${RED}[!] Cannot reach Ubuntu VM at $UBUNTU_IP${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Ubuntu VM ($UBUNTU_IP) reachable${NC}"

if ! ping -c 1 -W 2 "$KALI_IP" &>/dev/null; then
    echo -e "${RED}[!] Cannot reach Kali VM at $KALI_IP${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Kali VM ($KALI_IP) reachable${NC}"

# Check SSH on both
if ! sshpass -p "$UBUNTU_PASS" ssh $SSH_OPTS "$UBUNTU_USER@$UBUNTU_IP" "echo ok" &>/dev/null; then
    echo -e "${RED}[!] Cannot SSH into Ubuntu VM. Check credentials (${UBUNTU_USER}/${UBUNTU_PASS})${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Ubuntu VM SSH working${NC}"

if ! sshpass -p "$KALI_PASS" ssh $SSH_OPTS "$KALI_USER@$KALI_IP" "echo ok" &>/dev/null; then
    echo -e "${RED}[!] Cannot SSH into Kali VM. Run on Kali first: sudo systemctl start ssh${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Kali VM SSH working${NC}"

# ── Step 1: Setup Ubuntu VM ──────────────────────────────────
log_section "STEP 1/6 — Ubuntu VM setup"

echo "  Checking if Docker is installed..."
DOCKER_INSTALLED=$(run_ssh "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" \
    "command -v docker &>/dev/null && echo yes || echo no")

if [ "$DOCKER_INSTALLED" = "no" ]; then
    echo "  Installing Docker (this takes a minute)..."
    run_ssh "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" \
        "echo '$UBUNTU_PASS' | sudo -S apt-get update -qq && echo '$UBUNTU_PASS' | sudo -S apt-get install -y -qq docker.io docker-compose-v2 && echo '$UBUNTU_PASS' | sudo -S usermod -aG docker $UBUNTU_USER"
    echo -e "  ${GREEN}✓ Docker installed${NC}"
    echo "  Reconnecting (docker group refresh)..."
    sleep 2
else
    echo -e "  ${GREEN}✓ Docker already installed${NC}"
fi

# ── Step 2: Copy docker files to Ubuntu and build ─────────────
log_section "STEP 2/6 — Build Docker containers on Ubuntu"

run_ssh "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" "rm -rf ~/docker"
run_scp "$SCRIPT_DIR/docker" "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" "~/docker"
echo -e "  ${GREEN}✓ Docker files copied${NC}"

echo "  Building containers (first time takes 2-3 min)..."
run_ssh "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" \
    "cd ~/docker && docker compose down 2>/dev/null; docker compose up -d --build"
echo -e "  ${GREEN}✓ Containers built and running${NC}"

echo "  Verifying containers..."
CONTAINERS=$(run_ssh "$UBUNTU_USER" "$UBUNTU_IP" "$UBUNTU_PASS" "docker ps --format '{{.Names}}' | sort")
echo "$CONTAINERS" | while read -r name; do
    echo -e "    ${GREEN}✓ $name${NC}"
done

# ── Step 3: Copy attack files to Kali ─────────────────────────
log_section "STEP 3/6 — Copy attack files to Kali"

run_ssh "$KALI_USER" "$KALI_IP" "$KALI_PASS" "rm -rf ~/combined"
run_scp "$SCRIPT_DIR" "$KALI_USER" "$KALI_IP" "$KALI_PASS" "~/combined"
echo -e "  ${GREEN}✓ Attack files copied${NC}"

# ── Step 4: Install dependencies on Kali ──────────────────────
log_section "STEP 4/6 — Install Python dependencies on Kali"

run_ssh "$KALI_USER" "$KALI_IP" "$KALI_PASS" \
    "pip install paramiko cryptography flask --break-system-packages -q 2>/dev/null || pip3 install paramiko cryptography flask --break-system-packages -q"
echo -e "  ${GREEN}✓ paramiko + cryptography + flask installed${NC}"

# ── Step 5: Run the attack ────────────────────────────────────
log_section "STEP 5/6 — Launch attack from Kali → $UBUNTU_IP"

run_ssh "$KALI_USER" "$KALI_IP" "$KALI_PASS" \
    "cd ~/combined && python3 run_attack.py $UBUNTU_IP"

# ── Step 6: Verify damage ─────────────────────────────────────
log_section "STEP 6/6 — Verify damage on all 3 containers"

SUMMARY_FILE="${RESULTS_DIR}/damage_summary.txt"
{
    echo "Damage Summary — $(date)"
    echo "Target: $UBUNTU_IP"
    echo ""
} > "$SUMMARY_FILE"

for port in 2222 2223 2224; do
    case $port in
        2222) name="EHR Server" ;;
        2223) name="IoT Gateway" ;;
        2224) name="Staff Portal" ;;
    esac

    echo ""
    echo -e "  ${BOLD}── $name (port $port) ──${NC}"

    FILES=$(sshpass -p "Hospital2024!" ssh $SSH_OPTS -p "$port" "ehradmin@$UBUNTU_IP" \
        "ls /opt/hospital-data/ 2>/dev/null" 2>/dev/null || echo "CONNECT_FAILED")

    if [ "$FILES" = "CONNECT_FAILED" ]; then
        echo -e "    ${RED}✗ Could not connect${NC}"
        echo "$name (port $port): CONNECT FAILED" >> "$SUMMARY_FILE"
    else
        ENC_COUNT=$(echo "$FILES" | grep -c '\.enc$' || true)
        HAS_NOTE=$(echo "$FILES" | grep -c 'RANSOM_NOTE' || true)

        if [ "$ENC_COUNT" -gt 0 ] && [ "$HAS_NOTE" -gt 0 ]; then
            echo -e "    ${GREEN}✓ $ENC_COUNT encrypted files + ransom note found${NC}"
            echo "$name (port $port): $ENC_COUNT files encrypted, RANSOM_NOTE present" >> "$SUMMARY_FILE"
        else
            echo "    Files: $FILES"
            echo "$name (port $port): Files = $FILES" >> "$SUMMARY_FILE"
        fi
    fi
done

# ── Pull attack_log.json from Kali ───────────────────────────
echo ""
echo -e "  ${CYAN}Pulling attack_log.json from Kali...${NC}"
sshpass -p "$KALI_PASS" scp $SSH_OPTS \
    "$KALI_USER@$KALI_IP:~/combined/attack_log.json" \
    "${RESULTS_DIR}/attack_log.json" 2>/dev/null && \
    echo -e "  ${GREEN}✓ attack_log.json saved to results folder${NC}" || \
    echo -e "  ${YELLOW}  (attack_log.json not found on Kali — run may have been too short)${NC}"

# ── Final summary ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ALL DONE — Attack complete!${NC}"
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Results saved to:"
echo -e "  ${YELLOW}${RESULTS_DIR}${NC}"
echo ""
echo "  Contents:"
ls "$RESULTS_DIR" | sed 's/^/    /'
echo ""
echo "  To reset the lab, rebuild the containers on Ubuntu:"
echo "    ssh hospitalserver@$UBUNTU_IP"
echo "    cd ~/docker && docker compose down && docker compose up -d --build"
echo ""
