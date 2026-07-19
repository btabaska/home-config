# Pinchflat + nightly yt-dlp zipapp + global yt-dlp.conf (YouTube 403/JS-challenge
# fix, 2026-07-08). The base image's stable yt-dlp lags YouTube's player and 403s;
# the nightly zipapp carries the current n-signature solver. Rebuild to refresh:
#   docker compose build --pull && docker compose up -d
#
# fix-37 (M14): the bgutil PO-token plugin is baked in so yt-dlp fetches POTs
# from the bgutil-pot container (same `edge` network) — without it, YouTube
# "Sign in to confirm you're not a bot" checks permanently strand downloads
# (7 items stuck 2026-07-14) while bgutil-pot sat idle. The plugin zip version
# MUST match the bgutil-pot server image version (both 1.3.1) — bump together.
FROM ghcr.io/kieraneglin/pinchflat:latest
ADD https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp /usr/local/bin/yt-dlp
ADD https://github.com/Brainicism/bgutil-ytdlp-pot-provider/releases/download/1.3.1/bgutil-ytdlp-pot-provider.zip /etc/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip
RUN chmod 0755 /usr/local/bin/yt-dlp && chmod 0644 /etc/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip
COPY yt-dlp.conf /etc/yt-dlp.conf
