#!/usr/bin/env python3
"""
Railway Logs Monitor - Real-time WebSocket Event Viewer

This script helps you monitor Railway logs in real-time while testing Exotel WebSocket.
It highlights important WebSocket events for easy debugging.

Usage:
    python monitor_logs.py

Note: You'll need to install Railway CLI first:
    npm install -g @railway/cli
    railway login
    railway link (select your project)
"""

import subprocess
import re
import sys
from datetime import datetime


# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def colorize_log(line):
    """Add colors to important log events"""

    # WebSocket events
    if "WebSocket CONNECTED" in line or "✅ TEST: WebSocket CONNECTED" in line:
        return f"{Colors.GREEN}{Colors.BOLD}{line}{Colors.RESET}"

    if "Media streaming STARTED" in line or "✅ TEST: Media streaming STARTED" in line:
        return f"{Colors.CYAN}{Colors.BOLD}{line}{Colors.RESET}"

    if "MEDIA event" in line:
        return f"{Colors.BLUE}{line}{Colors.RESET}"

    if "Call STOPPED" in line or "✅ TEST: Call STOPPED" in line:
        return f"{Colors.YELLOW}{Colors.BOLD}{line}{Colors.RESET}"

    if "Sent test audio" in line:
        return f"{Colors.MAGENTA}{line}{Colors.RESET}"

    # Errors
    if "ERROR" in line or "❌" in line or "Failed" in line:
        return f"{Colors.RED}{Colors.BOLD}{line}{Colors.RESET}"

    # Session info
    if "Call SID:" in line or "Session created:" in line:
        return f"{Colors.CYAN}{line}{Colors.RESET}"

    # Default
    return line


def main():
    """Monitor Railway logs with real-time filtering"""

    print(f"{Colors.BOLD}{Colors.GREEN}🚀 Railway Logs Monitor - WebSocket Event Viewer{Colors.RESET}")
    print(f"{Colors.CYAN}Monitoring Railway logs for Exotel WebSocket events...{Colors.RESET}")
    print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}\n")
    print("=" * 80)
    print()

    try:
        # Check if Railway CLI is installed
        result = subprocess.run(
            ["railway", "--version"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print(f"{Colors.RED}❌ Railway CLI not found!{Colors.RESET}")
            print(f"{Colors.YELLOW}Install it with: npm install -g @railway/cli{Colors.RESET}")
            print(f"{Colors.YELLOW}Then run: railway login && railway link{Colors.RESET}")
            sys.exit(1)

        # Start monitoring logs
        process = subprocess.Popen(
            ["railway", "logs", "--follow"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        print(f"{Colors.GREEN}✅ Connected to Railway logs{Colors.RESET}")
        print(f"{Colors.CYAN}📞 Now make a test call to: 01414939962{Colors.RESET}\n")
        print("=" * 80)
        print()

        # Read and colorize output line by line
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # Add timestamp
                timestamp = datetime.now().strftime("%H:%M:%S")
                colored_line = colorize_log(line)
                print(f"[{timestamp}] {colored_line}")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Monitoring stopped{Colors.RESET}")
        sys.exit(0)

    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
