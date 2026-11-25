#!/usr/bin/env bash
# Regenerates the architecture diagrams: SVG (docs/diagrams.py) -> PNG (headless Google Chrome, 2x).
# Usage: docs/render.sh
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
python3 diagrams.py
for name in architecture-ha architecture-slim; do
  H=$(grep -o 'height="[0-9]*"' "$name.svg" | head -1 | tr -dc 0-9)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="1600,$H" --screenshot="$PWD/$name.png" "file://$PWD/$name.svg" >/dev/null 2>&1
  echo "docs/$name.png"
done
