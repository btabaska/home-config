# Prompt — design & build the end-to-end acceptance-test framework

Paste this into a fresh session to execute tasks #5 (design), #6 (movie/TV journey), and set up #10 (done-audit). Read `foss-setup/docs/quality-hardening-state.md` and the memory files first.

---

You are continuing the **quality-hardening workstream** on the "Going Analogue" homelab. Context is in `foss-setup/docs/quality-hardening-state.md` — read it. The mandate: the tracker/monitoring says "green/100%" but real user-facing features have been broken in live use (Pinchflat→Plex, Libreseerr→CWA, MusicSeerr requests — all now fixed). The gap is that checks test **liveness** (container up, port 200, upstream reachable), never the **outcome** the user experiences. Your job is to formalize the fix into a real acceptance-test framework and extend coverage. Work repo-first; validate live; commit to `origin` + `publish-deploy.sh` to forgejo. Secrets are in `foss-setup/.handoff-secrets.yaml`. mini has passwordless sudo; NAS sudo needs the vault password; deploy to NAS via base64-over-ssh (scp/sftp is blocked). Verification checks live in `foss-setup/verification/checks.d/*.yaml` + primitives in `verification/bin/`, deploy to mini `/opt/verification/`, env in mini `/etc/verification/env`, run hourly, page via ntfy.

**The pattern already established (3 stacks) — treat it as the seed, not a blank page.** The existing `checks.d/media.yaml` checks (`pinchflat-plex-visible`, `plex-youtube-readable`, `readarr-cwa-copy-drops`, `cwa-ingest-not-stuck`, `musicseerr-phantom-requests`) all compare **producer output** (files on disk / requests made) to **consumer visibility** (items served in Plex/CWA/Navidrome), reading state directly (filesystem / app sqlite DB / downstream API) — not container liveness. Each is negative-tested. Reusable primitive: `verification/bin/plex-flat-library-coverage.py`.

**Deliverables:**

1. **Design doc** (`foss-setup/wiki/docs/runbooks/acceptance-testing.md` or `docs/acceptance-test-framework.md`): articulate the framework —
   - Principle: probe the *user-journey outcome*, not the boxes around it. "Did a requested album/book/video actually become watchable/readable?"
   - Two check shapes: **outcome/coverage** (producer count vs consumer count, e.g. disk vs Plex) and **handoff-integrity** (the fragile seam between two services, e.g. copy-script drops, ingest-stuck, phantom-monitored).
   - A **journey catalog**: for each user-facing pipeline (movie/TV, book, album, YouTube, photos/Immich, documents/Paperless, smart-home) — the producer, the consumer, the fragile seams, and which check(s) cover it (✅ / gap).
   - Conventions: severity (crit = user-visible data invisible/lost; warn = degraded/transient-tolerant), false-positive discipline (ignore legitimately-unavailable items — see the musicseerr monitored-but-no-release case), mandatory **negative test** before a check is considered done, how checks read state without app auth (direct DB/filesystem), and the "fail loudly on a down mount, never a vacuous pass" rule.
   - Keep it **right-sized for a home fleet** — extend the existing runner, don't build a heavyweight CI.

2. **#6 — movie/TV request → served in Plex acceptance check.** Journey: Seerr request → Sonarr/Radarr grab → import → item visible/playable in Plex. Note Plex movie/TV item counts ≠ file counts (a show = many episodes), so a raw disk-vs-Plex ratio is wrong here — use a journey/seam approach instead (e.g. Sonarr/Radarr "imported" history items appear in Plex within N hours; or a low-impact synthetic request that must reach a served state). Reuse the Sonarr/Radarr API keys already in `/etc/verification/env`. Validate live + negative-test. Add to `checks.d/media.yaml`, deploy, commit.

3. **#10 setup — done-audit harness.** Once the journey checks exist, spot-check the user-facing services whose "done" is only liveness-verified (the *seerr/*arr/media pipelines especially), and correct `foss-setup/docs/progress.json` where "done" ≠ "working". Establish the rule: future "done" requires an end-to-end pass.

**Method per check (non-negotiable):** diagnose the real journey → build the check reading real state → run it live (must pass) → **negative-test** it (must fail when the outcome is actually broken) → deploy to mini → commit to origin + publish-deploy to forgejo → update `docs/quality-hardening-state.md` + memory.

When done, report the journey catalog with coverage ✅/gaps so we can see exactly which user journeys are guarded and which still aren't.
