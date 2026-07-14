# NAS reference

Synology DS920+ — volume/backup architecture plus the operational wiring for every
service that runs on the NAS (the \*arr media-automation stack, Plex, CWA, Stash).

**Infrastructure**

| Page | |
|---|---|
| [NAS volume schema](volume-schema.md) | Drive / share / snapshot / backup layout |
| [NAS backup architecture](backup-architecture.md) | Hyper Backup → B2, snapshots, tiers |

**Services on the NAS**

| Page | |
|---|---|
| [Home media-automation stack](media-automation.md) | \*arr suite wiring & operations (Sonarr/Radarr/Lidarr/Readarr/Prowlarr + unpackerr) |
| [Media-automation migration (Ubuntu → NAS)](media-automation-migration.md) | Completed historical cutover record |
| [Plex Media Server](plex.md) | Plex as a Synology package (not Docker) |
| [Calibre-Web-Automated](calibre-web-automated.md) | Operational wiring, ingest flow, Kobo sync |
| [Stash](stash.md) | Deployment + compose on the NAS |

_7 pages._
