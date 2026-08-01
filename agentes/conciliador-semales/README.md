# Agente Conciliador Semales

Concilia automáticamente la **planilla de remitos del local** (`Control_Remitos_SEMALEZ_BEYDE`)
contra la **planilla de la financiera** (`FERNANDO CHAVEZ`), detectando qué remitos fueron
efectivamente cobrados por Semales y cuáles no.

## Por qué código y no un prompt

La conciliación exige aritmética exacta (sumas de agrupaciones, subset-sum, detección de
duplicados y totales). Un modelo de lenguaje *estima* esos cálculos y aluce agrupaciones con
volúmenes grandes. Este motor los hace de forma **determinística y auditable**: los números
siempre cierran. El "criterio" (nombres difusos, casos dudosos) es lo único que queda para
revisión humana.

## Qué hace exactamente

1. Carga los remitos del local (Hoja 1; Hoja 2 se deduplica porque repite a Hoja 1).
2. Carga las transferencias de la financiera (hoja `AUTOMATIZACION`, columna `Monto`/`ARS`,
   `Fecha C`, titular), filtradas a la ventana temporal relevante.
3. Concilia en niveles, **sin reutilizar un comprobante ya usado**:
   - **Nivel 1** — 1 remito ↔ 1 comprobante (importe exacto + ventana de fecha + nombre).
   - **Nivel 2** — N remitos → 1 comprobante (varios pedidos del mismo cliente pagados juntos).
   - **Nivel 3** — 1 remito → N comprobantes (un pedido pagado en varias transferencias).
4. **Segundo cruce flexible**: para los remitos que el local marca como cobrados pero no
   concilian, busca en TODA la financiera por nombre parecido (ignora fecha e importe) y marca
   coincidencias exactas o casi-exactas (diferencias de redondeo).

### Reglas de negocio (configurables al inicio del script)

| Regla | Valor |
|---|---|
| Tolerancia de importe | **exacta** (0 pesos) |
| Ventana pedido → transferencia | **7 días** (`--ventana N` para cambiarla) |
| Agrupación máx. | 4 remitos/comprobantes |
| Umbral de nombre para confianza Alta | 0.72 |
| Reuso de comprobantes | **prohibido** |

## Salida — Excel con 6 hojas

1. **Resumen Ejecutivo** — totales, % conciliación, importe crítico.
2. **Conciliados** — con comprobante relacionado, tipo y nivel de confianza.
3. **Pendientes** — con motivo probable de cada uno.
4. **Comprobantes sin pedido** — transferencias de la financiera sin remito asociado.
5. **Diferencias** — remitos cobrados sin respaldo, duplicados, diferencias de importe.
6. **Revisión flexible** — candidatos por nombre para los remitos críticos.

## Uso

```bash
python conciliador.py <control_local.xlsx> <financiera.xlsx> [salida.xlsx] [--ventana 7]
```

Requiere `openpyxl` (`pip install openpyxl`).

## Herramientas que necesita el agente automático

- **Google Drive** (conector): leer las dos planillas y subir el resultado.
- **Python + openpyxl**: motor de conciliación.
- (Opcional) notificación push con el resumen de críticos.

## Fuentes de datos (Google Drive)

- Local: `Control_Remitos_SEMALEZ_BEYDE`
- Financiera: `FERNANDO CHAVEZ` (compartida por villagranmar@nexotuc.com)

> Las planillas nativas de Google Sheets se exportan a `.xlsx` antes de correr el script.
