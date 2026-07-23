# Operations — Secrets policy

One rule above all: **no secret value ever appears in a commit, a doc, a
handoff note, a chat transcript, or this wiki.** Vault keys (names) are fine;
values never. The 2026-07-07 audit found a live ntfy token committed in a
handoff doc — it had to be revoked and rotated. That failure mode is the
reason this page exists.

## The vault

- **File**: `foss-setup/.handoff-secrets.yaml` on the operator MacBook —
  **gitignored, chmod 600**. It is the single handoff point between the human
  and AI agents: the human puts credentials in; agents read them from there
  and nowhere else.
- It is intentionally **not backed up to any repo**. Long-term canonical
  storage of credentials is **Proton Pass** (plus a printed copy of the
  master/backup keys). The vault file is a working set, meant to be
  deletable: Plan v3's capstone (Run 7) ends with *delete the vault, rotate
  keys*.
- Referencing a secret in a doc: write the vault key, e.g.
  "token: see vault `ntfy.diun_token`" — never the value.

## Layers

| Layer | Mechanism |
|---|---|
| Human ↔ AI handoff | `.handoff-secrets.yaml` (above) |
| Runtime (containers) | `.env` per stack on the host — gitignored; repo carries `.env.example` with placeholders only |
| Repo-at-rest (ansible-consumed) | **SOPS + age** encrypted files (e.g. the restic env); roles gate on their presence |
| Long-term | Proton Pass (+ printed copy of age/restic/HA keys) |

`/etc` is in etckeeper and contains real secrets (`/etc/shadow`) — that
remote must stay private (Forgejo, LAN-only).

## Rotation log

Rotations are logged here and in the handoff state doc — **key names and
dates only**:

| Date | Credential (vault key) | Why |
|---|---|---|
| 2026-07-07 | `ntfy.diun_token` | Leaked in a committed handoff doc — revoked + rotated |
| 2026-07-07 | `wallabag.*` | Default admin replaced |
| 2026-07-17 | `backblaze_b2.application_key` | **Retired from the vault** (fix-22/H20: it holds `deleteFiles`+`bypassGovernance` — a vault compromise could hard-delete all B2 backups despite Object Lock). Value removed; keep it offline (Proton Pass/paper) or regenerate in the B2 console when needed for bucket admin (`scripts/backup/b2-apply-bucket-policy.py`). Day-to-day replaced by scoped read-only `backblaze_b2.ops_key_id`/`ops_key` |
| pending | `adguard_nas.admin_password` | Temp password set during API install; dns-02 closed so rotation is now unblocked — still to do |
| pending | `cloudflare.api_token` | Transcript exposure (2026-07-09 audit) |
| pending | `cubecoders_amp.admin_password` | Transcript exposure — and the deployed rig compose has it inline instead of `.env` (2026-07-09 audit; fix both together) |
| pending | `ntfy.phone_password` | Visible in `ps` output on the mini (2026-07-09 audit; move to netrc when rotating) |

When you rotate: update the vault + Proton Pass, update the consuming `.env`
on the host, restart the service, add a row here.

## Rules for AI agents

1. Read secrets only from the vault file; never ask for them in chat.
2. Never echo a secret into logs, command output you preserve, commits, or
   docs — redact before writing anything down.
3. If you find a secret anywhere in the repo or its history: treat it as
   burned — flag for revocation + rotation, don't just delete the text.
4. Generated-on-host secrets (e.g. a first-boot admin password) go **into the
   vault immediately**, not into a doc "temporarily".
