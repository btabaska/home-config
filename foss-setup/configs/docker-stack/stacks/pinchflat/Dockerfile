# Pinchflat + nightly yt-dlp zipapp + global yt-dlp.conf (YouTube 403/JS-challenge
# fix, 2026-07-08). The base image's stable yt-dlp lags YouTube's player and 403s;
# the nightly zipapp carries the current n-signature solver. Rebuild to refresh:
#   docker compose build --pull && docker compose up -d
FROM ghcr.io/kieraneglin/pinchflat:latest
ADD https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp /usr/local/bin/yt-dlp
RUN chmod 0755 /usr/local/bin/yt-dlp
COPY yt-dlp.conf /etc/yt-dlp.conf
