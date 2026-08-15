# Grupo "REDES SOCIALES" en Chrome

Todo lo que el asistente necesita abierto, en un grupo de pestañas con nombre.

## Armarlo (una sola vez, 30 segundos)

1. En Chrome: **Marcadores → Administrador de marcadores** (`Ctrl+Shift+O` / `⌘+⌥+B`).
2. Menú **⋮** (arriba a la derecha) → **Importar marcadores** → elegí
   [`REDES-SOCIALES.html`](./REDES-SOCIALES.html).
3. Va a aparecer una carpeta **REDES SOCIALES**.
4. **Clic derecho sobre la carpeta → "Abrir todo en un grupo de pestañas nuevo".**

Listo: el grupo queda creado, con ese nombre y con las 8 pestañas. De ahí en más lo abrís
igual, con dos clics.

> Chrome no deja crear grupos de pestañas desde la línea de comandos. Este es el único
> camino que produce un grupo **con nombre** sin instalar nada.

## Abrirlo rápido (sin grupo)

Si no te importa que estén agrupadas y solo querés las 8 pestañas abiertas:

```bash
bash mood-asistente/redes/abrir-redes.sh                 # macOS / Linux
```
```powershell
powershell -ExecutionPolicy Bypass -File mood-asistente\redes\abrir-redes.ps1   # Windows
```

## Qué se abre y para qué

| # | Pestaña | Para qué |
|---|---|---|
| 1 | Instagram — Mensajes | DMs y respuestas a historias |
| 2 | Instagram — Perfil | comentarios en publicaciones |
| 3 | TikTok — Mensajes | DMs |
| 4 | TikTok — Perfil | comentarios en videos |
| 5 | Facebook — Bandeja de la página | DMs y comentarios (Meta Business Suite) |
| 6 | Facebook — Página | comentarios en publicaciones |
| 7 | WhatsApp Web | grupo **PEDIDOS ONLINE** (derivaciones) |
| 8 | Planilla STOCK VALORIZADO | precios y talles |

## ⚠️ Cuál conectar a Browser MCP

**La extensión maneja una pestaña por vez.** Cuando el asistente pasa de Instagram a
WhatsApp, navega *dentro de esa misma pestaña* — o sea que si conectás una de las 8, te la
va a ir cambiando de sitio y el grupo queda desordenado.

Lo práctico:

- Abrí **una novena pestaña en blanco** y conectá la extensión ahí (ícono de Browser MCP →
  **Connect**). Esa es la pestaña de trabajo del asistente.
- Las 8 del grupo quedan como referencia tuya y, sobre todo, **mantienen las sesiones
  iniciadas**, que es lo que el asistente necesita para entrar.

## Antes de la primera ronda

Pasá por las 8 pestañas y confirmá que estás logueado en todas, en especial:

- **Facebook**: tiene que ser la cuenta con acceso a la página *MoodFitOficial*.
- **WhatsApp Web**: tiene que ser la cuenta que pertenece al grupo *PEDIDOS ONLINE*.

El asistente **nunca** se loguea solo ni pide credenciales: si una red está deslogueada, lo
reporta como pendiente y sigue con las otras.
