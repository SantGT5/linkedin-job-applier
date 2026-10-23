#!/bin/sh
# Creates .env from .env.example when missing and fills empty generated secrets.
# Never prints secret values.
set -eu
cd "$(dirname "$0")/../.."

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env from .env.example"
fi

fill() {
  key=$1
  bytes=$2
  note=${3:-}
  if grep -qE "^$key=.+" .env; then
    return
  fi
  value=$(openssl rand -hex "$bytes")
  if grep -qE "^$key=" .env; then
    sed -i.bak "s|^$key=.*|$key=$value|" .env && rm -f .env.bak
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
  echo "Generated $key in .env $note"
}

fill SESSION_SECRET 32
fill POSTGRES_PASSWORD 24
fill UI_PASSWORD 12 "(this is your UI password: read it in .env, or set your own and run make up)"
