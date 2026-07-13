# Handoff 02 — Home Assistant reliability (#11 backups, #12 Assist endpoint)

Prereqs: read `foss-setup/docs/quality-hardening-state.md` (esp. Operational cheatsheet) and memory [[ha-control-plane]]. HA is HAOS at `http://192.168.10.50:8123` (REST, token in vault `hosts.ha.api_token`; no ssh). Follow the loop: diagnose → fix → validate the real outcome → negative-tested regression check → commit origin + publish-deploy.

## #11 — Home Assistant backups (HIGH)
Current state (verified earlier): backups are effectively **absent** — only the local `hassio.local` eMMC agent, no schedule, no NAS/off-site agent, no encryption password; the only snapshot is `pre-homekit-bridge-claude` (id `bdcf6693`). A dead eMMC loses every automation.

Do:
1. Diagnose live via the Supervisor API (`/api/hassio/backups`, `/api/hassio/backups/info`) — confirm agents, schedule, encryption, existing backups.
2. Configure **scheduled automatic backups** (HAOS native automatic-backup, or a backup automation) with a retention policy.
3. Add an **off-site/NAS backup location** (Supervisor network-storage / Samba backup location pointing at a NAS share, or a cloud backup agent) so backups don't live only on the eMMC.
4. Set a **backup encryption password** and store it in **Vaultwarden** (`vault.tabaska.us`) + note it in the vault file — REQUIRED for restore. *(Storing the key is the one step that may need the user; if so, generate it, use it, and tell the user to save it.)*
5. Ideally add a git add-on / export for `/config` YAML.

Validate: trigger a backup, confirm it completes AND lands on the NAS share (check the file on `nas`), and that a restore path exists (don't do a destructive restore — verify the archive is readable/listable).

Harden: add a **dead-man check** — HA's newest backup is < 48h old and present off-eMMC. Put it in `checks.d/ha.yaml` (host mini, curl the Supervisor API with the HA token from `/etc/verification/env` `HA_TOKEN`; or check the backup file age on the NAS share). Negative-test it.

## #12 — HA-Assist LLM endpoint (mini:4000 → rig)
HA Assist points at the phantom `mini:4000` (never existed); should be the rig's `llm.tabaska.us`. In `scripts/docs/task-overrides.json` + `generate-task-overrides.py`. Fix, redeploy the override to HA, validate Assist actually reaches the rig endpoint (a test conversation / the conversation API returns a real completion). Note: the AI-stack SPOF itself is **accepted** by the user — this is only the endpoint correction, not a fallback deploy.

Done-criteria: HA has scheduled off-eMMC encrypted backups (key saved), a backup-age dead-man check deployed + negative-tested, and Assist hits the rig LLM. Commit; check item 02 off in HANDOFF-QUEUE.md; update the task board.
