#!/usr/bin/env bash
# cron-target-sanity.sh — every absolute-path cron command must be an existing
# executable FILE, not a directory and not missing.
#
# M62 class (fix-39): btabaska's crontab ran '0 0 * * * /home/btabaska/bin' —
# exec of a DIRECTORY — which failed silently every midnight for ~2.5 years
# (output went to nonexistent local mail). This validates the first command
# token of every entry in user crontabs and /etc/cron.d. Tokens resolved via
# PATH (cd, curl, docker ...) are assumed fine; the silent-failure class this
# hunts is absolute paths that rotted after a topology change.
set -u
bad=""

check_cmd() {           # $1 = origin label, $2 = command string
  local tok
  for tok in $2; do
    [[ "$tok" == *=* ]] && continue        # skip leading VAR=val assignments
    if [[ "$tok" == /* ]] && [[ ! -f "$tok" || ! -x "$tok" ]]; then
      bad="$bad $1:$tok"
    fi
    return 0                               # only the first real token matters
  done
}

# user crontabs (root-readable only)
for tab in $(sudo -n ls /var/spool/cron/crontabs 2>/dev/null); do
  while read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue
    if [[ "$line" =~ ^@ ]]; then
      check_cmd "$tab" "$(awk '{$1="";print}' <<<"$line")"
    else
      check_cmd "$tab" "$(awk '{$1=$2=$3=$4=$5="";print}' <<<"$line")"
    fi
  done < <(sudo -n cat "/var/spool/cron/crontabs/$tab" 2>/dev/null)
done

# /etc/cron.d (system format: 5 schedule fields + user + command)
for f in /etc/cron.d/*; do
  [[ -f "$f" ]] || continue
  while read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue
    if [[ "$line" =~ ^@ ]]; then
      check_cmd "cron.d/${f##*/}" "$(awk '{$1=$2="";print}' <<<"$line")"
    else
      check_cmd "cron.d/${f##*/}" "$(awk '{$1=$2=$3=$4=$5=$6="";print}' <<<"$line")"
    fi
  done <"$f"
done

if [[ -z "$bad" ]]; then
  echo "BROKEN_CRON=NONE"
else
  echo "BROKEN_CRON=${bad# }"
fi
