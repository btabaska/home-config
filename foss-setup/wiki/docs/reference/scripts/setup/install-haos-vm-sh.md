# `install-haos-vm.sh`

> install-haos-vm.sh

**Path:** `foss-setup/scripts/setup/install-haos-vm.sh` · **Category:** [Host setup](index.md) · **Type:** Bash

## What it does

```text
 install-haos-vm.sh
 Download the Home Assistant OS (HAOS) KVM image and create a libvirt VM.

 This is the "VM path" alternative to the recommended HA Green appliance.
 Run on the Ubuntu host that has KVM/libvirt installed. The VM bridges onto your
 LAN so HA appears as a normal peer (needed for mDNS device discovery: Hue, etc.).

 IMPORTANT NOTES
   * Never run HAOS from an SD card and never run HA in plain Docker (you lose the
     Supervisor and add-ons). This script uses HAOS in a proper KVM VM.
   * HA should live on the Trusted VLAN. Set NET_BRIDGE to the bridge attached to
     that VLAN (e.g. br0 / br-trusted). Trusted -> IoT is allowed by your firewall.
   * Uses UEFI (OVMF) WITHOUT secure boot, VirtIO disk + net, per official docs.

 Docs:
   https://www.home-assistant.io/installation/linux/   (KVM / virt-install section)
   https://github.com/home-assistant/operating-system/releases

 Idempotent: safe to re-run. It will skip the download if the image already exists
 and skip VM creation if a domain with the same name already exists.
```

## Environment / variables referenced

`DISK_SIZE_GB`, `EUID`, `HAOS_VERSION`, `IMAGE_BASENAME`, `IMAGE_DIR`, `IMAGE_PATH`, `IMAGE_URL`, `IMAGE_XZ`, `NET_BRIDGE`, `OVMF_CODE`, `VM_NAME`, `VM_RAM_MB`, `VM_VCPUS`

## See also

- [`cachyos-desktop-baseline.sh`](cachyos-desktop-baseline-sh.md)
- [`install-docker-ubuntu.sh`](install-docker-ubuntu-sh.md)
- [`nut-client-retire.sh`](nut-client-retire-sh.md)
- [`nut-client-ubuntu.sh`](nut-client-ubuntu-sh.md)
- [Host setup scripts](index.md) · [All scripts](../index.md)
