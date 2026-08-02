/**
 * Registro en memoria de las derivaciones pendientes: números de clientes que
 * hay que reenviar al grupo de WhatsApp PEDIDOS ONLINE.
 *
 * Es un almacén simple en memoria (se reinicia si se reinicia el servidor).
 * Lo comparten el webhook (que registra) y el panel interno (que lo muestra).
 */

export interface Derivacion {
  id: number;
  numero: string;
  origen: string; // ej "DM 12345", "comentario 999", "panel"
  fecha: string; // ISO 8601
  enviada: boolean;
}

export const derivacionesPendientes: Derivacion[] = [];

let contador = 0;

/**
 * Registra un número para derivar al grupo PEDIDOS ONLINE.
 * @param numero  Número del cliente (o null si no aplica; en ese caso no hace nada).
 * @param origen  De dónde vino (DM, comentario, panel).
 * @param fechaIso Fecha ISO (inyectable para tests / entornos sin Date).
 */
export function registrarDerivacion(
  numero: string | null,
  origen: string,
  fechaIso?: string,
): Derivacion | null {
  if (!numero) return null;
  const fecha = fechaIso ?? new Date().toISOString();
  const d: Derivacion = { id: ++contador, numero, origen, fecha, enviada: false };
  derivacionesPendientes.push(d);
  // El equipo humano toma este log y lo reenvía al grupo de WhatsApp PEDIDOS ONLINE.
  console.log(`[mood] >>> DERIVAR A PEDIDOS ONLINE: ${numero} (origen ${origen})`);
  return d;
}

/** Marca una derivación como ya enviada al grupo. Devuelve true si la encontró. */
export function marcarEnviada(id: number): boolean {
  const d = derivacionesPendientes.find((x) => x.id === id);
  if (!d) return false;
  d.enviada = true;
  return true;
}
