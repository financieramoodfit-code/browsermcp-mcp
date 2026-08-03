/**
 * Lectura y consulta de la planilla de stock de Mood Mayorista.
 *
 * La planilla vive en Google Sheets. Para leerla sin credenciales, la hoja debe
 * estar compartida como "Cualquiera con el enlace: Lector" (o publicada en la web).
 * Se descarga en formato CSV con la URL de export de Google Sheets.
 *
 * Estructura de columnas (según la planilla actual):
 *   0 Artículo (código, ej "0001")
 *   1 Descripción (ej "YM31017 REMERA ALGODON CHICAS")
 *   2 Color (código de color, ej "10")
 *   3 Descripción color (ej "NEGRO")
 *   4 Talle (ej "1", "M", "L/XL")
 *   5 Cantidad (stock, formato AR "12,00")
 *   6 LISTA1 (precio mayorista, formato AR "10.900,00")
 *   7 Valorizado LISTA1
 */

export const SHEET_ID =
  process.env.MOOD_SHEET_ID ?? "17eSV6YSboUuJHSWa0A4B5Fzn32nYaHUZGk9KZBqbWek";
export const SHEET_GID = process.env.MOOD_SHEET_GID ?? "10888679";

export interface Variante {
  color: string; // descripción del color, ej "NEGRO"
  talle: string; // ej "1", "M"
  cantidad: number; // stock disponible
}

export interface Producto {
  codigo: string; // "Artículo", ej "0001"
  descripcion: string; // ej "YM31017 REMERA ALGODON CHICAS"
  precioMayorista: number; // LISTA1
  variantes: Variante[];
}

/** Convierte un número en formato argentino ("10.900,00" / "12,00") a Number. */
export function parseNumeroAR(raw: string): number {
  const limpio = (raw ?? "").trim();
  if (!limpio) return 0;
  const normalizado = limpio.replace(/\./g, "").replace(",", ".");
  const n = Number(normalizado);
  return Number.isFinite(n) ? n : 0;
}

/** Parser CSV que respeta comillas dobles (Google exporta con comillas los campos con comas). */
export function parseCSV(texto: string): string[][] {
  const filas: string[][] = [];
  let campo = "";
  let fila: string[] = [];
  let enComillas = false;

  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (enComillas) {
      if (c === '"') {
        if (texto[i + 1] === '"') {
          campo += '"';
          i++;
        } else {
          enComillas = false;
        }
      } else {
        campo += c;
      }
    } else if (c === '"') {
      enComillas = true;
    } else if (c === ",") {
      fila.push(campo);
      campo = "";
    } else if (c === "\n") {
      fila.push(campo);
      filas.push(fila);
      fila = [];
      campo = "";
    } else if (c === "\r") {
      // ignorar
    } else {
      campo += c;
    }
  }
  if (campo.length > 0 || fila.length > 0) {
    fila.push(campo);
    filas.push(fila);
  }
  return filas;
}

/** Agrupa las filas de la planilla en productos por código de Artículo. */
export function parseProductos(filas: string[][]): Producto[] {
  const porCodigo = new Map<string, Producto>();

  for (const fila of filas) {
    const codigo = (fila[0] ?? "").trim();
    const descripcion = (fila[1] ?? "").trim();
    // Filas de encabezado o vacías: sin código numérico o con el título de columnas.
    if (!codigo || !/^\d+$/.test(codigo)) continue;

    let prod = porCodigo.get(codigo);
    if (!prod) {
      prod = { codigo, descripcion, precioMayorista: 0, variantes: [] };
      porCodigo.set(codigo, prod);
    }
    if (!prod.descripcion && descripcion) prod.descripcion = descripcion;

    const precio = parseNumeroAR(fila[6] ?? "");
    if (precio > prod.precioMayorista) prod.precioMayorista = precio;

    const colorDesc = (fila[3] ?? "").trim();
    const talle = (fila[4] ?? "").trim();
    const cantidad = parseNumeroAR(fila[5] ?? "");
    // Solo consideramos variantes reales (con talle). Las filas "resumen" no lo tienen.
    if (talle) {
      prod.variantes.push({ color: colorDesc || "SIN COLOR", talle, cantidad });
    }
  }

  return [...porCodigo.values()];
}

/** Descarga la planilla como CSV y devuelve la lista de productos. */
export async function fetchProductos(
  sheetId: string = SHEET_ID,
  gid: string = SHEET_GID,
): Promise<Producto[]> {
  const url = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=${gid}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(
      `No se pudo leer la planilla (HTTP ${res.status}). ` +
        `Verificá que esté compartida como "Cualquiera con el enlace: Lector".`,
    );
  }
  const csv = await res.text();
  return parseProductos(parseCSV(csv));
}

/** Normaliza texto para búsquedas (sin acentos, minúsculas). */
function norm(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();
}

/**
 * Busca productos por código de Artículo, por código interno de la descripción
 * (ej "YM31017", "1621") o por palabras de la descripción (ej "remera algodon").
 */
export function buscarProductos(productos: Producto[], consulta: string): Producto[] {
  const q = norm(consulta);
  if (!q) return [];

  // 1) Coincidencia exacta por código de Artículo (con o sin ceros a la izquierda).
  const qNum = q.replace(/^0+/, "");
  const porArticulo = productos.filter((p) => {
    const cod = norm(p.codigo);
    return cod === q || cod.replace(/^0+/, "") === qNum;
  });
  if (porArticulo.length) return porArticulo;

  // 2) El código interno / palabras aparecen en la descripción.
  const tokens = q.split(/\s+/).filter((t) => t.length >= 2);
  if (!tokens.length) return [];
  return productos.filter((p) => {
    const d = norm(p.descripcion);
    return tokens.every((t) => d.includes(t));
  });
}

/** Arma una ficha de texto de un producto para inyectar en el prompt del asistente. */
export function fichaProducto(p: Producto): string {
  const disponibles = p.variantes.filter((v) => v.cantidad > 0);
  const precio = p.precioMayorista
    ? `$${p.precioMayorista.toLocaleString("es-AR")}`
    : "sin precio cargado";

  const lineas: string[] = [
    `Código ${p.codigo} — ${p.descripcion}`,
    `Precio mayorista: ${precio}`,
  ];

  if (!disponibles.length) {
    lineas.push("Stock: sin unidades disponibles en este momento.");
  } else {
    const porColor = new Map<string, Variante[]>();
    for (const v of disponibles) {
      const arr = porColor.get(v.color) ?? [];
      arr.push(v);
      porColor.set(v.color, arr);
    }
    lineas.push("Stock disponible:");
    for (const [color, vs] of porColor) {
      const detalle = vs
        .sort((a, b) => a.talle.localeCompare(b.talle))
        .map((v) => `talle ${v.talle}: ${v.cantidad}`)
        .join(", ");
      lineas.push(`- ${color}: ${detalle}`);
    }
  }
  return lineas.join("\n");
}

/** Ficha combinada para una consulta (puede devolver varios productos). */
export function fichaParaConsulta(productos: Producto[], consulta: string): string {
  const encontrados = buscarProductos(productos, consulta).slice(0, 3);
  if (!encontrados.length) return "";
  return encontrados.map(fichaProducto).join("\n\n");
}
