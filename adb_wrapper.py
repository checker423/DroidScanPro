import subprocess
import shutil
import os


class ADBWrapper:
    def __init__(self, adb_path=None):
        # Try to find adb automatically: use provided path, then system PATH
        self.adb_path = self._resolve_adb(adb_path)

    def _resolve_adb(self, hint_path):
        """Find a working adb binary. Priority: hint_path > system PATH."""
        # 1. Try the explicitly provided path
        if hint_path and os.path.isfile(hint_path):
            return hint_path

        # 2. Try to find 'adb' on PATH (works when user sets env var in CMD)
        found = shutil.which("adb")
        if found:
            return found

        # 3. Common fallback locations
        fallbacks = [
            r"D:\platform-tools-latest-windows\platform-tools\adb.exe",
            r"C:\platform-tools\adb.exe",
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
        ]
        for path in fallbacks:
            if os.path.isfile(path):
                return path

        raise FileNotFoundError(
            "adb not found. Set its folder in your System PATH or pass the full path to ADBWrapper."
        )

    def run(self, command, timeout=10):
        """Run an adb command and return stdout as a string."""
        try:
            # Pass the current env so subprocess inherits PATH
            env = os.environ.copy()
            result = subprocess.run(
                f'"{self.adb_path}" {command}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            return f"__ERROR__:{e}"

    # ------------------------------------------------------------------ #
    #  Device Detection
    # ------------------------------------------------------------------ #

    def get_devices(self):
        """Return list of connected devices [{serial, status}]."""
        output = self.run("devices")
        if output.startswith("__ERROR__"):
            return {"error": output.replace("__ERROR__:", "")}

        lines = output.split("\n")[1:]
        devices = []
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({"serial": parts[0], "status": parts[1]})
        return devices

    def get_device_info(self, serial):
        """Return model, Android version, battery, storage and RAM for a device."""
        model = self.run(f"-s {serial} shell getprop ro.product.model")
        android = self.run(f"-s {serial} shell getprop ro.build.version.release")

        # Battery: fetch FULL dumpsys output and parse in Python
        # (Windows CMD swallows the pipe so "dumpsys battery | grep level" fails)
        battery_out = self.run(f"-s {serial} shell dumpsys battery")
        bat_level = "N/A"
        try:
            for line in battery_out.split("\n"):
                stripped = line.strip()
                if stripped.startswith("level:"):
                    bat_level = stripped.split(":")[1].strip()
                    break
        except Exception:
            pass

        # Storage: use /data partition (true internal storage), return free + total
        storage_out = self.run(f"-s {serial} shell df /data", timeout=10)
        storage_free = "N/A"
        storage_total = "N/A"
        try:
            for line in storage_out.strip().split("\n"):
                if line and not line.lower().startswith("filesystem"):
                    parts = line.split()
                    if len(parts) >= 4:
                        total_kb = int(parts[1])
                        avail_kb = int(parts[3])
                        storage_free  = f"{avail_kb  / (1024 * 1024):.1f}"
                        storage_total = f"{total_kb  / (1024 * 1024):.1f}"
                        break
        except Exception:
            pass

        # RAM from /proc/meminfo; MemAvailable preferred, MemFree as fallback
        meminfo = self.run(f"-s {serial} shell cat /proc/meminfo", timeout=10)
        ram_str = "N/A"
        try:
            mem_total = mem_avail = mem_free = 0
            for line in meminfo.split("\n"):
                ls = line.strip()
                if ls.startswith("MemTotal:"):
                    mem_total = int(ls.split()[1])
                elif ls.startswith("MemAvailable:"):
                    mem_avail = int(ls.split()[1])
                elif ls.startswith("MemFree:"):
                    mem_free = int(ls.split()[1])
            effective_avail = mem_avail if mem_avail > 0 else mem_free
            if mem_total > 0:
                used_gb  = (mem_total - effective_avail) / (1024 * 1024)
                total_gb = mem_total / (1024 * 1024)
                ram_str  = f"{used_gb:.1f} / {total_gb:.1f}"
        except Exception:
            pass

        return {
            "model":         model or "Unknown Device",
            "version":       android or "Unknown",
            "battery":       bat_level,
            "storage_free":  storage_free,
            "storage_total": storage_total,
            "ram_str":       ram_str,
        }

    # ------------------------------------------------------------------ #
    #  App / Package Management
    # ------------------------------------------------------------------ #

    def list_packages(self, serial, third_party_only=True):
        """Return list of installed package names. Defaults to user-installed apps only."""
        flag = "-3" if third_party_only else ""
        output = self.run(f"-s {serial} shell pm list packages {flag}", timeout=30)
        packages = []
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.replace("package:", ""))
        return packages

    def get_package_permissions(self, serial, package):
        """Return list of declared/granted permissions for a package."""
        output = self.run(
            f"-s {serial} shell dumpsys package {package}", timeout=10
        )
        perms = []
        capture = False
        for line in output.split("\n"):
            if "declared permissions:" in line.lower() or "install permissions:" in line.lower():
                capture = True
            if capture and "android.permission." in line:
                perm = line.strip().split(":")[0].strip()
                if perm:
                    perms.append(perm)
            # Stop at the next top-level block
            if capture and line and not line.startswith(" ") and "permission" not in line.lower():
                capture = False
        return list(set(perms))

    # ------------------------------------------------------------------ #
    #  File System
    # ------------------------------------------------------------------ #

    def list_files(self, serial, path="/sdcard/"):
        """Return list of file/dir names at the given path."""
        output = self.run(f"-s {serial} shell ls -p {path}", timeout=10)
        if not output or output.startswith("__ERROR__"):
            return []
        files = []
        for item in output.split("\n"):
            item = item.strip()
            if item:
                files.append(item)
        return files

    def pull_file(self, serial, remote_path, local_path):
        """Pull a file from the device."""
        result = self.run(f"-s {serial} pull {remote_path} {local_path}", timeout=60)
        return result

    # ------------------------------------------------------------------ #
    #  Process Manager
    # ------------------------------------------------------------------ #

    def get_processes(self, serial):
        """Return list of running processes [{user, pid, memory, name}].

        Android's ps output format (standard across Android 7+):
          USER       PID  PPID    VSZ    RSS WCHAN            ADDR S NAME
        Column indices are detected dynamically from the header so this
        survives across different Android versions.
        """
        output = self.run(f"-s {serial} shell ps -A", timeout=20)
        if not output or output.startswith("__ERROR__"):
            return []

        lines = [l for l in output.split("\n") if l.strip()]
        if len(lines) < 2:
            return []

        # --- detect column positions from header ---
        header_parts = lines[0].upper().split()
        try:
            pid_idx  = header_parts.index("PID")
        except ValueError:
            pid_idx  = 1
        try:
            rss_idx  = header_parts.index("RSS")
        except ValueError:
            # Some ROMs label it VSIZE / VSZ; fall back to column 4
            rss_idx  = 4
        # NAME is always the last column
        name_idx = len(header_parts) - 1

        processes = []
        seen_pids = set()

        for line in lines[1:]:
            parts = line.split()
            if len(parts) <= max(pid_idx, rss_idx):
                continue
            pid = parts[pid_idx] if pid_idx < len(parts) else ""
            if not pid or not pid.isdigit() or pid in seen_pids:
                continue
            seen_pids.add(pid)

            try:
                rss_kb = int(parts[rss_idx])
            except (ValueError, IndexError):
                rss_kb = 0

            # NAME is the last token on the line
            name = parts[-1]

            processes.append({
                "user":   parts[0],
                "pid":    pid,
                "memory": str(rss_kb),   # KB — JS divides by 1024 for MB
                "name":   name,
            })

        # Sort heaviest first, return top 100
        processes.sort(
            key=lambda x: int(x["memory"]) if x["memory"].isdigit() else 0,
            reverse=True,
        )
        return processes[:100]
