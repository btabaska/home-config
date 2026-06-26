#!/usr/bin/env bash
#
# install-haos-vm.sh
# Download the Home Assistant OS (HAOS) KVM image and create a libvirt VM.
#
# This is the "VM path" alternative to the recommended HA Green appliance.
# Run on the Ubuntu host that has KVM/libvirt installed. The VM bridges onto your
# LAN so HA appears as a normal peer (needed for mDNS device discovery: Hue, etc.).
#
# IMPORTANT NOTES
#   * Never run HAOS from an SD card and never run HA in plain Docker (you lose the
#     Supervisor and add-ons). This script uses HAOS in a proper KVM VM.
#   * HA should live on the Trusted VLAN. Set NET_BRIDGE to the bridge attached to
#     that VLAN (e.g. br0 / br-trusted). Trusted -> IoT is allowed by your firewall.
#   * Uses UEFI (OVMF) WITHOUT secure boot, VirtIO disk + net, per official docs.
#
# Docs:
#   https://www.home-assistant.io/installation/linux/   (KVM / virt-install section)
#   https://github.com/home-assistant/operating-system/releases
#
# Idempotent: safe to re-run. It will skip the download if the image already exists
# and skip VM creation if a domain with the same name already exists.

set -euo pipefail

# ----------------------------------------------------------------------------
# Configuration — edit these to taste.
# ----------------------------------------------------------------------------
HAOS_VERSION="${HAOS_VERSION:-18.0}"          # HAOS release; check the releases page for the latest
VM_NAME="${VM_NAME:-haos}"                      # libvirt domain name
VM_RAM_MB="${VM_RAM_MB:-4096}"                  # RAM in MB (4 GB is a good baseline)
VM_VCPUS="${VM_VCPUS:-2}"                        # vCPU count
DISK_SIZE_GB="${DISK_SIZE_GB:-32}"              # virtual disk size to grow the image to
NET_BRIDGE="${NET_BRIDGE:-br0}"                  # host bridge on the Trusted VLAN
IMAGE_DIR="${IMAGE_DIR:-/var/lib/libvirt/images/${VM_NAME}}"
# OVMF firmware path is used only for a fail-fast preflight check; virt-install itself
# uses `--boot uefi` (below) and lets libvirt auto-resolve the right firmware. Canonical
# Ubuntu filename is uppercase OVMF_CODE_4M.fd.
OVMF_CODE="${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE_4M.fd}"

# Derived values.
IMAGE_BASENAME="haos_ova-${HAOS_VERSION}.qcow2"
IMAGE_XZ="${IMAGE_BASENAME}.xz"
IMAGE_URL="https://github.com/home-assistant/operating-system/releases/download/${HAOS_VERSION}/${IMAGE_XZ}"
IMAGE_PATH="${IMAGE_DIR}/${IMAGE_BASENAME}"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
log()  { printf '\033[1;32m[haos-vm]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[haos-vm]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[haos-vm]\033[0m %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found. $2"
}

# ----------------------------------------------------------------------------
# Preflight
# ----------------------------------------------------------------------------
[[ "${EUID}" -eq 0 ]] || die "Please run as root (sudo), needed for libvirt + /var/lib/libvirt."

require_cmd virsh        "Install libvirt: apt install qemu-kvm libvirt-daemon-system libvirt-clients"
require_cmd virt-install "Install virtinst: apt install virtinst"
require_cmd wget         "Install wget: apt install wget"
require_cmd xz           "Install xz: apt install xz-utils"
require_cmd qemu-img     "Install qemu-utils: apt install qemu-utils"

# Fail fast: virt-install's `--boot uefi` will error out anyway without OVMF present.
[[ -f "${OVMF_CODE}" ]] || die "OVMF firmware not found at ${OVMF_CODE}. Install it: apt install ovmf (or set OVMF_CODE to your distro's OVMF_CODE_4M.fd path)."

# Verify the target bridge exists so we fail early with a clear message.
if ! ip link show "${NET_BRIDGE}" >/dev/null 2>&1; then
  warn "Network bridge '${NET_BRIDGE}' was not found on this host."
  warn "Create a bridge on the Trusted VLAN (netplan/systemd-networkd) and set NET_BRIDGE."
fi

# ----------------------------------------------------------------------------
# Idempotency: bail out cleanly if the VM already exists.
# ----------------------------------------------------------------------------
if virsh dominfo "${VM_NAME}" >/dev/null 2>&1; then
  log "A libvirt domain named '${VM_NAME}' already exists. Nothing to do."
  log "Manage it with:  virsh start ${VM_NAME}  |  virsh console ${VM_NAME}  |  virsh dominfo ${VM_NAME}"
  exit 0
fi

# ----------------------------------------------------------------------------
# Download + decompress the HAOS qcow2 image (skip if already present).
# ----------------------------------------------------------------------------
mkdir -p "${IMAGE_DIR}"

if [[ -f "${IMAGE_PATH}" ]]; then
  log "HAOS image already present: ${IMAGE_PATH} (skipping download)."
else
  log "Downloading HAOS ${HAOS_VERSION} image..."
  # -c resumes a partial download, making re-runs cheap.
  wget -c -O "${IMAGE_DIR}/${IMAGE_XZ}" "${IMAGE_URL}"

  log "Decompressing ${IMAGE_XZ}..."
  # -k keeps the .xz so a re-run does not re-download; decompress to the .qcow2.
  xz -d -k -v "${IMAGE_DIR}/${IMAGE_XZ}"
  [[ -f "${IMAGE_PATH}" ]] || die "Expected ${IMAGE_PATH} after decompression but it is missing."
fi

# ----------------------------------------------------------------------------
# Grow the disk image to the requested size (no-op if already >= target).
# ----------------------------------------------------------------------------
log "Resizing disk image to ${DISK_SIZE_GB}G (grow-only)..."
qemu-img resize "${IMAGE_PATH}" "${DISK_SIZE_GB}G" || warn "qemu-img resize reported an issue (image may already be larger)."

# ----------------------------------------------------------------------------
# Create + start the VM.
#   - UEFI boot: `--boot uefi` lets libvirt auto-resolve the firmware + create the
#     per-VM NVRAM VARS copy (more robust than hand-wiring loader/pflash paths,
#     which break on filename/casing drift like OVMF_CODE_4m.fd vs OVMF_CODE_4M.fd).
#   - VirtIO disk + bridged VirtIO NIC.
#   - --osinfo detect=on,require=off avoids failing on unknown os variants.
#   - --noautoconsole returns control to the shell; use 'virsh console' to view boot.
# ----------------------------------------------------------------------------
log "Creating libvirt VM '${VM_NAME}' (RAM=${VM_RAM_MB}MB, vCPUs=${VM_VCPUS}, bridge=${NET_BRIDGE})..."
virt-install \
  --name "${VM_NAME}" \
  --description "Home Assistant OS ${HAOS_VERSION}" \
  --memory "${VM_RAM_MB}" \
  --vcpus "${VM_VCPUS}" \
  --cpu host \
  --machine q35 \
  --boot uefi \
  --disk "path=${IMAGE_PATH},format=qcow2,bus=virtio" \
  --network "bridge=${NET_BRIDGE},model=virtio" \
  --osinfo detect=on,require=off \
  --graphics none \
  --noautoconsole \
  --import

# Make sure it starts on host boot.
virsh autostart "${VM_NAME}" >/dev/null 2>&1 || warn "Could not set autostart for ${VM_NAME}."

log "Done. HAOS VM '${VM_NAME}' is starting."
log "Watch boot:        virsh console ${VM_NAME}   (Ctrl+] to exit)"
log "After ~1-2 min, open Home Assistant at:  http://homeassistant.local:8123"
log "If mDNS is blocked, find the VM IP from your router/DHCP and use http://<IP>:8123"
