#!/usr/bin/env python3
# Deluge reaper: remove sonarr/sonarr-imported torrents (+data) older than MAX_AGE.
# Library copies live on the NAS (separate copies), so this only frees seedbox disk.
# Default DRY-RUN. Pass --live to actually remove.
import sys, os, time
from deluge.ui.client import client
from twisted.internet import reactor, defer

DRY = "--live" not in sys.argv
MAX_AGE = 14*86400
LABELS = {"sonarr", "sonarr-imported"}
LOG = os.path.expanduser("~/logs/deluge-reaper.log")

def localauth():
    for line in open(os.path.expanduser("~/.config/deluge/auth")):
        p=line.strip().split(":")
        if len(p)>=2 and p[0]=="btabaska": return p[0],p[1]
    raise SystemExit("no btabaska auth")

def logline(s):
    os.makedirs(os.path.dirname(LOG),exist_ok=True)
    line=time.strftime("%Y-%m-%d %H:%M:%S ")+s
    print(line); open(LOG,"a").write(line+"\n")

@defer.inlineCallbacks
def main():
    try:
        u,p=localauth()
        yield client.connect("127.0.0.1",3254,u,p)
        st=yield client.core.get_torrents_status({}, ["name","label","time_added","progress","state","total_size","ratio"])
        now=time.time(); cand=[]
        for h,v in st.items():
            if (v.get("label") or "") in LABELS and (v.get("progress") or 0)>=99.9:
                age=now-(v.get("time_added") or now)
                if age>=MAX_AGE: cand.append((h,v,age))
        total=sum((v.get("total_size") or 0) for _,v,_ in cand)
        logline(f"{'DRY-RUN' if DRY else 'LIVE'}: {len(cand)} eligible (age>=14d, labels={sorted(LABELS)}), {total/1e9:.1f} GB")
        for h,v,age in sorted(cand,key=lambda x:-x[2]):
            tag="WOULD REMOVE" if DRY else "REMOVED"
            if not DRY:
                yield client.core.remove_torrent(h, True)
            logline(f"  {tag} age={age/86400:.0f}d ratio={(v.get('ratio') or 0):.2f} size={ (v.get('total_size') or 0)/1e9:.1f}GB {(v.get('name') or '')[:55]}")
    except Exception as e:
        logline("ERR: "+repr(e))
    finally:
        try: client.disconnect()
        except: pass
        reactor.stop()

main()
reactor.run()
