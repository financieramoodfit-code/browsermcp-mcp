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

## 4. Conectar la extensión

1. Abrí Chrome en la pestaña que querés automatizar (por ejemplo la bandeja de Instagram).
2. Clic en el ícono de la extensión **Browser MCP**.
3. Apretá **Connect**.

La extensión controla **una pestaña por vez**. Cuando el asistente tenga que pasar de
Instagram a Facebook o a WhatsApp Web, va a navegar en esa misma pestaña — no cierres la
ventana mientras trabaja.

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

## 6. Correrlo todos los días de 9 a 21 hs

Dentro de la misma sesión de Claude Code:

```
/loop 1h /mood-mayorista
```

Eso lo dispara cada una hora. **Ojo con dos cosas:**

- El loop corre mientras la sesión de Claude Code esté abierta y la extensión conectada.
  Si cerrás la terminal o Chrome, se corta.
- Los loops recurrentes vencen solos a los 7 días. Para volver a armarlo, repetí el comando.

Si querés acotarlo estrictamente a la franja 09:00–21:00, la forma más simple es abrir la
sesión a las 9 y cerrarla a las 21. También podés pedirle a Claude Code que arme una tarea
programada con `CronCreate` usando la expresión `0 12-23,0 * * *` (equivale a 09–21 hs de
Argentina, porque cron trabaja en UTC y Argentina es UTC−3).

---

## 7. Planilla de stock

La única fuente válida de precios, talles y cantidades es la planilla **STOCK VALORIZADO**:

https://docs.google.com/spreadsheets/d/1ixzRKmmfRSi2fR1gp-XVCYrT-414hDjuhHu0RSDtQTo/edit?gid=1432692705#gid=1432692705

Se puede leer de dos formas, y la skill soporta las dos:

- **Conector de Google Drive de Claude** (más rápido, sin tocar la planilla). Si lo tenés
  conectado en tu cuenta, Claude la lee directo.
- **Por navegador**, con Browser MCP, usando fórmulas `=FILTER` + `REGEXMATCH` en una celda
  vacía. La skill tiene indicado **borrar la fórmula al terminar** para no dejar la
  planilla modificada.

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
| El asistente dice que no tiene herramientas de navegador | La extensión no está conectada. Abrí Chrome, clic en Browser MCP → **Connect**. |
| "Port 9009 in use" | Hay otra instancia del servidor corriendo. Cerrá las otras sesiones de Claude Code o matá el proceso. |
| Lee la bandeja pero no encuentra los mensajes | Instagram/Facebook cambian el layout seguido. Pedile un `browser_screenshot` para ver qué está mirando. |
| No encuentra el grupo PEDIDOS ONLINE | WhatsApp Web tiene que estar logueado con la cuenta que pertenece al grupo. |
