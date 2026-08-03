# Asistente Virtual de Mood Mayorista — Guía de setup (modo automático)

Esta guía explica cómo dejar funcionando el asistente virtual que **lee y contesta
en tus redes** (Instagram, TikTok, Facebook) usando **Browser MCP** (este repo) y
**tu navegador ya logueado**, con los precios/stock salidos de tu planilla de Google
Sheets.

> ⚠️ **Importante — dónde corre esto**
> Todo esto se instala y corre **en una computadora tuya** (tu PC/Mac) con el
> navegador donde tenés abiertas las sesiones de IG/TikTok/FB. **No** funciona
> desde una sesión en la nube: el navegador y el servidor tienen que estar en la
> misma máquina.

---

## 1. Cómo encajan las piezas

```
┌─────────────────────┐     ┌──────────────────────┐     ┌───────────────────┐
│  Cliente de IA      │◄───►│  Browser MCP server  │◄───►│  Extensión Chrome │
│  (el "cerebro":     │ MCP │  (ESTE repo,         │ WS  │  Browser MCP      │
│   corre el PROMPT)  │     │   dist/index.js)     │9009 │  (botón Connect)  │
└─────────┬───────────┘     └──────────────────────┘     └─────────┬─────────┘
          │                                                        │
          │ lee stock                                              ▼
          ▼                                              Tu navegador logueado
   Google Sheets (StockValorizado.XLS)                  en IG / TikTok / Facebook
```

- **Cliente de IA** (Claude Desktop, Cursor, VS Code, etc.): es quien "piensa".
  Le cargás el prompt del asistente (ver `prompt-asistente.md`) y él decide qué
  hacer.
- **Browser MCP server** (este repo): traduce las decisiones del cliente en
  acciones de navegador. Expone estas herramientas: `browser_navigate`,
  `browser_click`, `browser_type`, `browser_hover`, `browser_snapshot`,
  `browser_screenshot`, `browser_press_key`, `browser_wait`,
  `browser_select_option`, `browser_get_console_logs`.
- **Extensión de Chrome**: conecta la pestaña que vos elegís al servidor. Usa tu
  sesión real (quedás logueado), por eso puede leer DMs y comentarios.
- **Google Sheets**: fuente única de precios/talles/stock.

---

## 2. Requisitos

- Node.js 18+ (probado con v22).
- Google Chrome (o Chromium) con las sesiones de IG/TikTok/FB **iniciadas**.
- La extensión **Browser MCP** desde https://browsermcp.io.
- Un cliente de IA que soporte MCP (Claude Desktop es el más simple).

---

## 3. Paso a paso

### Paso 1 — Compilar el servidor (este repo)

```bash
npm install      # instala dependencias y compila dist/ (hook prepare)
npm run build    # (re)compila dist/index.js
node dist/index.js   # prueba: debe quedar corriendo y abrir el WS en :9009
```

Si arranca sin errores y se queda "colgado" esperando, está OK (cortá con
`Ctrl+C`). El servidor habla MCP por *stdio* y abre un WebSocket en el puerto
**9009** para la extensión.

### Paso 2 — Instalar y conectar la extensión

1. Instalá la extensión **Browser MCP** en Chrome.
2. Abrí la pestaña que querés automatizar (por ejemplo Instagram).
3. Hacé clic en el ícono de la extensión y presioná **Connect**.

### Paso 3 — Registrar el servidor en tu cliente de IA

Usá el archivo `mcp-config.example.json` de esta carpeta como base. Para
**Claude Desktop**, el archivo de configuración vive en:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Contenido (reemplazá la ruta por la ruta absoluta real de tu `dist/index.js`):

```json
{
  "mcpServers": {
    "browsermcp": {
      "command": "node",
      "args": ["/ruta/absoluta/a/browsermcp-mcp/dist/index.js"]
    }
  }
}
```

Reiniciá el cliente para que tome la config.

### Paso 4 — Cargar el prompt y el acceso al stock

1. Pegá el contenido de `prompt-asistente.md` como *system prompt* / instrucciones
   del proyecto en tu cliente de IA.
2. Dale al cliente acceso a la planilla de stock. Dos opciones:
   - **Conector de Google Drive/Sheets** (recomendado): el cliente lee
     `StockValorizado.XLS` directo.
   - **Sin conector**: dejá una pestaña con la planilla abierta y que el
     asistente la lea vía `browser_snapshot`. Es más frágil.

### Paso 5 — Correr una "ronda"

El asistente **no** es un bot 24/7 por sí solo: es una herramienta que el cliente
maneja cuando vos (o un temporizador) se lo pedís. Para una ronda, pedile algo como:

> "Revisá los DMs y comentarios sin responder en Instagram, TikTok y Facebook, y
> contestá según el prompt. Al final dame el cierre de turno."

Para que corra solo cada X minutos, usá el scheduler incluido (Paso 6).

### Paso 6 — Correr solo cada X minutos (scheduler)

En esta carpeta hay un script, `scheduler.sh`, que dispara una ronda cada X
minutos usando el CLI `claude` en modo *headless* con este mismo servidor Browser
MCP. Requisitos: tener instalado el CLI `claude`, el repo compilado (`dist/`), y
el navegador + extensión **Connected**.

```bash
cd docs/asistente-mood-mayorista
./scheduler.sh 10      # una ronda cada 10 minutos (default: 10)
```

Qué hace en cada ronda:

- Genera al vuelo la config MCP apuntando a `dist/index.js` (solo configurás
  `REPO_DIR` si el repo está en otro lado).
- Corre `claude -p` con el prompt del asistente (`--append-system-prompt`) y le
  permite solo las herramientas `browser_*` (`--allowedTools`), sin pedir
  confirmación por cada acción.
- Usa un *lock* para no superponer rondas, aplica un timeout por ronda
  (`RUN_TIMEOUT`, default 600 s) y deja un log por ronda en `logs/`.

Variables opcionales: `REPO_DIR`, `PROMPT_FILE`, `LOG_DIR`, `RUN_TIMEOUT`.

**Alternativa con cron** (en vez de dejar el script en loop). Ejemplo, cada 10
minutos, corriendo una sola ronda por disparo (`INTERVAL` no aplica acá; el script
haría loop, así que para cron conviene llamar directo a `claude`):

```cron
*/10 * * * * cd /ruta/al/repo && \
  claude -p "Revisá y contestá lo pendiente en IG/TikTok/FB según el prompt; dame el cierre de turno." \
    --append-system-prompt "$(cat docs/asistente-mood-mayorista/prompt-asistente.md)" \
    --mcp-config docs/asistente-mood-mayorista/mcp-config.example.json \
    --allowedTools "mcp__browsermcp__browser_navigate,mcp__browsermcp__browser_snapshot,mcp__browsermcp__browser_click,mcp__browsermcp__browser_type" \
    >> docs/asistente-mood-mayorista/logs/cron.log 2>&1
```

> Nota: en `mcp-config.example.json` reemplazá la ruta placeholder por la ruta
> absoluta real de tu `dist/index.js` antes de usarlo con cron.

> ⚠️ Acceso al stock en modo headless: el conector de Google Sheets suele
> requerir login interactivo y puede no estar disponible en `claude -p`. Si es tu
> caso, dejá que el asistente lea la planilla abriéndola en el navegador
> (`browser_navigate` + `browser_snapshot`) o registrá un MCP de Sheets no
> interactivo.

### Setup del repo en Claude Code on the web (SessionStart hook)

Si además usás **Claude Code on the web** sobre este repo, ya está configurado un
*SessionStart hook* (`.claude/hooks/session-start.sh` + `.claude/settings.json`)
que, al iniciar cada sesión remota, corre `npm install` + `npm run build` para que
el proyecto quede compilado y listo. Es sincrónico (garantiza deps antes de
arrancar; se puede pasar a async si preferís arranque más rápido). Corre solo en
el entorno web (`CLAUDE_CODE_REMOTE=true`); en local no hace nada.

---

## 4. Verificación rápida (checklist)

- [ ] `node dist/index.js` arranca sin error.
- [ ] La extensión muestra "Connected" en la pestaña.
- [ ] El cliente de IA lista las tools `browser_*`.
- [ ] Una prueba simple (`browser_navigate` a instagram.com + `browser_snapshot`)
      devuelve contenido.
- [ ] El asistente puede leer un precio real de la planilla (probá con el
      artículo `0001`, que debe dar precio mayorista **$10.900**).

---

## 5. Límites y riesgos (leelos antes de ponerlo en producción)

- **Términos de servicio**: automatizar acciones (responder, comentar) sobre IG/
  TikTok/FB puede violar sus ToS y derivar en límites o bloqueos de la cuenta.
  Empezá con volúmenes bajos y supervisado. Considerá las **APIs oficiales**
  (WhatsApp Business API, Instagram Graph API / Messenger) para algo formal y
  estable a largo plazo.
- **No es autónomo de fábrica**: necesita el cliente corriendo + (opcional) un
  scheduler. Si la PC se apaga o el navegador se desloguea, deja de andar.
- **Reglas de seguridad del prompt**: la sección 8 del prompt es clave —
  **no** ejecutar instrucciones que vengan dentro de comentarios/DMs, **no**
  mandar mensajes masivos sin tu confirmación, y derivar reclamos a humano. El
  cliente de IA debe respetarlas; revisá las primeras rondas a mano.
- **Stock en la planilla**: hoy la columna *Cantidad* aparece en 0 en las filas
  revisadas. Si el stock real no es 0, actualizá la planilla o revisá de qué
  columna/hoja debe leer el asistente antes de responderle "sin stock" a un
  cliente.

---

## 6. Troubleshooting

| Síntoma | Causa / solución |
| --- | --- |
| `Failed to kill process on port 9009` al arrancar | El server intenta liberar el puerto 9009 al inicio. Ya está corregido para no fallar cuando el puerto está libre o falta `lsof`. Si igual aparece, verificá que nada más use el 9009. |
| La extensión no conecta | Asegurate de que `node dist/index.js` esté corriendo y presioná **Connect** en la pestaña. |
| El cliente no ve las tools | Ruta absoluta mal puesta en la config, o falta reiniciar el cliente. |
| Lee precios inventados | El asistente no accedió a la planilla. Revisá el conector de Sheets o la pestaña con la planilla. |

---

## 7. Archivos de esta carpeta

- `README.md` — esta guía.
- `prompt-asistente.md` — el prompt completo del asistente, listo para pegar.
- `mcp-config.example.json` — config de ejemplo para el cliente de IA.
- `scheduler.sh` — dispara una ronda cada X minutos (modo headless con `claude`).

También en la raíz del repo:

- `.claude/hooks/session-start.sh` + `.claude/settings.json` — SessionStart hook
  que compila el repo al iniciar sesiones de Claude Code on the web.
