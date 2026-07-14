# `install-docker-ubuntu.sh`

> install-docker-ubuntu.sh

**Path:** `foss-setup/scripts/setup/install-docker-ubuntu.sh` · **Category:** [Host setup](index.md) · **Type:** Bash

## Synopsis

```
Safe to re-run: it skips steps already satisfied. Run with sudo (or as root).
```

## What it does

```text
 install-docker-ubuntu.sh
 Idempotent install of Docker Engine + Compose plugin on Ubuntu Server,
 following the official Docker apt-repository method.

 Docs: https://docs.docker.com/engine/install/ubuntu/
       https://docs.docker.com/engine/install/linux-postinstall/

 Safe to re-run: it skips steps already satisfied. Run with sudo (or as root).

   sudo ./install-docker-ubuntu.sh
```

## Environment / variables referenced

`DOCKER_GPG`, `DOCKER_LIST`, `EUID`, `PRETTY_NAME`, `SUDO_USER`, `UBUNTU_CODENAME`, `VERSION_CODENAME`

## See also

- [`cachyos-desktop-baseline.sh`](cachyos-desktop-baseline-sh.md)
- [`install-haos-vm.sh`](install-haos-vm-sh.md)
- [`nut-client-ubuntu.sh`](nut-client-ubuntu-sh.md)
- [Host setup scripts](index.md) · [All scripts](../index.md)
