# Asistente de Mood Mayorista

Núcleo del asistente virtual de **Mood Mayorista** (tienda de ropa mayorista):
responde consultas con la información de la tienda y con el **precio mayorista,
talles y stock** que lee de la planilla de Google Sheets, con el tono formal y
cordial de la marca. Genera las respuestas con Claude (API de Anthropic).

> **Leé esto primero — qué hace y qué NO hace.**
> Este código es el "cerebro" del asistente y un **conector para Instagram y
> Facebook** vía la API oficial de Meta. **No** es un sistema mágico que ya
> responde solo en todas tus redes: para funcionar en vivo necesita credenciales
> tuyas y un servidor siempre encendido (ver más abajo). Y **TikTok tiene una
> limitación real** que explicamos al final.

## Qué incluye

| Archivo | Qué hace |
|---|---|
| `config.ts` | Toda la info de la tienda (dirección, horarios, links, mínimos, medios de pago) y la "persona" del asistente. Editás acá y el resto lo toma solo. |
| `stock.ts` | Descarga la planilla de Google como CSV, la parsea y busca productos por código o descripción. Devuelve precio mayorista, talles y stock. |
| `reply.ts` | Combina la persona + la ficha de stock y le pide la respuesta a Claude. |
| `webhook.ts` | Servidor web que recibe mensajes/comentarios de Instagram y Facebook (Meta) y responde automáticamente. |
| `derivaciones.ts` | Registro en memoria de los números a derivar al grupo PEDIDOS ONLINE. |
| `panel.ts` | **Panel web interno** para el equipo: genera respuestas para copiar (TikTok) y muestra las derivaciones pendientes. |
| `cli.ts` | Para probar el asistente en tu compu, sin redes. |

## Cómo probarlo localmente (sin redes)

Es la forma más rápida de ver el asistente funcionando:

```bash
# 1) Instalar dependencias (desde la raíz del repo)
npm install

# 2) Compilar el asistente
npm run assistant:build

# 3) Configurar credenciales
cp assistant/.env.example .env   # y completá ANTHROPIC_API_KEY

# 4) Probar una consulta
export $(grep -v '^#' .env | xargs)   # carga las variables del .env
node dist-assistant/cli.js "¿Cuánto sale la 0008? ¿qué talles tienen?"
```

El asistente identifica el código `0008`, busca en la planilla y responde con el
precio mayorista, los talles y el stock disponible.

> **Importante sobre la planilla:** para que el asistente pueda leerla sin tus
> credenciales de Google, la hoja tiene que estar compartida como
> **"Cualquiera con el enlace: Lector"** (o publicada en la web). Si está
> privada, el asistente no verá el stock y ofrecerá derivar con un vendedor.

## Cómo ponerlo en vivo en Instagram y Facebook (lo que depende de vos)

El asistente responde por Instagram y Facebook a través de la **Graph API
oficial de Meta**. Esto **no** se puede activar desde este repositorio: hace
falta configurarlo en tu cuenta de Meta y hostear el servidor. Pasos:

1. **Cuentas de negocio:** una **Página de Facebook** + una cuenta de
   **Instagram Profesional** vinculada a esa página (Meta Business).
2. **App de Meta:** creá una app en developers.facebook.com con los productos
   *Messenger* e *Instagram*, y pedí los permisos
   `pages_messaging`, `instagram_manage_messages`, `pages_manage_engagement`
   (comentarios). Estos permisos requieren **App Review** de Meta.
3. **Tokens:** obtené el *Page Access Token* → cargalo como `META_PAGE_TOKEN`.
   Elegí un `META_VERIFY_TOKEN` (texto libre) y usalo también en el paso 5.
4. **Hosting:** subí este servidor a un lugar **siempre encendido y con HTTPS**
   (Render, Railway, Fly.io, un VPS, etc.). Este contenedor en la nube donde
   corre Claude Code es **efímero** y no sirve como hosting permanente.
5. **Webhook:** en el panel de Meta, configurá el webhook apuntando a
   `https://TU-DOMINIO/webhook`, con tu `META_VERIFY_TOKEN`, y suscribite a los
   eventos `messages` y `comments`.

Arranque del servidor una vez configurado:

```bash
npm run assistant:build
npm run assistant:start   # levanta el webhook en el PORT configurado
```

## Derivación de pedidos (grupo PEDIDOS ONLINE)

Cuando un cliente muestra intención de compra, el asistente le pide el número de
teléfono. Al recibirlo, deja registrada internamente una línea del tipo
`>>> DERIVAR A PEDIDOS ONLINE: <número>` en los logs (y en `derivacionesPendientes`).
El asistente **no** puede escribir solo en un grupo de WhatsApp; el equipo humano
toma ese registro y lo reenvía. Si querés automatizar ese último paso, se puede
integrar con la API de WhatsApp Cloud como mejora futura.

## Panel interno del equipo (`/panel`)

Una vez que el servidor está corriendo (`npm run assistant:start`), tu equipo
puede entrar a `https://TU-DOMINIO/panel?token=TU_PANEL_TOKEN` y:

- **Generar respuestas** pegando un comentario/mensaje del cliente (ideal para
  **WhatsApp Business** y **TikTok**, canales que se atienden a mano): el asistente
  arma la respuesta con precio, talles y stock, y hay un botón para **copiarla** y
  pegarla en el chat.
- **Ver las derivaciones pendientes**: la lista de números de clientes que
  pidieron ser contactados, con botón para **copiar el número** y marcarlo como
  **enviado** una vez que lo pasaron al grupo PEDIDOS ONLINE.

Protección: seteá `PANEL_TOKEN` en el `.env`. Si lo dejás vacío, el panel queda
sin protección (solo para pruebas locales). Servilo siempre detrás de HTTPS.

## TikTok — limitación real (importante)

**TikTok no ofrece una API pública que permita leer y responder DMs o
comentarios de forma autónoma** para la mayoría de los negocios. Su API de
contenido/mensajería es muy restringida y no está pensada para bots de atención
al cliente. Por eso el asistente **no** puede responder TikTok automáticamente
como sí lo hace con Instagram y Facebook. Opciones realistas:

- Atender TikTok de forma manual, o
- Usar el asistente para **generar** la respuesta (con `cli.ts` o una pantalla
  interna) y que una persona la copie y pegue en TikTok.

Preferimos decírtelo con claridad antes que prometer algo que la plataforma no
permite.

## Resumen honesto

- ✅ Cerebro del asistente: persona + consulta de stock + respuestas con Claude — **funciona y está probado**.
- ✅ Instagram y Facebook: **funciona**, pero necesita tu app de Meta, permisos aprobados, tokens y hosting.
- ⚠️ WhatsApp Business (app) y TikTok: se atienden **a mano** con ayuda del panel
  `/panel` (genera la respuesta con precio/talles/stock para copiar y pegar). No hay
  respuesta automática: WhatsApp Business (app) no tiene API abierta y TikTok tampoco.
  La respuesta automática por WhatsApp solo sería posible con la WhatsApp Cloud API.
- ⚠️ Grupo PEDIDOS ONLINE: el número queda registrado y visible en el panel para que una persona lo reenvíe.
- ✅ Panel interno `/panel`: para generar respuestas (WhatsApp Business, TikTok) y ver/gestionar derivaciones.
