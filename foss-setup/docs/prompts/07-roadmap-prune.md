# Handoff 07 — Walk & prune the unbuilt roadmap (#17) · NEEDS-USER (collaborative)

**This item is not autonomous — it requires the user's decisions.** The master loop should PAUSE here and surface it, not execute it alone.

Read `foss-setup-plan-2.md` (the master design narrative) and `foss-setup/docs/quality-hardening-state.md`. The plan doc still describes items that may or may not still be intended — some are already abandoned (Dependency-Track, SBOM, Tdarr, Maintainerr), some never built (Frigate, Zigbee backbone + HACS, MFA/2FA-everywhere, Tier-2/immutable + external-HDD backups, Borg/Hetzner second off-site, room-level presence, Nextcloud, etc.).

Prepare (autonomous part): for each unbuilt/ambiguous track, a one-line status — is it live, never-deployed, retired, or genuinely-planned — grounded in the live fleet and the tracker. Present as a decision list.

Then (with the user): walk the list, decide keep / prune / defer for each, and align `foss-setup/docs/progress.json` + the wiki so the tracker reflects real intent. Do NOT unilaterally retire or commit to building anything — these are the user's calls (like the earlier dtrack/Tdarr retirements).

Done-criteria: user has decided each open track; progress.json + docs updated to match; a clean picture of what remains. Commit the reconciliation; check item 07 off; update the task board.
