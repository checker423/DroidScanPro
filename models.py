# flake8: noqa
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_path='scanner.db'):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    serial TEXT PRIMARY KEY,
                    model TEXT,
                    android_version TEXT,
                    last_scan_at DATETIME
                )
            ''')
            # Scans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_serial TEXT,
                    timestamp DATETIME,
                    risk_score REAL,
                    total_apps INTEGER,
                    threats_found INTEGER,
                    FOREIGN KEY (device_serial) REFERENCES devices(serial)
                )
            ''')
            # Detected threats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detected_threats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    package_name TEXT,
                    risk_level TEXT,
                    reason TEXT,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                )
            ''')
            conn.commit()

    def upsert_device(self, serial, model, version):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO devices (serial, model, android_version, last_scan_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(serial) DO UPDATE SET
                    model=excluded.model,
                    android_version=excluded.android_version
            ''', (serial, model, version, datetime.now()))
            conn.commit()

    def save_scan(self, serial, risk_score, total_apps, threats_found):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scans (device_serial, timestamp, risk_score, total_apps, threats_found)
                VALUES (?, ?, ?, ?, ?)
            ''', (serial, datetime.now(), risk_score, total_apps, threats_found))
            scan_id = cursor.lastrowid
            
            # Update last scan at
            cursor.execute('UPDATE devices SET last_scan_at=? WHERE serial=?', (datetime.now(), serial))
            conn.commit()
            return scan_id

    def save_threat(self, scan_id, package_name, risk_level, reason):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO detected_threats (scan_id, package_name, risk_level, reason)
                VALUES (?, ?, ?, ?)
            ''', (scan_id, package_name, risk_level, reason))
            conn.commit()

    def get_device_history(self, serial):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, risk_score, total_apps, threats_found 
                FROM scans 
                WHERE device_serial = ? 
                ORDER BY timestamp DESC
            ''', (serial,))
            return cursor.fetchall()
            
    def get_last_scan_details(self, serial):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, risk_score FROM scans 
                WHERE device_serial = ? ORDER BY timestamp DESC LIMIT 1
            ''', (serial,))
            scan = cursor.fetchone()
            if not scan:
                return None
            
            cursor.execute('''
                SELECT package_name, risk_level, reason 
                FROM detected_threats WHERE scan_id = ?
            ''', (scan[0],))
            threats = cursor.fetchall()
            return {"scan": scan, "threats": threats}

    def get_scan_by_id(self, scan_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, device_serial, timestamp, risk_score, total_apps, threats_found 
                FROM scans WHERE id = ?
            ''', (scan_id,))
            scan = cursor.fetchone()
            if not scan:
                return None
            
            cursor.execute('''
                SELECT package_name, risk_level, reason 
                FROM detected_threats WHERE scan_id = ?
            ''', (scan_id,))
            threats = cursor.fetchall()
            return {"scan": scan, "threats": threats}

    def delete_scan(self, scan_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM detected_threats WHERE scan_id = ?', (scan_id,))
            cursor.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
            conn.commit()
            return True

    def clear_history(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM detected_threats')
            cursor.execute('DELETE FROM scans')
            conn.commit()
            return True

