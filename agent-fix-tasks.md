# Agent Fix Tasks — Homelab Repo Audit Remediation

Source: 5-agent audit of this repo on 2026-07-06. Repo root: `/Users/brandontabaska/Documents/Home/foss-setup/` (paths below are relative to it unless they start with `/`).

**Rules for the executing agent:**
- Each task touches only the file(s) it names. Do exactly what the task says — no refactors beyond the stated change.
- These are repo edits only. Never run commands against live hosts, containers, or the network.
- Line numbers are approximate ("near line N") — locate by the quoted text, not the number.
- After each task, run the Verify step. If the quoted text can't be found, stop and report — do not guess.

---

## Group A — Ansible (`configs/ansible/`)

### A-01: Fix sbom role env file path
**File:** `configs/ansible/roles/sbom/tasks/main.yml` (near line 39)
**Problem:** Role writes credentials to `/etc/sbom-nightly.env`, but `scripts/inventory/sbom-nightly.service` reads `EnvironmentFile=/etc/inventory/sbom.env`.
**Change:** (1) Add a task before the copy: `ansible.builtin.file: path=/etc/inventory state=directory mode=0700`. (2) Change the copy destination from `/etc/sbom-nightly.env` to `/etc/inventory/sbom.env`. (3) Ensure the file's variable names match `scripts/inventory/sbom.env.example` (`DTRACK_URL`, `DTRACK_API_KEY`, `SYFT_VERSION`, `GRYPE_VERSION`).
**Verify:** `grep -n 'sbom.env' configs/ansible/roles/sbom/tasks/main.yml` shows `/etc/inventory/sbom.env`; no reference to `/etc/sbom-nightly.env` remains in the repo.

### A-02: Deploy sbom-nightly.sh in the sbom role
**File:** `configs/ansible/roles/sbom/tasks/main.yml` (near lines 27–35)
**Problem:** Role installs `sbom-nightly.service`/`.timer` but never copies the script the unit executes (`ExecStart=/opt/scripts/inventory/sbom-nightly.sh`).
**Change:** Add a copy task before the unit-install tasks: src `{{ playbook_dir }}/../../scripts/inventory/sbom-nightly.sh`, dest `/opt/scripts/inventory/sbom-nightly.sh`, mode `0755`, owner root. Add a `file: state=directory` task for `/opt/scripts/inventory` first.
**Verify:** The role now has tasks creating `/opt/scripts/inventory` and copying `sbom-nightly.sh` before the systemd unit tasks.

### A-03: Create /etc/restic before copying into it
**File:** `configs/ansible/roles/backup/tasks/main.yml` (near lines 20–24)
**Problem:** `copy` to `/etc/restic/backup.env` fails on a fresh host because the directory is never created.
**Change:** Add before the copy: `ansible.builtin.file: path=/etc/restic state=directory mode=0700 owner=root`.
**Verify:** A directory task for `/etc/restic` appears before the `backup.env` copy task.

### A-04: Fix base role pkglist lookup path
**File:** `configs/ansible/roles/base/tasks/main.yml` (near lines 61 and 68)
**Problem:** `lookup('file', 'hosts/<host>/pkglist…')` resolves against the role/playbook dir, not the repo root where `export-manifests.sh` writes `hosts/<hostname>/`.
**Change:** Prefix both lookup paths with `{{ playbook_dir }}/../../` so they resolve to the repo-root `hosts/{{ inventory_hostname }}/...`. Mirror the pattern already used in `configs/ansible/roles/sbom/tasks/main.yml` (near lines 23–29).
**Verify:** Both lookups reference `{{ playbook_dir }}/../../hosts/`.

### A-05: Fix sops_age_keyfile to the admin user's home
**File:** `configs/ansible/group_vars/all.yml` (near line 17)
**Problem:** `{{ ansible_env.HOME }}` resolves to `/root` under the play's `become: true`, but the age key lives in the admin user's home.
**Change:** Set `sops_age_keyfile: "/home/{{ admin_user }}/.config/sops/age/keys.txt"`.
**Verify:** The value no longer references `ansible_env.HOME`.

### A-06: Backup role must install the repo's restic units, not an inline divergent unit
**File:** `configs/ansible/roles/backup/tasks/main.yml` (near lines 26–38)
**Problem:** The role writes an inline `restic-backup.service` that backs up fewer paths (`/home /opt/stacks /var/lib/docker/volumes`) and reads `/etc/restic/backup.env`, while the curated units in `scripts/backup/restic-backup.{service,timer}` run `/opt/scripts/restic-backup.sh` with `EnvironmentFile=/etc/restic/b2.env` and cover `/home /etc /opt /var/lib/docker/volumes /srv`.
**Change:** Replace the inline unit content with copy tasks that install `scripts/backup/restic-backup.service`, `scripts/backup/restic-backup.timer`, and `scripts/backup/restic-backup.sh` (script → `/opt/scripts/restic-backup.sh` mode 0755) from the repo, following the same copy pattern the sbom role uses. Keep the existing env-file task but write it to `/etc/restic/b2.env` to match the unit.
**Verify:** No inline `[Unit]`/`[Service]` heredoc remains in the backup role; the three repo files are copied; env dest matches the `EnvironmentFile=` line in `scripts/backup/restic-backup.service`.

### A-07: Install chezmoi via pinned .deb on apt hosts
**File:** `configs/ansible/roles/state/tasks/main.yml` (near lines 6–13), `configs/ansible/group_vars/all.yml`
**Problem:** `chezmoi` is not in Ubuntu/Debian apt archives; the apt task fails on the mini and aborts the play. (Keep the pacman task — Arch does package it.)
**Change:** Replace the apt-install-chezmoi task with a pinned .deb install, modeled on how this repo pins syft/grype:
1. Add to `group_vars/all.yml`: `chezmoi_version: "2.63.1"` and `chezmoi_deb_sha256: ""` (leave the checksum blank with a comment `# fill from the release's checksums.txt before first run`).
2. In the state role (apt branch only): `ansible.builtin.get_url` from `https://github.com/twpayne/chezmoi/releases/download/v{{ chezmoi_version }}/chezmoi_{{ chezmoi_version }}_linux_amd64.deb` to `/tmp/chezmoi.deb`, with `checksum: "sha256:{{ chezmoi_deb_sha256 }}"` applied `when: chezmoi_deb_sha256 | length > 0`; then `ansible.builtin.apt: deb=/tmp/chezmoi.deb`. Guard both with `when: ansible_facts.os_family == 'Debian'` and skip when `chezmoi` is already installed at the pinned version (register `chezmoi --version` output, `changed_when: false`, `failed_when: false`).
**Verify:** `ansible-playbook --syntax-check site.yml` from `configs/ansible/` passes; no plain `apt: name=chezmoi` task remains.

### A-08: Stop leaking secrets into logs
**Files:** `configs/ansible/roles/tailscale/tasks/main.yml` (near lines 45–48), `configs/ansible/roles/backup/tasks/main.yml` (near line 20), `configs/ansible/roles/sbom/tasks/main.yml` (near line 37)
**Change:** (1) In the tailscale role, pass the authkey via environment instead of argv: use `environment: TS_AUTHKEY: "{{ ... }}"` on the task and change the command to `tailscale up --auth-key env:TS_AUTHKEY ...` (or `--authkey=$TS_AUTHKEY` via shell). Add `no_log: true`. (2) Add `no_log: true` and `diff: false` to the secret-bearing copy tasks in the backup and sbom roles.
**Verify:** `grep -rn 'no_log' configs/ansible/roles/{tailscale,backup,sbom}/tasks/main.yml` shows all three; the authkey no longer appears in the command string.

### A-09: Don't swallow tailscale up failures
**File:** `configs/ansible/roles/tailscale/tasks/main.yml` (near lines 49–51)
**Change:** Remove `failed_when: false`. Change `changed_when` to `changed_when: ts_up.rc == 0`.
**Verify:** The task fails when `tailscale up` fails.

### A-10: Reinstall syft/grype when the pinned version changes
**File:** `configs/ansible/roles/sbom/tasks/main.yml` (near lines 12 and 20)
**Problem:** `creates: /usr/local/bin/syft` means bumping `syft_version`/`grype_version` never reinstalls, and `sbom-nightly.sh`'s `check_pin` then fails nightly.
**Change:** For each of syft and grype: add a `command: /usr/local/bin/syft version` (resp. grype) task with `register`, `changed_when: false`, `failed_when: false`; then run the installer `when:` the binary is missing or the registered stdout does not contain the pinned version string. Remove the `creates:` arg.
**Verify:** Installer tasks have a `when:` referencing the registered version output; no `creates:` remains on them.

### A-11: Wake-gate the sbom timer on the rig
**File:** `configs/ansible/roles/sbom/tasks/main.yml` (near lines 27–35)
**Problem:** The fixed `OnCalendar=03:30` timer is copied verbatim to the wake-gated rig, which is asleep at 03:30.
**Change:** Template the timer install the same way `configs/ansible/roles/backup/tasks/main.yml` (near lines 40–58) does: when `wake_gated | default(false)` is true, install a variant using `OnBootSec=` + `Persistent=true` instead of the fixed `OnCalendar`.
**Verify:** The role branches on `wake_gated` exactly like the backup role.

### A-12: Create audit output dir in audit playbook
**File:** `configs/ansible/playbooks/audit.yml` (near lines 33–36)
**Change:** Before the first localhost `copy` to `./audit/...`, add a task: `ansible.builtin.file: path=./audit state=directory` with `delegate_to: localhost`, `run_once: true`, `become: false`.
**Verify:** Directory-creation task precedes both copy tasks (near lines 33–36 and 58–61).

### A-13: Fix chezmoi creates guard and unmask failures
**File:** `configs/ansible/roles/state/tasks/main.yml` (near lines 28–34)
**Change:** Change `creates:` to `/home/{{ admin_user }}/.local/share/chezmoi/.git`. Remove `failed_when: false`.
**Verify:** No `ansible_env.HOME` in the `creates:` path; no `failed_when: false` on the task.

### A-14: Make ansible-pull actually converge (check-mode opt-in)
**Files:** `configs/ansible/ansible-pull.service` (near line 31)
**Problem:** `--check` is hardwired, so the pull layer is a permanent dry-run.
**Change:** Remove `--check` from `ExecStart`. Add `Environment=ANSIBLE_PULL_EXTRA_ARGS=` and append `$ANSIBLE_PULL_EXTRA_ARGS` to the command so a host can opt back into `--check` via a drop-in. Update the unit's comment block to describe this.
**Verify:** `--check` appears only in a comment; `$ANSIBLE_PULL_EXTRA_ARGS` is in `ExecStart`.

### A-15: Guard daemon-dependent tasks for fresh boxes
**File:** `configs/ansible/roles/docker/tasks/main.yml` (near lines 93–96)
**Change:** On the `community.docker.docker_network` task, ensure the docker service task runs before it and add `when: not ansible_check_mode` so a check-mode run on a fresh box (no daemon) doesn't fail.
**Verify:** The docker_network task carries the `when:` guard.

### A-16: Fix ansible-pull install-target comments
**Files:** `configs/ansible/ansible-pull.service` (near line 5), `configs/ansible/ansible-pull.timer` (near lines 3–4)
**Change:** Comments say to install on the seedbox; the seedbox is deliberately outside `[fleet]` and has no root. Change the comments to say "Install on: Mac mini, rig (NOT the seedbox — it is outside [fleet] by design)".
**Verify:** No comment tells the reader to install on the seedbox.

### A-17: Derive tailscale apt repo from facts
**File:** `configs/ansible/roles/tailscale/tasks/main.yml` (near lines 11 and 16)
**Change:** Replace hardcoded `ubuntu`/`noble` in the apt key and repo URLs with `{{ ansible_distribution | lower }}` and `{{ ansible_distribution_release }}`, matching the pattern in `configs/ansible/roles/docker/tasks/main.yml` (near lines 31, 41–42).
**Verify:** No literal `noble` remains in the tailscale role.

### A-18: Pin collection versions exactly
**File:** `configs/ansible/requirements.yml` (near lines 9–17)
**Change:** Replace every `>=X.Y.Z` version floor with the exact `version: "X.Y.Z"` currently listed (drop the `>=`). Keep the header comment; it claims pins, so make it true.
**Verify:** No `>=` remains in the file.

### A-19: Remove no-op SuccessExitStatus and add failure notification
**File:** `configs/ansible/ansible-pull.service` (near line 35)
**Change:** Delete the `SuccessExitStatus=0` line and its comment. Add `OnFailure=ntfy-notify@%n.service` under `[Unit]` with a comment noting it requires the ntfy notify template unit used elsewhere in this repo (see `scripts/nas/nas-docker-health.sh` ntfy pattern); if no such template unit exists in the repo, add the `OnFailure=` line commented out with a TODO instead.
**Verify:** `SuccessExitStatus` is gone.

### A-20: Add per-role tags in site.yml
**File:** `configs/ansible/site.yml` (near lines 27–35)
**Change:** Add `tags: [<rolename>]` to each role entry (base, docker, tailscale, backup, sbom, state — match the actual role list).
**Verify:** `ansible-playbook --syntax-check site.yml` passes; every role entry has a tag.

---

## Group B — Docker stacks / Caddy / Homepage (`configs/docker-stack/`, `configs/nas/`, `configs/git/`)

### B-01: Bind Frigate's unauthenticated API to localhost
**File:** `configs/docker-stack/stacks/frigate/compose.yaml` (near lines 44–45)
**Change:** Change the port mapping `"5000:5000"` to `"127.0.0.1:5000:5000"`. Add a comment: `# unauthenticated internal API — never expose beyond localhost; UI/auth is on 8971`. Do NOT touch `privileged: true` (separate human task — hardware-specific).
**Verify:** Port 5000 mapping is loopback-bound.

### B-02: Add NAS overlay for Frigate and Tdarr (external edge network doesn't exist on NAS)
**Files:** create `configs/docker-stack/stacks/frigate/compose.nas.yaml` and `configs/docker-stack/stacks/tdarr/compose.nas.yaml`
**Change:** Copy the overlay pattern from `configs/docker-stack/stacks/dependency-track/compose.nas.yaml`: redefine the `edge` network as `external: false` so `docker compose -f compose.yaml -f compose.nas.yaml up` works on the NAS. Add one comment line at the top of each base `compose.yaml`: `# On the NAS, layer compose.nas.yaml (the external edge network only exists on the mini).`
**Verify:** Both new files exist and match the dependency-track overlay structure.

### B-03: Fix Dependency-Track frontend API default and publish the apiserver port
**File:** `configs/docker-stack/stacks/dependency-track/compose.yaml` (near lines 58–62)
**Change:** (1) Change `API_BASE_URL=${DTRACK_API_BASE_URL:-http://localhost:9010}` default to `http://localhost:9011`. (2) Add a host port mapping `“9011:8080”` to the **apiserver** service (the Caddyfile routes `deptrack.<domain>/api/*` to `{$NAS_IP}:9011`). (3) On the frontend's `depends_on: apiserver`, use `condition: service_healthy` (apiserver has a healthcheck).
**Verify:** apiserver publishes 9011; frontend default points at 9011; depends_on uses service_healthy.

### B-04: Fail fast on blank Caddy upstream IPs
**Files:** `configs/docker-stack/stacks/caddy/compose.yaml` (near lines 37–39), `configs/docker-stack/stacks/caddy/.env.example` (near lines 17, 21, 25)
**Change:** (1) In compose.yaml change `${NAS_IP:-}`, `${SEEDBOX_IP:-}`, `${HOST_IP:-}` to required form: `${NAS_IP:?set in .env}` etc. (2) In `.env.example`, set `NAS_IP=192.168.10.4`, `HOST_IP=192.168.10.2`, and leave `SEEDBOX_IP=` blank but add comment `# Tailscale IP of the seedbox — required; compose will refuse to start while unset`.
**Verify:** No `:-}` defaults remain for the three vars; example file carries the real LAN IPs for NAS/HOST.

### B-05: Fix stale Caddy build rationale comment
**File:** `configs/docker-stack/stacks/caddy/compose.yaml` (near lines 10–14 and 21–24)
**Change:** The comments claim the Caddyfile uses `import cloudflare_tls` so the custom `build: .` is mandatory — but the working-tree Caddyfile has that snippet commented out and every site imports `local_tls`. Rewrite the comments to: the custom build is only needed if/when `cloudflare_tls` is re-enabled; the stock `caddy:2.11.4-alpine` image works with the current Caddyfile. Do not change the build itself.
**Verify:** Comment no longer asserts the Cloudflare module is currently required.

### B-06: Regenerate README pinned-versions table
**File:** `configs/docker-stack/README.md` (near lines 63, 65, 76, 80, 83)
**Change:** Fix five stale rows to match the compose files: Miniflux `2.3.1`; Navidrome `0.62.0`; Pinchflat `v2025.9.26`; Dependency-Track apiserver `5.0.2` / frontend `5.0.1`; Maintainerr `ghcr.io/maintainerr/maintainerr:3.15.3`. Cross-check each value against the actual `image:` line in the corresponding `stacks/*/compose.yaml` before writing.
**Verify:** Every version in the table matches its compose `image:` tag exactly.

### B-07: Default Healthchecks ALLOWED_HOSTS to real hosts
**File:** `configs/docker-stack/stacks/healthchecks/compose.yaml` (near line 32)
**Change:** Change the `ALLOWED_HOSTS` default from `*` to `${HC_ALLOWED_HOSTS:-health.tabaska.us,localhost}`.
**Verify:** No bare `*` default remains.

### B-08: Close the AdGuard-NAS setup-wizard port after setup + fix admin-port trap
**Files:** `configs/docker-stack/stacks/adguard-nas/compose.yaml` (near lines 19–21), `configs/docker-stack/stacks/adguard-nas/README.md`
**Change:** (1) In compose, add `"8080:80/tcp"` with comment `# post-wizard admin UI (AdGuard moves admin to :80 in-container after first run)`. (2) Change `"3000:3000"` mapping comment to instruct removing or loopback-binding it after the wizard completes, and add that instruction to the README as an explicit post-setup step.
**Verify:** Port 80 is reachable via a published mapping; README documents closing 3000.

### B-09: De-duplicate hardcoded IPs in homepage services.yaml
**File:** `configs/docker-stack/stacks/homepage/config/services.yaml` (near lines 139, 144, and all `192.168.10.4` occurrences)
**Change:** Replace the literal seedbox Tailscale IP `100.119.134.94` with `{{HOMEPAGE_VAR_SEEDBOX_IP}}` and every literal `192.168.10.4` with `{{HOMEPAGE_VAR_NAS_IP}}`. Add `HOMEPAGE_VAR_SEEDBOX_IP=` and `HOMEPAGE_VAR_NAS_IP=192.168.10.4` to the homepage stack's `.env.example`, and pass them through in `stacks/homepage/compose.yaml` `environment:` if HOMEPAGE_VAR_* vars are passed explicitly there (match how existing `HOMEPAGE_VAR_*` keys are wired).
**Verify:** `grep -c '192.168.10.4' services.yaml` returns 0; the two new vars exist in `.env.example`.

### B-10: Add missing Homepage tiles (Tdarr, Frigate, LiteLLM)
**File:** `configs/docker-stack/stacks/homepage/config/services.yaml`
**Change:** Add three tiles in the style of existing entries: Tdarr (`href: https://tdarr.tabaska.us`, ping `http://{{HOMEPAGE_VAR_NAS_IP}}:8265`), Frigate (`href: https://frigate.tabaska.us`, ping `http://{{HOMEPAGE_VAR_NAS_IP}}:8971`), LiteLLM (`href: https://llm.tabaska.us`, ping `http://litellm:4000`). Place Tdarr/Frigate near the other NAS media/monitoring tiles and LiteLLM near the utility tiles.
**Verify:** All three hostnames from the Caddyfile now have a tile.

### B-11: Fix Forgejo port comment in homepage compose
**File:** `configs/docker-stack/stacks/homepage/compose.yaml` (near line 10)
**Change:** Comment says "avoid clashing with Forgejo (3000)" — Forgejo publishes host `3030:3000`. Change to "(3030)".
**Verify:** Comment matches `configs/git/docker-compose.yml` (near line 52).

### B-12: Add healthchecks to AdGuard (mini) and Navidrome
**Files:** `configs/docker-stack/stacks/adguard/compose.yaml`, `configs/docker-stack/stacks/navidrome/compose.yaml`
**Change:** Add compose healthchecks following the style used by other stacks in this repo: Navidrome: `test: ["CMD", "wget", "-q", "--spider", "http://localhost:4533/ping"]`. AdGuard: `test: ["CMD", "nslookup", "adguard-health-probe.local.test", "127.0.0.1"]` — if `nslookup` isn't in the image, use `wget -q --spider http://127.0.0.1:80/` against the admin UI instead. interval 60s, timeout 10s, retries 3.
**Verify:** Both services have a `healthcheck:` block; YAML parses (`docker compose config` or a YAML linter).

### B-13: Add memory limits to heavy services
**Files:** `configs/docker-stack/stacks/frigate/compose.yaml`, `configs/docker-stack/stacks/tdarr/compose.yaml`, `configs/nas/immich/docker-compose.yml` (immich-machine-learning service), and the paperless webserver service in its compose file
**Change:** Add `mem_limit:` following the existing pattern in `stacks/dependency-track/compose.yaml`: frigate `2g`, tdarr `2g`, immich-machine-learning `4g`, paperless webserver `2g`. Add a one-line comment on each: `# cap so an OCR/ML/transcode burst can't OOM neighbors`.
**Verify:** Each named service has `mem_limit`.

### B-14: Use service_healthy in immich depends_on
**File:** `configs/nas/immich/docker-compose.yml` (near lines 37–39)
**Change:** Change immich-server's `depends_on` on redis and database from list form to mapping form with `condition: service_healthy` (both have healthchecks).
**Verify:** `depends_on` uses conditions; YAML parses.

### B-15: Add Stash healthcheck
**File:** `configs/nas/stash/docker-compose.yml`
**Change:** Add `healthcheck: test: ["CMD", "wget", "-q", "--spider", "http://localhost:9999/healthz"]`, interval 60s, timeout 10s, retries 3. Do NOT change the user/root setup (separate human task — needs the NAS media UID:GID).
**Verify:** Healthcheck block present; YAML parses.

### B-16: Blank the PUID/PGID trap in media-automation .env.example
**File:** `configs/nas/media-automation/.env.example` (near lines 11–12)
**Change:** Change `PUID=1000` / `PGID=1000` to `PUID=` / `PGID=` and add comment: `# REQUIRED — run 'id <user>' on the NAS (DSM users are typically 1026/100); compose refuses to start while blank, by design.`
**Verify:** No `1000` values remain; the compose `${PUID:?...}` guard will now fire on a verbatim copy.

---

## Group C — Network docs + verify script (`configs/network/`, `scripts/network/`)

### C-01: Document DNS pinhole rules required for failover
**Files:** `configs/network/dns-resilience-plan.md` (dns-03 section, near lines 68–72), `configs/network/firewall-policy-order.md`
**Change:** (1) In firewall-policy-order.md, add three new numbered policies immediately ABOVE the Block IoT→Trusted / Block Work→Trusted / Block Guest→Trusted rules (#15/#18/#19): "Allow <zone> → Trusted, Destination IP 192.168.10.2 and 192.168.10.4, TCP/UDP 53" for IoT, Work, and Hotspot. Note they must sit above the corresponding blocks. (2) In dns-resilience-plan.md dns-03, add a prerequisite line referencing those pinhole rules by their new numbers. Do not renumber existing rules; use suffixes (e.g. 14c/14d/14e) to avoid churn.
**Verify:** Both docs cross-reference the same pinhole rule identifiers.

### C-02: Make dns-05 depend on the pinholes and exclude resolvers from the NAT redirect
**File:** `configs/network/dns-resilience-plan.md` (dns-05 section, near line 96)
**Change:** Add: (a) prerequisite: the C-01 pinhole rules must exist first, otherwise redirected IoT/Work/Guest DNS hits the zone blocks and all DNS on those VLANs dies; (b) the redirect must exclude source IPs 192.168.10.2 and 192.168.10.4 to avoid redirect loops.
**Verify:** dns-05 lists both caveats.

### C-03: Fix Guest-VLAN DNS reachability note
**File:** `configs/network/dns-resilience-plan.md` (dns-03 section, near line 68)
**Change:** Note that the Guest network uses the Hotspot type whose client isolation blocks RFC1918 destinations regardless of ZBF policy, so Guest cannot reach 192.168.10.2/.4. Amend dns-03: for Guest, either keep DNS = gateway (192.168.50.1) only, or add 192.168.10.2/.4 to the Hotspot pre-authorization/allowed-subnet exception list. Mark the choice as a pending human decision.
**Verify:** dns-03 no longer silently includes Guest in the AdGuard-first DNS list.

### C-04: Fix zbf-isolation-verify.sh defaults and doc ping targets
**Files:** `scripts/network/zbf-isolation-verify.sh` (near lines 21–22), `configs/network/firewall-policy-walkthrough.md` (near lines 213, 229), `configs/network/firewall-policy-checklist.md` (near lines 607, 613)
**Change:** (1) Script: change default `TRUSTED_IP=192.168.10.1` to `192.168.10.2` and default `IOT_IP=192.168.20.1` to a placeholder real-host variable with a comment `# must be a client IP, never a gateway .1 interface (gateway is its own zone)`. (2) Docs: change the `ping 192.168.10.1` isolation-test examples to `ping 192.168.10.2`.
**Verify:** No isolation test in the script defaults or those doc lines targets a `.1` gateway IP.

### C-05: Fix macOS ping timeout units in zbf-isolation-verify.sh
**File:** `scripts/network/zbf-isolation-verify.sh` (near lines 32, 37)
**Change:** `ping -W` is seconds on Linux but milliseconds on macOS. Branch on `uname -s`: on Darwin use `-W $((PING_TIMEOUT * 1000))` (or `-t "$PING_TIMEOUT"`); on Linux keep `-W "$PING_TIMEOUT"`.
**Verify:** `bash -n scripts/network/zbf-isolation-verify.sh` passes; Darwin branch multiplies by 1000.

### C-06: State one firewall baseline model in all three policy docs
**Files:** `configs/network/firewall-policy-order.md` (near line 67), `configs/network/firewall-policy-checklist.md` (near lines 78–80), `configs/network/vlan-zone-firewall-plan.md`
**Change:** firewall-policy-order.md claims "implicit default-deny"; the checklist says UniFi's built-in Allow All Traffic stays below your rules. The checklist is correct for UniFi ZBF. Rewrite the order doc's wording to: "UniFi ZBF default is allow (built-in Allow All Traffic rule below yours); every zone-matrix Block cell therefore needs an explicit block policy — nothing is denied implicitly." Add the same one-line note to the matrix section of vlan-zone-firewall-plan.md.
**Verify:** No doc claims implicit default-deny.

### C-07: Add the missing Trusted→Work and Trusted→Hotspot blocks to the policy doc
**File:** `configs/network/firewall-policy-order.md` (Phase C section)
**Change:** The zone matrix (vlan-zone-firewall-plan.md near line 56) marks Trusted→Work and Trusted→Hotspot as Block, but no policy implements them. Add two policies to Phase C: "Block Trusted → Work (any/any)" and "Block Trusted → Hotspot (any/any)", with a note that under the Allow-All default these flows are currently open.
**Verify:** Every B cell in the matrix now has a corresponding block policy in the order doc (or an explicit "accepted-open" annotation).

### C-08: Document a gateway-management break-glass rule
**Files:** `configs/network/firewall-policy-order.md`, `configs/network/ssh-maintenance-access.md`
**Change:** Add a policy to the order doc: "Allow Trusted → Gateway TCP 443, source limited to admin device IPs (the MacBooks' fixed IPs)" with rationale: the Internal/mgmt zone has no clients, so without this rule no client can reach the UniFi admin UI once tightening lands. Add a paragraph to ssh-maintenance-access.md covering gateway console access (this rule + one wired mgmt-VLAN port as physical break-glass).
**Verify:** Both docs mention gateway admin access explicitly.

### C-09: Extend camera→gateway policy for UniFi Protect ports
**Files:** `configs/network/firewall-policy-order.md` (rule #7, near line 44), `configs/network/firewall-policy-checklist.md` (near line 264)
**Change:** Rule #7 (Cameras→Gateway) allows only UDP 67/123, but Protect adoption/streaming needs TCP 443/7442/7447/7550 to the console on the Dream Wall. Extend rule #7's port list to `UDP 67/123 + TCP 443/7442/7447/7550` in both docs, with comment `# UniFi Protect adoption/management/streaming`.
**Verify:** Both docs list the Protect TCP ports on rule #7.

### C-10: Make rule #6 (IoT→Gateway DNS) TCP+UDP
**Files:** `configs/network/firewall-policy-order.md` (near line 43), `configs/network/firewall-policy-checklist.md` (near line 238)
**Change:** Rule #6 is UDP-only; truncated/DNSSEC responses retry over TCP 53. Change to `TCP/UDP 53 + UDP 67/123`, matching rule #5's pattern.
**Verify:** Rule #6 lists TCP/UDP 53 in both docs.

### C-11: Add LAN-IP fallback aliases to ssh-config.example
**File:** `configs/network/ssh-config.example` (near lines 20–44)
**Change:** The break-glass config uses only `*.ts.net` MagicDNS names, which fail exactly when tailscaled is down. Add LAN aliases: `Host nas-lan` → `HostName 192.168.10.4`, `Host mini-lan` → `HostName 192.168.10.2`, `Host rig-lan` → `HostName 192.168.10.12` (reuse the User/IdentityFile settings from the corresponding ts.net entries). Add comment `# LAN fallbacks for when Tailscale control plane / tailscaled is down`.
**Verify:** Three `-lan` Host blocks exist with RFC1918 HostNames.

### C-12: Fix small network-doc inconsistencies (batch)
**Files:** `configs/network/vlan-zone-firewall-plan.md`, `configs/network/firewall-policy-walkthrough.md`, `configs/network/firewall-policy-order.md`, `configs/network/dns-resilience-plan.md`, `configs/network/ssh-maintenance-access.md`, `configs/network/firewall-policy-checklist.md`
**Change (six independent one-liners):**
1. vlan-zone-firewall-plan.md near line 3: "Target: 5 networks" → "Target: 6 networks (Cameras optional)" (its own table lists 6).
2. vlan-zone-firewall-plan.md near line 28 vs walkthrough near lines 27–34: align zone count — state there are six predefined zones (incl. VPN, DMZ) and that the walkthrough table shows only the four relevant ones.
3. firewall-policy-order.md near lines 65–66: reword the 14b ordering note to "ZBF ordering only matters within a source→destination zone pair; keep 14b below #6 among IoT→Gateway policies."
4. dns-resilience-plan.md near lines 20–23: add one sentence: clients (macOS/iOS/Android) rotate/race DNS servers, so listing the gateway as tertiary means occasional filter bypass — accepted fail-open tradeoff until dns-05.
5. firewall-policy-checklist.md near line 264: add note that Protect-adopted cameras sync time from the console, so gateway NTP isn't needed once C-09's ports are open.
6. ssh-maintenance-access.md near lines 92–100: add note that WoL requires the rig to be on wired Ethernet; device-onboarding-and-migration.md lists the gaming PCs as Wi-Fi — magic packets won't wake a Wi-Fi NIC. Cross-fix the connectivity column in device-onboarding-and-migration.md near line 48 if the rig is actually wired.
**Verify:** All six edits applied; no other content changed.

### C-13: Document per-VLAN DHCP pool boundaries
**File:** `configs/network/vlan-zone-firewall-plan.md`
**Change:** Add a short subsection: per-VLAN convention `.2–.99` reserved for static/fixed assignments (mini .2, NAS .4, rig .12, HA .13 already fall in range), `.100–.254` DHCP pool. Mark as "recommended — set pools in UniFi to match" (human applies in UI).
**Verify:** Subsection exists and lists the four known static IPs.

### C-14: Add DNS fallbacks to homepage container
**File:** `configs/docker-stack/stacks/homepage/compose.yaml` (near line 32)
**Change:** The `dns:` list pins only `192.168.10.2`, contradicting the fail-open design. Add `192.168.10.4` and `192.168.10.1` as second/third entries.
**Verify:** Three DNS entries in fail-open order.

---

## Group D — Scripts & backup (`scripts/`)

### D-01: Make immich-pg-dump atomic and verified
**File:** `scripts/nas/immich-pg-dump.sh` (near line 12)
**Change:** Dump to `${OUT}.tmp`, then `gzip -t "${OUT}.tmp"`, then `mv "${OUT}.tmp" "${OUT}"`. Before dumping, check the container is running: `docker inspect -f '{{.State.Running}}' immich_postgres` (use the actual container name already referenced in the script) and exit non-zero with a message if not. On any failure, remove the `.tmp` file.
**Verify:** `bash -n` passes; no code path writes a partial file to the final name.

### D-02: Add flock to rclone mount script and watchdog
**Files:** `scripts/media/rclone-seedbox-mount.sh`, `scripts/media/rclone-seedbox-watchdog.sh`
**Change:** At the top of each script's main body add the lock pattern already used in `scripts/media/seedbox-sync.sh` (near line 127): `exec 9>/var/run/seedbox-mount.lock; flock -n 9 || exit 0` — both scripts must use the SAME lock file so they exclude each other.
**Verify:** Both scripts open FD 9 on `/var/run/seedbox-mount.lock`.

### D-03: Remove the watchdog's duplicate container restart
**File:** `scripts/media/rclone-seedbox-watchdog.sh` (near lines 90–95, 104, 144)
**Change:** The watchdog's copy of `restart_download_containers` duplicates the one inside rclone-seedbox-mount.sh, which the mount script already calls — so every watchdog remount restarts sonarr/radarr/lidarr/readarr/unpackerr twice. Delete the watchdog's function and its call sites; the mount script's restart is the single source.
**Verify:** `grep -c restart_download_containers scripts/media/rclone-seedbox-watchdog.sh` returns 0.

### D-04: Alert when the watchdog's remount fails
**File:** `scripts/media/rclone-seedbox-watchdog.sh` (near lines 104, 144)
**Change:** `"$MOUNT_SCRIPT" ... || true` hides permanent mount death. Replace `|| true` with a failure branch that sends an ntfy alert using the same pattern as `scripts/nas/nas-docker-health.sh` (near line 114), then exits non-zero.
**Verify:** A failed remount reaches an ntfy call.

### D-05: Fix zero-count bug in gen-inventory-md.sh
**File:** `scripts/inventory/gen-inventory-md.sh` (near line 33)
**Change:** `grep -cvE ... || printf '0'` emits `0` twice when the file has zero matching lines (grep prints 0 AND exits 1), corrupting counts and aborting under `set -e` at the arithmetic on line 68. Replace with: `c=$(grep -cvE '^\s*(#|$)' "$f" 2>/dev/null) || true; printf '%s' "${c:-0}"`.
**Verify:** `f=$(mktemp); source-free test: running the count function on an empty file prints exactly '0'`.

### D-06: Bound the monthly restore test
**File:** `scripts/backup/restore-test.sh` (near lines 64, 76)
**Change:** (1) Change `restic restore latest --target "$RESTORE_DIR"` to add `--include /etc` so it restores a bounded subset instead of the full 1–2 TB snapshot (disk-fill + full B2 egress). (2) Raise `MIN_FILES` from 1 to 10. (3) Near line 76, remove the `2>/dev/null` on the borgmatic list call and restructure so the command's failure produces its own stderr before the "no archives found" message (e.g. capture with `|| true` and test output afterwards).
**Verify:** `bash -n` passes; restore command carries `--include`; no `2>/dev/null` on the borgmatic call.

### D-07: Fix apostrophe-breaking trim in readarr ingest hook
**File:** `scripts/media/readarr-copy-to-cwa-ingest.sh` (near line 28)
**Change:** Replace the `xargs` trim (breaks on apostrophes in book paths, leaving `BOOK_PATH` empty) with pure-bash trimming:
```bash
BOOK_PATH="${BOOK_PATH#"${BOOK_PATH%%[![:space:]]*}"}"
BOOK_PATH="${BOOK_PATH%"${BOOK_PATH##*[![:space:]]}"}"
```
**Verify:** `bash -n` passes; feeding a var containing `Ender's Game.epub` through the trim preserves it.

### D-08: Scope restic log exclude and add flock
**File:** `scripts/backup/restic-backup.sh` (near lines 27, 83, 93)
**Change:** (1) Replace `--exclude '*.log'` with `--exclude '/var/log'` and `--exclude '/home/*/.cache'` (the glob was excluding app data inside docker volumes — Tier 1 data). (2) At the top of the script add `exec 9>/var/run/restic-backup.lock; flock -n 9 || { echo "another run holds the lock"; exit 0; }`.
**Verify:** No bare `*.log` exclude; lock precedes the backup call.

### D-09: Fix gpu-power-tune systemd ordering cycle
**Files:** `scripts/gaming/gpu-power-tune.service` (near lines 13, 24), embedded copy in `scripts/gaming/gpu-power-tune.sh` (near line 110)
**Change:** Remove `After=multi-user.target` (a unit `WantedBy=multi-user.target` cannot also be After= it without creating a cycle). Keep/add `After=nvidia-persistenced.service`. Apply identically to the heredoc copy inside the .sh.
**Verify:** Neither file contains `After=multi-user.target`.

### D-10: Compute HEALTH_CMD_B64 at runtime
**File:** `scripts/nas/install-nas-docker-health-task.sh` (near lines 8, 32, 46)
**Change:** Replace the hardcoded base64 blob with `HEALTH_CMD_B64="$(printf '%s' "bash ${HEALTH_SCRIPT}" | base64)"` computed after `HEALTH_SCRIPT` is defined, so the synocrond `cmd=` can never drift from the visible strings.
**Verify:** No literal base64 constant remains; `bash -n` passes.

### D-11: Fix misleading LockPersonality comment
**File:** `scripts/backup/borgmatic.service` (near line 31)
**Change:** The comment claims LockPersonality prevents timer pile-up; it's a seccomp hardening option with zero concurrency effect (systemd already serializes per-unit starts). Move the option under a `# hardening` comment and delete the concurrency claim.
**Verify:** No comment ties LockPersonality to concurrency.

### D-12: Align borg append-only claim between doc and config
**File:** `configs/nas/backup-architecture.md` (near line 33)
**Change:** Mapping row #5 claims "append-only repo", but `scripts/backup/borgmatic-config.yaml` states the repo is NOT append-only (client prunes; server-side enforcement is only a comment). Change the row to "append-only NOT yet enforced — requires Hetzner server-side `borg serve --append-only` forced command (TODO, human task)".
**Verify:** Doc and config agree.

### D-13: Fix small script nits (batch)
**Files & one-line changes:**
1. `scripts/setup/nut-client-ubuntu.sh` (near lines 37, 55): change example `NAS_IP=192.168.1.7` to `192.168.10.4` (matches every other config).
2. `scripts/inventory/gen-inventory-md.sh` (near line 90) and `configs/inventory/inventory.md` (near line 3): change "nightly/weekly" claim to "weekly (Mon 04:00) by export-manifests.timer" (only sbom is nightly).
3. `scripts/media/install-slskd-native.sh` (near lines 91–95): move `loginctl enable-linger` BEFORE the `systemctl --user daemon-reload`/`enable --now` calls, and remove the `2>/dev/null || true` on the enable so failures surface.
4. `scripts/setup/cachyos-desktop-baseline.sh` (near line 135): change `pacman -Sy` + later installs to `pacman -Syu --needed` (partial-upgrade footgun); also fix the header comment "LibreOffice 25.8 still branch" to match the `libreoffice-fresh` default near line 34.
**Verify:** All four applied; `bash -n` passes on each script.

---

## Group E — HTML guide (`foss-setup/docs/index.html`) and plan docs

The guide is one HTML file with an embedded JSON task list ("taskData") near line 1426. Edit strings in place; do not reformat the JSON. After every Group E task, verify the JSON still parses: `python3 -c "import json,re,sys; html=open('foss-setup/docs/index.html').read(); # extract and parse the taskData array"` — simpler: run `python3 - <<'EOF'` extracting the array between the known markers and `json.loads` it; if you cannot extract it reliably, at minimum verify the file's quote/brace balance around your edit is unchanged.

### E-01: Fix Wallabag port 8200 → 8085 everywhere
**File:** `foss-setup/docs/index.html` (taskData entries `read-07` and `read-08`)
**Change:** In read-07 steps/commands and read-08 steps/pitfalls, replace every `:8200` with `:8085` (the compose maps 8085:80; the guide's own pitfall text says 8200 was a typo). Do not change the pitfall sentence that explains the typo history.
**Verify:** `grep -c '8200' foss-setup/docs/index.html` returns only the occurrences inside the explanatory pitfall text (or 0 if none).

### E-02: Add edge-network mitigation to NAS deploy tasks
**File:** `foss-setup/docs/index.html` (taskData entries `ha-15`, `sbom-01`, `media-04`)
**Change:** Each deploys a stack (frigate, dependency-track, tdarr) to the NAS, where the external `edge` network doesn't exist. Add to each task's steps: "On the NAS, layer the overlay: `docker compose -f compose.yaml -f compose.nas.yaml up -d` (the external edge network only exists on the mini)." Match the wording doc-01 already uses for this problem.
**Verify:** All three task entries mention compose.nas.yaml or the edge-network removal.

### E-03: Standardize Tailscale hostnames (macmini / cachyos)
**File:** `foss-setup/docs/index.html` (static-IP table near lines 632–633; taskData `seed-03`, `game-07`)
**Change:** MagicDNS knows the names set by net-07/net-11: `macmini` and `cachyos`. (1) In the Network-tab static-IP table change Tailscale names "mac-mini" → "macmini" and "rig" → "cachyos". (2) In seed-03 change `PEERS="mac-mini nas"` to `PEERS="macmini nas"`. (3) In game-07 change `tailscale ping rig --until-direct` to `tailscale ping cachyos --until-direct`.
**Verify:** `grep -c 'mac-mini' foss-setup/docs/index.html` returns 0.

### E-04: Fix net-05 isolation-test example IP
**File:** `foss-setup/docs/index.html` (taskData `net-05`)
**Change:** Change `TRUSTED_IP=192.168.10.1` to `TRUSTED_IP=192.168.10.2` in the verify command (`.1` is the gateway — its own zone — so the test result is meaningless).
**Verify:** net-05's command uses `192.168.10.2`.

### E-05: Fix ha-09 / ha-17 circular dependency
**File:** `foss-setup/docs/index.html` (taskData `ha-17`)
**Change:** ha-17 (LiteLLM) declares `depends_on: ["ha-09", "docker-02"]` while ha-09 (voice) says "point conversation agent to LiteLLM (ha-17)". Change ha-17's depends_on to `["docker-02"]` and add "ha-17" to ha-09's depends_on list.
**Verify:** ha-17 no longer depends on ha-09; ha-09 depends on ha-17; the JSON parses.

### E-06: Fix game-05 Sunshine autostart unit name
**File:** `foss-setup/docs/index.html` (taskData `game-05`)
**Change:** Steps install Sunshine via the LizardByte pacman repo but then enable the Flatpak-style unit `app-dev.lizardbyte.app.Sunshine`. Change the enable command to `systemctl --user enable --now sunshine` (the pacman package ships `sunshine.service`).
**Verify:** No Flatpak-ID-style unit name remains in game-05.

### E-07: Fix ha-04 no-op verify
**File:** `foss-setup/docs/index.html` (taskData `ha-04`)
**Change:** The verify `curl -sf http://homeassistant:8123/api/ || true` always succeeds. Replace with: `test "$(curl -s -o /dev/null -w '%{http_code}' http://homeassistant:8123/api/)" = "401"` (unauthenticated /api/ returns 401 when HA is up).
**Verify:** No `|| true` in ha-04's verify command.

### E-08: Fix sbom-02 scp permission failure
**File:** `foss-setup/docs/index.html` (taskData `sbom-02`)
**Change:** `scp .../sbom-nightly.sh mini:/opt/scripts/` fails because `/opt/scripts` is root-owned 0700. Change to the pattern used elsewhere in the guide: scp to `/tmp/`, then `ssh mini sudo install -m 0755 /tmp/sbom-nightly.sh /opt/scripts/inventory/sbom-nightly.sh`.
**Verify:** sbom-02 no longer scps directly into /opt.

### E-09: Fix game-02 Pelican bootstrap URL
**File:** `foss-setup/docs/index.html` (taskData `game-02`, and `game-03` context)
**Change:** The command fetches `docker-compose.yml` from Pelican's GitHub release assets, which don't ship one. Replace the curl with: "Follow the Docker install in Pelican's docs (https://pelican.dev/docs) — copy the documented compose file into /opt/stacks/pelican/ on the rig." Also prefix game-02/game-03 command blocks with `ssh rig` context like every other CachyOS task (use the standardized hostname `cachyos` per E-03).
**Verify:** No `releases/latest/download/docker-compose.yml` URL remains.

### E-10: Fix guide status/wording drift (batch)
**File:** `foss-setup/docs/index.html`
**Changes:**
1. Near line 371: reword "finish nas-01 (snapshots) and glue-01 (UPS) first — they gate Immich, Paperless…" to "nas-01 gates them; glue-01 protects them (UPS — protects data, gates nothing in the dependency graph)".
2. Near lines 371/383/1365 + taskData `nas-08`: Immich is already deployed (2026-07-02) while nas-01 is undone. Reword the nas-01 gate as "must precede production reliance, not deployment" and mark Immich's snapshot/backup exposure as an open risk.
3. Costs tab near line 504: change B2 status "bucket created, Object Lock on" to match `docs/handoff-rollout-state.md` ("user skip until B2 ready — bucket NOT yet created; nas-02..07 and sec-03 chain off handoff-05").
4. Near line 510: "new lifetime → $749.99 on Jul 1 2026" → "since Jul 1 2026".
5. Near line 722: change seedbox "Deluge-only P2P" to "Deluge + slskd", and add an "slskd (native binary)" chip to the Hardware-tab software list near lines 1176–1179.
6. taskData `nas-09`: change prerequisite text "nas-02, nas-00c complete" to "nas-00c, nas-prep-01 complete" (matching its actual depends_on and the B2 skip).
7. Port map near lines 644–693: add a row for Libreseerr (mini, host 8789 per handoff-rollout-state.md); annotate Forgejo's row as host 3030 → container 3000.
**Verify:** All seven applied; taskData JSON still parses.

### E-11: Fix doc-01's contradictory gates
**File:** `foss-setup/docs/index.html` (taskData `doc-01`, wscard near line 381)
**Change:** The wscard says Paperless is gated on nas-01; doc-01's step says the gate is the NAS RAM ≥20GB upgrade. Make both say: "Gates: NAS RAM ≥20GB AND nas-01 (snapshots)". Do NOT change the host field — Paperless placement is a pending human decision (see Blocked section).
**Verify:** Both locations state the same two gates.

### E-12: Update stale plan-2 table and inventory comment
**Files:** `/Users/brandontabaska/Documents/Home/foss-setup-plan-2.md` (near lines 27, 242–243), `configs/ansible/inventory.ini`
**Change:** (1) The "what runs where" table near line 27 still assigns qBittorrent + *arrs + sync agent to the seedbox — superseded by the ARCHITECTURE UPDATE box (near lines 162–235: Deluge+slskd on Betty, *arrs on NAS, rclone mount). Update the table rows to match the update box and add "(see ARCHITECTURE UPDATE)" notes at the old pipeline description near lines 242–243. (2) In inventory.ini, fix the seedbox description "rootless Docker… seedbox-sync" to "native slskd binary + Deluge (no Docker — host forbids it); outside [fleet] by design".
**Verify:** No table row in plan-2 assigns the *arrs to the seedbox.

---

## Blocked — do NOT start until a human decision (listed for tracking only)

| ID | Decision needed | Then unblocks |
|----|----|----|
| H-01 | **Paperless host: mini or NAS?** (plan-2 forbids mini; handoff + working tree put it on mini) | Edits to guide port map/swlist/doc-01, README.md:46-50, Caddyfile, homepage ping |
| H-02 | **MeTube: deploy it or drop it?** (routed + tiled, no compose anywhere) | Either new `stacks/metube/compose.yaml` or removal of Caddyfile:261-264 + services.yaml tile |
| H-03 | **Guest VLAN DNS approach** (gateway-only vs hotspot exception list) | Final dns-03 wording beyond C-03's caveat |
| H-04 | **Libreseerr pinned tag + CWA image digest** (needs live-host/registry lookup) | Pin edits in `stacks/libreseerr/compose.yaml:9` and `configs/nas/calibre-web-automated/docker-compose.yml:19` |
| H-05 | **NAS media UID:GID** (run `id` on DSM) | Stash `user:` de-rooting |
| H-06 | **Frigate hardware passthrough** (Coral/iGPU device paths) | Replacing `privileged: true` with explicit `devices:` |
| H-07 | **Tdarr node placement** (compose says NAS but `nodeName=macmini-internal`) | Fixing the nodeName + Caddy target coherently |
