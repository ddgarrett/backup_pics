#!/usr/bin/env python3
"""
Placeholder for Pic Quality Review process.

Run by the menu GUI. Replace this script with the actual implementation
that rates the quality of backed-up photos.
"""
import signal
import sys
import time

_running = True


def _handle_stop(signum, frame):
    global _running
    _running = False


def main():
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    print("Pic Quality Review running. (Placeholder - replace with real implementation.)")
    while _running:
        time.sleep(1)
    print("Pic Quality Review stopped.")
    sys.exit(0)


if __name__ == "__main__":
    main()
