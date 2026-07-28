# Checks — game-saves

`foss-setup/verification/checks.d/game-saves.yaml` — 2 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `game-saves-mesh-synced`

ludusavi game-saves folder fully replicated to the NAS hub (rig peer 100%)

- **host:** `nas` · **severity:** `warn` · **guards task:** `game-12` · **enabled:** True
- **expects:** `^game_saves_mesh=ok `

```bash
API=$(grep -o '<apikey>[^<]*</apikey>' /volume1/docker/syncthing/config/config.xml | sed 's/<[^>]*>//g'); RIG=KDLS63N-KNX5Q4U-IAGLHGX-2BW7CS2-VGVQBNL-V7VOZ4R-O2NBHQZ-VMSCAQ7; S=$(curl -s -H "X-API-Key: $API" "http://127.0.0.1:8384/rest/db/status?folder=game-saves"); C=$(curl -s -H "X-API-Key: $API" "http://127.0.0.1:8384/rest/db/completion?folder=game-saves&device=$RIG"); printf '%s\n@@@\n%s\n' "$S" "$C" | python3 -c "import json,sys; P=sys.stdin.read().split('@@@'); s=json.loads(P[0]); c=json.loads(P[1]); g=s.get('globalFiles',0); n=s.get('needFiles',0); st=s.get('state','?'); comp=c.get('completion',0); ok = g>0 and n==0 and comp>=100; print('game_saves_mesh=ok files=%d rig_complete=%d%% state=%s'%(g,comp,st) if ok else 'game_saves_mesh=DEGRADED files=%d need=%d rig_complete=%.1f%% state=%s'%(g,n,comp,st))"
```

## `ludusavi-backup-timer-alive`

rig ludusavi-backup.timer enabled + last run succeeded (keeps saves fresh)

- **host:** `rig` · **severity:** `warn` · **guards task:** `game-12` · **enabled:** True
- **expects:** `^ludusavi_timer=active last_result=success$`

```bash
A=$(systemctl --user is-active ludusavi-backup.timer 2>/dev/null); R=$(systemctl --user show ludusavi-backup.service -p Result --value 2>/dev/null); echo "ludusavi_timer=$A last_result=$R"
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
