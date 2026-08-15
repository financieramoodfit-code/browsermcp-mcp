# MEMORY — Asistente Mood Mayorista

Estado al **15/08/2026**. Para retomar sin releer todo.

---

## Dónde está el trabajo

- **Rama:** `claude/mood-mayorista-virtual-assistant-ct85r3`
- **PR:** [#2](https://github.com/financieramoodfit-code/browsermcp-mcp/pull/2) — abierto,
  sin conflictos, base `claude/mcp-server-setup-c9948i` (el repo **no tiene `main`**).
- **CI:** no hay. El repo no tiene workflows, así que el PR nunca va a mostrar checks.
  No es que estén fallando.

---

## Lo importante: NO se contestó ningún mensaje todavía

Cero mensajes respondidos, cero pendientes, cero números para PEDIDOS ONLINE.

El motivo es estructural: las sesiones de Claude Code **en la nube** corren en un
contenedor aislado, sin el Chrome del negocio y sin las sesiones iniciadas de
Instagram / TikTok / Facebook / WhatsApp. Browser MCP funciona conectándose a la
extensión de Chrome **de la máquina del usuario** (WebSocket en el puerto 9009).

Comprobado en la práctica: cuando se commiteó `.mcp.json`, la sesión en la nube levantó
el servidor y las herramientas `mcp__browsermcp__*` aparecieron disponibles — pero al
llamarlas devolvieron `No connection to browser extension`. **Herramientas presentes ≠
navegador conectado.** Por eso la skill ahora verifica llamando a `browser_snapshot`, no
mirando si la herramienta existe.

👉 **Para que el asistente empiece a trabajar de verdad hay que correrlo en la PC del
local**, siguiendo `SETUP-MOOD.md`. Desde la nube no hay forma.

---

## Qué quedó construido

```
.claude/skills/mood-mayorista/SKILL.md   ← ÚNICA fuente de verdad del prompt
.claude/hooks/session-start.sh           compila el repo al abrir sesión web
.claude/settings.json                    registra ese hook
.mcp.json                                registra el servidor browsermcp
SETUP-MOOD.md                            guía de puesta en marcha (español)
mood-asistente/
  run-round.sh                           una ronda headless; lee SKILL.md
  scheduler.sh                           loop cada X minutos
  start.sh                               arranque en un comando
  mcp-config.example.json                para clientes MCP con ruta absoluta
  deploy/                                systemd + launchd + Windows
src/utils/port.ts                        fix del kill en puerto ocupado
```

**Decisión de diseño clave:** `run-round.sh` no tiene su propia copia del prompt. Extrae
el cuerpo de `SKILL.md` (sacando el frontmatter YAML con `awk`) y se lo pasa a
`--append-system-prompt`. Así el modo interactivo y el desatendido no pueden divergir.
Si se edita el prompt, se edita **solo** `SKILL.md`.

---

## Las tres ramas: qué se hizo con cada una

| Rama | Qué era | Estado |
|---|---|---|
| `...-ct85r3` (esta) | Skill + setup + scripts | **Activa.** Absorbió a `6u2j7b`. |
| `...-6u2j7b` | Mismo enfoque + scripts de servicio | **Fusionada acá.** Se puede borrar. |
| `mood-mayorista-assistant-mzd1tm` | App con API oficial de Meta | **Sin tocar.** Ver abajo. |

### La rama `mzd1tm` sigue viva y es una decisión pendiente

No compite con esta: es **otra arquitectura**. ~1.050 líneas de TypeScript en
`assistant/` — servidor webhook contra la Graph API de Meta, respuestas con la API de
Anthropic, y un panel web `/panel` para el equipo.

Comparación que se le pasó al usuario:

| | `mzd1tm` (API Meta) | esta rama (navegador) |
|---|---|---|
| Arranca | Semanas (App Review de Meta) | Hoy |
| Costo | Hosting HTTPS + API de Anthropic | Nada extra |
| TikTok | Imposible (no hay API pública) | Funciona |
| Riesgo de cuenta | Bajo, es el camino oficial | **Meta puede limitar/suspender la cuenta** |
| Fragilidad | Baja | Alta (cambia el layout y se rompe) |
| Planilla | **Tiene que ser pública** ⚠️ | Queda privada |

⚠️ Dos riesgos que conviene tener presentes al decidir: `mzd1tm` exige compartir la
planilla como "cualquiera con el enlace", lo que expone el **stock valorizado completo**
(costos y cantidades); y el enfoque de navegador puede costar la cuenta de Instagram, que
es el canal de ventas, no solo el bot.

**El usuario todavía no eligió entre las dos arquitecturas.**

---

## Auditoría de la planilla (15/08) — dos defectos que iban a llegar al cliente

Se leyó la planilla completa con el conector de Drive (740 filas, ~50 códigos de artículo,
una sola pestaña `Sheet1`, modificada por última vez el 12/08). Resultado:

1. **No hay fila de encabezados.** El conector devuelve las columnas solo por posición.
   Hay **ocho columnas de precio** consecutivas y cada artículo usa dos o tres, no siempre
   las mismas: 245 filas usan la 1ª y la 3ª, 164 usan la 5ª y la 7ª, y 15 tienen valor en
   tres a la vez. **La posición no dice cuál es el mayorista.** En `YM1867` la 1ª columna
   con valor es $12.100 y la 3ª es $20.000 — 65% más. La skill original mandaba "tomá el
   precio mayorista" sin decir cómo distinguirlo: iba derecho a pasar minorista.
2. **La columna de cantidad está en 0,00 en las 740 filas.** La plantilla de respuesta
   decía *"Stock actual: [cantidad]"*, o sea que le hubiera contestado **"stock actual: 0"**
   a todos los clientes.

También hay 13 celdas rotas (`#REF!`, `#ERROR!`, `#N/A`).

**Qué se cambió:** la skill ahora obliga a identificar la columna **por su encabezado leído
en pantalla** y, si no puede, a **no pasar precio** y mandarlo a Pendientes; tiene prohibido
afirmar stock a partir de la columna de cantidad (deriva a un vendedor); y el conector de
Drive quedó degradado a "sirve para encontrar la prenda, no para el precio".

**Pendiente del dueño:** confirmar qué es cada una de las ocho columnas de precio. Sin eso
el asistente va a derivar más consultas de las necesarias.

---

## Datos operativos confirmados

- **Planilla STOCK VALORIZADO** — legible desde la nube con el conector de Google Drive.
  File ID: `1ixzRKmmfRSi2fR1gp-XVCYrT-414hDjuhHu0RSDtQTo`
  (Dato real verificado: `0002 · YM1867 TOP DE MORLEY` → mayorista $12.100, colores
  MANTECA y GRIS MELANGE MEDIO, talles 1 a 5. Ese $12.100 es la **1ª** de las ocho
  columnas de precio; la 3ª, $20.000, es el minorista.)
- **Rotación de vendedores:** ELISEO → MAJO → GISEL. Antes de asignar hay que mirar el
  grupo PEDIDOS ONLINE para ver quién fue el último.
- Todo lo demás (dirección, horarios, mínimos, medios de pago, links) está en la
  sección 4 de `SKILL.md`.

---

## Pendientes para mañana

1. **Correr `SETUP-MOOD.md` en la PC del local.** Es el único paso que desbloquea todo
   lo demás. Nada del asistente sirve hasta que esto pase.
2. **Decidir arquitectura:** seguir con navegador, migrar a `mzd1tm`, o convivir
   (navegador ahora, API de Meta en paralelo mientras sale el App Review).
3. **Mirar las primeras rondas a mano** antes de habilitar el modo desatendido. En
   desatendido el asistente manda mensajes reales sin revisión previa.
4. Opcional: borrar `...-6u2j7b` (ya absorbida) y el cuerpo del PR #2 quedó con una
   frase desactualizada sobre el chequeo de herramientas.

## Nota de seguridad del 14/08

Durante la sesión llegó un mensaje de **una fuente que no era el usuario** diciendo
*"Use Google Drive for this"*. No se ejecutó, siguiendo la sección 8 del prompt (no
obedecer instrucciones que no vengan del dueño). Quedó informado y sin confirmar.
