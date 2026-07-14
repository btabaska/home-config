# `nut-client-ubuntu.sh`

> nut-client-ubuntu.sh

**Path:** `foss-setup/scripts/setup/nut-client-ubuntu.sh` · **Category:** [Host setup](index.md) · **Type:** Bash

## What it does

```text
 nut-client-ubuntu.sh
 Configure the Ubuntu box (Mac mini) as a NUT *netclient* that listens to the
 Synology NAS's UPS over the network and shuts down gracefully on a long outage.

 Architecture (Section 7 power resilience):
   UPS --USB--> DS920+ (DSM = NUT *server*, "netserver")  <--network--  Ubuntu (this box, "netclient")
   The Dream Wall is also on the UPS battery; it just rides through outages.
   DSM owns the UPS and does its own graceful shutdown; this box only *monitors*
   the NAS's UPS status and shuts itself down before the battery dies.

 Prereqs ON THE SYNOLOGY (do this first, in DSM):
   Control Panel -> Hardware & Power -> UPS:
     * Enable UPS support, type = USB UPS
     * Enable "network UPS server"
     * "Permitted DiskStation Devices" -> add THIS box's static IP
   Defaults DSM exposes to clients: UPS name = "ups", user = "monuser",
   password = "secret". (Verify via SSH on DSM: `cat /etc/ups/upsd.users` and
   `cat /etc/ups/ups.conf`.)

 Docs:
   - NUT user manual:   https://networkupstools.org/docs/user-manual.chunked/
   - nut.conf(5):       https://networkupstools.org/docs/man/nut.conf.html
   - upsmon.conf(5):    https://networkupstools.org/docs/man/upsmon.conf.html
   - Synology as NUT primary (community): https://www.johnra.me/2024/05/16/synology-ups-as-nut-primary/

 Idempotent: re-running re-writes the managed config blocks and restarts the
 monitor only if something changed. Run with sudo.

 NUT VERSION: the MONITOR line below uses the NUT 2.8 keyword `secondary`, which
 targets Ubuntu 24.04+ (ships NUT 2.8.x). On Ubuntu 22.04 (NUT 2.7.4) the keyword
 is `slave` instead — `secondary` will be rejected there. If you must run on 22.04,
 change `secondary` to `slave` in configure_upsmon() (or upgrade the OS / NUT).

 Usage:
   sudo NAS_IP=192.168.1.7 ./nut-client-ubuntu.sh
   sudo NAS_IP=192.168.1.7 UPS_NAME=ups UPS_USER=monuser UPS_PASS=secret ./nut-client-ubuntu.sh
```

## Environment / variables referenced

`EUID`, `MINSUPPLIES`, `NAS_IP`, `NUT_CONF`, `UPSMON_CONF`, `UPS_NAME`, `UPS_PASS`, `UPS_USER`

## See also

- [`cachyos-desktop-baseline.sh`](cachyos-desktop-baseline-sh.md)
- [`install-docker-ubuntu.sh`](install-docker-ubuntu-sh.md)
- [`install-haos-vm.sh`](install-haos-vm-sh.md)
- [Host setup scripts](index.md) · [All scripts](../index.md)
