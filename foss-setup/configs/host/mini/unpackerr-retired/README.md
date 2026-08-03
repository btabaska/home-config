# unpackerr (mini host service) — RETIRED 2026-08-03 (fix-69 / SL18)

The mini carried an **orphaned, deb-packaged `unpackerr` host service** (package
`unpackerr 0.13.1-613`, installed 2024-06-16, `unpackerr.service` running as PID
756 with an admin `unpackerr.service.d/override.conf` forcing `User=root`). Its
`/etc/unpackerr/unpackerr.conf` still pointed Radarr/Sonarr at
`http://192.168.1.2:7878` / `:8989` — a **dead subnet** (the fleet is
`192.168.10.0/24`; the mini is `192.168.10.2`). It could reach nothing, so it
logged `context deadline exceeded` into the journal every ~2 minutes for weeks,
and it held cleartext *arr API keys (sec-10 adjacent).

It was never one of the mini's managed host units (see
`configs/host/mini/` — tv-cleanup, net-selfheal, static-ip, lidarr-reconcile, …),
never in a coverage manifest, and did no useful work: **the real extraction
service is the `unpackerr` container on the NAS** (colocated with sonarr/radarr,
`Up` and healthy, actively finishing extractions). The fleet-sweep verify pass
confirmed the mini host unit was pure noise, not a live extraction path.

## What was done

```sh
sudo systemctl disable --now unpackerr.service
sudo apt-get purge -y unpackerr        # removes the unit + /etc/unpackerr (incl. cleartext keys)
sudo rm -rf /etc/systemd/system/unpackerr.service.d /etc/unpackerr
sudo systemctl daemon-reload
```

Result: no `unpackerr.service` unit, no process, package purged, `/etc/unpackerr`
gone. (etckeeper auto-committed the `/etc` deletions.)

## Guard

Check **`unpackerr-host-retired`** (task fix-69,
`verification/checks.d/host-hygiene.yaml`) goes red if a host-level `unpackerr`
unit, process, or package ever reappears on the mini. The NAS container unpackerr
remains the sole extractor.
