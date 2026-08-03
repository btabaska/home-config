# Checks — notes

`foss-setup/verification/checks.d/notes.yaml` — 1 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `trilium-web-serves-app`

Trilium serves its app shell through Caddy (read-27 consumer end)

- **host:** `mini` · **severity:** `warn` · **guards task:** `read-27` · **enabled:** True
- **expects:** `^TRILIUM_OK$`

```bash
code=$(curl -s -o /tmp/trilium-probe.html -m 20 -w '%{http_code}' https://trilium.tabaska.us/); if [ "$code" = "200" ] && grep -qi 'trilium' /tmp/trilium-probe.html; then echo TRILIUM_OK; else echo "TRILIUM_BAD code=$code"; fi; rm -f /tmp/trilium-probe.html
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
