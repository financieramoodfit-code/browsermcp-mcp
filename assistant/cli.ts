/**
 * CLI para probar el asistente de Mood Mayorista localmente, sin redes ni Meta.
 *
 * Uso:
 *   ANTHROPIC_API_KEY=... node dist-assistant/cli.js "¿precio de la 0008?"
 *
 * Imprime la respuesta que el asistente le daría al cliente y, si corresponde,
 * el número que habría que derivar al grupo PEDIDOS ONLINE.
 */

import { generarRespuesta } from "./reply.js";

async function main(): Promise<void> {
  const mensaje = process.argv.slice(2).join(" ").trim();
  if (!mensaje) {
    console.error('Uso: node dist-assistant/cli.js "tu mensaje de prueba"');
    process.exit(1);
  }
  const r = await generarRespuesta(mensaje);
  console.log("\n--- Respuesta al cliente ---\n");
  console.log(r.texto);
  if (r.derivarNumero) {
    console.log(`\n[interno] Derivar al grupo PEDIDOS ONLINE: ${r.derivarNumero}`);
  }
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
