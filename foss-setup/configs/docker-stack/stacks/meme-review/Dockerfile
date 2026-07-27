# Meme Review — single-stage build. Node 24 ships the stable built-in `node:sqlite`
# module, so there is no native build step (esbuild is a static Go binary). The
# server runs the TypeScript directly via tsx; `npm start` sets NODE_ENV=production.
FROM node:24-alpine

WORKDIR /app

# install ALL deps (vite/tsx/react live in devDependencies and are needed to build
# the SPA and run the server) — do NOT set NODE_ENV=production before `npm ci`.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV DATA_DIR=/data
EXPOSE 8787
VOLUME ["/data"]

CMD ["npm", "start"]
