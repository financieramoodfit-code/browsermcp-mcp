#!/bin/bash
#
# Arranque en un solo paso del Asistente Virtual de Mood Mayorista (macOS/Linux).
#
# Qué hace: verifica requisitos, compila el repo si hace falta, y arranca el
# asistente en loop (una ronda cada 10 min). Dejá esta ventana abierta.
#
# Requisitos que NO puede instalar por vos (son con tu cuenta):
#   - Node.js 18+            -> https://nodejs.org
#   - CLI de Claude logueado -> npm i -g @anthropic-ai/claude-code  (y hacé login)
#   - Chrome con IG/TikTok/FB logueados + extensión Browser MCP en "Connect"
#     -> https://browsermcp.io
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
INTERVAL_MINUTES="${1:-10}"

say()  { printf "\n\033[1;36m%s\033[0m\n" "$*"; }
ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
bad()  { printf "  \033[1;31m✗\033[0m %s\n" "$*"; }

say "1/4  Verificando requisitos…"
missing=0
if command -v node >/dev/null; then ok "Node.js $(node --version)"; else bad "Falta Node.js → instalá desde https://nodejs.org"; missing=1; fi
if command -v claude >/dev/null; then ok "CLI claude $(claude --version 2>/dev/null | head -1)"; else bad "Falta el CLI de Claude → npm i -g @anthropic-ai/claude-code (y logueate)"; missing=1; fi
if [ "$missing" -ne 0 ]; then
  say "Instalá lo que falta arriba y volvé a correr este script."
  exit 1
fi

say "2/4  Instalando dependencias (solo la 1ª vez tarda un poco)…"
cd "$REPO_DIR"
npm install --no-audit --no-fund >/dev/null 2>&1 && ok "Dependencias listas"

say "3/4  Compilando…"
npm run build >/dev/null 2>&1 && ok "dist/index.js compilado"

say "4/4  Antes de arrancar, confirmá:"
cat <<'CHK'
  • Chrome abierto y logueado en Instagram / TikTok / Facebook.
  • Extensión Browser MCP instalada y con "Connect" presionado en una pestaña.
  • CLI de Claude ya logueado (probá:  claude --version).
CHK
printf "\n¿Todo listo? Arranca el asistente y queda contestando cada %s min. (Ctrl+C para frenar)\n" "$INTERVAL_MINUTES"
read -r -p "Enter para arrancar… " _ || true

exec "$SCRIPT_DIR/scheduler.sh" "$INTERVAL_MINUTES"
