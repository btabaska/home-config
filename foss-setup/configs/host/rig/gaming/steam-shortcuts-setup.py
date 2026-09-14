#!/usr/bin/env python3
"""One-shot Steam wiring for Battle.net gaming on the rig (2026-09-14).

Run ON the rig as btabaska with Steam FULLY SHUT DOWN (`steam -shutdown`).
Backs up, then rewrites:
  - userdata/34948152/config/shortcuts.vdf
      * drops 4 stale shortcuts that pointed at the deleted prefix compatdata/3083077599
      * repoints the "Battle.net-Setup.exe" shortcut (appid 2951284266 — its compatdata
        prefix holds the real 39G Battle.net + WC3 Reforged + WoW-classic install)
        at the installed "Battle.net Launcher.exe" and renames it "Battle.net"
      * adds "Warcraft III: Reforged" and "World of Warcraft" shortcuts that launch
        through the SAME prefix (STEAM_COMPAT_DATA_PATH pin) with Battle.net
        --exec="launch W3" / "launch WoW" product codes (Lutris convention)
  - config/config.vdf CompatToolMapping: all three shortcuts -> GE-Proton11-WC3-CertFix
    (full GE-Proton 11 fork with the WC3 crypt32 cert fix; fine for WoW too),
    and removes the stale 2412228651 mapping.

Repo copy: foss-setup/configs/host/rig/gaming/steam-shortcuts-setup.py
"""
import os, shutil, struct, sys, time

import vdf

HOME = os.path.expanduser("~")
SD = f"{HOME}/.local/share/Steam"
UID = "34948152"
SHORTCUTS = f"{SD}/userdata/{UID}/config/shortcuts.vdf"
CONFIG = f"{SD}/config/config.vdf"
TOOL = "GE-Proton11-WC3-CertFix"

PREFIX = "/home/btabaska/.steam/steam/steamapps/compatdata/2951284266"
BNET_DIR = f"{PREFIX}/pfx/drive_c/Program Files (x86)/Battle.net"
BNET_EXE = f'"{BNET_DIR}/Battle.net Launcher.exe"'
ICONS = f"{HOME}/.local/share/icons/hicolor/256x256/apps"

APPID_BNET = 2951284266
APPID_WC3 = 2371484709   # zlib.crc32(exe+appname)|0x80000000, precomputed
APPID_WOW = 3238950932
STALE = {3995890469, 3117760306, 2412228651, 2537080474}


def u32(v):
    return v & 0xFFFFFFFF


def s32(v):
    v = u32(v)
    return v - 2**32 if v >= 2**31 else v


def gameid(appid):
    return (u32(appid) << 32) | 0x02000000


ts = time.strftime("%Y%m%d-%H%M%S")
if os.system("pgrep -x steam >/dev/null") == 0:
    sys.exit("Steam is still running — `steam -shutdown` first.")
for f in (SHORTCUTS, CONFIG):
    shutil.copy2(f, f + f".bak-{ts}")
    print(f"backup: {f}.bak-{ts}")

# ---- shortcuts.vdf -------------------------------------------------------
with open(SHORTCUTS, "rb") as fh:
    data = vdf.binary_load(fh)
entries = data["shortcuts"]
kept, template = [], None
for _, e in sorted(entries.items(), key=lambda kv: int(kv[0])):
    aid = u32(e.get("appid", 0))
    if aid == APPID_BNET:
        template = dict(e)
    if aid in STALE:
        print(f"dropping stale shortcut {aid}: {e.get('AppName') or e.get('appname')}")
        continue
    if aid == APPID_BNET:
        continue  # re-added below in canonical form
    kept.append(e)
if template is None:
    sys.exit("expected shortcut appid 2951284266 not found — aborting, nothing written")

name_key = "AppName" if "AppName" in template else "appname"


def mk(appid, name, launchopts, icon):
    e = dict(template)
    e["appid"] = s32(appid)
    e[name_key] = name
    e["Exe"] = BNET_EXE
    e["StartDir"] = f'"{BNET_DIR}/"'
    e["icon"] = f"{ICONS}/{icon}.png"
    e["LaunchOptions"] = launchopts
    e["LastPlayTime"] = 0
    e["IsHidden"] = 0
    return e


share = f"STEAM_COMPAT_DATA_PATH={PREFIX} %command%"
new = [
    mk(APPID_BNET, "Battle.net", "", "battlenet"),
    mk(APPID_WC3, "Warcraft III: Reforged", f'{share} --exec="launch W3"', "warcraft3-reforged"),
    mk(APPID_WOW, "World of Warcraft", f'{share} --exec="launch WoW"', "wow"),
]
data["shortcuts"] = {str(i): e for i, e in enumerate(kept + new)}
with open(SHORTCUTS, "wb") as fh:
    vdf.binary_dump(data, fh)
print(f"shortcuts.vdf written: {len(kept)} kept + {len(new)} managed entries")

# ---- config.vdf CompatToolMapping ---------------------------------------
with open(CONFIG) as fh:
    cfg = vdf.load(fh, mapper=vdf.VDFDict)


def ci_get(node, key):
    for k in node.keys():
        if k.lower() == key.lower():
            return node[k]
    raise KeyError(key)


steam = ci_get(ci_get(ci_get(ci_get(cfg, "InstallConfigStore"), "Software"), "Valve"), "Steam")
try:
    ctm = ci_get(steam, "CompatToolMapping")
except KeyError:
    steam["CompatToolMapping"] = vdf.VDFDict()
    ctm = steam["CompatToolMapping"]
if "2412228651" in ctm:
    del ctm["2412228651"]
    print("removed stale CompatToolMapping 2412228651")
for aid in (APPID_BNET, APPID_WC3, APPID_WOW):
    key = str(aid)
    val = {"name": TOOL, "config": "", "priority": "250"}
    if key in ctm:
        ctm[key] = val
    else:
        ctm[key] = val
    print(f"CompatToolMapping {key} -> {TOOL}")
with open(CONFIG, "w") as fh:
    vdf.dump(cfg, fh, pretty=True)
print("config.vdf written")

for label, aid in (("Battle.net", APPID_BNET), ("Warcraft III: Reforged", APPID_WC3), ("World of Warcraft", APPID_WOW)):
    print(f"steam://rungameid/{gameid(aid)}  # {label}")
print("Done — start Steam again.")
