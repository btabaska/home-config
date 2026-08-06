# kiwix — NAS offline ZIM library (lai-12) + the `zim` SMB share (lai-13)

| File | Live target on the NAS | Purpose |
|------|------------------------|---------|
| `docker-compose.yml` | `/volume1/docker/kiwix/docker-compose.yml` | kiwix-serve `:8092` + kiwix-manage sibling (library.xml rebuilds) |
| `kiwix-library-refresh.sh` | `/volume1/docker/kiwix/kiwix-library-refresh.sh` | nightly DSM task 05:15 rebuilds `library.xml` (kiwix-serve cannot hot-add ZIMs) |
| `zim-download-queue.sh` | `/volume1/docker/kiwix/zim-download-queue.sh` | sequential `wget -c` fetcher into `/volume1/zim/.incoming/`, atomic mv on completion |

The library itself lives at **`/volume1/zim`** (grows over days — Wikipedia en maxi ~115G
lands last; treat the dir read-only except via the queue script).

## The `zim` DSM shared folder (lai-13)

`/volume1/zim` was promoted from a plain dir to a DSM shared folder so the **rig** can
CIFS-mount it read-only for **openzim-mcp** (`//192.168.10.4/zim → /mnt/nas-zim`, see
`configs/host/rig/nas-mounts/`).

- Share: `zim` — "Offline ZIM library (kiwix-serve; lai-12/13)", recycle bin OFF.
- Share perms: `btabaska` RW (queue script writes), **`zimro` RO** — a DEDICATED low-priv
  local DSM user created for the rig mount only (password at vault
  `hosts.nas.zimro_smb_password`; created with
  `synouser --add zimro <pw> 'ZIM RO mount (lai-13)' 0 '' 0`).
- ACLs on the share dir (DSM only adds `administrators` by default):
  `synoacltool -add /volume1/zim user:btabaska:allow:rwxpdDaARWc--:fd--` and
  `synoacltool -add /volume1/zim user:zimro:allow:r-x---a-R-c--:fd--`.

### Recreation gotchas (cost real time — DSM 7.2.2)

- **DSM refuses to create a share on ANY pre-existing path — even an EMPTY dir**:
  `synoshare --add` → `0xE700`, `SYNO.Core.Share create` → error `3312`. The
  `0xE700`-is-about-populated-folders framing (ipod-abs-sync memory) is incomplete: the
  path must NOT EXIST at all. Promotion dance = move the WHOLE dir aside
  (`mv /volume1/zim /volume1/zim.premove`), `synoshare --add zim … /volume1/zim` (creates
  a fresh dir), set share perms + ACLs, `mv` the contents back, remove the premove dir.
- **The in-flight download survives the dance without pausing wget**: SIGSTOP only the
  queue *shell* pids (`zim-download-queue.sh`) so the script can't advance mid-dance, and
  leave `wget` running — its open fd + cwd follow the renamed `.incoming` inode, the
  TCP session never stalls, and after the contents move back every absolute path in the
  script resolves again. SIGCONT the shells when done. (If wget *does* die: nothing is
  lost — `wget -c` resumes from the partial in `.incoming/` on the next queue run.)
- **kiwix-serve must be restarted after the dance**: its bind mount references the OLD dir
  inode (deleted with the premove dir). It keeps serving open ZIM fds for a while, then
  `--monitorLibrary` drops every book (catalog goes to 0 entries, green-but-broken).
  `docker restart kiwix` re-binds the new dir. Docker CLI calls can hang for minutes while
  the NAS is under download I/O (load ~20+) — pause the wget (SIGSTOP) for the restart if
  needed.

## Consumers

- kiwix-serve `:8092` / `kiwix.tabaska.us` (mini Caddy vhost) — humans + check
  `kiwix-search-consumer` (lai-12).
- **openzim-mcp v2.5.5** on the rig (mcpo `/openzim`, OWUI-filtered to 3 tools; opencode
  stdio full 8) — check `openzim-mcp-search` (lai-13), runbook
  `wiki/docs/runbooks/openzim-mcp.md`.
