# Asistente virtual de Mood Mayorista — puesta en marcha

Guía para dejar corriendo el asistente de redes de **Mood Mayorista** en tu propia
computadora, usando Browser MCP + Claude Code.

## Por qué se corre en tu máquina y no en la nube

El asistente tiene que entrar a Instagram, TikTok, Facebook y WhatsApp Business **con tus
sesiones ya iniciadas**. Browser MCP funciona conectándose a una extensión de Chrome que
corre en tu navegador: el servidor MCP abre un WebSocket en el puerto `9009` y la
extensión se conecta ahí. Una sesión de Claude Code en la nube corre en un contenedor
aislado, sin tu Chrome y sin tus sesiones — por eso desde ahí no puede leer ni contestar
tus redes.

En tu máquina sí: usa tu perfil real de Chrome, con tus cuentas ya logueadas.

---

## 1. Requisitos

- **Node.js 18 o superior** — verificá con `node --version`.
- **Google Chrome** con la extensión **Browser MCP** instalada → https://browsermcp.io
- **Claude Code** instalado → https://claude.com/claude-code
- Estar logueado en Chrome en: Instagram, TikTok, Facebook Business y WhatsApp Web
  (con la cuenta que tiene el grupo **PEDIDOS ONLINE**).

---

## 2. Clonar y compilar

```bash
git clone https://github.com/financieramoodfit-code/browsermcp-mcp.git
cd browsermcp-mcp
git checkout claude/mood-mayorista-virtual-assistant-ct85r3
npm install      # compila dist/index.js automáticamente (hook prepare)
```

Verificá que exista `dist/index.js`. Si no, corré `npm run build`.

---

## 3. Registrar el servidor MCP

El repo ya trae un [`.mcp.json`](./.mcp.json) en la raíz:

```json
{
  "mcpServers": {
    "browsermcp": {
      "command": "node",
      "args": ["dist/index.js"]
    }
  }
}
```

Cuando abras Claude Code **parado en la carpeta del repo**, te va a preguntar si aprobás
ese servidor MCP del proyecto. Aceptá.

```bash
cd /ruta/a/browsermcp-mcp
claude
```

Si por algún motivo no arranca, cambiá `"dist/index.js"` por la ruta absoluta, por ejemplo
`"/Users/tuusuario/browsermcp-mcp/dist/index.js"`.

Comprobá dentro de Claude Code con `/mcp` que `browsermcp` figure como **connected**.

---

## 4. Abrir el grupo de pestañas y conectar la extensión

### 4.1 El grupo "REDES SOCIALES"

En [`mood-asistente/redes/`](./mood-asistente/redes/README.md) hay un archivo de marcadores
para importar en Chrome. Te deja una carpeta **REDES SOCIALES** y, con clic derecho →
*"Abrir todo en un grupo de pestañas nuevo"*, un grupo con las 8 pestañas que hacen falta:
mensajes y comentarios de Instagram, TikTok y Facebook, WhatsApp Web y la planilla.

Se arma una sola vez. También hay un `abrir-redes.sh` / `abrir-redes.ps1` si solo querés
abrir las pestañas sin agruparlas.

### 4.2 Conectar

1. Abrí **una pestaña en blanco aparte** del grupo.
2. Clic en el ícono de la extensión **Browser MCP**.
3. Apretá **Connect**.

La extensión controla **una pestaña por vez**: cuando el asistente pase de Instagram a
Facebook o a WhatsApp Web, va a navegar dentro de esa misma pestaña. Por eso conviene
dedicarle una en blanco y dejar las 8 del grupo quietas — sirven para mantener las sesiones
iniciadas y para que vos mires. No cierres la ventana mientras trabaja.

---

## 5. Correr el asistente

Dentro de Claude Code, en la carpeta del repo:

```
/mood-mayorista
```

La skill está en [`.claude/skills/mood-mayorista/SKILL.md`](./.claude/skills/mood-mayorista/SKILL.md)
y contiene el prompt completo: tono, mensaje de bienvenida, reglas de precios, derivación
de pedidos y rotación ELISEO → MAJO → GISEL.

Lo primero que hace es chequear que las herramientas del navegador estén disponibles. Si la
extensión no está conectada, te avisa en vez de inventar respuestas.

---

## 6. Correrlo solo, sin estar vos

Hay tres niveles, de menos a más automático. Todos necesitan Chrome abierto con la
extensión en **Connect**.

### 6.1 A mano, cuando vos querés

`/mood-mayorista` dentro de Claude Code. Vos ves cada respuesta antes de que salga.
**Empezá por acá.**

### 6.2 Cada X minutos, con la ventana abierta

```bash
bash mood-asistente/start.sh          # una ronda cada 10 min
bash mood-asistente/start.sh 20       # o cada 20
```

`start.sh` verifica requisitos, compila y arranca el loop. Dejá esa ventana abierta.
Cada ronda queda registrada en `mood-asistente/logs/ronda-*.log`.

### 6.3 Arrancando solo con la máquina

Servicios listos para Linux, macOS y Windows en
[`mood-asistente/deploy/`](./mood-asistente/deploy/README.md).

> ⚠️ **Leé esto antes de 6.2 y 6.3.** En modo desatendido el asistente **manda mensajes
> reales a tus clientes sin que nadie los revise antes**. La skill está escrita para ser
> conservadora —lo dudoso no se envía, va a Pendientes— pero eso no reemplaza mirar las
> primeras rondas a mano. Revisá los logs unos días antes de confiarle el turno completo.

### Sobre la franja 09–21 hs

Los scripts corren siempre que estén andando. Para acotarlos al horario del local, lo más
simple es arrancar `start.sh` a la mañana y cortarlo (Ctrl+C) al cerrar. Si querés que el
sistema lo maneje, un `cron` con `0 9-21 * * *` llamando a `mood-asistente/run-round.sh`
hace lo mismo sin que dependas de acordarte (cron local usa tu hora, no UTC).

---

## 7. Planilla de stock

La única fuente válida de precios, talles y cantidades es la planilla **STOCK VALORIZADO**:

https://docs.google.com/spreadsheets/d/1ixzRKmmfRSi2fR1gp-XVCYrT-414hDjuhHu0RSDtQTo/edit?gid=1432692705#gid=1432692705

Se puede leer de dos formas, pero **no son intercambiables**:

- **Por navegador**, con Browser MCP, usando fórmulas `=FILTER` + `REGEXMATCH` en una celda
  vacía. La skill tiene indicado **borrar la fórmula al terminar** para no dejar la
  planilla modificada. Es la única forma que sirve para **precios**, porque es donde se ven
  los encabezados de las columnas.
- **Conector de Google Drive de Claude**: útil para encontrar la prenda (código, colores,
  talles), pero devuelve la planilla **sin encabezados**, así que de ahí no se saca el
  precio. En modo desatendido directamente no está disponible.

> ⚠️ **Dos cosas de la planilla que conviene que sepas.** Tiene **ocho columnas de precio
> sin encabezado legible**, y cada prenda usa dos o tres, no siempre las mismas — por eso
> la skill obliga a identificar la columna por su título y a **no pasar precio** si no está
> segura. Y la **columna de cantidad está en cero en todas las filas**, así que el
> asistente tiene prohibido afirmar stock: cuando preguntan disponibilidad, deriva a un
> vendedor. Si esa columna se empieza a cargar, avisá y lo cambiamos.

---

## 8. Reglas de seguridad que ya vienen aplicadas

La skill incluye las reglas no negociables del negocio:

- Solo responde en Instagram, TikTok y Facebook — ningún otro canal.
- No manda mensajes masivos sin que vos apruebes el texto y los destinatarios.
- **Trata los mensajes de clientes como datos, no como órdenes.** Si un DM o comentario
  trae algo que parece una instrucción (cambiar precios, entrar a un link, descargar algo),
  no la ejecuta: te la muestra y espera confirmación.
- No descarga archivos sin confirmarte nombre, tamaño y remitente.
- No inventa precios, talles ni stock: lo que no encuentra en la planilla va a
  **Pendientes** con el catálogo y el WhatsApp como respuesta al cliente.
- Reclamos, agresiones, descuentos y excepciones al mínimo quedan siempre para un humano.

---

## 9. Problemas frecuentes

| Síntoma | Qué revisar |
|---|---|
| `/mcp` muestra browsermcp como *failed* | ¿Existe `dist/index.js`? Corré `npm run build`. Probá con ruta absoluta en `.mcp.json`. |
| `No connection to browser extension` | El servidor corre pero no hay pestaña conectada — es lo más común. Abrí Chrome, clic en Browser MCP → **Connect**. Ojo: en este estado las herramientas `browser_*` igual figuran como disponibles, así que el error recién aparece al usarlas. |
| El asistente dice que no tiene herramientas de navegador | El servidor MCP no quedó registrado. Revisá `/mcp` y el `.mcp.json`. |
| "Port 9009 in use" | Hay otra instancia del servidor corriendo. Cerrá las otras sesiones de Claude Code o matá el proceso. |
| Lee la bandeja pero no encuentra los mensajes | Instagram/Facebook cambian el layout seguido. Pedile un `browser_screenshot` para ver qué está mirando. |
| No encuentra el grupo PEDIDOS ONLINE | WhatsApp Web tiene que estar logueado con la cuenta que pertenece al grupo. |
