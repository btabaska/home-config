# Services

32 compose stacks, generated from the repo (`configs/docker-stack/` and `configs/nas/`) by `scripts/docs/gen-wiki-services.py`. If a page here disagrees with a compose file, regenerate — the compose file wins.

## AI & Cameras

| Stack | Host | URL |
|---|---|---|
| [frigate](frigate.md) | mini | https://frigate.tabaska.us |
| [litellm](litellm.md) | mini | https://litellm.tabaska.us |

## Documents & Life

| Stack | Host | URL |
|---|---|---|
| [mealie](mealie.md) | mini | https://recipes.tabaska.us |
| [paperless-ngx](paperless-ngx.md) | mini | https://paperless.tabaska.us |

## Media & Acquisition

| Stack | Host | URL |
|---|---|---|
| [kometa](kometa.md) | mini | — |
| [libreseerr](libreseerr.md) | mini | https://libreseerr.tabaska.us (LAN: http://192.168.10.2:8789) |
| [maintainerr](maintainerr.md) | mini | https://maintainerr.tabaska.us |
| [media-automation](media-automation.md) | nas | — |
| [musicseerr](musicseerr.md) | mini | https://musicseerr.tabaska.us |
| [pinchflat](pinchflat.md) | mini | https://pinchflat.tabaska.us |
| [recyclarr](recyclarr.md) | mini | — |
| [seerr](seerr.md) | mini | https://seerr.tabaska.us |
| [stash](stash.md) | nas | https://stash.tabaska.us |
| [tautulli](tautulli.md) | mini | https://tautulli.tabaska.us |
| [tdarr](tdarr.md) | mini | https://tdarr.tabaska.us |

## Monitoring & Ops

| Stack | Host | URL |
|---|---|---|
| [beszel](beszel.md) | mini | https://beszel.tabaska.us |
| [dependency-track](dependency-track.md) | mini | https://deptrack.tabaska.us |
| [diun](diun.md) | mini | — |
| [dockge](dockge.md) | mini | https://dockge.tabaska.us |
| [healthchecks](healthchecks.md) | mini | https://healthchecks.tabaska.us |
| [homepage](homepage.md) | mini | https://home.tabaska.us |
| [ntfy](ntfy.md) | mini | https://ntfy.tabaska.us |
| [uptime-kuma](uptime-kuma.md) | mini | https://uptime.tabaska.us |

## Networking & Access

| Stack | Host | URL |
|---|---|---|
| [adguard](adguard.md) | mini | https://dns.tabaska.us |
| [adguard-nas](adguard-nas.md) | nas | http://192.168.10.4:3000 (LAN; secondary DNS itself is :53) |
| [caddy](caddy.md) | mini | — |
| [unbound](unbound.md) | mini | — |

## Photos & Reading

| Stack | Host | URL |
|---|---|---|
| [calibre-web-automated](calibre-web-automated.md) | nas | http://192.168.10.4:8083 (deliberately LAN/VPN-only) |
| [immich](immich.md) | nas | https://immich.tabaska.us (LAN: http://192.168.10.4:2283) |
| [miniflux](miniflux.md) | mini | https://rss.tabaska.us |
| [navidrome](navidrome.md) | mini | https://music.tabaska.us |
| [wallabag](wallabag.md) | mini | https://wallabag.tabaska.us |

Not compose-managed (so not listed above): **Plex** (native NAS package), **slskd + Deluge** (seedbox, provider-managed/native — see [seedbox](../hosts/seedbox.md)), **Forgejo** (runs from `/opt/stacks` on the mini).

*Generated — do not edit by hand.*
