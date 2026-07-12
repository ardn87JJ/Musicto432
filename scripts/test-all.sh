#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$root/backend"
python -m pytest
python -m ruff check .

cd "$root/frontend"
npm test
npm run lint
npm run build

