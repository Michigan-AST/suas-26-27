#!/usr/bin/env bash
# Tear down the SUAS tmux session and SITL Docker container.

set -euo pipefail

SESSION="${SUAS_TMUX_SESSION:-suas}"

docker stop suas-px4-sitl >/dev/null 2>&1 || true

if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${SESSION}" 2>/dev/null; then
    tmux kill-session -t "${SESSION}"
    echo "Killed tmux session '${SESSION}' and stopped suas-px4-sitl."
else
    echo "Stopped suas-px4-sitl (no tmux session '${SESSION}' running)."
fi
