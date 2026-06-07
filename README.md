# 📱 DroidScan Pro

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-%233776AB?logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.2-%23000?logo=flask)](https://flask.palletsprojects.com/)

**DroidScan Pro** is an open‑source, Flask‑based Android security scanner that can:
- Detect known malicious APK signatures.
- Perform heuristic permission analysis.
- Run fast mock scans (no device required) **or** real scans on a connected Android device via ADB.
- Generate beautiful HTML reports.
- Expose a clean REST API for automation.

---

## 🎯 Features
- **Signature blacklist** with hundreds of real‑world malware families.
- **Permission risk weighting** for heuristic detection.
- **Mock mode** for quick demos and CI testing.
- **Web UI** (single‑page dashboard) powered by Flask.
- **REST endpoints** for programmatic integration.
- **SQLite** storage of scan history.
- **Self‑contained** ADB binary for Windows users.

---

## 📦 Installation
```powershell
# 1️⃣ Clone the repo
git clone https://github.com/checker423/DroidScanPro.git
cd DroidScanPro/SZDRFTYG

# 2️⃣ Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell (or `source .venv/bin/activate` on macOS/Linux)

# 3️⃣ Install Python dependencies
pip install -r requirements.txt
```

> The repository already contains a copy of `adb.exe` for Windows. If you prefer your own Android SDK, edit **line 20** in `app.py` to point at the correct `adb` path.

---

## 🚀 Quick start
### Mock demo (no device)
```python
# Open app.py and set
MOCK_MODE = True
python app.py
```
Open <http://127.0.0.1:5000> in a browser – the UI will instantly show a fake device and a list of mock apps.

### Real device scan
1. Enable **USB‑debugging** on your Android phone (Settings → Developer options).
2. Connect the phone via USB.
3. Keep `MOCK_MODE = False`.
4. Run the server:
```powershell
python app.py
```
5. Click **Start Scan** in the UI or call the API (see below).

---

## 📡 REST API reference
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/device/status` | GET | Returns connection status and basic device info. |
| `/api/scan/start` | POST | Starts a quick or deep scan. Body: `{ "serial":"<SERIAL>", "scan_mode":"quick|deep" }` |
| `/api/scan/progress` | GET | Polls current scan progress. |
| `/api/virus/start` | POST | Fast signature‑only scan. |
| `/api/virus/progress` | GET | Poll virus‑scan progress. |
| `/api/scan/report/<scan_id>` | GET | Download an HTML report of a completed scan. |
| `/api/files/list` | GET | List files on the device (`path` query param). |
| `/api/files/download` | GET | Pull a file from the device. |
| `/api/apps/uninstall` | POST | Uninstall a package (`package` & `serial` in JSON). |
| `/api/device/kill` | POST | Kill a process (`pid` & `serial`). |
| `/api/settings/clear_db` | POST | Delete all scan history. |
| `/api/history/delete/<scan_id>` | DELETE | Remove a specific scan entry. |

All responses are JSON‑encoded. Use `curl`, *Postman*, or any HTTP client.

---

## 🛠️ Extending the scanner
- **Add a new signature** – edit `engine.signature_blacklist` in `engine.py`. Provide `description`, `category`, `solution`, `fix_action`.
- **Tweak permission weights** – modify `engine.permission_risks`.
- **Custom UI** – update the HTML/CSS under `templates/` and `static/`.
- **Package as executable** – run `pyinstaller -F app.py` (the repo already contains a `.spec` file).

---

## 🤝 Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome‑thing`).
3. Make your changes and ensure the code passes linting:
```powershell
flake8 .
```
4. Run the test suite (if added):
```powershell
pytest
```
5. Commit with a clear message and push.
6. Open a Pull Request describing the changes.

All contributions are welcome – feel free to add signatures, improve heuristics, polish the UI, or write documentation.

---

## 📄 License
This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact
- **Author:** Vansh (GitHub: [`@checker423`](https://github.com/checker423))
- **Issues:** Please open a GitHub Issue for bugs or feature requests.

---

  Made By Vansh Yadav
