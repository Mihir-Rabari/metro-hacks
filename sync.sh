#!/bin/bash
# Auto-pull at stations: retries `git pull` every 15s until it succeeds, then beeps.
# Run this in the repo folder when you board; Ctrl+C to stop.
cd "$(dirname "$0")"
echo "metro-hacks sync: watching for station stops (retrying git pull every 15s)..."
while true; do
  if git pull --rebase --autostash >/dev/null 2>&1; then
    NEW=$(git log HEAD@{1}..HEAD --oneline 2>/dev/null | wc -l)
    if [ "$NEW" -gt 0 ]; then
      echo ""
      echo "  NEW BUILD ARRIVED ($NEW commits) — open dist/app.html to check it"
      printf '\a'  # beep
    fi
  fi
  sleep 15
done
