#!/bin/bash
#
# Scheduler del Asistente Virtual de Mood Mayorista.
#
# Loop simple que llama a run-round.sh (una ronda) cada INTERVAL_MINUTES. Útil
# para dejarlo corriendo en primer plano o bajo un servicio permanente
# (systemd Type=simple, launchd KeepAlive). Para tareas por intervalo del sistema
# (cron, systemd timer, Task Scheduler) llamá directamente a run-round.sh.
#
# Uso:
#   ./scheduler.sh [minutos]      # p.ej. ./scheduler.sh 10   (default: 10)
#
# Variables de entorno: las mismas que run-round.sh (REPO_DIR, SKILL_FILE,
# LOG_DIR, RUN_TIMEOUT).
#
set -euo pipefail

INTERVAL_MINUTES="${1:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Asistente Mood Mayorista — scheduler cada ${INTERVAL_MINUTES} min. Ctrl+C para detener."

while true; do
  "$SCRIPT_DIR/run-round.sh" || echo "(scheduler) run-round.sh devolvió error; sigo."
  sleep "$(( INTERVAL_MINUTES * 60 ))"
done
