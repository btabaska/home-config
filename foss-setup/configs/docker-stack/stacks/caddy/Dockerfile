# Optional: build Caddy with the Cloudflare DNS module for DNS-01 wildcard certs.
# Only needed if your Caddyfile uses the `dns cloudflare` directive (internal services).
# Docs: https://caddyserver.com/docs/build#xcaddy
#   https://github.com/caddy-dns/cloudflare
#
# To use: in compose.yaml comment the `image:` line and uncomment `build: .`, then:
#   docker compose up -d --build
ARG CADDY_VERSION=2.11.4
FROM caddy:${CADDY_VERSION}-builder AS builder
RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare

FROM caddy:${CADDY_VERSION}-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
