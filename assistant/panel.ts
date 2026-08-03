/**
 * Panel web interno para el equipo de Mood Mayorista.
 *
 * Sirve, en el mismo servidor que el webhook, rutas bajo /panel:
 *  - GET  /panel                     Página HTML del panel.
 *  - GET  /panel/derivaciones        JSON con las derivaciones (números a PEDIDOS ONLINE).
 *  - POST /panel/derivaciones/enviada { id }  Marca una derivación como enviada.
 *  - POST /panel/responder           { mensaje }  Genera una respuesta del asistente
 *                                    (para copiar/pegar en TikTok u otro canal sin API).
 *
 * Protección: si está seteada la variable PANEL_TOKEN, se exige ese token
 * (en la query `?token=` para la página, o en el header `x-panel-token` para las
 * llamadas JSON). Es un panel interno; usalo detrás de HTTPS.
 */

import type http from "node:http";

import { generarRespuesta } from "./reply.js";
import { derivacionesPendientes, marcarEnviada, registrarDerivacion } from "./derivaciones.js";

const PANEL_TOKEN = process.env.PANEL_TOKEN ?? "";

function autorizado(req: http.IncomingMessage, url: URL): boolean {
  if (!PANEL_TOKEN) return true; // sin token configurado, no se exige (solo para pruebas)
  const enQuery = url.searchParams.get("token");
  const enHeader = req.headers["x-panel-token"];
  return enQuery === PANEL_TOKEN || enHeader === PANEL_TOKEN;
}

function leerBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch {
        resolve({});
      }
    });
  });
}

function json(res: http.ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

/**
 * Maneja las rutas del panel. Devuelve true si la request fue del panel
 * (y ya se respondió), false si no le corresponde (para que siga otro handler).
 */
export async function manejarPanel(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  url: URL,
): Promise<boolean> {
  if (!url.pathname.startsWith("/panel")) return false;

  if (!autorizado(req, url)) {
    json(res, 401, { error: "No autorizado. Falta el token del panel." });
    return true;
  }

  // Página HTML
  if (req.method === "GET" && url.pathname === "/panel") {
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(paginaHtml(url.searchParams.get("token") ?? ""));
    return true;
  }

  // Listado de derivaciones
  if (req.method === "GET" && url.pathname === "/panel/derivaciones") {
    json(res, 200, { derivaciones: derivacionesPendientes });
    return true;
  }

  // Marcar una derivación como enviada
  if (req.method === "POST" && url.pathname === "/panel/derivaciones/enviada") {
    const body = await leerBody(req);
    const ok = marcarEnviada(Number(body.id));
    json(res, ok ? 200 : 404, { ok });
    return true;
  }

  // Generar respuesta para un mensaje (para copiar/pegar donde no hay API, ej. TikTok)
  if (req.method === "POST" && url.pathname === "/panel/responder") {
    const body = await leerBody(req);
    const mensaje = typeof body.mensaje === "string" ? body.mensaje.trim() : "";
    if (!mensaje) {
      json(res, 400, { error: "Falta el campo 'mensaje'." });
      return true;
    }
    try {
      const r = await generarRespuesta(mensaje);
      // Si el mensaje traía un número, lo registramos como derivación (origen: panel).
      if (r.derivarNumero) registrarDerivacion(r.derivarNumero, "panel");
      json(res, 200, { texto: r.texto, derivarNumero: r.derivarNumero });
    } catch (err) {
      console.error("[mood] Error generando respuesta en el panel:", err);
      json(res, 500, { error: "No se pudo generar la respuesta." });
    }
    return true;
  }

  json(res, 404, { error: "Ruta del panel no encontrada." });
  return true;
}

/** HTML del panel (autocontenido, sin dependencias externas). */
function paginaHtml(token: string): string {
  const tokenJs = JSON.stringify(token);
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel interno — Mood Mayorista</title>
<style>
  :root { --rosa: #d6336c; --bg: #faf7f8; --card: #fff; --borde: #eadfe3; --texto: #2b2b2b; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background: var(--bg); color: var(--texto); }
  header { background: var(--rosa); color: #fff; padding: 16px 20px; }
  header h1 { margin: 0; font-size: 18px; }
  main { max-width: 860px; margin: 0 auto; padding: 20px; display: grid; gap: 20px; }
  .card { background: var(--card); border: 1px solid var(--borde); border-radius: 12px; padding: 18px; }
  .card h2 { margin: 0 0 12px; font-size: 15px; }
  textarea { width: 100%; min-height: 90px; border: 1px solid var(--borde); border-radius: 8px;
             padding: 10px; font: inherit; resize: vertical; }
  button { background: var(--rosa); color: #fff; border: 0; border-radius: 8px; padding: 9px 14px;
           font: inherit; cursor: pointer; }
  button.sec { background: #fff; color: var(--rosa); border: 1px solid var(--rosa); }
  .resp { margin-top: 12px; white-space: pre-wrap; background: #fdf2f6; border: 1px solid var(--borde);
          border-radius: 8px; padding: 12px; display: none; }
  .fila { display: flex; align-items: center; justify-content: space-between; gap: 10px;
          padding: 10px 0; border-top: 1px solid var(--borde); }
  .fila:first-child { border-top: 0; }
  .fila.enviada { opacity: .5; }
  .num { font-weight: 600; }
  .meta { font-size: 12px; color: #777; }
  .vacio { color: #999; font-size: 14px; }
</style>
</head>
<body>
<header><h1>🛍️ Panel interno — Mood Mayorista</h1></header>
<main>
  <section class="card">
    <h2>Generar respuesta (WhatsApp Business, TikTok u otro canal manual)</h2>
    <p class="meta">Pegá el comentario o mensaje del cliente y obtené la respuesta lista para copiar y pegar.</p>
    <textarea id="msg" placeholder="Ej: ¿Cuánto sale la 0008? ¿qué talles tienen?"></textarea>
    <div style="margin-top:10px; display:flex; gap:8px;">
      <button id="gen">Generar respuesta</button>
      <button id="copiar" class="sec" style="display:none;">Copiar</button>
    </div>
    <div class="resp" id="resp"></div>
  </section>

  <section class="card">
    <h2>Derivaciones pendientes → PEDIDOS ONLINE</h2>
    <p class="meta">Números de clientes que pidieron que los contacten. Copiá y reenvialos al grupo.</p>
    <div id="lista"><p class="vacio">Cargando…</p></div>
  </section>
</main>
<script>
const TOKEN = ${tokenJs};
const headers = { "content-type": "application/json" };
if (TOKEN) headers["x-panel-token"] = TOKEN;

const $ = (id) => document.getElementById(id);

$("gen").onclick = async () => {
  const mensaje = $("msg").value.trim();
  if (!mensaje) return;
  $("gen").disabled = true; $("gen").textContent = "Generando…";
  try {
    const r = await fetch("/panel/responder", { method: "POST", headers, body: JSON.stringify({ mensaje }) });
    const data = await r.json();
    const resp = $("resp");
    if (data.error) { resp.textContent = "Error: " + data.error; }
    else {
      resp.textContent = data.texto + (data.derivarNumero ? "\\n\\n[interno] Nº a derivar: " + data.derivarNumero : "");
      $("copiar").style.display = "inline-block";
      $("copiar").onclick = () => navigator.clipboard.writeText(data.texto);
    }
    resp.style.display = "block";
    if (data.derivarNumero) cargarDerivaciones();
  } finally {
    $("gen").disabled = false; $("gen").textContent = "Generar respuesta";
  }
};

async function cargarDerivaciones() {
  const r = await fetch("/panel/derivaciones", { headers });
  const data = await r.json();
  const cont = $("lista");
  const items = (data.derivaciones || []);
  if (!items.length) { cont.innerHTML = '<p class="vacio">No hay derivaciones pendientes.</p>'; return; }
  cont.innerHTML = "";
  for (const d of items.slice().reverse()) {
    const fila = document.createElement("div");
    fila.className = "fila" + (d.enviada ? " enviada" : "");
    const info = document.createElement("div");
    info.innerHTML = '<div class="num">' + d.numero + '</div><div class="meta">' + d.origen + ' · ' + new Date(d.fecha).toLocaleString("es-AR") + '</div>';
    const acciones = document.createElement("div");
    const btnCopiar = document.createElement("button");
    btnCopiar.className = "sec"; btnCopiar.textContent = "Copiar Nº";
    btnCopiar.onclick = () => navigator.clipboard.writeText(d.numero);
    acciones.appendChild(btnCopiar);
    if (!d.enviada) {
      const btnHecho = document.createElement("button");
      btnHecho.style.marginLeft = "8px"; btnHecho.textContent = "Marcar enviada";
      btnHecho.onclick = async () => {
        await fetch("/panel/derivaciones/enviada", { method: "POST", headers, body: JSON.stringify({ id: d.id }) });
        cargarDerivaciones();
      };
      acciones.appendChild(btnHecho);
    }
    fila.appendChild(info); fila.appendChild(acciones);
    cont.appendChild(fila);
  }
}
cargarDerivaciones();
setInterval(cargarDerivaciones, 15000);
</script>
</body>
</html>`;
}
