import os
from flask import Flask, render_template, jsonify, request, send_file
from adb_wrapper import ADBWrapper
from models import Database
from engine import ScanEngine
from datetime import datetime
import json
import threading

import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    template_folder = os.path.join(base_path, 'templates')
    static_folder = os.path.join(base_path, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    adb_path = os.path.join(base_path, 'adb.exe')
else:
    app = Flask(__name__)
    adb_path = r"D:\platform-tools-latest-windows\platform-tools\adb.exe"

db = Database()
engine = ScanEngine()
adb = ADBWrapper(adb_path)

# Mock settings for demonstration
MOCK_MODE = True

# Progress tracking for scans
scan_progress       = {"status": "idle", "percent": 0, "current_task": "", "results": None}
virus_scan_progress = {"status": "idle", "percent": 0, "current_task": "", "results": None}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/device/status')
def device_status():
    if MOCK_MODE:
        return jsonify({
            "connected": True,
            "device_id": "ADB-MOCK-7788",
            "model": "Samsung Galaxy S23 (Mock)",
            "android_version": "14",
            "battery": "92",
            "storage_free": "45.2",
            "storage_total": "109.5",
            "ram_str": "4.2 / 8.0"
        })
    
    devices = adb.get_devices()
    if isinstance(devices, dict) and "error" in devices:
        return jsonify({"connected": False, "error": devices["error"]})
    
    if not devices:
        return jsonify({"connected": False, "error": "No device detected. Enable USB Debugging."})
    
    device = devices[0]
    info = adb.get_device_info(device['serial'])
    db.upsert_device(device['serial'], info['model'], info['version'])
    
    return jsonify({
        "connected": True, 
        "device_id": device['serial'],
        "model": info['model'],
        "android_version": info['version'],
        "battery": info.get('battery', 'N/A'),
        "storage_free": info.get('storage_free', 'N/A'),
        "storage_total": info.get('storage_total', 'N/A'),
        "ram_str": info.get('ram_str', 'N/A')
    })

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    global scan_progress
    if scan_progress["status"] == "running":
        return jsonify({"status": "error", "message": "Scan already in progress"})
    
    data = request.json
    serial    = data.get('serial', 'MOCK')
    scan_mode = data.get('scan_mode', 'quick')  # 'quick' = user apps only, 'deep' = all apps
    third_party_only = (scan_mode != 'deep')

    def run_scan():
        global scan_progress
        scan_progress = {"status": "running", "percent": 0, "current_task": "Initializing...", "results": None}
        
        try:
            if MOCK_MODE:
                mock_packages = ["com.android.vending", "com.google.android.youtube", "com.whatsapp", "com.vanced.mod.youtube", "com.fakeapp.whatsapp"]
                total = len(mock_packages)
                app_results = []
                
                for i, pkg in enumerate(mock_packages):
                    time_sleep = 0.5
                    import time
                    time.sleep(time_sleep)
                    
                    scan_progress["percent"] = int(((i + 1) / total) * 100)
                    scan_progress["current_task"] = f"Scanning {pkg}..."
                    
                    # Simulated permissions
                    perms = []
                    if "mod" in pkg or "fakeapp" in pkg: perms = ["android.permission.READ_SMS", "android.permission.INTERNET", "android.permission.BIND_DEVICE_ADMIN"]
                    
                    threats, score = engine.analyze_package(pkg, perms)
                    app_results.append({"package": pkg, "threats": threats, "score": score})
                
                device_risk = engine.calculate_device_risk(app_results)
                scan_id = db.save_scan("ADB-MOCK-7788", device_risk, total, sum(1 for a in app_results if a['threats']))
                
                for res in app_results:
                    for t in res['threats']:
                        db.save_threat(scan_id, res['package'], t['risk'], t['description'])
                
                scan_progress["results"] = {
                    "total_apps": total,
                    "risk_score": round(device_risk, 1),
                    "threats_found": sum(1 for a in app_results if a['threats']),
                    "apps": app_results
                }
            else:
                # Real device scan
                packages = adb.list_packages(serial, third_party_only=third_party_only)
                total = len(packages)
                app_results = []
                
                for i, pkg in enumerate(packages):
                    scan_progress["percent"] = int(((i + 1) / total) * 100)
                    scan_progress["current_task"] = f"Analyzing {pkg}..."
                    
                    perms = adb.get_package_permissions(serial, pkg)
                    threats, score = engine.analyze_package(pkg, perms)
                    app_results.append({"package": pkg, "threats": threats, "score": score})
                
                device_risk = engine.calculate_device_risk(app_results)
                scan_id = db.save_scan(serial, device_risk, total, sum(1 for a in app_results if a['threats']))
                
                for res in app_results:
                    for t in res['threats']:
                        db.save_threat(scan_id, res['package'], t['risk'], t['description'])
                
                scan_progress["results"] = {
                    "total_apps": total,
                    "risk_score": round(device_risk, 1),
                    "threats_found": sum(1 for a in app_results if a['threats']),
                    "apps": app_results
                }
                
            scan_progress["status"] = "completed"
            scan_progress["current_task"] = "Scan Complete"
        except Exception as e:
            scan_progress["status"] = "error"
            scan_progress["current_task"] = f"Error: {str(e)}"

    threading.Thread(target=run_scan).start()
    return jsonify({"status": "success"})

@app.route('/api/scan/progress')
def get_progress():
    return jsonify(scan_progress)

@app.route('/api/device/history/<serial>')
def get_history(serial):
    history = db.get_device_history(serial)
    return jsonify({"history": history})

@app.route('/api/scan/report/<int:scan_id>')
def download_report(scan_id):
    report_data = db.get_scan_by_id(scan_id)
    if not report_data:
        return "Report not found", 404
        
    scan = report_data["scan"]
    threats = report_data["threats"]
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Security Report - Scan {scan[0]}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #1e293b; padding: 40px; margin: 0; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 6px solid #4f46e5; }}
            h1 {{ color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: 0; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; background: #f1f5f9; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
            .stat-box {{ border-left: 3px solid #4f46e5; padding-left: 15px; }}
            .stat-label {{ font-size: 0.85em; color: #64748b; text-transform: uppercase; font-weight: bold; }}
            .stat-value {{ font-size: 1.25em; font-weight: bold; margin-top: 5px; }}
            h2 {{ color: #334155; margin-top: 30px; }}
            .threat-item {{ background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #ef4444; }}
            .threat-title {{ font-weight: bold; color: #b91c1c; font-size: 1.1em; }}
            .threat-risk {{ display: inline-block; background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-bottom: 8px; }}
            .no-threats {{ background: #d1fae5; color: #065f46; padding: 15px; border-radius: 6px; border: 1px solid #a7f3d0; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>DroidScan Pro - Security Audit</h1>
            <p style="color: #64748b;">Generated natively by DroidScan Pro Engine.</p>
            
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Device Serial</div>
                    <div class="stat-value">{scan[1]}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Audit Date</div>
                    <div class="stat-value">{scan[2]}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Overall Risk Score</div>
                    <div class="stat-value" style="color: {'#ef4444' if scan[3] > 70 else '#f59e0b' if scan[3] > 30 else '#10b981'}">{scan[3]:.1f}/100</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Applications Scanned</div>
                    <div class="stat-value">{scan[4]}</div>
                </div>
            </div>
            
            <h2>Threat Analysis Findings ({scan[5]})</h2>
    """
    
    if not threats:
        html_content += '<div class="no-threats">System is clean. No malicious signatures or dangerous permissions detected.</div>'
    else:
        for t in threats:
            risk_color = "#ef4444" if t[1] == "CRITICAL" else "#f59e0b" if t[1] == "HIGH" else "#3b82f6"
            html_content += f"""
            <div class="threat-item" style="border-left-color: {risk_color};">
                <div class="threat-risk" style="background: {risk_color};">{t[1]}</div>
                <div class="threat-title">{t[0]}</div>
                <p style="margin-bottom:0; color:#334155; font-size: 0.95em;">{t[2]}</p>
            </div>
            """
            
    html_content += """
        </div>
    </body>
    </html>
    """
            
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".html")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return send_file(path, as_attachment=True, download_name=f"Security_Report_{scan[0]}.html")


@app.route('/api/files/list')
def list_files():
    path = request.args.get('path', '/sdcard/')
    serial = request.args.get('serial', 'MOCK')
    
    if MOCK_MODE:
        return jsonify({
            "path": path,
            "files": [
                {"name": "DCIM/", "type": "dir"},
                {"name": "Download/", "type": "dir"},
                {"name": "Pictures/", "type": "dir"},
                {"name": "suspicious_file.apk", "type": "file"},
                {"name": ".hidden_config", "type": "file"}
            ]
        })
    
    files = adb.list_files(serial, path)
    formatted = []
    for f in files:
        f_type = "dir" if f.endswith('/') else "file"
        formatted.append({"name": f, "type": f_type})
    
    return jsonify({"path": path, "files": formatted})

@app.route('/api/device/processes')
def list_processes():
    serial = request.args.get('serial', 'MOCK')
    if MOCK_MODE:
        return jsonify({"processes": [
            {"user": "u0_a1", "pid": "1024", "memory": "45200", "name": "com.android.systemui"},
            {"user": "u0_a2", "pid": "2048", "memory": "120000", "name": "com.whatsapp"},
            {"user": "u0_a3", "pid": "3450", "memory": "8500", "name": "com.example.malware"},
            {"user": "root", "pid": "1", "memory": "2400", "name": "init"}
        ]})
    processes = adb.get_processes(serial)
    return jsonify({"processes": processes})

@app.route('/api/files/download')
def download_file():
    path = request.args.get('path')
    serial = request.args.get('serial', 'MOCK')

    import tempfile
    filename = path.split('/')[-1] if path and '/' in path else (path or 'extracted_file')

    if not MOCK_MODE and serial and serial != 'MOCK':
        suffix = os.path.splitext(filename)[-1] or '.bin'
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        adb.pull_file(serial, path, temp_path)
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return send_file(temp_path, as_attachment=True, download_name=filename)
        return jsonify({"error": "Could not pull file from device. Check path and permissions."}), 500
    else:
        # Mock / fallback
        fd, temp_path = tempfile.mkstemp(suffix='.extracted')
        with os.fdopen(fd, 'w') as f:
            f.write(f"SIMULATED EXTRACTION OF: {path}\nThis is a mock pulled file for analysis.")
        return send_file(temp_path, as_attachment=True, download_name=filename)


@app.route('/api/files/install', methods=['POST'])
def install_apk():
    data = request.json
    remote_path = data.get('path')
    serial = data.get('serial')

    if not remote_path or not serial:
        return jsonify({"status": "error", "message": "Missing path or serial."}), 400

    import tempfile
    fd, temp_path = tempfile.mkstemp(suffix='.apk')
    os.close(fd)

    adb.pull_file(serial, remote_path, temp_path)

    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
        return jsonify({"status": "error", "message": "Could not pull APK from device."}), 500

    result = adb.run(f'-s {serial} install -r "{temp_path}"', timeout=90)
    try:
        os.unlink(temp_path)
    except Exception:
        pass

    if 'Success' in result:
        return jsonify({"status": "success", "message": "APK installed successfully on device!"})
    return jsonify({"status": "error", "message": f"Install failed: {result}"}), 500

@app.route('/api/files/preview')
def preview_file():
    path   = request.args.get('path')
    serial = request.args.get('serial', 'MOCK')

    import tempfile, base64
    filename = path.split('/')[-1] if path and '/' in path else (path or 'file')
    ext = os.path.splitext(filename)[-1].lower()

    TEXT_EXTS  = {'.txt','.log','.json','.xml','.csv','.md','.py','.js','.html','.css','.java','.kt','.sh','.yaml','.yml'}
    IMAGE_EXTS = {'.jpg','.jpeg','.png','.gif','.webp','.bmp'}
    MIME_MAP   = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
                  '.gif':'image/gif','.webp':'image/webp','.bmp':'image/bmp'}

    if not MOCK_MODE and serial and serial != 'MOCK':
        fd, temp_path = tempfile.mkstemp(suffix=ext or '.bin')
        os.close(fd)
        adb.pull_file(serial, path, temp_path)
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            return jsonify({"error": "Could not fetch file for preview."}), 500
        if ext in IMAGE_EXTS:
            with open(temp_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode()
            os.unlink(temp_path)
            return jsonify({"type": "image", "src": f"data:{MIME_MAP.get(ext,'image/jpeg')};base64,{data}", "name": filename})
        elif ext in TEXT_EXTS:
            with open(temp_path, 'r', errors='replace') as f:
                content = f.read(60000)
            os.unlink(temp_path)
            return jsonify({"type": "text", "content": content, "name": filename})
        else:
            os.unlink(temp_path)
            return jsonify({"error": "Preview not supported for this file type."}), 415
    else:
        return jsonify({"type": "text", "content": f"[MOCK PREVIEW]\nFile: {path}\nConnect a real device for actual file preview.", "name": filename})

@app.route('/api/settings/clear_db', methods=['POST'])
def clear_db():
    try:
        db.clear_history()
        return jsonify({"status": "success", "message": "History cleared."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/apps/uninstall', methods=['POST'])
def uninstall_app():
    data    = request.json
    package = data.get('package')
    serial  = data.get('serial')
    if not package or not serial:
        return jsonify({"status": "error", "message": "Missing package or serial."}), 400
    result = adb.run(f"-s {serial} shell pm uninstall {package}", timeout=30)
    if 'Success' in result:
        return jsonify({"status": "success", "message": f"'{package}' uninstalled successfully."})
    return jsonify({"status": "error", "message": f"Uninstall failed: {result.strip()}"}), 500

@app.route('/api/device/kill', methods=['POST'])
def kill_process():
    data   = request.json
    pid    = data.get('pid')
    serial = data.get('serial')
    if not pid or not serial:
        return jsonify({"status": "error", "message": "Missing PID or serial."}), 400
    adb.run(f"-s {serial} shell kill -9 {pid}", timeout=10)
    return jsonify({"status": "success", "message": f"Process {pid} terminated."})

@app.route('/api/history/delete/<int:scan_id>', methods=['DELETE'])
def delete_history(scan_id):
    try:
        db.delete_scan(scan_id)
        return jsonify({"status": "success", "message": f"Scan #{scan_id} deleted."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan/estimate')
def scan_estimate():
    """Return package count and estimated scan times for Quick/Deep/Virus modes."""
    serial    = request.args.get('serial', 'MOCK')
    if MOCK_MODE or serial == 'MOCK':
        return jsonify({"quick": {"count": 35, "eta_sec": 18}, "deep": {"count": 280, "eta_sec": 140}, "virus": {"count": 280, "eta_sec": 14}})
    try:
        user_pkgs   = adb.list_packages(serial, third_party_only=True)
        all_pkgs    = adb.list_packages(serial, third_party_only=False)
        quick_count = len(user_pkgs)
        deep_count  = len(all_pkgs)
        return jsonify({
            "quick": {"count": quick_count, "eta_sec": round(quick_count * 0.4)},
            "deep":  {"count": deep_count,  "eta_sec": round(deep_count  * 0.4)},
            "virus": {"count": deep_count,  "eta_sec": round(deep_count  * 0.05)},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/virus/start', methods=['POST'])
def start_virus_scan():
    global virus_scan_progress
    if virus_scan_progress["status"] == "running":
        return jsonify({"status": "error", "message": "Virus scan already running."})
    data      = request.json
    serial    = data.get('serial', 'MOCK')
    scan_mode = data.get('scan_mode', 'quick')
    third_party_only = (scan_mode != 'deep')

    def run_virus_scan():
        global virus_scan_progress
        virus_scan_progress = {"status": "running", "percent": 0, "current_task": "Loading signatures...", "results": None}
        try:
            if MOCK_MODE or serial == 'MOCK':
                mock_pkgs = list(engine.signature_blacklist.keys())[:15] + ["com.whatsapp", "com.android.systemui", "com.google.android.youtube"] + list(engine.signature_blacklist.keys())[15:]
            else:
                mock_pkgs = adb.list_packages(serial, third_party_only=third_party_only)

            total    = len(mock_pkgs)
            infected = []
            import time

            for i, pkg in enumerate(mock_pkgs):
                virus_scan_progress["percent"]      = int(((i + 1) / total) * 100)
                virus_scan_progress["current_task"] = f"Checking {pkg}..."
                if not MOCK_MODE:
                    time.sleep(0.03)   # lightweight — signature only
                else:
                    time.sleep(0.3)

                # Signature-only check (no heuristics)
                if pkg in engine.signature_blacklist:
                    info = engine.signature_blacklist[pkg]
                    infected.append({
                        "package":     pkg,
                        "category":    info["category"],
                        "description": info["description"],
                        "solution":    info["solution"],
                        "fix_action":  info["fix_action"],
                    })

            virus_scan_progress["results"] = {
                "total_checked": total,
                "infected":      infected,
                "clean":         total - len(infected),
            }
            virus_scan_progress["status"]       = "completed"
            virus_scan_progress["current_task"] = "Scan Complete"
        except Exception as e:
            virus_scan_progress["status"]       = "error"
            virus_scan_progress["current_task"] = f"Error: {str(e)}"

    threading.Thread(target=run_virus_scan).start()
    return jsonify({"status": "success"})

@app.route('/api/virus/progress')
def get_virus_progress():
    return jsonify(virus_scan_progress)

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        import webbrowser
        from threading import Timer
        Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
        app.run(debug=False, port=5000, host='0.0.0.0', use_reloader=False)
    else:
        app.run(debug=True, port=5000, host='0.0.0.0')
