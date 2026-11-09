import concurrent.futures
import ipaddress
import re
import socket
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "netwatch.db"

PING_TIMEOUT_MS = 300
MAX_WORKERS = 40

# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Enable SQLite foreign-key enforcement.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn

def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                hostname TEXT,
                device_name TEXT,
                status TEXT NOT NULL DEFAULT 'Unknown',
                notes TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                times_seen INTEGER NOT NULL DEFAULT 1,
                online INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_devices_ip
            ON devices(ip_address)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_devices_status
            ON devices(status)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                network TEXT,
                local_ip TEXT,
                active_ips_found INTEGER NOT NULL DEFAULT 0,
                devices_identified INTEGER NOT NULL DEFAULT 0,
                new_devices_found INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'running'
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scans_started
            ON scans(started_at)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                mac_address TEXT NOT NULL,
                ip_address TEXT,
                hostname TEXT,
                observed_at TEXT NOT NULL,
                online INTEGER NOT NULL DEFAULT 1,

                FOREIGN KEY (scan_id)
                    REFERENCES scans(id),

                FOREIGN KEY (mac_address)
                    REFERENCES devices(mac_address)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scan_history_scan
            ON scan_history(scan_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scan_history_mac
            ON scan_history(mac_address)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scan_history_time
            ON scan_history(observed_at)
        """)

# ---------------------------------------------------------
# Network detection
# ---------------------------------------------------------

def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()

def get_network(local_ip):
    """
    Initial version assumes a typical /24 home network.
    Example:
        192.168.1.24 -> 192.168.1.0/24
    """
    return ipaddress.ip_network(f"{local_ip}/24", strict=False)

# ---------------------------------------------------------
# Ping sweep
# ---------------------------------------------------------

def ping_host(ip):
    ip = str(ip)

    result = subprocess.run(
        [
            "ping",
            "-n", "1",
            "-w", str(PING_TIMEOUT_MS),
            ip
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    if result.returncode == 0:
        return ip

    return None

def scan_network(network):
    hosts = list(network.hosts())

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        results = executor.map(ping_host, hosts)

    return [ip for ip in results if ip]

# ---------------------------------------------------------
# ARP
# ---------------------------------------------------------

def get_arp_table():
    result = subprocess.run(
        ["arp", "-a"],
        capture_output=True,
        text=True,
        errors="ignore"
    )

    # Windows MAC format:
    # aa-bb-cc-dd-ee-ff
    pattern = re.compile(
        r"(\d+\.\d+\.\d+\.\d+)\s+"
        r"([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})"
    )

    arp_entries = {}

    for ip, mac in pattern.findall(result.stdout):
        arp_entries[ip] = normalize_mac(mac)

    return arp_entries

def normalize_mac(mac):
    return mac.strip().upper().replace(":", "-")

# ---------------------------------------------------------
# Hostname
# ---------------------------------------------------------

def get_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (
        socket.herror,
        socket.gaierror,
        socket.timeout
    ):
        return ""

# ---------------------------------------------------------
# Inventory management
# ---------------------------------------------------------

def mark_all_offline(conn):
    conn.execute("""
        UPDATE devices
        SET online = 0
    """)
def start_scan(network, local_ip):
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scans (
                started_at,
                network,
                local_ip,
                status
            )
            VALUES (?, ?, ?, 'running')
            """,
            (
                started_at,
                str(network),
                local_ip
            )
        )

        return cursor.lastrowid

def complete_scan(
    scan_id,
    active_ips_found,
    devices_identified,
    new_devices_found
):
    completed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scans
            SET
                completed_at = ?,
                active_ips_found = ?,
                devices_identified = ?,
                new_devices_found = ?,
                status = 'completed'
            WHERE id = ?
            """,
            (
                completed_at,
                active_ips_found,
                devices_identified,
                new_devices_found,
                scan_id
            )
        )

def fail_scan(scan_id):
    completed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE scans
            SET
                completed_at = ?,
                status = 'failed'
            WHERE id = ?
            """,
            (
                completed_at,
                scan_id
            )
        )

def update_device(conn, ip, mac, hostname):
    now = datetime.now().astimezone().isoformat(timespec="seconds")

    existing = conn.execute(
        """
        SELECT *
        FROM devices
        WHERE mac_address = ?
        """,
        (mac,)
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE devices
            SET
                ip_address = ?,
                hostname = ?,
                last_seen = ?,
                times_seen = times_seen + 1,
                online = 1
            WHERE mac_address = ?
            """,
            (
                ip,
                hostname,
                now,
                mac
            )
        )

        return False

    conn.execute(
        """
        INSERT INTO devices (
            mac_address,
            ip_address,
            hostname,
            first_seen,
            last_seen,
            times_seen,
            online
        )
        VALUES (?, ?, ?, ?, ?, 1, 1)
        """,
        (
            mac,
            ip,
            hostname,
            now,
            now
        )
    )

    return True

def add_scan_history(
    conn,
    scan_id,
    ip,
    mac,
    hostname
):
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO scan_history (
            scan_id,
            mac_address,
            ip_address,
            hostname,
            observed_at,
            online
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            scan_id,
            mac,
            ip,
            hostname,
            observed_at
        )
    )

def save_scan(scan_id, active_ips):
    arp_table = get_arp_table()

    discovered = []
    new_devices = []

    with get_connection() as conn:
        mark_all_offline(conn)

        for ip in active_ips:

            mac = arp_table.get(ip)

            # We need a stable identifier before inserting
            # the device into the inventory.
            if not mac:
                continue

            hostname = get_hostname(ip)

            is_new = update_device(
                conn,
                ip,
                mac,
                hostname
            )

            add_scan_history(
                conn,
                scan_id,
                ip,
                mac,
                hostname
            )

            device = {
                "ip": ip,
                "mac": mac,
                "hostname": hostname,
                "new": is_new
            }

            discovered.append(device)

            if is_new:
                new_devices.append(device)

    return discovered, new_devices

# ---------------------------------------------------------
# Inventory reporting
# ---------------------------------------------------------

def show_inventory():
    with get_connection() as conn:

        rows = conn.execute("""
            SELECT
                ip_address,
                mac_address,
                hostname,
                device_name,
                status,
                online,
                first_seen,
                last_seen,
                times_seen
            FROM devices
            ORDER BY
                online DESC,
                status,
                ip_address
        """).fetchall()

    print()
    print("=" * 110)
    print("DEVICE INVENTORY")
    print("=" * 110)

    print(
        f"{'IP':<16}"
        f"{'MAC':<19}"
        f"{'Name':<24}"
        f"{'Status':<12}"
        f"{'Online':<9}"
        f"{'Seen':<7}"
    )

    print("-" * 110)

    for row in rows:

        name = (
            row["device_name"]
            or row["hostname"]
            or "Unknown"
        )

        online = "YES" if row["online"] else "NO"

        print(
            f"{(row['ip_address'] or ''):<16}"
            f"{row['mac_address'\]:<19}"
            f"{name[:22\]:<24}"
            f"{row['status'\]:<12}"
            f"{online:<9}"
            f"{row['times_seen'\]:<7}"
        )

    print("-" * 110)
    print(f"Inventory contains {len(rows)} device(s).")

def show_recent_history(limit=20):
    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                h.observed_at,
                h.scan_id,
                h.ip_address,
                h.mac_address,
                h.hostname,
                d.device_name,
                d.status
            FROM scan_history h
            LEFT JOIN devices d
                ON h.mac_address = d.mac_address
            ORDER BY h.observed_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    print()
    print("=" * 110)
    print("RECENT SCAN HISTORY")
    print("=" * 110)

    print(
        f"{'Scan':<8}"
        f"{'Time':<27}"
        f"{'IP':<16}"
        f"{'MAC':<19}"
        f"{'Device':<24}"
        f"{'Status':<12}"
    )

    print("-" * 110)

    for row in rows:

        name = (
            row["device_name"]
            or row["hostname"]
            or "Unknown"
        )

        print(
            f"{row['scan_id']:<8}"
            f"{row['observed_at']:<27}"
            f"{(row['ip_address'] or ''):<16}"
            f"{row['mac_address']:<19}"
            f"{name[:22]:<24}"
            f"{row['status']:<12}"
        )

    print("-" * 110)

# ---------------------------------------------------------
# Scan
# ---------------------------------------------------------

def run_scan():
    initialize_database()

    local_ip = get_local_ip()
    network = get_network(local_ip)

    print()
    print("=" * 70)
    print("NETWATCH")
    print("=" * 70)
    print()
    print(f"This computer : {local_ip}")
    print(f"Scanning      : {network}")
    print()
    print("Looking for devices...")

    scan_id = start_scan(
        network,
        local_ip
    )

    try:
        active_ips = scan_network(network)

        discovered, new_devices = save_scan(
            scan_id,
            active_ips
        )

        complete_scan(
            scan_id=scan_id,
            active_ips_found=len(active_ips),
            devices_identified=len(discovered),
            new_devices_found=len(new_devices)
        )

    except Exception:
        fail_scan(scan_id)
        raise

    print()
    print(
        f"{len(discovered)} device(s) identified "
        "with IP/MAC information."
    )

    if new_devices:
        print()
        print("=" * 70)
        print("NEW DEVICES")
        print("=" * 70)

        for device in new_devices:

            hostname = (
                device["hostname"]
                or "Unknown"
            )

            print()
            print(f"IP       : {device['ip']}")
            print(f"MAC      : {device['mac']}")
            print(f"Hostname : {hostname}")

    show_inventory()
    show_recent_history()

# -----------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    try:
        run_scan()

    except KeyboardInterrupt:
        print("\nScan cancelled.")

    except Exception as exc:
        print()
        print(f"ERROR: {exc}")