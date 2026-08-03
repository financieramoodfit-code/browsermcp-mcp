#!/bin/bash
#
# Una (1) ronda del Asistente Virtual de Mood Mayorista.
#
# Corre el CLI `claude` en modo headless con el servidor Browser MCP de este repo
# para revisar y contestar lo pendiente en IG/TikTok/FB. Pensado para ser llamado:
#   - en loop por scheduler.sh, o
#   - por un servicio/tarea por intervalo (systemd timer, launchd, cron, Task
#     Scheduler de Windows).
#
# El navegador con las sesiones abiertas y la extensión Browser MCP (Connect)
# deben estar activos en ESTA máquina.
#
# Variables de entorno opcionales:
#   REPO_DIR      Ruta del repo (default: dos niveles arriba de este script)
#   PROMPT_FILE   Prompt del asistente (default: ./prompt-asistente.md)
#   LOG_DIR       Carpeta de logs (default: ./logs)
#   RUN_TIMEOUT   Timeout de la ronda en segundos (default: 600)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PROMPT_FILE="${PROMPT_FILE:-$SCRIPT_DIR/prompt-asistente.md}"
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
RUN_TIMEOUT="${RUN_TIMEOUT:-600}"

SERVER_ENTRY="$REPO_DIR/dist/index.js"
LOCK_FILE="$SCRIPT_DIR/.scheduler.lock"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

command -v claude >/dev/null || { echo "$(ts) ERROR: falta el CLI 'claude' en el PATH."; exit 1; }
command -v node   >/dev/null || { echo "$(ts) ERROR: falta 'node' en el PATH."; exit 1; }
[ -f "$SERVER_ENTRY" ] || { echo "$(ts) ERROR: falta $SERVER_ENTRY. Corré 'npm install && npm run build' en $REPO_DIR."; exit 1; }
[ -f "$PROMPT_FILE" ]  || { echo "$(ts) ERROR: falta el prompt $PROMPT_FILE."; exit 1; }

mkdir -p "$LOG_DIR"

# Evita rondas superpuestas si una tarda más que el intervalo.
if [ -f "$LOCK_FILE" ]; then
  echo "$(ts) ronda anterior aún en curso; salto esta."
  exit 0
fi
: > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# Config MCP generada al vuelo desde REPO_DIR.
MCP_CONFIG="$(mktemp)"
cat > "$MCP_CONFIG" <<JSON
{ "mcpServers": { "browsermcp": { "command": "node", "args": ["$SERVER_ENTRY"] } } }
JSON
trap 'rm -f "$LOCK_FILE" "$MCP_CONFIG"' EXIT

ROUND_INSTRUCTION="Revisá los mensajes directos, comentarios y respuestas a historias/videos SIN responder en Instagram, TikTok y Facebook (los canales de la sección 2 del prompt) y contestá SOLO lo pendiente siguiendo todas las reglas. No dupliques respuestas ya hechas por un humano. Al terminar, entregá el cierre de turno (sección 9): contestados, pendientes para humano, y números para PEDIDOS ONLINE. Respetá estrictamente las reglas de seguridad de la sección 8."

LOG="$LOG_DIR/ronda-$(date +%Y%m%d-%H%M%S).log"
echo "$(ts) iniciando ronda -> $LOG"

# --allowedTools: solo las tools del navegador, sin pedir confirmación.
# --append-system-prompt: carga el prompt del asistente.
if timeout "$RUN_TIMEOUT" claude -p "$ROUND_INSTRUCTION" \
      --append-system-prompt "$(cat "$PROMPT_FILE")" \
      --mcp-config "$MCP_CONFIG" \
      --allowedTools "mcp__browsermcp__browser_navigate,mcp__browsermcp__browser_snapshot,mcp__browsermcp__browser_click,mcp__browsermcp__browser_type,mcp__browsermcp__browser_hover,mcp__browsermcp__browser_press_key,mcp__browsermcp__browser_wait,mcp__browsermcp__browser_select_option,mcp__browsermcp__browser_screenshot,mcp__browsermcp__browser_get_console_logs" \
      >"$LOG" 2>&1; then
  echo "$(ts) ronda OK"
else
  echo "$(ts) ronda terminó con error/timeout (ver $LOG)"
fi
