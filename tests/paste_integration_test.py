#!/usr/bin/env python3
"""Live Wayland paste regression test; requires the installed plugin and wtype.

Temporarily replaces the clipboard and opens/closes Find. Restores the previous
clipboard's preferred MIME representation without writing its contents to disk.
Run: python3 tests/paste_integration_test.py
"""
import json
import subprocess
import time

PLUGIN = "jesseburlamaque.omarchy-find"


def run(*args, **kwargs):
    if args[0] == "wl-copy":
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5, **kwargs)
        return b""
    return subprocess.run(args, check=True, capture_output=True, timeout=5, **kwargs).stdout


def state():
    return json.loads(run("omarchy-shell", "shell", "call", PLUGIN,
                          "debugState", "{}"))


def wait_query(expected):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if state()["filterText"] == expected:
            return
        time.sleep(0.05)
    # Never print clipboard contents on failure.
    raise AssertionError("Search query did not match the paste fixture")


def main():
    types = subprocess.run(["wl-paste", "--list-types"], capture_output=True)
    mime = types.stdout.decode().splitlines()[0] if types.returncode == 0 and types.stdout else None
    original = run("wl-paste", "--no-newline", "--type", mime) if mime else None
    cases = [
        ("", "paste-fixture", ["-M", "ctrl", "-k", "v", "-m", "ctrl"], "paste-fixture"),
        ("ai ", "two\nlines\t café", ["-M", "ctrl", "-M", "shift", "-k", "v", "-m", "shift", "-m", "ctrl"], "ai two lines  café"),
        ("go ", "<b>literal</b> $(not-a-command)", ["-M", "shift", "-k", "Insert", "-m", "shift"], "go <b>literal</b> $(not-a-command)"),
        ("keep", "", ["-M", "ctrl", "-k", "v", "-m", "ctrl"], "keep"),
    ]
    try:
        for prefix, clipboard, chord, expected in cases:
            run("wl-copy", "--type", "text/plain;charset=utf-8", input=clipboard.encode())
            run("omarchy-shell", "shell", "summon", PLUGIN, json.dumps({"query": prefix}))
            wait_query(prefix)
            time.sleep(0.2)  # Allow the compositor to map/focus the layer.
            run("wtype", *chord)
            wait_query(expected)
            run("omarchy-shell", "shell", "hide", PLUGIN)
        print(f"{len(cases)} live paste cases passed")
    finally:
        run("omarchy-shell", "shell", "hide", PLUGIN)
        if mime:
            run("wl-copy", "--type", mime, input=original)
        else:
            run("wl-copy", "--clear")


if __name__ == "__main__":
    main()
