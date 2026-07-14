Show Version Script
===================

OVERVIEW
--------
show_version.py connects to one or more Cisco switches via SSH, runs the
"show version" command on each one, and saves all of the output to a
timestamped text file (e.g. show_version_20260714_113045.txt).

This is useful for quickly auditing the IOS version running across a fleet
of switches without having to log into each one manually.


REQUIREMENTS
------------
Python 3.7 or higher is required.

Install the netmiko library before running the script:

    pip install netmiko


HOW TO RUN
----------
From a terminal, navigate to the Show-Version directory and run:

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

Each switch in the output file is separated by a header block:

    ============================================================
    Host: 192.168.1.1
    ============================================================
    <show version output here>

If a switch fails to connect, the error reason is recorded in the output
file instead of the command output, and the script moves on to the next
switch without stopping.


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
