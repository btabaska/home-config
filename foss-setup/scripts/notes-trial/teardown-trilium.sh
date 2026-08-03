#!/usr/bin/env bash
# teardown-trilium.sh — fully revert the read-27 Trilium (TriliumNext) Obsidian-replacement trial.
#
# DRY-RUN by default: prints exactly what it would do and changes nothing. Add --apply to run.
#
# Usage:
#   teardown-trilium.sh                          # dry-run: print the plan, touch nothing
#   teardown-trilium.sh --apply                  # tear down the LIVE trial (keeps ./data notes)
#   teardown-trilium.sh --apply --purge-data     # also delete the notes (after a backup tarball)
#   teardown-trilium.sh --apply --repo-revert    # also git-revert the repo commit + print publish steps
#
# Live things removed: the trilium container, the Caddy vhost, the Homepage tile, the coverage
# manifest line, the verification check, and the Uptime-Kuma monitor. Because every byte of
# Trilium state is in /opt/stacks/trilium/data and nothing else was modified in place, this
# leaves no residue. The repo/config files are reverted with git (see --repo-revert).
set -euo pipefail

MINI="${MINI_SSH:-mini}"
STACK="/opt/stacks/trilium"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"          # foss-setup/
MONITOR="Edge Trilium (vhost)"

APPLY=0 PURGE=0 REPO_REVERT=0
for a in "$@"; do case "$a" in
  --apply) APPLY=1 ;;
  --purge-data) PURGE=1 ;;
  --repo-revert) REPO_REVERT=1 ;;
  -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "unknown arg: $a" >&2; exit 2 ;;
esac; done

hdr()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
show() { echo "   \$ $*"; }
sh_m() { # run a command on the mini, honoring dry-run
  show "ssh $MINI $*"
  [ "$APPLY" = 1 ] && ssh "$MINI" "$@"
  return 0
}

[ "$APPLY" = 1 ] || hdr "DRY-RUN — nothing will change. Re-run with --apply to execute."

# Ship the (tested) config-strip helper to the mini so it can edit the live files.
if [ "$APPLY" = 1 ]; then
  scp -q "$HERE/strip-trilium-config.py" "$MINI:/tmp/strip-trilium-config.py"
fi

hdr "1) Stop & remove the trilium container"
sh_m "cd $STACK 2>/dev/null && docker compose down || docker rm -f trilium 2>/dev/null || true"

hdr "2) Notes data ($STACK/data)"
if [ "$PURGE" = 1 ]; then
  sh_m "ts=\$(date +%Y%m%d-%H%M%S); tar czf /opt/stacks/trilium-data-backup-\$ts.tgz -C $STACK data 2>/dev/null && echo \"backup: /opt/stacks/trilium-data-backup-\$ts.tgz\" || echo '(no data dir to back up)'"
  sh_m "rm -rf $STACK"
else
  echo "   · keeping $STACK (stopped). Re-run with --purge-data to delete the notes (a backup"
  echo "     tarball is written to /opt/stacks/ first)."
fi

hdr "3) Remove the Caddy vhost + Homepage tile (live), then reload Caddy"
sh_m "python3 /tmp/strip-trilium-config.py --caddyfile /opt/stacks/caddy/caddy/Caddyfile --homepage /opt/stacks/homepage/config/services.yaml"
sh_m "docker exec caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1 && docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile && echo caddy-reloaded"

hdr "4) Remove the verification check + coverage-manifest line (live, root-owned)"
sh_m "sudo rm -f /opt/verification/checks.d/notes.yaml && echo removed-check"
sh_m "sudo python3 /tmp/strip-trilium-config.py --coverage /opt/verification/coverage/mini.containers"

hdr "5) Remove the Uptime-Kuma monitor '$MONITOR' + restart Kuma"
if [ "$APPLY" = 1 ]; then
  ssh "$MINI" "cat > /tmp/trilium-kuma-teardown.sql" <<SQL
DELETE mn FROM monitor_notification mn JOIN monitor m ON m.id=mn.monitor_id WHERE m.name='${MONITOR}';
DELETE mg FROM monitor_group mg JOIN monitor m ON m.id=mg.monitor_id WHERE m.name='${MONITOR}';
DELETE FROM monitor WHERE name='${MONITOR}';
SQL
  ssh "$MINI" 'docker exec -i uptime-kuma mariadb --socket=/app/data/run/mariadb.sock kuma < /tmp/trilium-kuma-teardown.sql && rm -f /tmp/trilium-kuma-teardown.sql && docker restart uptime-kuma >/dev/null && echo kuma-monitor-removed'
else
  show "ssh $MINI 'docker exec -i uptime-kuma mariadb ... kuma  # DELETE monitor \"$MONITOR\" + links, then docker restart uptime-kuma'"
fi

# Clean up the shipped helper.
if [ "$APPLY" = 1 ]; then ssh "$MINI" 'rm -f /tmp/strip-trilium-config.py' || true; fi

hdr "6) Repo revert"
SHA="$(git -C "$REPO" log --grep='notes-trial' --format=%H -1 2>/dev/null || true)"
if [ "$REPO_REVERT" = 1 ]; then
  if [ -n "$SHA" ]; then
    show "git -C $REPO revert --no-edit $SHA"
    [ "$APPLY" = 1 ] && git -C "$REPO" revert --no-edit "$SHA"
    echo "   · then push + rebuild:"
    echo "       $REPO/scripts/docs/publish-deploy.sh"
    echo "       $REPO/scripts/docs/build-wiki.sh"
    echo "   · and drop /opt/stacks/trilium from the docker-stacks repo on the mini:"
    echo "       ssh $MINI 'cd /opt/stacks && git rm -r --cached trilium 2>/dev/null; git commit -am \"notes-trial: revert Trilium\" && git push origin'"
  else
    echo "   · could not find the notes-trial commit — revert the repo manually."
  fi
else
  echo "   · repo files are still committed (SHA ${SHA:-unknown}). To finish the revert:"
  echo "       git -C $REPO revert --no-edit ${SHA:-<notes-trial commit>}"
  echo "       $REPO/scripts/docs/publish-deploy.sh    # push the revert to GitHub + forgejo"
  echo "       $REPO/scripts/docs/build-wiki.sh         # rebuild the wiki without the Trilium page"
  echo "     Also drop /opt/stacks/trilium from the docker-stacks repo on the mini and push."
fi

hdr "Done.$([ "$APPLY" = 1 ] || echo ' (dry-run — nothing changed)')"
