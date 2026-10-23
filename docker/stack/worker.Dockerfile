# worker: runs the bot (undetected-chromedriver + PyAutoGUI) in native arm64/amd64 Chromium
# on a virtual display (Xvfb), shown in the UI through x11vnc + noVNC.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data \
    PYTHONPATH=/app:/app/bot \
    DISPLAY=:99 \
    CHROME_BINARY=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver \
    CHROME_PROFILE_DIR=/data/chrome-profile

RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium chromium-driver \
      xvfb xauth x11vnc fluxbox novnc websockify \
      tk libx11-6 x11-utils xdotool \
      fonts-liberation fonts-noto-color-emoji fonts-dejavu-core \
      procps tini ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml ./
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; open('/tmp/requirements.txt', 'w').write('\n'.join(p['dependencies']))" \
 && pip install -r /tmp/requirements.txt

RUN useradd --create-home --uid 1000 applier && mkdir -p /data && chown applier:applier /data \
 && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
COPY --chown=applier:applier backend/ ./
COPY --chmod=755 docker/stack/worker-entrypoint.sh /usr/local/bin/worker-entrypoint.sh
USER applier

EXPOSE 6080
# Healthy once the virtual display is served through noVNC.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:6080/vnc.html', timeout=2).status == 200 else 1)"
ENTRYPOINT ["tini", "--", "/usr/local/bin/worker-entrypoint.sh"]
