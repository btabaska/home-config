#!/usr/bin/env python3
"""beszel-notify-coherent — fix-29 / L28 guard.

Beszel had an email destination configured while the hub has no SMTP_* env, so
email alerts failed silently — a channel that looks armed but delivers nothing.
This guards the class: a notification destination must have a working transport,
and at least one working channel (the ntfy webhook) must be present.

  FAIL if any user_settings record has a non-empty emails[] while SMTP is not
       configured on the container, or if no webhook channel exists at all.

Reads BESZEL_ADMIN_USER / BESZEL_ADMIN_PASSWORD from the verification env (vault
beszel.admin_user / beszel.admin_password), same as alert-beszel-none-down.

Prints  BESZEL_COHERENT_OK ...  or  BESZEL_COHERENT_FAIL/…  .
"""
import json
import os
import subprocess
import sys
import urllib.request

URL = os.environ.get("BESZEL_URL", "http://localhost:8090")
USER = os.environ.get("BESZEL_ADMIN_USER")
PW = os.environ.get("BESZEL_ADMIN_PASSWORD")
CONTAINER = os.environ.get("BESZEL_CONTAINER", "beszel")


def main():
    if not USER or not PW:
        print("BESZEL_COHERENT_NOCREDS (set BESZEL_ADMIN_USER/PASSWORD in "
              "/etc/verification/env)")
        return 1

    env = subprocess.run(
        ["docker", "inspect", CONTAINER,
         "--format", "{{range .Config.Env}}{{println .}}{{end}}"],
        capture_output=True, text=True,
    ).stdout
    smtp = any(line.upper().startswith("SMTP_") for line in env.splitlines())

    try:
        req = urllib.request.Request(
            f"{URL}/api/collections/_superusers/auth-with-password",
            data=json.dumps({"identity": USER, "password": PW}).encode(),
            headers={"Content-Type": "application/json"},
        )
        tok = json.loads(urllib.request.urlopen(req, timeout=8).read())["token"]
    except Exception as e:  # noqa: BLE001
        print(f"BESZEL_COHERENT_FAIL auth ({e})")
        return 1

    try:
        req = urllib.request.Request(
            f"{URL}/api/collections/user_settings/records",
            headers={"Authorization": tok},
        )
        items = json.loads(urllib.request.urlopen(req, timeout=8).read()).get("items", [])
    except Exception as e:  # noqa: BLE001
        print(f"BESZEL_COHERENT_FAIL fetch ({e})")
        return 1

    if not items:
        print("BESZEL_COHERENT_FAIL (no user_settings records)")
        return 1

    dead = []
    have_webhook = False
    for r in items:
        s = r.get("settings", {}) or {}
        if (s.get("emails") or []) and not smtp:
            dead.append(f"{r['id']}:dead-email")
        if s.get("webhooks"):
            have_webhook = True

    if dead:
        print("BESZEL_COHERENT_FAIL " + ",".join(dead) + " (email dest, no SMTP)")
        return 1
    if not have_webhook:
        print("BESZEL_COHERENT_FAIL (no working webhook channel configured)")
        return 1

    print(f"BESZEL_COHERENT_OK smtp={smtp} webhook=yes records={len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
