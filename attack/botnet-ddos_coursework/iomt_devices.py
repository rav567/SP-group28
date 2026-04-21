from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import time
import urllib.request

DEVICES = [
    {"name": "Infusion Pump 1",   "port": 8081, "ward": "Ward A", "patient": "P001"},
    {"name": "Infusion Pump 2",   "port": 8082, "ward": "ICU",    "patient": "P003"},
    {"name": "Patient Monitor 1", "port": 8083, "ward": "Ward B", "patient": "P002"},
    {"name": "Patient Monitor 2", "port": 8084, "ward": "ICU",    "patient": "P005"},
    {"name": "Smart Bed Sensor",  "port": 8085, "ward": "Ward C", "patient": "P004"},
    {"name": "DNS Server",        "port": 8086, "ward": "Network","patient": "N/A"},
]

def check_device(port):
    try:
        urllib.request.urlopen(f"http://localhost:{port}/status", timeout=1)
        return "ONLINE"
    except:
        return "OFFLINE"

class NetworkMonitorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        device_rows = ""
        all_online = True

        for device in DEVICES:
            status = check_device(device['port'])
            if status == "OFFLINE":
                all_online = False
            status_color = "#28a745" if status == "ONLINE" else "#dc3545"

            device_rows += f"""
            <tr>
                <td><strong>{device['name']}</strong></td>
                <td>{device['ward']}</td>
                <td>{device['patient']}</td>
                <td>192.168.1.{device['port'] - 8080}</td>
                <td>Port {device['port']}</td>
                <td>
                    <span style="background:{status_color};color:white;
                    padding:4px 12px;border-radius:4px;font-weight:bold;
                    font-size:12px;">{status}</span>
                </td>
            </tr>
            """

        network_status = "ALL SYSTEMS OPERATIONAL" if all_online else "NETWORK UNDER ATTACK - DEVICES OFFLINE"
        network_color = "#28a745" if all_online else "#dc3545"
        online_count = sum(1 for d in DEVICES if check_device(d['port']) == "ONLINE")
        offline_count = len(DEVICES) - online_count

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>St. Raphael's NHS Trust - Network Monitor</title>
            <meta http-equiv="refresh" content="3">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ font-family: Arial, sans-serif; background: #f0f2f5; }}
                .header {{
                    background: #003087;
                    color: white;
                    padding: 15px 25px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .header h1 {{ font-size: 22px; }}
                .header p {{ font-size: 12px; opacity: 0.8; margin-top: 3px; }}
                .header-right {{ text-align: right; font-size: 12px; }}
                .network-status {{
                    background: {network_color};
                    color: white;
                    padding: 15px 25px;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                }}
                .stats-bar {{
                    background: white;
                    padding: 12px 25px;
                    display: flex;
                    gap: 20px;
                    border-bottom: 3px solid #005EB8;
                    align-items: center;
                }}
                .stat-box {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }}
                .stat-box strong {{ color: #003087; }}
                .container {{ padding: 20px 25px; }}
                .section-title {{
                    font-size: 15px;
                    font-weight: bold;
                    color: #003087;
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #005EB8;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                th {{
                    background: #003087;
                    color: white;
                    padding: 11px 12px;
                    text-align: left;
                    font-size: 12px;
                    text-transform: uppercase;
                }}
                td {{
                    padding: 12px;
                    border-bottom: 1px solid #f0f0f0;
                    font-size: 13px;
                }}
                tr:hover {{ background: #f8f9ff; }}
                .footer {{
                    background: #003087;
                    color: white;
                    text-align: center;
                    padding: 10px;
                    font-size: 11px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <h1>St. Raphael's NHS Trust</h1>
                    <p>IoMT Network Monitor - IT Security Operations</p>
                </div>
                <div class="header-right">
                    <div>Last Updated: {current_time}</div>
                    <div>Auto-refresh: every 3 seconds</div>
                </div>
            </div>
            <div class="network-status">{network_status}</div>
            <div class="stats-bar">
                <div class="stat-box">Total Devices: <strong>{len(DEVICES)}</strong></div>
                <div class="stat-box" style="color:#28a745">Online: <strong>{online_count}</strong></div>
                <div class="stat-box" style="color:#dc3545">Offline: <strong>{offline_count}</strong></div>
                <div class="stat-box">Last Check: <strong>{current_time}</strong></div>
            </div>
            <div class="container">
                <div class="section-title">IoMT Device Status - St. Raphael's NHS Trust</div>
                <table>
                    <tr>
                        <th>Device Name</th>
                        <th>Ward</th>
                        <th>Patient ID</th>
                        <th>IP Address</th>
                        <th>Port</th>
                        <th>Status</th>
                    </tr>
                    {device_rows}
                </table>
            </div>
            <div class="footer">
                St. Raphael's NHS Trust - Network Operations Centre | Monitoring {len(DEVICES)} IoMT Devices
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass

def make_handler(device):
    class DeviceHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/status':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'ONLINE')
                return
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"{device['name']} - ONLINE".encode())

        def log_message(self, format, *args):
            pass

    return DeviceHandler

def start_device(device):
    handler = make_handler(device)
    server = HTTPServer(('0.0.0.0', device['port']), handler)
    print(f"Device online: {device['name']} - Port {device['port']}")
    server.serve_forever()

def start_monitor():
    server = HTTPServer(('0.0.0.0', 8087), NetworkMonitorHandler)
    print("Network Monitor running at: http://localhost:8087")
    server.serve_forever()

print("St. Raphael's NHS Trust - IoMT Device Network")
print("Starting all devices...")

threads = []
for device in DEVICES:
    t = threading.Thread(target=start_device, args=(device,))
    t.daemon = True
    t.start()
    threads.append(t)
    time.sleep(0.1)

monitor_thread = threading.Thread(target=start_monitor)
monitor_thread.daemon = True
monitor_thread.start()

print("All IoMT devices running on ports 8081-8086")
print("Network Monitor running at: http://localhost:8087")
print("Press Ctrl+C to stop")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down IoMT network")