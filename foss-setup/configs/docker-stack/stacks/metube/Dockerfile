# MeTube + bgutil PO-token plugin + nightly yt-dlp (YouTube JS-challenge/403 fix,
# 2026-07-08). Nightly carries the current player's n-signature solver; the
# stable yt-dlp bundled in the base image lags and 403s. Rebuild to refresh:
#   docker compose build --pull && docker compose up -d
FROM ghcr.io/alexta69/metube:latest
RUN pip install --no-cache-dir bgutil-ytdlp-pot-provider \
 && pip install --no-cache-dir -U --pre "yt-dlp[default]"
