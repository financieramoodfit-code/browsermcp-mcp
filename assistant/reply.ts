/**
 * Generación de respuestas del asistente de Mood Mayorista con Claude.
 *
 * Combina la persona/guía de la tienda (config.ts) con la ficha de stock
 * relevante a la consulta (stock.ts) y le pide a Claude una respuesta acorde.
 *
 * Requiere la variable de entorno ANTHROPIC_API_KEY (o un perfil de `ant auth login`).
 */

import Anthropic from "@anthropic-ai/sdk";

import { buildSystemPrompt, store } from "./config.js";
import { fetchProductos, fichaParaConsulta, type Producto } from "./stock.js";

const MODEL = process.env.MOOD_MODEL ?? "claude-opus-5";

const client = new Anthropic();

// Cache simple del stock para no descargar la planilla en cada mensaje.
let cacheProductos: { data: Producto[]; expira: number } | null = null;
const CACHE_MS = 5 * 60 * 1000; // 5 minutos

async function getProductos(now: number): Promise<Producto[]> {
  if (cacheProductos && cacheProductos.expira > now) return cacheProductos.data;
  const data = await fetchProductos();
  cacheProductos = { data, expira: now + CACHE_MS };
  return data;
}

export interface RespuestaAsistente {
  /** Texto listo para mostrar al cliente (sin la marca interna de derivación). */
  texto: string;
  /**
   * Si el cliente dejó su número, acá viene el número a reenviar al grupo
   * PEDIDOS ONLINE (extraído de la marca interna del modelo). null si no aplica.
   */
  derivarNumero: string | null;
}

/**
 * Genera la respuesta del asistente para un mensaje entrante del cliente.
 *
 * @param mensajeCliente  Texto del comentario / mensaje del cliente.
 * @param opts.nowMs      Timestamp actual en ms (inyectable para tests / entornos sin Date.now).
 */
export async function generarRespuesta(
  mensajeCliente: string,
  opts: { nowMs?: number } = {},
): Promise<RespuestaAsistente> {
  const now = opts.nowMs ?? Date.now();

  // 1) Buscar producto en el stock (si la consulta lo menciona).
  let fichaStock: string | undefined;
  try {
    const productos = await getProductos(now);
    const ficha = fichaParaConsulta(productos, mensajeCliente);
    if (ficha) fichaStock = ficha;
  } catch (err) {
    // Si la planilla no está disponible, seguimos sin ficha: el prompt le indica
    // al asistente ofrecer derivar con un vendedor en ese caso.
    console.error("[mood] No se pudo consultar el stock:", err);
  }

  // 2) Pedirle la respuesta a Claude con la persona + ficha.
  const message = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    system: buildSystemPrompt(fichaStock),
    messages: [{ role: "user", content: mensajeCliente }],
  });

  const textoBruto = message.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("")
    .trim();

  return limpiarRespuesta(textoBruto);
}

/**
 * Separa la marca interna [ENVIAR A PEDIDOS ONLINE: número XXX] del texto visible.
 * Devuelve el texto limpio y el número a derivar (si lo hubiera).
 */
export function limpiarRespuesta(texto: string): RespuestaAsistente {
  const marca = new RegExp(
    `\\[ENVIAR A ${store.grupoDerivacion}:\\s*(?:número\\s*)?([+\\d][\\d\\s().-]*)\\]`,
    "i",
  );
  const match = texto.match(marca);
  const derivarNumero = match ? match[1].trim() : null;
  const textoLimpio = texto.replace(marca, "").trim();
  return { texto: textoLimpio, derivarNumero };
}
