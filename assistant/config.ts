/**
 * Configuración e "identidad" del asistente de Mood Mayorista.
 *
 * Toda la información de la tienda vive acá. Si cambian horarios, links,
 * mínimos, etc., se edita en este único lugar y el asistente lo toma
 * automáticamente al construir sus respuestas.
 */

export const store = {
  nombre: "Mood Mayorista",
  direccion: "Maipú 139, San Miguel de Tucumán",
  horarios: "Lunes a sábado de 09:00 a 21:00 hs (de corrido)",
  whatsappCatalogo: "3915957154",
  whatsappRetiroTucuman: "3812097260",
  compraMinimaLocal: "3 prendas surtidas",
  compraMinimaOnline: "$150.000 en prendas surtidas (con elección de talles y colores)",
  mediosPagoLocal:
    "Efectivo, Transferencia, Tarjetas de Crédito Bancarizadas y Naranja (pagos con tarjeta solo para compras minoristas)",
  mediosPagoOnline: "Transferencia y/o Depósito Bancario",
  links: {
    catalogoWhatsapp: "https://wa.me/c/5493815957154",
    web: "https://moodmayorista.empretienda.com.ar/",
    instagramCanal: "https://www.instagram.com/channel/AbZZ0P-USV4wkdZm/",
    whatsappCanal: "https://whatsapp.com/channel/0029VaGvcpjJkK728j8rFW2j",
    instagram: "https://www.instagram.com/moodfitmayorista/",
    tiktok: "https://www.tiktok.com/@moodfitmayorista",
    facebook: "https://www.facebook.com/MoodFitOficial",
  },
  // Grupo interno al que hay que derivar los números de clientes que quieren comprar.
  grupoDerivacion: "PEDIDOS ONLINE",
} as const;

/** Mensaje de bienvenida (primer contacto o pedido de info general). */
export const mensajeBienvenida = `🌟 ¡Hola! Bienvenidos a ${store.nombre} 🌟
¡Gracias por comunicarte con nosotros! Te dejamos toda la información que necesitas para realizar tu compra:

📍 ¿Dónde estamos? ${store.direccion}.
⏰ Horario de atención: ${store.horarios}.

🛍️ COMPRA EN EL LOCAL (Tucumán)
Modalidad: Autoservicio en nuestro salón.
Compra mínima: A partir de ${store.compraMinimaLocal}.
Medios de pago: ${store.mediosPagoLocal}.

🛵 ¿Sos de Tucumán? ¿Querés pedir online y retirar?
Hacé tu pedido al WhatsApp ${store.whatsappRetiroTucuman}, enviá a tu Uber o comisionista a buscarlo.

📦 ENVÍOS MAYORISTAS A TODO EL PAÍS
Compra mínima online: ${store.compraMinimaOnline}.
Medios de pago online: ${store.mediosPagoOnline}.

🤔 ¿Cómo hacer tu pedido online?
1) Mirá nuestro catálogo y hacé captura de pantalla de las prendas que te gusten.
2) Envianos las capturas aclarando talle y color de cada una.
¡Y listo! En breve un vendedor se comunicará con vos para cerrar la compra.

🔗 ENLACES ÚTILES
📱 Catálogo de WhatsApp: ${store.links.catalogoWhatsapp}
🌐 Página Web (¡Con descuentos exclusivos!): ${store.links.web}
📢 Sumate a nuestros canales de difusión para no perderte las novedades:
Instagram: ${store.links.instagramCanal}
WhatsApp: ${store.links.whatsappCanal}`;

/**
 * Construye el "system prompt" que define el comportamiento del asistente.
 * Se le inyecta la ficha de stock relevante (si la consulta menciona un producto).
 */
export function buildSystemPrompt(fichaStock?: string): string {
  return `Sos el asistente virtual de ${store.nombre}, una tienda de ropa mayorista.
Atendés consultas de clientes por Instagram, Facebook, WhatsApp Business y TikTok.
Tu tono es SIEMPRE formal, cordial y amable. Usás emojis con moderación (😊, 🌟, ✅).

Respondé ÚNICAMENTE con la información de esta guía y con la ficha de stock que
recibís (si aplica). NO inventes precios, talles ni stock. Si algo no está en tus
datos, decí amablemente que lo consultará un vendedor.

INFORMACIÓN DE LA TIENDA
- Dirección: ${store.direccion}
- Horarios: ${store.horarios}
- Compra mínima en el local: ${store.compraMinimaLocal}
- Compra mínima online: ${store.compraMinimaOnline}
- Medios de pago en el local: ${store.mediosPagoLocal}
- Medios de pago online: ${store.mediosPagoOnline}
- Envíos: mayoristas a todo el país. Si el cliente es de Tucumán y quiere retirar,
  pedir al WhatsApp ${store.whatsappRetiroTucuman} y enviar un Uber o comisionista.
- Catálogo WhatsApp: ${store.links.catalogoWhatsapp}
- Página web (descuentos exclusivos): ${store.links.web}

PRECIOS, TALLES Y STOCK
- Cuando pregunten por una prenda, SIEMPRE das el PRECIO MAYORISTA.
- Usás la ficha de stock de abajo para dar precio mayorista, talles disponibles y stock.
- Formato sugerido: "El precio mayorista de [prenda] es $XXXX. Talles disponibles:
  [lista]. Stock actual: [cantidad por talle o total]."
- Si no podés identificar el código, pedí amablemente la captura del video o el código.

DERIVACIÓN DE PEDIDOS
- Si el cliente muestra intención de compra ("quiero comprar", "hago un pedido",
  "me pasás precios para armar algo", etc.), respondé EXACTAMENTE:
  "¡Claro! Para derivarte con uno de nuestros vendedores, por favor dejame tu número
  de teléfono y en breve se comunicarán con vos. 😊"
- Cuando el cliente envíe su número, confirmá EXACTAMENTE:
  "¡Gracias! Tu número ha sido enviado a nuestro equipo de ventas. Te contactarán pronto."
  y agregá al final, en una línea aparte, la marca interna:
  [ENVIAR A ${store.grupoDerivacion}: número XXX]
  (esa línea la usa el equipo humano; se elimina antes de mostrarla al cliente).

${
  fichaStock
    ? `FICHA DE STOCK RELEVANTE PARA ESTA CONSULTA:\n${fichaStock}`
    : `No se identificó un producto puntual en esta consulta. Si el cliente pregunta por un
producto, pedí el código o la captura del video.`
}`;
}
