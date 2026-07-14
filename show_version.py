import csv
import getpass
import os
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


def get_credentials():
    print("\n--- Cisco Switch Version Collector ---\n")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return username, password


def get_ip_list():
    print("\nHow would you like to enter switch IPs?")
    print("  1. Enter IPs manually")
    print("  2. Load from a CSV file")
    choice = input("\nChoice (1 or 2): ").strip()

    if choice == "1":
        print("\nEnter IP addresses one per line. Leave blank and press Enter when done.")
        ips = []
        while True:
            ip = input("IP: ").strip()
            if not ip:
                break
            ips.append(ip)
        return ips

    elif choice == "2":
        filename = input("\nCSV filename (include .csv extension): ").strip()
        if not os.path.isfile(filename):
            print(f"Error: File '{filename}' not found.")
            return []
        ips = []
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0].strip():
                    ips.append(row[0].strip())
        print(f"Loaded {len(ips)} IP(s) from '{filename}'.")
        return ips

    else:
        print("Invalid choice.")
        return []


def query_switch(host, username, password):
    device = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
        "timeout": 30,
    }
    conn = ConnectHandler(**device)
    output = conn.send_command("show version")
    conn.disconnect()
    return output


def main():
    username, password = get_credentials()
    ip_list = get_ip_list()

    if not ip_list:
        print("No IPs provided. Exiting.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"show_version_{timestamp}.txt"

    print(f"\nConnecting to {len(ip_list)} switch(es)...\n")

    with open(output_file, "w") as f:
        for host in ip_list:
            print(f"  Querying {host}...", end=" ")
            f.write(f"{'=' * 60}\n")
            f.write(f"Host: {host}\n")
            f.write(f"{'=' * 60}\n")
            try:
                result = query_switch(host, username, password)
                f.write(result + "\n\n")
                print("OK")
            except NetmikoAuthenticationException:
                msg = "Authentication failed."
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")
            except NetmikoTimeoutException:
                msg = "Connection timed out."
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")
            except Exception as e:
                msg = str(e)
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")

    print(f"\nDone. Output saved to: {output_file}")


if __name__ == "__main__":
    main()
