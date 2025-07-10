#!/usr/bin/env python3
import time
import sys
import subprocess
import os
from evdev import InputDevice, list_devices, ecodes
import select
import threading

DEBUG = False

try:
    import dbus
    import dbus.mainloop.glib
    import dbus.lowlevel
    try:
        from gi.repository import GLib
    except ImportError:
        GLib = None
except ImportError:
    dbus = None
    GLib = None

active_inhibitors = set()
lock = threading.Lock()

def inhibitor_listener():
    print("[xss] inhibitor_listener thread started (dbus-monitor mode)")
    import subprocess as sp
    import re
    try:
        proc = sp.Popen(['dbus-monitor', '--session'], stdout=sp.PIPE, stderr=sp.DEVNULL, text=True, bufsize=1)
    except FileNotFoundError:
        print("[xss] ERROR: dbus-monitor not found. Inhibitor detection will not work.", file=sys.stderr)
        return
    inhibit_re = re.compile(r"member=Inhibit|member=AddInhibition", re.IGNORECASE)
    uninhibit_re = re.compile(r"member=(?!Inhibit$|AddInhibition$)[^ ]*inhibit[^ ]*", re.IGNORECASE)
    for line in proc.stdout:
        if 'inhibit' in line.lower():
            print(f"[xss] DEBUG: inhibit-related line: {line.strip()}")
        m_inh = inhibit_re.search(line)
        m_uninh = uninhibit_re.search(line)
        is_portal_signal = (
            'signal' in line and 'interface=org.freedesktop.portal.Inhibit' in line and (
                'member=Inhibit' in line or 'member=Uninhibit' in line)
        )
        if m_inh:
            if 'interface=org.freedesktop.portal.Inhibit' in line:
                key = ('portal', 'unknown')
                if DEBUG:
                    print(f"[xss] Inhibitor event detected (add): {line.strip()}")
                with lock:
                    active_inhibitors.add(key)
                    print(f"[xss] ADD: {key} -> {active_inhibitors}")
	# Really I should only care about portal inhibitors but there's never a fucking
	# deassert and afaic the spec doesn't even include one. Extremely stupid.
	# So I'm tracking KDE's random inhibitors which are set in response to the
	# portal inhibitor (which may in fact cause us spurious problems later).
	# It works well enough.
	# God damn I fucking hate this.
	# Wayland can suck the shit right out of my ass.
	# Yet another solution looking for a problem to solve.
            elif 'interface=org.kde.Solid.PowerManagement.PolicyAgent' in line:
                key = ('kde', 'unknown')
                if DEBUG:
                    print(f"[xss] Inhibitor event detected (add): {line.strip()}")
                with lock:
                    active_inhibitors.add(key)
                    print(f"[xss] ADD: {key} -> {active_inhibitors}")
            else:
                if DEBUG:
                    print(f"[xss] Ignored inhibitor event (add): {line.strip()}")
        elif m_uninh or is_portal_signal:
            if 'interface=org.freedesktop.portal.Inhibit' in line:
                key = ('portal', 'unknown')
                print(f"[xss] Portal uninhibit signal or removal detected: {line.strip()}")
                with lock:
                    active_inhibitors.discard(key)
                    print(f"[xss] REMOVE: {key} -> {active_inhibitors}")
            elif 'interface=org.kde.Solid.PowerManagement.PolicyAgent' in line:
                key = ('kde', 'unknown')
                if DEBUG:
                    print(f"[xss] Inhibitor event detected (remove): {line.strip()}")
                with lock:
                    active_inhibitors.discard(key)
                    print(f"[xss] REMOVE: {key} -> {active_inhibitors}")
                    # Workaround: also remove portal inhibitor if present
                    if ('portal', 'unknown') in active_inhibitors:
                        active_inhibitors.discard(('portal', 'unknown'))
                        print(f"[xss] WORKAROUND: Also removed ('portal', 'unknown') -> {active_inhibitors}")
            else:
                if DEBUG:
                    print(f"[xss] Ignored inhibitor event (remove): {line.strip()}")

def is_inhibited():
    with lock:
        if DEBUG:
            print(f"[xss] is_inhibited? {len(active_inhibitors)} inhibitors: {active_inhibitors}")
        return len(active_inhibitors) > 0

def activate_xscreensaver():
    print("[xss] Activating screensaver")
    subprocess.Popen(['xscreensaver-command', '-activate'])

def deactivate_xscreensaver():
    print("[xss] Deactivating screensaver")
    subprocess.Popen(['xscreensaver-command', '-deactivate'])

def main():
    try:
        if len(sys.argv) < 2:
            print(f"Usage: {sys.argv[0]} <idle_timeout_seconds>")
            sys.exit(1)
        idle_timeout = int(sys.argv[1])
        if idle_timeout < 1:
            idle_timeout = 1

        t = threading.Thread(target=inhibitor_listener, daemon=True)
        t.start()
        time.sleep(0.5)

        devices = [InputDevice(path) for path in list_devices()]
        if not devices:
            print("No input devices found or insufficient permissions.")
            sys.exit(1)
        print(f"[xss] Monitoring {len(devices)} input devices. Idle timeout: {idle_timeout} seconds")

        last_activity = time.time()
        screensaver_active = False
        last_inhibited = False
        inhibitor_blocked = False

        fds = [dev.fd for dev in devices]

        while True:
            try:
                r, _, _ = select.select(fds, [], [], 0.1)
                now = time.time()
                if r:
                    for dev in devices:
                        if dev.fd in r:
                            for event in dev.read():
                                if event.type in [ecodes.EV_KEY, ecodes.EV_REL, ecodes.EV_ABS, ecodes.EV_MSC]:
                                    last_activity = now
                                    if screensaver_active:
                                        deactivate_xscreensaver()
                                        screensaver_active = False
                                    inhibitor_blocked = False
                inhibited = is_inhibited()
                if not screensaver_active and (now - last_activity) >= idle_timeout:
                    if not inhibited:
                        activate_xscreensaver()
                        screensaver_active = True
                        last_inhibited = False
                        inhibitor_blocked = False
                    else:
                        if not last_inhibited:
                            print("[xss] Inhibitor(s) active, not activating screensaver.")
                        last_inhibited = True
                        inhibitor_blocked = True
                # If we are in inhibitor wait mode, check every iter if inhibitor has been deasserted
                if inhibitor_blocked and not inhibited:
                    print("[xss] Inhibitor(s) cleared, resetting idle countdown.")
                    last_activity = now
                    inhibitor_blocked = False
                    last_inhibited = False
                time.sleep(0.1)
            except Exception as e:
                print(f"[xss] Exception in main loop: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[xss] Fatal exception: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
