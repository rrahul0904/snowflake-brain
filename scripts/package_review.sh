#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
STAMP="${1:-$(date +%Y-%m-%d)}"
ZIP_PATH="$DIST_DIR/snowflake-brain-source-$STAMP.zip"

mkdir -p "$DIST_DIR"
rm -f "$ZIP_PATH"

cd "$ROOT_DIR"

zip -qr "$ZIP_PATH" \
  app \
  frontend \
  docs \
  scripts \
  requirements.txt \
  Dockerfile \
  docker-compose.yml \
  README.md \
  REVIEW_PACKAGE.md \
  .gitignore \
  .dockerignore \
  -x \
  '*/__pycache__/*' \
  '*.pyc' \
  '*.pyo' \
  '.DS_Store' \
  '__MACOSX/*' \
  'data/*' \
  'static/*' \
  'review_artifacts/*' \
  'dist/*' \
  '.git/*' \
  '.venv/*' \
  'node_modules/*'

echo "$ZIP_PATH"
