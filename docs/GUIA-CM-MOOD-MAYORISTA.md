# Guía: CM Virtual de Mood Mayorista con Browser MCP

Esta guía explica cómo correr el asistente de atención (CM) en **tu propia
máquina**, usando este repo + la extensión de Chrome de Browser MCP.

> **Por qué en tu máquina y no en la nube:** Browser MCP no abre un navegador
> propio. Levanta un WebSocket en `localhost:9009` al que se conecta la extensión
> de Chrome, y opera **tu** navegador con **tu** perfil ya logueado. Una sesión
> de Claude Code en la nube corre en un contenedor aislado: tu Chrome no puede
> llegar a ese puerto. Por eso este flujo es exclusivamente local.

---

## 1. Requisitos

- **Node.js 18+** (probado con v22.22.2) y npm.
- **Google Chrome** con la [extensión Browser MCP](https://browsermcp.io).
- **Claude Code de escritorio o CLI** (no la versión web).
- Sesiones ya iniciadas en Chrome de: Instagram, Facebook, TikTok y WhatsApp Web
  (con la cuenta que administra Mood Mayorista).

## 2. Compilar el servidor

```bash
git clone <este-repo>
cd browsermcp-mcp
npm install      # el hook `prepare` compila dist/ automáticamente
```

Verificá que quedó bien:

```bash
npm run typecheck   # debe terminar sin errores
ls dist/index.js    # debe existir
```

## 3. Registrar el MCP en Claude Code

Desde la carpeta del repo:

```bash
claude mcp add browsermcp -- node "$(pwd)/dist/index.js"
```

O a mano, en la config de tu cliente MCP:

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

Reiniciá Claude Code y confirmá con `/mcp` que aparece `browsermcp` conectado.

## 4. Conectar la pestaña

1. Abrí en Chrome la pestaña que querés operar (ej. el inbox de Instagram).
2. Clic en el ícono de la extensión Browser MCP.
3. Clic en **Connect**.

Si Claude responde *"No connection to browser extension"*, es que no apretaste
Connect, o lo apretaste en otra pestaña.

## 5. Usar el asistente

El prompt operativo está en
[`.claude/skills/cm-mood-mayorista/SKILL.md`](../.claude/skills/cm-mood-mayorista/SKILL.md).
Como es una skill del repo, en Claude Code local lo invocás con:

```
/cm-mood-mayorista
```

Para la ronda diaria de 9 a 22 hs podés combinarlo con `/loop`:

```
/loop 1h /cm-mood-mayorista
```

> `/loop` no soporta ventanas horarias (solo intervalos), así que corta vos la
> ronda al final del día, o programalo con el cron de tu sistema operativo.

---

## Herramientas disponibles

El servidor expone 13 herramientas:

| Herramienta | Para qué |
|---|---|
| `browser_navigate` | Ir a una URL |
| `browser_go_back` / `browser_go_forward` | Historial |
| `browser_snapshot` | Árbol de accesibilidad de la página (la forma principal de "leer") |
| `browser_screenshot` | Captura visual |
| `browser_click` | Clic en un elemento |
| `browser_hover` | Pasar el mouse |
| `browser_type` | Escribir texto |
| `browser_select_option` | Elegir en un `<select>` |
| `browser_press_key` | Teclas (`PageDown`, `Enter`, `Escape`…) |
| `browser_drag` | Arrastrar |
| `browser_wait` | Esperar |
| `browser_get_console_logs` | Logs de consola |

---

## Limitaciones reales (leelas antes de confiar en esto)

**Una pestaña por vez.** `src/context.ts` guarda una sola conexión WebSocket
(`private _ws`). Cada vez que apretás Connect en otra pestaña, esa reemplaza a la
anterior. Para recorrer los 4 canales tenés que ir apretando Connect en cada uno
— no es un barrido automático desatendido.

**No hay herramienta de scroll.** No existe `browser_scroll`. Para bajar en una
lista de DMs hay que usar `browser_press_key` con `PageDown`, que en los feeds
virtualizados de Instagram y TikTok es poco confiable. Recuperar conversaciones
viejas es justamente lo más frágil de todo esto.

**Riesgo de bloqueo de cuenta.** Automatizar respuestas en Instagram, TikTok y
Facebook mediante navegación simulada va contra los términos de servicio de esas
plataformas. Browser MCP usa tu navegador real, lo que reduce la detección, pero
no la elimina. Estás arriesgando la cuenta comercial. Para producción sostenida,
el camino correcto es la Instagram Messaging API + Messenger Platform +
WhatsApp Business Cloud API. TikTok no tiene API pública de DMs.

**"Bandeja Cero" no es alcanzable de forma confiable.** Ninguna plataforma expone
un listado limpio de "todo lo no respondido histórico", y contestar DMs viejos en
masa dispara los filtros anti-spam de Meta. Tratá el objetivo como "todo lo
reciente y visible", no como una garantía.

**Supervisá antes de mandar.** La skill está configurada para mostrarte el texto
y esperar tu confirmación antes de publicar. No le saques ese freno hasta que
tengas varias rondas de resultados revisados a mano.

---

## Pendiente de resolver: stock

En la pestaña `gid=170561894` de la planilla, la columna **Cantidad está en 0,00
en todas las filas**. Mientras siga así, el asistente **no puede** responder
"Stock actual: [cantidad]" — tiene instrucción explícita de no inventarlo y de
omitir el dato. Si el stock real se lleva en otra pestaña o en otro archivo,
actualizá la sección correspondiente de la skill.
