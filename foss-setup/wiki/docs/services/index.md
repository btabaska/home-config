# Services

52 compose stacks, generated from the repo (`configs/docker-stack/stacks/`, `configs/nas/`, `configs/gaming/`) by `scripts/docs/gen-wiki-services.py`. If a page here disagrees with a compose file, regenerate — the compose file wins.

## AI & Cameras

| Stack | Host | URL |
|---|---|---|
| [frigate](frigate.md) *(not deployed)* | mini | — |

## AI & Gaming

| Stack | Host | URL |
|---|---|---|
| [amp](amp.md) | rig | https://amp.tabaska.us |
| [bedrock-connect](bedrock-connect.md) | mini | — |
| [palworld](palworld.md) | rig | — |
| [playit](playit.md) | rig | — |
| [romm](romm.md) | mini | https://romm.tabaska.us |
| [terraria](terraria.md) | mini | — |

## Documents & Life

| Stack | Host | URL |
|---|---|---|
| [paperless-ngx](paperless-ngx.md) | mini | https://paperless.tabaska.us |

## Files & Sync

| Stack | Host | URL |
|---|---|---|
| [syncthing-node](syncthing-node.md) | mini | http://192.168.10.2:8384 (mini node GUI; LAN/Tailscale-only, admin auth) |

## Infrastructure & Ops

| Stack | Host | URL |
|---|---|---|
| [beszel](beszel.md) | mini | https://status.tabaska.us |
| [caddy](caddy.md) | mini | — |
| [diun](diun.md) | mini | — |
| [dockge](dockge.md) | mini | https://dockge.tabaska.us |
| [forgejo](forgejo.md) | mini | https://git.tabaska.us |
| [healthchecks](healthchecks.md) | mini | https://health.tabaska.us |
| [homepage](homepage.md) | mini | https://home.tabaska.us |
| [ntfy](ntfy.md) | mini | https://ntfy.tabaska.us |
| [scrutiny](scrutiny.md) | nas | https://scrutiny.tabaska.us |
| [scrutiny-collector](scrutiny-collector.md) | mini | https://scrutiny-collector.tabaska.us |
| [syncthing](syncthing.md) | nas | https://syncthing.tabaska.us |
| [unbound](unbound.md) | mini | — |
| [uptime-kuma](uptime-kuma.md) | mini | https://uptime.tabaska.us |

## Life

| Stack | Host | URL |
|---|---|---|
| [journaling](journaling.md) | mini | https://memos.tabaska.us |
| [mealie](mealie.md) | mini | https://recipes.tabaska.us |
| [meme-review](meme-review.md) | mini | https://memes.tabaska.us |

## Media

| Stack | Host | URL |
|---|---|---|
| [bgutil-pot](bgutil-pot.md) | mini | — |
| [jellyfin](jellyfin.md) | nas | https://jellyfin.tabaska.us |
| [kometa](kometa.md) | mini | — |
| [metube](metube.md) | mini | https://metube.tabaska.us |
| [pinchflat](pinchflat.md) | mini | https://pinchflat.tabaska.us |

## Media & Acquisition

| Stack | Host | URL |
|---|---|---|
| [media-automation](media-automation.md) | nas | — |

## Media Automation

| Stack | Host | URL |
|---|---|---|
| [bazarr](bazarr.md) | nas | https://bazarr.tabaska.us |
| [bitmagnet](bitmagnet.md) | nas | https://bitmagnet.tabaska.us |
| [recyclarr](recyclarr.md) | mini | — |
| [tautulli](tautulli.md) | mini | https://tautulli.tabaska.us |

## Music

| Stack | Host | URL |
|---|---|---|
| [navidrome](navidrome.md) | mini | https://music.tabaska.us |

## Networking & Access

| Stack | Host | URL |
|---|---|---|
| [adguard](adguard.md) | mini | https://dns.tabaska.us |
| [adguard-nas](adguard-nas.md) | nas | http://192.168.10.4:3000 (LAN; secondary DNS itself is :53) |

## Photos

| Stack | Host | URL |
|---|---|---|
| [immich](immich.md) | nas | https://immich.tabaska.us |

## Private

| Stack | Host | URL |
|---|---|---|
| [stash](stash.md) | nas | https://stash.tabaska.us |

## Reading & Docs

| Stack | Host | URL |
|---|---|---|
| [audiobookshelf](audiobookshelf.md) | nas | https://abs.tabaska.us |
| [booklogr](booklogr.md) | mini | https://booklogr.tabaska.us |
| [calibre-web-automated](calibre-web-automated.md) | nas | https://books.tabaska.us |
| [komga](komga.md) | nas | https://komga.tabaska.us |
| [miniflux](miniflux.md) | mini | https://rss.tabaska.us |
| [mylar3](mylar3.md) | nas | https://mylar.tabaska.us |
| [trilium](trilium.md) | mini | https://trilium.tabaska.us |
| [wallabag](wallabag.md) | mini | https://wallabag.tabaska.us |

## Requests

| Stack | Host | URL |
|---|---|---|
| [libreseerr](libreseerr.md) | mini | https://libreseerr.tabaska.us |
| [musicseerr](musicseerr.md) | mini | https://musicseerr.tabaska.us |
| [seerr](seerr.md) | mini | https://seerr.tabaska.us |
| [shelfmark](shelfmark.md) | nas | https://shelfmark.tabaska.us |

Not compose-managed in this repo (so not listed above): **Plex** (native NAS package), **slskd + Deluge** (seedbox — see [seedbox](../hosts/seedbox.md)), and the **rig AI stack** (litellm, open-webui, mcpo — compose lives in the separate `local-ai-tooling` repo; see [rig](../hosts/rig.md)).

*Generated — do not edit by hand.*
