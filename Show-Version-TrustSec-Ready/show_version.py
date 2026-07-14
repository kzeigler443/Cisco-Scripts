# =============================================================================
# show_version.py
#
# PURPOSE:
#   SSH into one or more Cisco switches, run "show version" on each one,
#   and save the output to a timestamped text file. Each switch's result
#   also includes a TrustSec compatibility summary based on its model and
#   IOS version.
#
# USAGE:
#   1. Activate the virtual environment:  .\netmiko_env\Scripts\activate
#   2. Run the script:                    python show_version.py
#   3. Follow the on-screen prompts.
#
# OUTPUT:
#   A text file named show_version_YYYYMMDD_HHMMSS.txt is created in the
#   same folder the script is run from.
# =============================================================================

# --- Standard library imports ---
import csv       # For reading IP addresses from a CSV file
import getpass   # For securely prompting the user for a password (input is hidden)
import os        # For checking if a file exists on disk
import re        # For parsing model and version out of 'show version' output
from datetime import datetime  # For generating a timestamp on the output file

# --- Third-party library imports (requires: pip install netmiko) ---
from netmiko import ConnectHandler  # Main class for opening SSH connections to network devices
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
# NetmikoAuthenticationException: raised when the username/password is wrong
# NetmikoTimeoutException: raised when the device doesn't respond in time


# ---------------------------------------------------------------------------
# TrustSec Compatibility Reference Table
# ---------------------------------------------------------------------------
# Each entry is a tuple of (regex_pattern, compatibility_info_dict).
#
# HOW IT WORKS:
#   When we detect a switch model from 'show version', we walk this list
#   top-to-bottom and return the info dict for the FIRST pattern that matches.
#   Because of this, MORE SPECIFIC patterns must come BEFORE broader ones.
#   Example: "WS-C2960XR" must appear before "WS-C2960X", which must appear
#   before "WS-C2960" — otherwise a 2960XR would incorrectly match 2960.
#
# 'supported' values:
#   "Yes"     - Platform fully supports TrustSec (SGT tagging + SGACL enforcement)
#   "Partial" - Supports SXP-based SGT propagation only; no inline tagging
#   "Limited" - 802.1X/MAB auth only; no SGT or SGACL features
#   "No"      - TrustSec is not supported on this platform
#   "Unknown" - Model not found in this table; manual verification needed
#
# Source: Cisco TrustSec Platform Support Matrix
# NOTE: This table covers common enterprise access/distribution switches.
#       Always verify against Cisco's official documentation for your
#       specific deployment, as support can vary by software release.
# ---------------------------------------------------------------------------
TRUSTSEC_COMPAT = [

    # --- Catalyst 9000 Series ---
    # The 9200/9300/9400/9500 and 9600 all ship with full TrustSec out of the box.
    (r"C9[2345]\d{2}", {
        "supported": "Yes",
        "min_version": None,
        "notes": "Full TrustSec support: inline SGT tagging, SGACL enforcement, and SXP."
    }),
    (r"C96\d{2}", {
        "supported": "Yes",
        "min_version": None,
        "notes": "Full TrustSec support: inline SGT tagging, SGACL enforcement, and SXP."
    }),

    # --- Catalyst 3850 / 3650 ---
    # These platforms support full TrustSec but require a minimum IOS-XE version.
    (r"WS-C3850", {
        "supported": "Yes",
        "min_version": "3.6.0E",
        "notes": "Full TrustSec support. Requires IOS-XE 3.6.0E or later."
    }),
    (r"WS-C3650", {
        "supported": "Yes",
        "min_version": "3.6.0E",
        "notes": "Full TrustSec support. Requires IOS-XE 3.6.0E or later."
    }),

    # --- Catalyst 3750-X / 3560-X ---
    # The -X suffix models support full TrustSec; non-X models below are limited.
    # These entries must come before the broader WS-C3750 / WS-C3560 entries.
    (r"WS-C3750X", {
        "supported": "Yes",
        "min_version": "15.0(1)SE",
        "notes": "Full TrustSec support. Requires IOS 15.0(1)SE or later."
    }),
    (r"WS-C3560X", {
        "supported": "Yes",
        "min_version": "15.0(1)SE",
        "notes": "Full TrustSec support. Requires IOS 15.0(1)SE or later."
    }),

    # --- Catalyst 4500 ---
    # Supported, but depends on which supervisor engine is installed.
    (r"WS-C4[59]\d{2}", {
        "supported": "Yes",
        "min_version": None,
        "notes": "TrustSec supported with Supervisor 8-E or later. Verify supervisor model separately."
    }),

    # --- Catalyst 6500 / 6800 ---
    # Supported on specific supervisor + IOS combinations.
    (r"WS-C6[58]\d{2}", {
        "supported": "Yes",
        "min_version": "12.2(33)SXI",
        "notes": "TrustSec supported. Requires IOS 12.2(33)SXI+ and Supervisor 720 or VS-S720-10G or better."
    }),

    # --- Catalyst 2960-XR ---
    # Must appear BEFORE WS-C2960X so "XR" models don't get caught by the X pattern.
    (r"WS-C2960XR", {
        "supported": "Partial",
        "min_version": None,
        "notes": "SGT propagation via SXP only. No inline SGT tagging or SGACL enforcement."
    }),

    # --- Catalyst 2960-X ---
    # Must appear BEFORE the generic WS-C2960 entry below.
    (r"WS-C2960X", {
        "supported": "Partial",
        "min_version": None,
        "notes": "SGT propagation via SXP only. No inline SGT tagging or SGACL enforcement."
    }),

    # --- Catalyst 2960S ---
    # Must appear BEFORE the generic WS-C2960 entry below.
    (r"WS-C2960S", {
        "supported": "Limited",
        "min_version": None,
        "notes": "802.1X and MAB authentication only. No SGT tagging or SGACL enforcement."
    }),

    # --- Catalyst 2960 (non-X, non-S) / 2960-L / 2960-Plus ---
    # This broad pattern is intentionally last among 2960 variants.
    (r"WS-C2960", {
        "supported": "No",
        "min_version": None,
        "notes": "TrustSec is not supported on this platform."
    }),

    # --- Catalyst 3560 (non-X) ---
    # The -X variant is already handled above; this catches all other 3560 models.
    (r"WS-C3560", {
        "supported": "Limited",
        "min_version": None,
        "notes": "Limited TrustSec support. Verify your specific model and IOS version with the Cisco compatibility matrix."
    }),

    # --- Catalyst 3750 (non-X) ---
    # The -X variant is already handled above; this catches all other 3750 models.
    (r"WS-C3750", {
        "supported": "Limited",
        "min_version": None,
        "notes": "Limited TrustSec support. Verify your specific model and IOS version with the Cisco compatibility matrix."
    }),
]


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

    # ConnectHandler opens the SSH session.
    # The ** before 'device' is Python's dictionary unpacking syntax — it
    # passes each key/value pair in the dict as a separate named argument,
    # which is the same as writing:
    #   ConnectHandler(device_type="cisco_ios", host=host, username=..., ...)
    conn = ConnectHandler(**device)

    # send_command sends 'show version' and waits for the prompt to return,
    # then gives us the full output as a string
    output = conn.send_command("show version")

    # Always disconnect cleanly to free up the SSH session on the switch
    conn.disconnect()

    return output


def parse_show_version(output):
    """
    Extract the switch model and IOS version string from 'show version' output.
    Returns a tuple: (model, version) — either value may be None if not found.

    'show version' output format differs between IOS and IOS-XE, so we try
    multiple regex patterns to cover both styles.
    """
    model = None
    version = None

    # --- Model detection ---

    # Pattern 1 (IOS-XE / Catalyst 9000 style):
    #   "Model Number              : C9300-24P"
    #
    # Regex breakdown: r"[Mm]odel [Nn]umber\s*:\s*(\S+)"
    #   [Mm]odel [Nn]umber  — matches "Model Number" or "model number" (case-insensitive first letters)
    #   \s*                 — zero or more spaces/tabs
    #   :                   — literal colon
    #   \s*                 — zero or more spaces after the colon
    #   (\S+)               — capture one or more non-whitespace characters (the model number)
    #   .group(1)           — returns just the captured part inside the parentheses
    match = re.search(r"[Mm]odel [Nn]umber\s*:\s*(\S+)", output)
    if match:
        model = match.group(1)

    # Pattern 2 (classic IOS style):
    #   "cisco WS-C3850-24P (MIPS) processor with ..."
    #
    # Regex breakdown: r"^cisco\s+([\w-]+)\s*\("
    #   ^                   — start of a line (re.MULTILINE makes ^ work per-line)
    #   cisco               — literal word "cisco"
    #   \s+                 — one or more spaces
    #   ([\w-]+)            — capture one or more word characters or hyphens (the model number)
    #   \s*\(               — optional space then a literal opening parenthesis
    if not model:
        match = re.search(r"^cisco\s+([\w-]+)\s*\(", output, re.MULTILINE | re.IGNORECASE)
        if match:
            model = match.group(1)

    # --- Version detection ---

    # Handles both formats:
    #   "Version 16.12.4,"   (IOS-XE)
    #   "Version 15.2(7)E3," (classic IOS)
    #
    # Regex breakdown: r"[Vv]ersion\s+([\d\w\.\(\)]+)[,\s]"
    #   [Vv]ersion          — matches "Version" or "version"
    #   \s+                 — one or more spaces
    #   ([\d\w\.\(\)]+)     — capture digits, letters, dots, and parentheses (the version string)
    #   [,\s]               — the version string ends at a comma or whitespace
    match = re.search(r"[Vv]ersion\s+([\d\w\.\(\)]+)[,\s]", output)
    if match:
        version = match.group(1)

    return model, version


def check_trustsec_compat(model):
    """
    Look up TrustSec compatibility for a given switch model string.
    Returns a dict with 'supported', 'min_version', and 'notes' keys.
    """
    if not model:
        return {
            "supported": "Unknown",
            "min_version": None,
            "notes": "Could not parse model from 'show version' output. Manual verification required."
        }

    # Walk the compatibility table and return the first matching entry.
    # re.IGNORECASE means 'ws-c3850' matches the same as 'WS-C3850'.
    for pattern, compat_info in TRUSTSEC_COMPAT:
        if re.search(pattern, model, re.IGNORECASE):
            return compat_info

    # If we reach here, no pattern matched — model is not in our table
    return {
        "supported": "Unknown",
        "min_version": None,
        "notes": (
            f"Model '{model}' is not in the local compatibility table. "
            "Verify manually using the Cisco TrustSec Platform Support Matrix."
        )
    }


def format_trustsec_block(model, version, compat):
    """
    Build the TrustSec summary block that gets appended to each switch's
    section in the output file.
    """
    # Build each line of the summary as a separate string in a list,
    # then join them together at the end with newline characters between them.
    lines = [
        "",
        "--- TrustSec Compatibility ---",
        f"  Detected Model   : {model or 'Unknown'}",   # 'model or Unknown' prints "Unknown" if model is None
        f"  Detected Version : {version or 'Unknown'}",
        f"  TrustSec Support : {compat['supported']}",
    ]
    # Only show the minimum version line when the table specifies one
    if compat.get("min_version"):
        lines.append(f"  Minimum Version  : {compat['min_version']}")
    lines.append(f"  Notes            : {compat['notes']}")
    lines.append("")

    # "\n".join(lines) combines all strings in the list into one string,
    # placing a newline character between each item — like joining with glue.
    return "\n".join(lines)


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

            # try/except lets us attempt a risky operation (connecting to a switch)
            # and handle any failures gracefully instead of crashing the whole script.
            # Each 'except' block catches a specific type of error so we can give
            # a meaningful message rather than a generic Python traceback.
            try:
                # Attempt to connect and run 'show version'
                result = query_switch(host, username, password)
                f.write(result + "\n")

                # Parse the model and IOS version from the output, look up
                # TrustSec compatibility, and append the summary to the file
                model, version = parse_show_version(result)
                compat = check_trustsec_compat(model)
                f.write(format_trustsec_block(model, version, compat))
                f.write("\n")

                # Print a one-line summary to the console so the user can
                # see the TrustSec result without having to open the file
                print(f"OK  [TrustSec: {compat['supported']}]")

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
                # Catch-all for any other unexpected error (e.g. DNS failure, refused connection).
                # 'Exception as e' captures the error object so we can read its message with str(e).
                msg = str(e)
                f.write(f"ERROR: {msg}\n\n")
                print(f"FAILED ({msg})")

    print(f"\nDone. Output saved to: {output_file}")


# This block ensures main() only runs when the script is executed directly,
# not if it were imported as a module by another Python file.
if __name__ == "__main__":
    main()
