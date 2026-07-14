# --- Standard library imports ---
import csv       # For reading IP addresses from a CSV file
import getpass   # For securely prompting the user for a password (input is hidden)
import os        # For checking if a file exists on disk
from datetime import datetime  # For generating a timestamp on the output file

# --- Third-party library imports (requires: pip install netmiko) ---
from netmiko import ConnectHandler  # Main class for opening SSH connections to network devices
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
# NetmikoAuthenticationException: raised when the username/password is wrong
# NetmikoTimeoutException: raised when the device doesn't respond in time


def get_credentials():
    """Prompt the user for their SSH username and password."""
    print("\n--- Cisco Switch Version Collector ---\n")
    username = input("Username: ")
    # getpass hides the password as the user types it, so it won't appear on screen
    password = getpass.getpass("Password: ")
    return username, password


def get_ip_list():
    """Ask the user how they want to provide switch IPs, then return a list of them."""
    print("\nHow would you like to enter switch IPs?")
    print("  1. Enter IPs manually")
    print("  2. Load from a CSV file")
    choice = input("\nChoice (1 or 2): ").strip()

    if choice == "1":
        # Manual entry: keep asking for IPs until the user submits a blank line
        print("\nEnter IP addresses one per line. Leave blank and press Enter when done.")
        ips = []
        while True:
            ip = input("IP: ").strip()
            if not ip:  # Empty input signals the user is done
                break
            ips.append(ip)
        return ips

    elif choice == "2":
        # CSV entry: read every non-empty value from the first column of the file
        filename = input("\nCSV filename (include .csv extension): ").strip()

        # Make sure the file actually exists before trying to open it
        if not os.path.isfile(filename):
            print(f"Error: File '{filename}' not found.")
            return []

        ips = []
        with open(filename, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # row[0] is the first column; skip blank rows or empty first cells
                if row and row[0].strip():
                    ips.append(row[0].strip())

        print(f"Loaded {len(ips)} IP(s) from '{filename}'.")
        return ips

    else:
        print("Invalid choice.")
        return []


def query_switch(host, username, password):
    """
    Open an SSH connection to a single Cisco switch, run 'show version',
    close the connection, and return the command output as a string.
    """
    # This dictionary tells Netmiko everything it needs to connect to the device.
    # 'cisco_ios' is the device type — Netmiko uses this to handle IOS-specific
    # prompts and behavior automatically (e.g. pagination with --More--).
    device = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
        "timeout": 30,  # Seconds to wait before giving up on a connection
    }

    # ConnectHandler opens the SSH session
    conn = ConnectHandler(**device)

    # send_command sends 'show version' and waits for the prompt to return,
    # then gives us the full output as a string
    output = conn.send_command("show version")

    # Always disconnect cleanly to free up the SSH session on the switch
    conn.disconnect()

    return output


def main():
    """Main entry point: collect credentials and IPs, query each switch, write results to file."""

    # Step 1: Get login credentials from the user
    username, password = get_credentials()

    # Step 2: Get the list of switch IPs from the user
    ip_list = get_ip_list()

    # If the user provided no IPs (e.g. blank manual entry or bad CSV), exit early
    if not ip_list:
        print("No IPs provided. Exiting.")
        return

    # Step 3: Build a timestamped output filename so each run creates a new file
    # Example: show_version_20260714_113045.txt
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"show_version_{timestamp}.txt"

    print(f"\nConnecting to {len(ip_list)} switch(es)...\n")

    # Step 4: Open the output file and loop through every switch IP
    with open(output_file, "w") as f:
        for host in ip_list:
            print(f"  Querying {host}...", end=" ")

            # Write a header separator for this device in the output file
            f.write(f"{'=' * 60}\n")
            f.write(f"Host: {host}\n")
            f.write(f"{'=' * 60}\n")

            try:
                # Attempt to connect and run 'show version'
                result = query_switch(host, username, password)
                f.write(result + "\n\n")
                print("OK")

            except NetmikoAuthenticationException:
                # Wrong username or password for this device
                msg = "Authentication failed."
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")

            except NetmikoTimeoutException:
                # Device didn't respond — may be unreachable or SSH is disabled
                msg = "Connection timed out."
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")

            except Exception as e:
                # Catch-all for any other unexpected errors (e.g. DNS failure, refused connection)
                msg = str(e)
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")

    print(f"\nDone. Output saved to: {output_file}")


# This block ensures main() only runs when the script is executed directly,
# not if it were imported as a module by another Python file.
if __name__ == "__main__":
    main()
