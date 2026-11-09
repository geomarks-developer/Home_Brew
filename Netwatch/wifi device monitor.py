import concurrent.futures
import ipaddress
import re
import socket
import subprocess


def get_local_ip():
    """Return this computer's local LAN/Wi-Fi IP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # No traffic needs to be sent; this helps Windows select
        # the interface used for normal network access.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def ping(ip):
    """Return IP if the device responds to ping."""
    result = subprocess.run(
        ["ping", "-n", "1", "-w", "250", str(ip)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    return str(ip) if result.returncode == 0 else None


def read_arp_table():
    """Read Windows ARP cache and return IP -> MAC mapping."""
    output = subprocess.check_output(
        ["arp", "-a"],
        text=True,
        errors="ignore"
    )

    devices = {}

    pattern = re.compile(
        r"(\d+\.\d+\.\d+\.\d+)\s+"
        r"([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})"
    )

    for ip, mac in pattern.findall(output):
        devices[ip] = mac.upper()

    return devices


def get_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, socket.timeout):
        return ""


def main():
    local_ip = get_local_ip()

    # Most home Wi-Fi networks use a /24 subnet.
    network = ipaddress.ip_network(f"{local_ip}/24", strict=False)

    print("=" * 72)
    print("PulseScout-style Local Network Scanner")
    print("=" * 72)
    print(f"Your IP : {local_ip}")
    print(f"Network : {network}")
    print()
    print("Scanning...")
    print()

    hosts = list(network.hosts())

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        results = list(executor.map(ping, hosts))

    active_ips = [ip for ip in results if ip]

    # Ping sweep populates Windows' ARP cache.
    arp_table = read_arp_table()

    print(f"{'IP Address':<18} {'MAC Address':<20} {'Device Name'}")
    print("-" * 72)

    for ip in sorted(active_ips, key=ipaddress.ip_address):
        mac = arp_table.get(ip, "Unknown")
        hostname = get_hostname(ip)

        marker = "  <-- THIS PC" if ip == local_ip else ""

        print(
            f"{ip:<18} "
            f"{mac:<20} "
            f"{hostname}{marker}"
        )

    print("-" * 72)
    print(f"Devices responding: {len(active_ips)}")


if __name__ == "__main__":
    main()