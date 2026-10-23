# frontend: Vite build served by nginx, which also proxies /api and /novnc.
FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM deps AS test
COPY frontend/ ./
CMD ["npm", "test"]

FROM deps AS build
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/stack/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
