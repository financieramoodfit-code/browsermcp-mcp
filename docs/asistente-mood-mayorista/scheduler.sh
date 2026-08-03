#!/bin/bash
#
# Scheduler del Asistente Virtual de Mood Mayorista.
#
# Dispara una "ronda" (revisar y contestar lo pendiente en IG/TikTok/FB) cada
# INTERVAL_MINUTES, usando el CLI `claude` en modo headless con el servidor
# Browser MCP de este repo. El navegador con las sesiones abiertas y la extensión
# Browser MCP (botón Connect) deben estar activos en ESTA máquina.
#
# Uso:
#   ./scheduler.sh [minutos]      # p.ej. ./scheduler.sh 10   (default: 10)
#
# Variables de entorno opcionales:
#   REPO_DIR      Ruta del repo (default: dos niveles arriba de este script)
#   PROMPT_FILE   Prompt del asistente (default: ./prompt-asistente.md)
#   LOG_DIR       Carpeta de logs (default: ./logs)
#   RUN_TIMEOUT   Timeout por ronda en segundos (default: 600)
#
set -euo pipefail

INTERVAL_MINUTES="${1:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PROMPT_FILE="${PROMPT_FILE:-$SCRIPT_DIR/prompt-asistente.md}"
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
RUN_TIMEOUT="${RUN_TIMEOUT:-600}"

SERVER_ENTRY="$REPO_DIR/dist/index.js"
LOCK_FILE="$SCRIPT_DIR/.scheduler.lock"

# --- checks ------------------------------------------------------------------
command -v claude >/dev/null || { echo "ERROR: no se encontró el CLI 'claude' en el PATH."; exit 1; }
command -v node   >/dev/null || { echo "ERROR: no se encontró 'node' en el PATH."; exit 1; }
[ -f "$SERVER_ENTRY" ] || { echo "ERROR: falta $SERVER_ENTRY. Corré 'npm install && npm run build' en $REPO_DIR."; exit 1; }
[ -f "$PROMPT_FILE" ]  || { echo "ERROR: falta el prompt $PROMPT_FILE."; exit 1; }

mkdir -p "$LOG_DIR"

# Config MCP para el CLI, generada desde REPO_DIR (así solo configurás la ruta acá).
MCP_CONFIG="$(mktemp)"
cat > "$MCP_CONFIG" <<JSON
{ "mcpServers": { "browsermcp": { "command": "node", "args": ["$SERVER_ENTRY"] } } }
JSON
trap 'rm -f "$MCP_CONFIG"' EXIT

ROUND_INSTRUCTION="Revisá los mensajes directos, comentarios y respuestas a historias/videos SIN responder en Instagram, TikTok y Facebook (los canales de la sección 2 del prompt) y contestá SOLO lo pendiente siguiendo todas las reglas. No dupliques respuestas ya hechas por un humano. Al terminar, entregá el cierre de turno (sección 9): contestados, pendientes para humano, y números para PEDIDOS ONLINE. Respetá estrictamente las reglas de seguridad de la sección 8."

echo "Asistente Mood Mayorista — scheduler cada ${INTERVAL_MINUTES} min."
echo "Repo:   $REPO_DIR"
echo "Prompt: $PROMPT_FILE"
echo "Logs:   $LOG_DIR"
echo "Ctrl+C para detener."

ts() { date '+%Y-%m-%d %H:%M:%S'; }

run_round() {
  # Evita rondas superpuestas si una tarda más que el intervalo.
  if [ -f "$LOCK_FILE" ]; then
    echo "$(ts) ronda anterior aún en curso; salto esta."
    return
  fi
  : > "$LOCK_FILE"
  local log="$LOG_DIR/ronda-$(date +%Y%m%d-%H%M%S).log"
  echo "$(ts) iniciando ronda -> $log"

  # --allowedTools: permite solo las tools del navegador sin pedir confirmación.
  # --append-system-prompt: carga el prompt del asistente.
  timeout "$RUN_TIMEOUT" claude -p "$ROUND_INSTRUCTION" \
      --append-system-prompt "$(cat "$PROMPT_FILE")" \
      --mcp-config "$MCP_CONFIG" \
      --allowedTools "mcp__browsermcp__browser_navigate,mcp__browsermcp__browser_snapshot,mcp__browsermcp__browser_click,mcp__browsermcp__browser_type,mcp__browsermcp__browser_hover,mcp__browsermcp__browser_press_key,mcp__browsermcp__browser_wait,mcp__browsermcp__browser_select_option,mcp__browsermcp__browser_screenshot,mcp__browsermcp__browser_get_console_logs" \
      >"$log" 2>&1 \
    && echo "$(ts) ronda OK" \
    || echo "$(ts) ronda terminó con error/timeout (ver $log)"

  rm -f "$LOCK_FILE"
}

while true; do
  run_round
  sleep "$(( INTERVAL_MINUTES * 60 ))"
done
