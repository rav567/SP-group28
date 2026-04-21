import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PATIENTS = {}
CONDITIONS = {}
MEDICATIONS = {}

def load_all_data():
    global PATIENTS, CONDITIONS, MEDICATIONS

    with open('patients.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['Id']
            PATIENTS[pid] = {
                'name': row['FIRST'] + ' ' + row['LAST'],
                'dob': row['BIRTHDATE'],
                'gender': row['GENDER'],
                'city': row.get('CITY', 'Unknown'),
            }

    with open('conditions.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['PATIENT']
            if pid not in CONDITIONS:
                CONDITIONS[pid] = []
            if row['DESCRIPTION'] not in CONDITIONS[pid]:
                CONDITIONS[pid].append(row['DESCRIPTION'])

    with open('medications.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['PATIENT']
            if pid not in MEDICATIONS:
                MEDICATIONS[pid] = []
            if row['DESCRIPTION'] not in MEDICATIONS[pid]:
                MEDICATIONS[pid].append(row['DESCRIPTION'])

    print(f"Loaded {len(PATIENTS)} patients successfully")

class EHRHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ONLINE')
            return

        rows = ""
        wards = ["Ward A", "Ward B", "Ward C", "ICU", "Ward D"]

        for i, (pid, p) in enumerate(list(PATIENTS.items())[:20]):
            conds = "<br>".join(CONDITIONS.get(pid, ["None"])[:2])
            meds = "<br>".join(MEDICATIONS.get(pid, ["None"])[:2])
            ward = wards[i % len(wards)]
            conditions_text = " ".join(CONDITIONS.get(pid, []))
            risk = "HIGH" if "failure" in conditions_text.lower() or "cardiac" in conditions_text.lower() else "NORMAL"
            risk_color = "#dc3545" if risk == "HIGH" else "#28a745"

            rows += f"""
            <tr>
                <td><strong>P{i+1:03d}</strong></td>
                <td>{p['name']}</td>
                <td>{p['dob']}</td>
                <td>{p['gender']}</td>
                <td>{p['city']}</td>
                <td style="font-size:11px">{conds}</td>
                <td style="font-size:11px">{meds}</td>
                <td>{ward}</td>
                <td><span style="color:{risk_color};font-weight:bold">{risk}</span></td>
            </tr>
            """

        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        total_patients = len(PATIENTS)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>St. Raphael's NHS Trust - EHR System</title>
            <meta http-equiv="refresh" content="5">
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
                .status-bar {{
                    background: white;
                    padding: 12px 25px;
                    display: flex;
                    gap: 20px;
                    border-bottom: 3px solid #005EB8;
                    align-items: center;
                }}
                .status-badge {{
                    background: #28a745;
                    color: white;
                    padding: 6px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                .stat-box {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
                }}
                .stat-box strong {{ color: #003087; }}
                .confidential {{
                    background: #fff3cd;
                    border-bottom: 1px solid #ffc107;
                    color: #856404;
                    padding: 8px 25px;
                    font-size: 12px;
                    font-weight: bold;
                }}
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
                    padding: 10px 12px;
                    border-bottom: 1px solid #f0f0f0;
                    font-size: 12px;
                    vertical-align: top;
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
                    <p>Electronic Health Records System - Authorised Access Only</p>
                </div>
                <div class="header-right">
                    <div>Last Updated: {current_time}</div>
                    <div>System Version: EHR v4.2.1</div>
                </div>
            </div>
            <div class="status-bar">
                <div class="status-badge">SYSTEM ONLINE</div>
                <div class="stat-box">Total Patients: <strong>{total_patients}</strong></div>
                <div class="stat-box">Active Records: <strong>{min(20, total_patients)}</strong></div>
                <div class="stat-box">Last Sync: <strong>{current_time}</strong></div>
                <div class="stat-box">Security: <strong>GDPR Compliant</strong></div>
            </div>
            <div class="confidential">
                CONFIDENTIAL - Patient data protected under GDPR Article 32.
                Unauthorised access is a criminal offence under the Computer Misuse Act 1990.
            </div>
            <div class="container">
                <div class="section-title">Patient Records - St. Raphael's NHS Trust</div>
                <table>
                    <tr>
                        <th>Patient ID</th>
                        <th>Full Name</th>
                        <th>Date of Birth</th>
                        <th>Gender</th>
                        <th>Location</th>
                        <th>Conditions</th>
                        <th>Medications</th>
                        <th>Ward</th>
                        <th>Risk Level</th>
                    </tr>
                    {rows}
                </table>
            </div>
            <div class="footer">
                St. Raphael's NHS Trust EHR System | NHS Digital Infrastructure | All data encrypted in transit and at rest
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

load_all_data()

print("St. Raphael's NHS Trust - EHR System")
print(f"Running at: http://localhost:8080")
print(f"Patients loaded: {len(PATIENTS)}")

server = HTTPServer(('0.0.0.0', 8080), EHRHandler)
server.serve_forever()