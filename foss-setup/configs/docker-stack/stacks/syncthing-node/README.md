# syncthing-node — mirror-naming exception (read before mirroring)

**The live dir is `/opt/stacks/syncthing` on the mini, but this repo mirror is
intentionally named `syncthing-node`. Do NOT create a `stacks/syncthing/` dir.**

Why the names differ:

- The bare name `syncthing` is already taken by the **NAS hub** mirror
  (`configs/nas/syncthing/`). `gen-wiki-services.py` keys one wiki service page
  per stack **dir name** and processes the mini tree first, so a second
  `syncthing` dir here would shadow the NAS hub's service page (only one would
  render).
- Naming this one `syncthing-node` keeps the two distinct: the mini **node**
  (`syncthing-node.md`) and the NAS **hub** (`syncthing.md`).

The anti-drift rule ("mirror changed files back to `stacks/<app>/`") therefore has
one documented exception for this stack: live `syncthing` ↔ repo `syncthing-node`.
`scripts/verification/stack-mirror-check.sh` encodes it as
`MIRROR_RENAME=( [syncthing]=syncthing-node )`, so the `stack-mirror-drift` check
byte-compares `/opt/stacks/syncthing/compose.yaml` against
`configs/docker-stack/stacks/syncthing-node/compose.yaml` (not a nonexistent
`stacks/syncthing/`). Keep the compose file **byte-identical** on both sides.
