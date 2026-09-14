# rig gaming — Battle.net via Steam + ProtonGE-WC3, and giving the GPU back to AI

**Doc-only, manually deployed** (like the rest of `configs/host/rig/`) — installed 2026-09-14.
Repo copies here are the source of truth for the script + launchers; the Steam VDF wiring is a
one-shot (`steam-shortcuts-setup.py`) with dated `.bak-*` files next to the originals.

## Why this exists

2026-09-14 incident: an idle Battle.net launcher held **421 MiB** of VRAM and that alone killed
the `q38` lane (sized to the edge of the 24 GB card; it died 308 MiB short allocating its MTP
draft context: `cudaMalloc failed: out of memory`), which took down every agentic AI client
(opencode / Hermes / OWUI ops). Gaming and the top AI lane do not coexist — hence the explicit
"Game Over" hand-back step. Operator decision 2026-09-14: keep `q38` at max ctx / hard-fail
(no headroom trim, no `-ngl` auto-fit fallback).

## Pieces

| file | live location (rig) | purpose |
|---|---|---|
| `game-over.sh` | `~/.local/bin/game-over.sh` | Kill all Proton/game processes (identified by `STEAM_COMPAT_DATA_PATH` in `/proc/<pid>/environ`, plus Battle.net/Agent/wineserver belt-and-braces), then verify **no game/wine processes remain on the GPU**. AI processes (llama-server, ComfyUI) are never touched or counted as failures. |
| `game-over.desktop` | `~/Desktop/` + `~/.local/share/applications/` | Terminal launcher for the above. |
| `battlenet.desktop`, `warcraft3-reforged.desktop`, `wow.desktop` | `~/Desktop/` + `~/.local/share/applications/` | `steam steam://rungameid/<id>` launchers (ids below). Icons extracted from the game exes with `wrestool`/`magick` into `~/.local/share/icons/hicolor/256x256/apps/`. |
| `steam-shortcuts-setup.py` | run once from `/tmp` (Steam shut down) | Rewrote `shortcuts.vdf` + `config.vdf` CompatToolMapping. Uses the system `python-vdf`. |

## The Proton build

**GE-Proton11-WC3-CertFix** — full GE-Proton 11 fork (Statharas/proton-ge-wc3) whose only
functional change is a backport of 4 upstream Wine crypt32 commits (88-byte
`CERT_CHAIN_ENGINE_CONFIG`), fixing Warcraft III Reforged's login/cert failure. Fine for WoW and
other Battle.net titles. Downloaded from the Hive Workshop thread
<https://www.hiveworkshop.com/threads/protonge-wc3.374113/> (outer zip → inner
`GE-Proton11-WC3-CertFix.tar.gz`, SHA256SUMS verified), extracted to
`~/.local/share/Steam/compatibilitytools.d/GE-Proton11-WC3-CertFix/`. Requires Steam Linux
Runtime 4 (already installed). **Obsolescence note:** the Wine fix is upstream, so official
GE-Proton releases newer than GE-Proton 11 should eventually replace this build.

## Steam wiring (userdata 34948152)

One shared prefix — `steamapps/compatdata/2951284266` (39G; Battle.net + full WC3 Reforged +
WoW classic-era bits; **retail WoW installs from the Battle.net UI**). All three shortcuts run
`Battle.net Launcher.exe` from that prefix and map to `GE-Proton11-WC3-CertFix`:

| shortcut | appid | rungameid | LaunchOptions |
|---|---|---|---|
| Battle.net | 2951284266 | 12675669403702919168 | *(none — its appid owns the prefix)* |
| Warcraft III: Reforged | 2371484709 | 10185449268152631296 | `STEAM_COMPAT_DATA_PATH=…/compatdata/2951284266 %command% --exec="launch W3"` |
| World of Warcraft | 3238950932 | 13911188326322274304 | same + `--exec="launch WoW"` |

`--exec="launch <code>"` are Battle.net product codes (Lutris convention; classic-era would be
`WoWC`). Four stale shortcuts pointing at the long-gone prefix `3083077599` were dropped;
`compatdata/2412228651` (379M vanilla prefix from one of them) was left on disk.

## Gotchas learned

- `pkill -f 'Battle.net'` **run over ssh kills the ssh session itself** (the pattern matches the
  remote command line). `game-over.sh` avoids this by running as a local script.
- Env-var scan: `tr … </proc/$p/environ 2>/dev/null` still prints the shell's redirect error —
  wrap the whole pipeline in `{ …; } 2>/dev/null`.
- Judge "GPU free" by *absence of game processes*, not total VRAM — a loaded llama-server is the
  goal state, not a failure.
- apollo (game streaming) is an **AUR package linking boost** — every boost soname bump breaks it
  silently until the next reboot (2026-08-31 boost 1.92 → surfaced 2026-09-14). Fix:
  `paru -G apollo && makepkg` then `pacman -U`, `systemctl --user restart apollo`.
