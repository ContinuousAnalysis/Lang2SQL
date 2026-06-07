#!/bin/bash
# Auto-reload dev runner for lang2sql-bot.
# Watches src/ for .py changes and restarts the bot automatically.

set -a
source "$(dirname "$0")/.env"
set +a

REF=$(mktemp)

restart_bot() {
    if [ -n "$BOT_PID" ] && kill -0 "$BOT_PID" 2>/dev/null; then
        echo "[watch] stopping PID $BOT_PID..."
        kill "$BOT_PID"
        wait "$BOT_PID" 2>/dev/null
    fi
    echo "[watch] starting bot..."
    .venv/bin/lang2sql-bot &
    BOT_PID=$!
    touch "$REF"
    echo "[watch] PID $BOT_PID"
}

trap 'kill $BOT_PID 2>/dev/null; rm -f $REF; exit' INT TERM

restart_bot

while true; do
    sleep 2
    if find src/ -name "*.py" -newer "$REF" | grep -q .; then
        CHANGED=$(find src/ -name "*.py" -newer "$REF" | head -3 | tr '\n' ' ')
        echo "[watch] changed: $CHANGED"
        restart_bot
    elif ! kill -0 "$BOT_PID" 2>/dev/null; then
        echo "[watch] bot crashed, restarting in 2s..."
        sleep 2
        restart_bot
    fi
done
