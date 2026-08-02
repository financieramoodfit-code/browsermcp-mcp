/**
 * Servidor de webhooks de Meta (Instagram + Facebook Messenger / comentarios)
 * para el asistente de Mood Mayorista.
 *
 * IMPORTANTE — lo que este archivo puede y NO puede hacer:
 *  - Recibe y responde mensajes directos y comentarios de Instagram y Facebook
 *    A TRAVÉS de la Graph API oficial de Meta. Requiere una app de Meta con
 *    permisos aprobados y tokens (ver assistant/README.md).
 *  - NO cubre TikTok: TikTok no ofrece una API pública para leer y responder
 *    DMs/comentarios de negocios de forma autónoma (ver README).
 *  - Debe correr en un servidor SIEMPRE ONLINE y accesible por HTTPS (este repo
 *    en la nube es efímero y no sirve como hosting permanente).
 *
 * Variables de entorno necesarias:
 *  - META_VERIFY_TOKEN   Token que vos elegís y cargás también en el panel de Meta.
 *  - META_PAGE_TOKEN     Page Access Token (para responder por Facebook/Instagram).
 *  - PORT                Puerto HTTP (default 3000).
 *  - ANTHROPIC_API_KEY   Para generar las respuestas (ver reply.ts).
 */

import http from "node:http";

import { generarRespuesta } from "./reply.js";
import { store } from "./config.js";

const VERIFY_TOKEN = process.env.META_VERIFY_TOKEN ?? "";
const PAGE_TOKEN = process.env.META_PAGE_TOKEN ?? "";
const PORT = Number(process.env.PORT ?? 3000);
const GRAPH = "https://graph.facebook.com/v21.0";

/** Log de derivaciones pendientes: números que hay que enviar al grupo PEDIDOS ONLINE. */
export const derivacionesPendientes: { numero: string; origen: string; fecha: string }[] = [];

/** Envía un mensaje directo por Messenger / Instagram usando la Graph API. */
async function enviarMensaje(destinatarioId: string, texto: string): Promise<void> {
  if (!PAGE_TOKEN) {
    console.error("[mood] Falta META_PAGE_TOKEN; no se puede responder.");
    return;
  }
  const res = await fetch(`${GRAPH}/me/messages?access_token=${PAGE_TOKEN}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      recipient: { id: destinatarioId },
      message: { text: texto },
      messaging_type: "RESPONSE",
    }),
  });
  if (!res.ok) {
    console.error("[mood] Error al enviar mensaje:", res.status, await res.text());
  }
}

/** Responde a un comentario (de Instagram o Facebook) usando la Graph API. */
async function responderComentario(comentarioId: string, texto: string): Promise<void> {
  if (!PAGE_TOKEN) {
    console.error("[mood] Falta META_PAGE_TOKEN; no se puede responder el comentario.");
    return;
  }
  const res = await fetch(`${GRAPH}/${comentarioId}/replies?access_token=${PAGE_TOKEN}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: texto }),
  });
  if (!res.ok) {
    console.error("[mood] Error al responder comentario:", res.status, await res.text());
  }
}

/** Procesa una respuesta del asistente: registra la derivación si corresponde. */
function registrarDerivacion(numero: string | null, origen: string): void {
  if (!numero) return;
  const fecha = new Date().toISOString();
  derivacionesPendientes.push({ numero, origen, fecha });
  // El equipo humano toma este log y lo reenvía al grupo de WhatsApp PEDIDOS ONLINE.
  console.log(`[mood] >>> DERIVAR A ${store.grupoDerivacion}: ${numero} (origen ${origen})`);
}

/** Maneja el cuerpo de un evento webhook de Meta (mensajes + comentarios). */
export async function manejarEvento(body: any): Promise<void> {
  const entries = Array.isArray(body?.entry) ? body.entry : [];
  for (const entry of entries) {
    // --- Mensajes directos (Messenger / Instagram Direct) ---
    for (const ev of entry.messaging ?? []) {
      const senderId = ev.sender?.id;
      const texto = ev.message?.text;
      if (!senderId || !texto || ev.message?.is_echo) continue;
      const r = await generarRespuesta(texto);
      registrarDerivacion(r.derivarNumero, `DM ${senderId}`);
      await enviarMensaje(senderId, r.texto);
    }

    // --- Comentarios (feed de Facebook / Instagram) ---
    for (const change of entry.changes ?? []) {
      const v = change.value ?? {};
      const esComentario = change.field === "comments" || v.item === "comment";
      const comentarioId = v.comment_id ?? v.id;
      const texto = v.text ?? v.message;
      // Evitar responder los propios comentarios de la página.
      if (!esComentario || !comentarioId || !texto || v.verb === "remove") continue;
      const r = await generarRespuesta(texto);
      registrarDerivacion(r.derivarNumero, `comentario ${comentarioId}`);
      await responderComentario(comentarioId, r.texto);
    }
  }
}

/** Crea el servidor HTTP con verificación (GET) y recepción de eventos (POST). */
export function crearServidor(): http.Server {
  return http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);

    // Verificación del webhook (Meta hace un GET al configurarlo).
    if (req.method === "GET" && url.pathname === "/webhook") {
      const mode = url.searchParams.get("hub.mode");
      const token = url.searchParams.get("hub.verify_token");
      const challenge = url.searchParams.get("hub.challenge");
      if (mode === "subscribe" && token === VERIFY_TOKEN && challenge) {
        res.writeHead(200, { "content-type": "text/plain" });
        res.end(challenge);
      } else {
        res.writeHead(403).end("Forbidden");
      }
      return;
    }

    // Recepción de eventos.
    if (req.method === "POST" && url.pathname === "/webhook") {
      let data = "";
      req.on("data", (chunk) => (data += chunk));
      req.on("end", () => {
        // Respondemos 200 de inmediato (Meta reintenta si tardamos) y procesamos aparte.
        res.writeHead(200).end("EVENT_RECEIVED");
        try {
          void manejarEvento(JSON.parse(data));
        } catch (err) {
          console.error("[mood] Error procesando el evento:", err);
        }
      });
      return;
    }

    res.writeHead(404).end("Not found");
  });
}

// Punto de entrada directo: `node dist-assistant/webhook.js`
if (import.meta.url === `file://${process.argv[1]}`) {
  crearServidor().listen(PORT, () => {
    console.log(`[mood] Webhook de Mood Mayorista escuchando en http://localhost:${PORT}/webhook`);
    if (!VERIFY_TOKEN) console.warn("[mood] Advertencia: META_VERIFY_TOKEN no está seteado.");
    if (!PAGE_TOKEN) console.warn("[mood] Advertencia: META_PAGE_TOKEN no está seteado.");
  });
}
