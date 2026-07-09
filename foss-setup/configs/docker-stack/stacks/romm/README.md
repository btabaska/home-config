# RomM — retro ROM library (retro-01 / retro-02)

Self-hosted ROM manager with IGDB metadata + web player. Runs on the **mini**
at `/opt/stacks/romm`, fronted by Caddy at <https://romm.tabaska.us>.

## Layout

- **App + DB**: `romm` (rommapp/romm) + `romm-db` (mariadb:11). Redis is bundled
  inside the romm image. Direct LAN: `mini:8998`.
- **ROM library** (retro-01): on the NAS `games` share, mounted rw on the mini at
  `/mnt/share/Games` (CIFS, uid=1000). RomM's library root is
  `/mnt/share/Games/romm` → `/romm/library` in the container, kept in its own
  subfolder so Synology `#recycle`/`@eaDir` cruft is out of RomM's view.

  ```
  /mnt/share/Games/romm/
  ├── roms/
  │   ├── gb/  gbc/  gba/  nes/  snes/  n64/  genesis/  psx/  …
  │   └── <platform-folder-name>/<game files>
  └── bios/
      └── <platform>/<bios files>
  ```
  Platform folder names follow RomM's slugs — see
  <https://docs.romm.app/latest/Getting-Started/Folder-Structure/>. Drop ROMs into
  the matching `roms/<platform>/` folder, then Scan in the web UI.
- **Saves/states/config**: local disk under `assets/` and `config/` (gitignored).

## Secrets

`.env` (gitignored) is filled from the vault:

| .env var | vault key |
|---|---|
| `ROMM_DB_ROOT_PASSWD` | `romm.db_root_password` |
| `ROMM_DB_PASSWD` | `romm.db_password` |
| `ROMM_AUTH_SECRET_KEY` | `romm.auth_secret_key` |
| `IGDB_CLIENT_ID` | `igdb.client_id` |
| `IGDB_CLIENT_SECRET` | `igdb.client_secret` |

## First run

1. `docker compose up -d` (DB comes up healthy first, then romm migrates).
2. Open <https://romm.tabaska.us> → create the first admin user in the UI.
3. Add ROMs under `/mnt/share/Games/romm/roms/<platform>/` → **Scan** in the UI;
   IGDB matches covers/metadata automatically.
