#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Install on first run (or after dependencies change), then build the existing UI.
python -m pip install -r requirements.txt
(cd frontend && if [ ! -x node_modules/.bin/vite ]; then npm ci --include=dev; fi && npm run build)
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
