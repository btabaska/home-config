# Checks — meme-review

`foss-setup/verification/checks.d/meme-review.yaml` — 3 check(s). Run hourly/daily by the verification harness; page via ntfy. See [Verification runbook](../../runbooks/verification.md).

## `meme-review-api-health`

meme-review API answers /api/health through Caddy TLS

- **host:** `mini` · **severity:** `crit` · **guards task:** `meme-review-01` · **enabled:** True
- **expects:** `"ok":true`

```bash
curl -s -m 8 https://memes.tabaska.us/api/health
```

## `meme-review-spa-served`

meme-review serves the built SPA (not the 'not built yet' fallback)

- **host:** `mini` · **severity:** `crit` · **guards task:** `meme-review-01` · **enabled:** True
- **expects:** `<title>Meme Review</title>`

```bash
curl -s -m 8 https://memes.tabaska.us/
```

## `meme-review-auth-wall`

meme-review rejects unauthenticated /api/drops with 401

- **host:** `mini` · **severity:** `warn` · **guards task:** `meme-review-01` · **enabled:** True
- **expects:** `^401$`

```bash
curl -s -o /dev/null -m 8 -w '%{http_code}' https://memes.tabaska.us/api/drops
```

[← All checks](index.md) · [Verification runbook](../../runbooks/verification.md)
