Show Version Script
===================

OVERVIEW
--------
show_version.py connects to one or more Cisco switches via SSH, runs the
"show version" command on each one, and saves all of the output to a
timestamped text file (e.g. show_version_20260714_113045.txt).

After capturing the output, the script automatically parses the switch model
and IOS version, then cross-references them against a built-in Cisco TrustSec
compatibility table. A TrustSec compatibility summary is appended to each
switch's section in the output file.

This is useful for quickly auditing the IOS version and TrustSec readiness
across a fleet of switches without having to log into each one manually.


REQUIREMENTS
------------
Python 3.7 or higher is required.

It is strongly recommended to run this script inside a Python virtual
environment. A virtual environment is an isolated Python installation that
keeps the netmiko library (and its dependencies) separate from the rest of
your system. This avoids version conflicts with other Python projects and is
the most reliable way to get netmiko installed correctly on Windows.

Step 1 — Create the virtual environment (one time only):

    python -m venv netmiko_env

This creates a folder called "netmiko_env" in your current directory.

Step 2 — Activate the virtual environment:

    .\netmiko_env\Scripts\activate

Your terminal prompt will change to show "(netmiko_env)" when it is active.
You must activate the environment every time you open a new terminal window
before running the script.

Step 3 — Install netmiko into the virtual environment:

    pip install netmiko

This only needs to be done once after creating the environment.

To deactivate the virtual environment when you are done, run:

    deactivate


HOW TO RUN
----------
From a terminal, activate the virtual environment (Step 2 above), then
navigate to the Show-Version directory and run:

    python show_version.py

The script will walk you through the rest interactively.


WHAT THE SCRIPT ASKS FOR
------------------------
1. Username  - Your SSH username for the switches.
2. Password  - Your SSH password (hidden as you type).
3. IP source - Choose one of two options:

   Option 1 - Manual entry:
       Type each switch IP address one at a time and press Enter.
       When you are done, press Enter on a blank line.

   Option 2 - CSV file:
       Provide the name of a CSV file (including the .csv extension).
       The script reads IP addresses from the FIRST COLUMN of the file.
       The file can have a header row — any non-empty first-column value
       is treated as an IP, so make sure the first column contains only
       IP addresses (or a header you don't mind skipping if it fails
       to connect).

       Example CSV layout:
           ip_address,location,model
           192.168.1.1,Building A,C9300
           192.168.1.2,Building B,C9300


OUTPUT
------
Results are written to a text file in the same directory where the script
is run. The filename includes a timestamp so each run creates a new file
and previous results are never overwritten.

Each switch in the output file is separated by a header block, followed by
the raw 'show version' output and a TrustSec compatibility summary:

    ============================================================
    Host: 192.168.1.1
    ============================================================
    <show version output here>

    --- TrustSec Compatibility ---
      Detected Model   : C9300-24P
      Detected Version : 16.12.4
      TrustSec Support : Yes
      Notes            : Full TrustSec support: inline SGT tagging, SGACL enforcement, and SXP.

The console also prints a one-line TrustSec result per switch as it runs:

    Querying 192.168.1.1... OK  [TrustSec: Yes]
    Querying 192.168.1.2... OK  [TrustSec: Partial]

If a switch fails to connect, the error reason is recorded in the output
file instead of the command output, and the script moves on to the next
switch without stopping.


TRUSTSEC SUPPORT LEVELS
------------------------
The compatibility summary uses one of four values for "TrustSec Support":

  Yes     - Platform fully supports TrustSec: inline SGT tagging,
            Security Group ACL (SGACL) enforcement, and SXP.
  Partial - Platform supports SGT propagation via SXP only.
            No inline tagging or SGACL enforcement on this switch.
  Limited - 802.1X and MAB authentication supported, but no SGT
            tagging or SGACL features.
  No      - TrustSec is not supported on this platform.
  Unknown - Model was not recognized or not found in the local
            compatibility table. Manual verification required.

When a minimum IOS version is required, it is shown as "Minimum Version"
in the output. Compare this against "Detected Version" to confirm the
switch is running a supported release.

IMPORTANT: The compatibility table in this script covers common enterprise
platforms and is provided as a reference only. Always verify against the
official Cisco TrustSec Platform Support Matrix for your deployment:
  https://www.cisco.com/c/en/us/solutions/enterprise-networks/trustsec/trustsec-platform-support.html


ERROR HANDLING
--------------
- Authentication failed  : Wrong username or password for that device.
- Connection timed out   : Device is unreachable or SSH is not enabled.
- Any other error        : The error message is logged and the script continues.


NOTES
-----
- The script uses device type "cisco_ios". It is compatible with most
  Cisco IOS and IOS-XE switches (Catalyst 9000, 3850, 2960, etc.).
- The SSH timeout per device is set to 30 seconds.
- Credentials are the same for all switches in a single run. If your
  switches use different credentials, run the script separately for each
  group.
