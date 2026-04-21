from flask import Flask, jsonify, request
from datetime import datetime
import urllib.request
import threading
import time

app = Flask(__name__)

attack_state = {
    "active": False,
    "type": "None",
    "alerts": []
}

DEVICES = [
    {"name": "EHR System",        "port": 8080, "type": "Critical"},
    {"name": "Infusion Pump 1",   "port": 8081, "type": "IoMT"},
    {"name": "Infusion Pump 2",   "port": 8082, "type": "IoMT"},
    {"name": "Patient Monitor 1", "port": 8083, "type": "IoMT"},
    {"name": "Patient Monitor 2", "port": 8084, "type": "IoMT"},
    {"name": "Smart Bed Sensor",  "port": 8085, "type": "IoMT"},
    {"name": "DNS Server",        "port": 8086, "type": "Network"},
]

ATTACK_SEQUENCE = [
    {"type": "SYN Flood",  "msg": "CRITICAL: SYN Flood detected - 1000 packets/sec from randomised IPs"},
    {"type": "UDP Flood",  "msg": "CRITICAL: UDP Flood detected - Hospital infrastructure targeted"},
    {"type": "DNS Flood",  "msg": "CRITICAL: DNS Flood detected - hospital.nhs.uk targeted"},
    {"type": "ICMP Flood", "msg": "CRITICAL: ICMP Flood detected - Network saturated"},
]

def check_device(port):
    if attack_state["active"]:
        return "OFFLINE"
    try:
        urllib.request.urlopen(f"http://localhost:{port}/status", timeout=1)
        return "ONLINE"
    except:
        return "ONLINE"

def run_attack_sequence():
    attack_state["alerts"] = []
    for attack in ATTACK_SEQUENCE:
        if not attack_state["active"]:
            break
        attack_state["type"] = attack["type"]
        attack_state["alerts"].insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": attack["msg"],
            "critical": True
        })
        time.sleep(3)

    if attack_state["active"]:
        attack_state["alerts"].insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": "IPS BLOCK: Attack mitigated - Custom Snort rules triggered - Systems restoring",
            "critical": False
        })

@app.route('/api/toggle', methods=['POST'])
def toggle_attack():
    attack_state["active"] = not attack_state["active"]
    if attack_state["active"]:
        t = threading.Thread(target=run_attack_sequence)
        t.daemon = True
        t.start()
    else:
        attack_state["type"] = "None"
        attack_state["alerts"].insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": "IPS: All systems restored - Attack blocked successfully",
            "critical": False
        })
    return jsonify({"active": attack_state["active"]})

@app.route('/api/status')
def get_status():
    device_status = []
    online_count = 0

    for device in DEVICES:
        status = check_device(device['port'])
        if status == "ONLINE":
            online_count += 1
        device_status.append({
            "name": device['name'],
            "port": device['port'],
            "type": device['type'],
            "status": status
        })

    offline_count = len(DEVICES) - online_count

    return jsonify({
        "devices": device_status,
        "online": online_count,
        "offline": offline_count,
        "attack_active": attack_state["active"],
        "attack_type": attack_state["type"],
        "alerts": attack_state["alerts"][:10],
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })

@app.route('/')
def dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>St. Raphael's NHS Trust - Security Operations Centre</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; background: #0a0e1a; color: #e0e0e0; }
            .header {
                background: #003087;
                padding: 15px 25px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 3px solid #005EB8;
            }
            .header h1 { font-size: 20px; color: white; }
            .header p { font-size: 12px; color: #aac4e8; margin-top: 3px; }
            .header-right { text-align: right; font-size: 12px; color: #aac4e8; }
            .network-banner {
                padding: 12px 25px;
                text-align: center;
                font-weight: bold;
                font-size: 15px;
                letter-spacing: 1px;
                cursor: pointer;
                user-select: none;
                transition: all 0.5s;
            }
            .network-banner.operational { background: #155724; color: #d4edda; }
            .network-banner.attack { background: #721c24; color: #f8d7da; animation: blink 1s infinite; }
            @keyframes blink { 0%{opacity:1} 50%{opacity:0.7} 100%{opacity:1} }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }
            .panel { background: #111827; border: 1px solid #1f2937; border-radius: 8px; overflow: hidden; }
            .panel-header {
                background: #1f2937;
                padding: 12px 15px;
                font-size: 13px;
                font-weight: bold;
                color: #93c5fd;
                text-transform: uppercase;
                letter-spacing: 1px;
                border-bottom: 1px solid #374151;
            }
            .panel-body { padding: 15px; }
            .device-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #1f2937;
                font-size: 13px;
            }
            .device-row:last-child { border-bottom: none; }
            .device-name { color: #e0e0e0; }
            .device-type { color: #6b7280; font-size: 11px; }
            .badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            .badge-online { background: #065f46; color: #6ee7b7; }
            .badge-offline { background: #7f1d1d; color: #fca5a5; }
            .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
            .stat-card { background: #1f2937; border-radius: 6px; padding: 15px; text-align: center; }
            .stat-value { font-size: 28px; font-weight: bold; color: #93c5fd; }
            .stat-label { font-size: 11px; color: #6b7280; margin-top: 4px; text-transform: uppercase; }
            .attack-type { background: #1f2937; border-radius: 6px; padding: 12px; text-align: center; margin-bottom: 15px; font-size: 13px; }
            .attack-type span { color: #fca5a5; font-weight: bold; }
            .alert-feed { height: 220px; overflow-y: auto; background: #0a0e1a; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 11px; }
            .alert-item { padding: 5px 0; border-bottom: 1px solid #1f2937; color: #6ee7b7; line-height: 1.4; }
            .alert-item.critical { color: #fca5a5; }
            .timestamp { color: #4b5563; margin-right: 8px; }
            #clock { color: #93c5fd; font-size: 13px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>St. Raphael's NHS Trust</h1>
                <p>Security Operations Centre - Real Time Network Monitor</p>
            </div>
            <div class="header-right">
                <div id="clock">Loading...</div>
                <div>SOC Dashboard v2.0</div>
            </div>
        </div>
        <div class="network-banner operational" id="networkBanner" onclick="toggleAttack()">
            ALL SYSTEMS OPERATIONAL
        </div>
        <div class="grid">
            <div class="panel">
                <div class="panel-header">IoMT Device Status</div>
                <div class="panel-body" id="deviceList">Loading...</div>
            </div>
            <div class="panel">
                <div class="panel-header">Network Statistics</div>
                <div class="panel-body">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" id="onlineCount">-</div>
                            <div class="stat-label">Devices Online</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="offlineCount" style="color:#fca5a5">-</div>
                            <div class="stat-label">Devices Offline</div>
                        </div>
                    </div>
                    <div class="attack-type">
                        Current Threat: <span id="attackType">None Detected</span>
                    </div>
                    <div class="panel-header" style="margin: 0 -15px 10px -15px; padding: 10px 15px;">
                        IPS Alert Feed
                    </div>
                    <div class="alert-feed" id="alertFeed">
                        <div class="alert-item">System monitoring active - Waiting for events...</div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            async function toggleAttack() {
                await fetch('/api/toggle', {method: 'POST'});
            }
            function updateClock() {
                document.getElementById('clock').textContent = new Date().toLocaleString('en-GB');
            }
            async function updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    document.getElementById('deviceList').innerHTML = data.devices.map(d => `
                        <div class="device-row">
                            <div>
                                <div class="device-name">${d.name}</div>
                                <div class="device-type">${d.type} - Port ${d.port}</div>
                            </div>
                            <span class="badge ${d.status === 'ONLINE' ? 'badge-online' : 'badge-offline'}">${d.status}</span>
                        </div>
                    `).join('');
                    document.getElementById('onlineCount').textContent = data.online;
                    document.getElementById('offlineCount').textContent = data.offline;
                    document.getElementById('attackType').textContent = data.attack_active ? data.attack_type : 'None Detected';
                    const banner = document.getElementById('networkBanner');
                    if (data.attack_active) {
                        banner.className = 'network-banner attack';
                        banner.textContent = 'NETWORK UNDER ATTACK - DDoS DETECTED - IPS ACTIVE - CLICK TO RESOLVE';
                    } else {
                        banner.className = 'network-banner operational';
                        banner.textContent = 'ALL SYSTEMS OPERATIONAL';
                    }
                    if (data.alerts && data.alerts.length > 0) {
                        document.getElementById('alertFeed').innerHTML = data.alerts.map(a => `
                            <div class="alert-item ${a.critical ? 'critical' : ''}">
                                <span class="timestamp">[${a.time}]</span>${a.msg}
                            </div>
                        `).join('');
                    }
                } catch(e) {
                    console.log('Update error:', e);
                }
            }
            setInterval(updateClock, 1000);
            setInterval(updateStatus, 2000);
            updateClock();
            updateStatus();
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    print("St. Raphael's NHS Trust - Security Operations Centre")
    print("Dashboard running at: http://localhost:5000")
    print("Click the status banner to toggle attack simulation")
    app.run(host='0.0.0.0', port=5000, debug=False)