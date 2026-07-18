# `fix-notify-channels.sh`

> fix-29 / L28 — keep Beszel's alert channels coherent.

**Path:** `foss-setup/scripts/beszel/fix-notify-channels.sh` · **Category:** [beszel](index.md) · **Type:** Bash

## What it does

```text
 fix-29 / L28 — keep Beszel's alert channels coherent.

 Beszel user_settings listed an email destination while the hub has NO SMTP_*
 env configured, so every email alert send fails silently — a dead notification
 path that reads as "I'll get emailed" but delivers nothing. The working channel
 is the ntfy webhook (and beszel-down is independently caught by the
 alert-beszel-none-down verification check). This script removes email
 destinations whenever SMTP is not configured, and leaves them untouched if it
 is — so re-enabling email later (add SMTP_* to the beszel env) just works.

 Idempotent. Run on the mini (where the beszel container + PocketBase live):
   BESZEL_ADMIN_USER=… BESZEL_ADMIN_PASSWORD=… bash fix-notify-channels.sh
 (creds: vault beszel.admin_user / beszel.admin_password — never hard-coded here)
```

## Environment / variables referenced

`BESZEL_ADMIN_PASSWORD`, `BESZEL_ADMIN_USER`, `BESZEL_CONTAINER`, `BESZEL_URL`, `CONTAINER`, `RECORDS`, `SMTP_CONFIGURED`, `TOK`

## See also

- [beszel scripts](index.md) · [All scripts](../index.md)
