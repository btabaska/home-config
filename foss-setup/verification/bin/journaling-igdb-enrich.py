#!/usr/bin/env python3
# journal-07 consumer-end check for IGDB #gamelog enrichment. It runs the EXACT external
# dependency the workflow's IGDB branch relies on — a Twitch client_credentials OAuth
# grant + an IGDB games search — from INSIDE the n8n container, using that container's own
# IGDB_CLIENT_ID/IGDB_CLIENT_SECRET env. That is the true consumer: it proves the creds are
# still valid (Twitch app secrets can be rotated/revoked → enrichment would silently stop),
# the container's egress + DNS reach id.twitch.tv/api.igdb.com, the IGDB API still answers,
# and the creds are wired into the container — WITHOUT posting a memo or waking the coach GPU.
# Creds never leave the container (read from its own process.env inside node).
#
# Output (one line, matched by the check's `expect`):
#   IGDB_ENRICH_OK          a known title (Celeste) resolves with cover art  -> pass
#   IGDB_SKIP_DISABLED      IGDB_ENABLED=false (operator opted out)           -> pass (skip)
#   IGDB_ENRICH_FAIL:<why>  creds missing / oauth / no-results / egress / etc -> FAIL
import subprocess, sys

JS = r'''
(async () => {
  const en = (process.env.IGDB_ENABLED || 'true').trim().toLowerCase();
  if (['0','false','off','no','disabled'].includes(en)) { console.log('IGDB_SKIP_DISABLED'); return; }
  const cid = (process.env.IGDB_CLIENT_ID || '').trim();
  const csec = (process.env.IGDB_CLIENT_SECRET || '').trim();
  if (!cid || !csec) { console.log('IGDB_ENRICH_FAIL:creds-missing'); process.exitCode = 1; return; }
  try {
    const q = new URLSearchParams({ client_id: cid, client_secret: csec, grant_type: 'client_credentials' });
    const t = await fetch('https://id.twitch.tv/oauth2/token', { method: 'POST', body: q }).then(r => r.json());
    if (!t || !t.access_token) { console.log('IGDB_ENRICH_FAIL:oauth-' + ((t && (t.status || t.message)) || 'no-token')); process.exitCode = 1; return; }
    const body = 'search "Celeste"; fields name,cover.image_id,involved_companies.developer; limit 10;';
    const g = await fetch('https://api.igdb.com/v4/games', { method: 'POST', headers: { 'Client-ID': cid, 'Authorization': 'Bearer ' + t.access_token, 'Content-Type': 'text/plain' }, body }).then(r => r.json());
    if (!Array.isArray(g) || !g.length) { console.log('IGDB_ENRICH_FAIL:no-results'); process.exitCode = 1; return; }
    const hit = g.find(x => (x.name || '').toLowerCase() === 'celeste') || g[0];
    if (hit && hit.cover && hit.cover.image_id) { console.log('IGDB_ENRICH_OK'); }
    else { console.log('IGDB_ENRICH_FAIL:no-cover'); process.exitCode = 1; }
  } catch (e) { console.log('IGDB_ENRICH_FAIL:' + String(e && e.message || 'exception').slice(0, 60)); process.exitCode = 1; }
})();
'''

try:
    # Pipe the probe into a temp file inside the container, run it, then remove it
    # (n8n's node cannot execute /dev/stdin). rc of node is propagated out.
    p = subprocess.run(
        ['docker', 'exec', '-i', 'n8n', 'sh', '-c',
         'cat > /tmp/igdb_probe.js && node /tmp/igdb_probe.js; rc=$?; rm -f /tmp/igdb_probe.js; exit $rc'],
        input=JS, capture_output=True, text=True, timeout=60)
except Exception as e:
    print('IGDB_ENRICH_FAIL:exec-' + str(e)[:60]); sys.exit(1)

out = (p.stdout or '').strip()
if not out:
    out = 'IGDB_ENRICH_FAIL:' + ((p.stderr or '').strip()[:80] or 'no-output')
print(out)
sys.exit(0 if ('IGDB_ENRICH_OK' in out or 'IGDB_SKIP_DISABLED' in out) else 1)
