#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conciliador Semales <-> Control de Remitos
Motor deterministico: importes, fechas, agrupaciones y duplicados se calculan
con codigo (nunca se "estiman"). El resultado es 100% auditable.
"""
import openpyxl, datetime, re, unicodedata, difflib, sys
from itertools import combinations

# ---------------- CONFIG (reglas confirmadas por el usuario) ----------------
# Uso:  python conciliador.py <control_local.xlsx> <financiera.xlsx> [salida.xlsx]
import argparse
_ap = argparse.ArgumentParser(description="Conciliador Semales <-> Control de Remitos")
_ap.add_argument("local", nargs="?", default="1a1bff47-Control_Remitos_SEMALEZ_BEYDE.xlsx",
                 help="Planilla LOCAL de remitos (Control_Remitos_SEMALEZ_BEYDE)")
_ap.add_argument("financiera", nargs="?", default="7831b7e2-FERNANDO_CHAVEZ_10.xlsx",
                 help="Planilla de la FINANCIERA (FERNANDO CHAVEZ)")
_ap.add_argument("salida", nargs="?", default="CONCILIACION_SEMALES_resultado.xlsx",
                 help="Archivo Excel de salida")
_ap.add_argument("--ventana", type=int, default=7, help="Ventana de dias pedido->transferencia")
_args = _ap.parse_args()

LOCAL_FILE  = _args.local
FIN_FILE    = _args.financiera
OUT         = _args.salida
LOCAL_SHEET = "Hoja 1"
FIN_SHEET   = "AUTOMATIZACION"
VENTANA_DIAS = _args.ventana   # ventana pedido -> transferencia
IMPORTE_EXACTO = True     # tolerancia 0 (importe debe coincidir al peso)
MAX_GRUPO = 4             # tam. maximo de agrupacion N->1 o 1->N
SIM_ALTA = 0.72           # umbral de similitud de nombre para confianza Alta

# ---------------- utilidades ----------------
def _one_token(tok):
    """Parsea un token monetario respetando formato AR ('.'=miles ','=dec) y US (','=miles)."""
    lc, ld = tok.rfind(','), tok.rfind('.')
    last = max(lc, ld)
    if last != -1 and len(tok) - last - 1 in (1, 2):   # separador decimal
        ent = re.sub(r'\D', '', tok[:last]) or '0'
        return round(int(ent) + int(tok[last+1:].ljust(2, '0')[:2]) / 100)
    d = re.sub(r'\D', '', tok)
    return int(d) if d else None

def money_to_int(s):
    """Monto principal (primer token). Devuelve int en pesos."""
    if s is None: return None
    if isinstance(s,(int,float)): return int(round(s))
    m = re.search(r'\d[\d.,]*', str(s))
    return _one_token(m.group()) if m else None

def money_candidates(s):
    """Todos los montos >= 1000 que aparecen en el texto (para notas tipo
    '$446.768 ... = $433.968 cobrado')."""
    if s is None: return []
    if isinstance(s,(int,float)): return [int(round(s))]
    vals = []
    for tok in re.findall(r'\d[\d.,]*', str(s)):
        v = _one_token(tok)
        if v and v >= 1000: vals.append(v)
    return sorted(set(vals))

def norm_name(s):
    if not s: return ""
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode()
    s = re.sub(r'[^a-zA-Z ]',' ', s).lower()
    toks = sorted(t for t in s.split() if len(t) > 1)
    return " ".join(toks)

def name_sim(a, b):
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb: return 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jacc = len(ta & tb) / len(ta | tb) if (ta|tb) else 0
    return max(ratio, jacc)

def days_between(fa, fb):
    if not (isinstance(fa,datetime.datetime) and isinstance(fb,datetime.datetime)):
        return None
    return (fb.date() - fa.date()).days

def win_ok(rem_fecha, t_fecha):
    """True si el remito no tiene fecha (Hoja 2) o si cae dentro de la ventana."""
    if not isinstance(rem_fecha, datetime.datetime):
        return True
    d = days_between(rem_fecha, t_fecha)
    return d is not None and -3 <= d <= VENTANA_DIAS

# ---------------- cargar LOCAL (remitos) ----------------
def _mk(fila, origen, remito, cliente, imp_raw, fecha, estado, empresa):
    rem = int(remito) if isinstance(remito,(int,float)) else remito
    dni_like = isinstance(rem, int) and rem >= 1_000_000   # remito real ~5 digitos
    return dict(
        fila=fila, origen=origen, remito=rem, cliente=cliente,
        importe=money_to_int(imp_raw), importe_raw=imp_raw, cands=money_candidates(imp_raw),
        nota=bool(imp_raw and re.search(r'[a-zA-Z(]', str(imp_raw))),
        dni_like=dni_like, fecha=fecha, estado=str(estado or '').strip(),
        empresa=empresa, usado=False, match=None)

def load_local():
    wb = openpyxl.load_workbook(LOCAL_FILE, data_only=True)
    out = []
    # --- Hoja 1 (con encabezados y fecha/estado) ---
    ws = wb[LOCAL_SHEET]
    hdr = {c: ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)}
    col = {v:k for k,v in hdr.items() if v and str(v).strip()}
    fecha_col = col.get('Fecha/Hora', 1)   # col. A suele venir sin encabezado en la planilla real
    for r in range(2, ws.max_row+1):
        g = lambda name: ws.cell(row=r, column=col[name]).value if name in col else None
        if g('Importe') is None and g('N° Remito') is None: continue
        out.append(_mk(f"H1:{r}", 'Hoja1', g('N° Remito'), g('Cliente'),
                       g('Importe'), ws.cell(row=r, column=fecha_col).value, g('Estado Pago'), g('Empresa')))
    # --- Hoja 2: solo remitos que NO esten ya en Hoja 1 (evita duplicar) ---
    ya = {r['remito'] for r in out if isinstance(r['remito'], int)}
    if 'Hoja 2' in wb.sheetnames:
        ws2 = wb['Hoja 2']
        for r in range(1, ws2.max_row+1):
            rem = ws2.cell(row=r, column=1).value      # A remito
            cli = ws2.cell(row=r, column=2).value      # B cliente
            imp = ws2.cell(row=r, column=5).value      # E importe
            if rem is None and imp is None: continue
            rnum = int(rem) if isinstance(rem,(int,float)) else rem
            if rnum in ya: continue                    # ya analizado desde Hoja 1
            ya.add(rnum)
            out.append(_mk(f"H2:{r}", 'Hoja2', rem, cli, imp, None,
                           '(Hoja 2 - sin estado)', None))
    return out

# ---------------- cargar FINANCIERA (transferencias) ----------------
def load_fin(dmin, dmax):
    wb = openpyxl.load_workbook(FIN_FILE, data_only=True); ws = wb[FIN_SHEET]
    # header en fila 2: E=Monto, C=ARS, F=Fecha C, H=titular, I=planilla
    lo = dmin - datetime.timedelta(days=3)
    hi = dmax + datetime.timedelta(days=VENTANA_DIAS + 3)
    out = []
    for r in range(3, ws.max_row+1):
        monto = ws.cell(row=r,column=5).value      # E Monto
        ars   = ws.cell(row=r,column=3).value      # C ARS
        fecha = ws.cell(row=r,column=6).value      # F Fecha C
        tit   = ws.cell(row=r,column=8).value      # H titular
        plan  = ws.cell(row=r,column=9).value      # I planilla
        m = money_to_int(monto)
        if m is None or m <= 0: continue
        if not isinstance(fecha, datetime.datetime): continue
        if not (lo <= fecha <= hi): continue
        out.append(dict(
            fila=r, monto=m, ars=money_to_int(ars), fecha=fecha,
            titular=tit, planilla=plan, usado=False))
    return out

def load_fin_all():
    """Toda la planilla financiera (sin filtro de fecha) para el cruce flexible."""
    wb = openpyxl.load_workbook(FIN_FILE, data_only=True); ws = wb[FIN_SHEET]
    out = []
    for r in range(3, ws.max_row+1):
        m = money_to_int(ws.cell(row=r,column=5).value)
        fecha = ws.cell(row=r,column=6).value
        tit = ws.cell(row=r,column=8).value
        if m is None or m <= 0 or not tit: continue
        out.append(dict(fila=r, monto=m, ars=money_to_int(ws.cell(row=r,column=3).value),
                        fecha=fecha, titular=tit, planilla=ws.cell(row=r,column=9).value))
    return out

# ---------------- motor de conciliacion ----------------
def conciliar(local, fin):
    concs = []   # conciliaciones
    # ---- Nivel 1: 1 a 1 exacto (importe == monto/ars y |dias|<=ventana) ----
    for rem in local:
        if rem['usado'] or rem['importe'] is None: continue
        cset = set(rem['cands']) or {rem['importe']}
        sin_fecha = not isinstance(rem['fecha'], datetime.datetime)
        cand = []
        for i, t in enumerate(fin):
            if t['usado']: continue
            if t['monto'] not in cset and t['ars'] not in cset:
                continue
            if not win_ok(rem['fecha'], t['fecha']): continue
            sim = name_sim(rem['cliente'], t['titular'])
            if sin_fecha and sim < SIM_ALTA: continue   # sin fecha -> exijo nombre fuerte
            d = days_between(rem['fecha'], t['fecha'])
            cand.append((sim, -abs(d) if d is not None else -99, i, t))
        if cand:
            cand.sort(key=lambda x: (x[0], x[1], -x[2]), reverse=True)
            sim, _, _, t = cand[0]
            rem['usado'] = t['usado'] = True
            conf = 'Alta' if (sim >= SIM_ALTA and not sin_fecha) else 'Media'
            rem['match'] = 'N1'
            concs.append(dict(tipo='1 a 1', remitos=[rem], comps=[t],
                              monto=t['monto'], sim=sim, conf=conf))
    # ---- Nivel 2: N remitos -> 1 comprobante (mismo cliente) ----
    from collections import defaultdict
    grupos = defaultdict(list)
    for rem in local:
        if not rem['usado'] and rem['importe']:
            grupos[norm_name(rem['cliente'])].append(rem)
    for t in fin:
        if t['usado']: continue
        best = None
        for cli, rems in grupos.items():
            disp = [r for r in rems if not r['usado']]
            if len(disp) < 2: continue
            for k in range(2, min(MAX_GRUPO, len(disp))+1):
                for combo in combinations(disp, k):
                    if sum(r['importe'] for r in combo) != t['monto']: continue
                    if any(not win_ok(r['fecha'], t['fecha']) for r in combo): continue
                    sim = max(name_sim(r['cliente'], t['titular']) for r in combo)
                    if best is None or sim > best[0]:
                        best = (sim, combo)
        if best and best[0] >= 0.40:   # exige vínculo de nombre (evita sumas casuales)
            sim, combo = best
            t['usado'] = True
            for r in combo: r['usado'] = True; r['match'] = 'N2'
            conf = 'Alta' if sim >= SIM_ALTA else 'Media'
            concs.append(dict(tipo='varios pedidos -> un comprobante', remitos=list(combo),
                              comps=[t], monto=t['monto'], sim=sim, conf=conf))
    # ---- Nivel 3: 1 remito -> N comprobantes ----
    for rem in local:
        if rem['usado'] or not rem['importe']: continue
        # solo transferencias en ventana y de monto significativo (>=1000)
        disp = [t for t in fin if not t['usado'] and t['monto'] >= 1000
                and win_ok(rem['fecha'], t['fecha'])]
        found = None
        for k in range(2, min(MAX_GRUPO, len(disp))+1):
            for combo in combinations(disp, k):
                if sum(t['monto'] for t in combo) != rem['importe']: continue
                # exige que al menos UN titular coincida fuerte con el cliente
                if max(name_sim(rem['cliente'], t['titular']) for t in combo) >= SIM_ALTA:
                    found = combo; break
            if found: break
        if found:
            rem['usado'] = True; rem['match'] = 'N3'
            for t in found: t['usado'] = True
            sim = max(name_sim(rem['cliente'], t['titular']) for t in found)
            concs.append(dict(tipo='un pedido -> varios comprobantes', remitos=[rem],
                              comps=list(found), monto=rem['importe'], sim=sim, conf='Media'))
    return concs

# ---------------- motivo probable para pendientes ----------------
def motivo(rem, fin, local):
    est = rem['estado'].lower()
    if 'pendiente' in est:
        return ('Estado local = Pendiente de Pago (aun no cobrado)', 'Alta')
    # importe existe pero fuera de ventana?
    for t in fin:
        if t['usado']: continue
        if rem['importe'] in (t['monto'], t['ars']):
            d = days_between(rem['fecha'], t['fecha'])
            return (f'Importe coincide con transferencia de {t["titular"]} pero fuera de ventana ({d} dias) - revisar', 'Media')
    # nombre similar con otro importe?
    for t in fin:
        if t['usado']: continue
        if name_sim(rem['cliente'], t['titular']) >= SIM_ALTA:
            return (f'Cliente aparece con transferencia de ${t["monto"]:,} (difiere del remito) - posible diferencia de importe', 'Media')
    return ('No figura en planilla financiera - posible comprobante no enviado al grupo', 'Media')

# ==================== EJECUCION ====================
local = load_local()
fechas = [r['fecha'] for r in local if isinstance(r['fecha'], datetime.datetime)]
dmin, dmax = min(fechas), max(fechas)
fin = load_fin(dmin, dmax)
print(f"Remitos locales: {len(local)} | Transferencias financiera en ventana: {len(fin)}")
print(f"Ventana de fechas: {dmin.date()} .. {dmax.date()} (+{VENTANA_DIAS}d)")

concs = conciliar(local, fin)

pend = [r for r in local if not r['usado']]
comp_sin = [t for t in fin if not t['usado']]

tot_conc = sum(c['monto'] for c in concs)
tot_pend = sum(r['importe'] or 0 for r in pend)
print(f"\n=== RESULTADO ===")
print(f"Conciliados: {len(concs)} conciliaciones ({sum(len(c['remitos']) for c in concs)} remitos) | ${tot_conc:,}")
print(f"  - 1 a 1: {sum(1 for c in concs if c['tipo']=='1 a 1')}")
print(f"  - N->1 : {sum(1 for c in concs if 'varios pedidos' in c['tipo'])}")
print(f"  - 1->N : {sum(1 for c in concs if 'un pedido' in c['tipo'])}")
print(f"Pendientes (remitos sin conciliar): {len(pend)} | ${tot_pend:,}")
print(f"Comprobantes sin pedido: {len(comp_sin)}")
rem_tot = sum(len(c['remitos']) for c in concs) + len(pend)
print(f"% conciliacion (remitos): {100*sum(len(c['remitos']) for c in concs)/rem_tot:.1f}%")

# ---------------- diferencias y duplicados ----------------
for r in pend:
    r['motivo'], r['motivo_conf'] = motivo(r, fin, local)

# duplicados de remito (mismo N°)
from collections import defaultdict
byrem = defaultdict(list)
for r in local:
    if r['remito'] is not None: byrem[r['remito']].append(r)
rem_dups = {k: v for k, v in byrem.items() if len(v) > 1}
# duplicados de comprobante (mismo titular+monto+fecha)
bycomp = defaultdict(list)
for t in fin:
    bycomp[(norm_name(t['titular']), t['monto'], t['fecha'].date())].append(t)
comp_dups = {k: v for k, v in bycomp.items() if len(v) > 1}

# diferencias destacadas
difs = []
for r in pend:
    est = r['estado'].lower()
    cobrado = ('pag' in est or 'recib' in est) and 'pendiente' not in est
    if cobrado:
        difs.append(('Local dice COBRADO pero NO figura en financiera', r,
                     'Posible comprobante no enviado al grupo o no cargado por la financiera'))
    else:
        for t in fin:
            if t['usado']: continue
            if name_sim(r['cliente'], t['titular']) >= SIM_ALTA and t['monto'] not in set(r['cands']):
                difs.append(('Nombre coincide con importe distinto', r,
                             f'Financiera tiene ${t["monto"]:,} de {t["titular"]} (remito ${r["importe"]:,})'))
                break

# ---------------- SEGUNDO CRUCE FLEXIBLE (solo criticos) ----------------
# Criticos = local dice cobrado pero no concilio. Busca en TODA la financiera
# por nombre parecido, ignorando fecha e importe, para no darlos por perdidos.
criticos = [r for r in pend if ('pag' in r['estado'].lower() or 'recib' in r['estado'].lower())
            and 'pendiente' not in r['estado'].lower()]
fin_all = load_fin_all()
flex_rows = []
SIM_FLEX = 0.55
for r in criticos:
    cands_flex = []
    for t in fin_all:
        s = name_sim(r['cliente'], t['titular'])
        if s >= SIM_FLEX:
            diff = (t['monto'] - (r['importe'] or 0))
            cands_flex.append((s, t, diff))
    cands_flex.sort(key=lambda x: (-x[0], abs(x[2])))
    if cands_flex:
        for s, t, diff in cands_flex[:3]:   # top 3 candidatos por remito
            igual = (t['monto'] in set(r['cands'])) or (r['importe'] == t['monto'])
            if igual:
                diag = '★ IMPORTE IGUAL (solo revisar fecha)'
            elif abs(diff) <= 100:
                diag = f'★ CASI IGUAL (dif ${diff:,} - prob. redondeo)'
            else:
                diag = f'Difiere ${diff:,}'
            flex_rows.append([r['remito'], r['cliente'], r['importe'],
                              t['titular'], t['fecha'].date() if hasattr(t['fecha'],'date') else t['fecha'],
                              t['monto'], round(s,2), diag, t['fila']])
    else:
        flex_rows.append([r['remito'], r['cliente'], r['importe'],
                          '(sin candidato por nombre)', '', '', '', 'Sin coincidencia de nombre en toda la financiera', ''])
n_flex_rescatables = len({fr[0] for fr in flex_rows if '★' in str(fr[7])})
print(f"\nCruce flexible: {len(criticos)} criticos | {n_flex_rescatables} con importe IGUAL fuera de ventana (recuperables)")

# =============== GENERAR EXCEL ===============
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ARIAL = 'Arial'
HFILL = PatternFill('solid', fgColor='1F4E78')   # azul oscuro header
HFONT = Font(name=ARIAL, bold=True, color='FFFFFF', size=10)
TITLE = Font(name=ARIAL, bold=True, size=14, color='1F4E78')
CELL  = Font(name=ARIAL, size=10)
CONF_FILL = {'Alta': PatternFill('solid', fgColor='C6EFCE'),
             'Media': PatternFill('solid', fgColor='FFEB9C'),
             'Baja': PatternFill('solid', fgColor='FFC7CE')}
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = '$#,##0'

def sheet(wb, title, headers, rows, conf_col=None, widths=None, money_cols=()):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in range(1, len(headers)+1):
        cell = ws.cell(row=1, column=c); cell.font = HFONT; cell.fill = HFILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER
    for rec in rows:
        ws.append(rec)
    for ri in range(2, ws.max_row+1):
        for ci in range(1, len(headers)+1):
            cell = ws.cell(row=ri, column=ci); cell.font = CELL; cell.border = BORDER
            cell.alignment = Alignment(vertical='center', wrap_text=(ci not in money_cols))
            if ci in money_cols and isinstance(cell.value, (int, float)):
                cell.number_format = MONEY
        if conf_col:
            cv = ws.cell(row=ri, column=conf_col).value
            if cv in CONF_FILL: ws.cell(row=ri, column=conf_col).fill = CONF_FILL[cv]
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
    if widths:
        for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    return ws

wb = Workbook(); wb.remove(wb.active)

# --- Hoja 1: Conciliados ---
rows = []
tipo_map = {'1 a 1': '1 a 1', 'varios pedidos -> un comprobante': 'N pedidos -> 1 comprobante',
            'un pedido -> varios comprobantes': '1 pedido -> N comprobantes'}
for c in sorted(concs, key=lambda x: (x['tipo'], -x['monto'])):
    rems = ", ".join(str(r['remito']) for r in c['remitos'])
    cli = c['remitos'][0]['cliente']
    imp_rem = sum(r['importe'] or 0 for r in c['remitos'])
    comps = " ; ".join(f"{t['titular']} | {t['fecha'].date()} | ${t['monto']:,} (fila {t['fila']})"
                       for t in c['comps'])
    rows.append([tipo_map[c['tipo']], rems, cli, imp_rem, comps, c['monto'],
                 round(c['sim'], 2), c['conf']])
sheet(wb, '1-Conciliados',
      ['Tipo conciliación', 'Remito(s)', 'Cliente', 'Importe remito(s)',
       'Comprobante(s) financiera (titular | fecha | monto | fila)', 'Monto conciliado',
       'Similitud nombre', 'Confianza'],
      rows, conf_col=8, widths=[24, 14, 26, 15, 60, 15, 11, 11], money_cols=(4, 6))

# --- Hoja 2: Pendientes ---
rows = []
for r in sorted(pend, key=lambda x: -(x['importe'] or 0)):
    rows.append([r['remito'], r['cliente'], r['importe'],
                 r['fecha'].date() if hasattr(r['fecha'], 'date') else r['fecha'],
                 r['estado'], r['motivo'], r['motivo_conf']])
sheet(wb, '2-Pendientes',
      ['Remito', 'Cliente', 'Importe', 'Fecha remito', 'Estado (planilla local)',
       'Motivo probable', 'Confianza'],
      rows, conf_col=7, widths=[12, 26, 14, 14, 26, 48, 11], money_cols=(3,))

# --- Hoja 3: Comprobantes sin pedido ---
rows = [[t['fila'], t['fecha'].date(), t['titular'], t['monto'], t['planilla']]
        for t in sorted(comp_sin, key=lambda x: -x['monto'])]
sheet(wb, '3-Comprob. sin pedido',
      ['Fila financiera', 'Fecha', 'Titular transferencia', 'Monto', 'Planilla'],
      rows, widths=[14, 14, 32, 15, 14], money_cols=(4,))

# --- Hoja 4: Diferencias ---
rows = []
for tipo, r, obs in sorted(difs, key=lambda x: (x[0], -(x[1]['importe'] or 0))):
    rows.append([tipo, r['remito'], r['cliente'], r['importe'], r['estado'], obs])
# agregar duplicados
for k, v in rem_dups.items():
    rows.append(['Remito DUPLICADO en planilla local', k, v[0]['cliente'],
                 v[0]['importe'], f"{len(v)} apariciones", "Verificar carga duplicada"])
for k, v in comp_dups.items():
    rows.append(['Comprobante DUPLICADO en financiera', '-', v[0]['titular'],
                 v[0]['monto'], f"{len(v)} apariciones (filas {', '.join(str(x['fila']) for x in v)})",
                 "Posible doble registro de la financiera"])
sheet(wb, '4-Diferencias',
      ['Tipo de diferencia', 'Remito', 'Cliente/Titular', 'Importe', 'Estado / Detalle', 'Observación'],
      rows, widths=[38, 12, 26, 14, 30, 46], money_cols=(4,))

# --- Hoja 6: Revisión flexible (críticos por nombre) ---
sheet(wb, '6-Revision flexible',
      ['Remito', 'Cliente (local)', 'Importe remito', 'Titular financiera (nombre parecido)',
       'Fecha transf.', 'Monto transf.', 'Similitud', 'Diagnóstico', 'Fila fin.'],
      flex_rows, widths=[12, 24, 15, 30, 13, 15, 11, 34, 10], money_cols=(3, 6))

# --- Hoja 5: Resumen Ejecutivo ---
ws = wb.create_sheet('5-Resumen Ejecutivo'); wb.move_sheet(ws, -(len(wb.sheetnames)-1))
ws['A1'] = 'RESUMEN EJECUTIVO - Conciliación Semales'; ws['A1'].font = TITLE
ws['A2'] = f'Ventana analizada: {dmin.date()} a {dmax.date()} (+{VENTANA_DIAS} días) | Regla: importe exacto'
ws['A2'].font = Font(name=ARIAL, italic=True, size=9, color='808080')
n_rem = sum(len(c['remitos']) for c in concs) + len(pend)
n_conc = sum(len(c['remitos']) for c in concs)
crit = [r for r in pend if ('pag' in r['estado'].lower() or 'recib' in r['estado'].lower())
        and 'pendiente' not in r['estado'].lower()]
metrics = [
    ('Total remitos analizados', n_rem, ''),
    ('Remitos conciliados', n_conc, f'{100*n_conc/n_rem:.1f}%'),
    ('  · 1 a 1', sum(len(c['remitos']) for c in concs if c['tipo']=='1 a 1'), ''),
    ('  · Agrupados (N pedidos -> 1 comprobante)', sum(len(c['remitos']) for c in concs if 'varios' in c['tipo']), ''),
    ('  · Pagos parciales (1 pedido -> N comprobantes)', sum(1 for c in concs if 'un pedido' in c['tipo']), ''),
    ('Remitos PENDIENTES (sin conciliar)', len(pend), f'{100*len(pend)/n_rem:.1f}%'),
    ('  · de los cuales, local dice "Pendiente de Pago"', len(pend)-len(crit), ''),
    ('  · CRÍTICO: local dice COBRADO pero sin transferencia', len(crit), '⚠️'),
    ('Comprobantes de la financiera SIN pedido asociado', len(comp_sin), ''),
    ('  · CRÍTICOS con candidato fuerte por nombre (importe igual/casi)', n_flex_rescatables, '★ ver Hoja 6'),
    ('Remitos duplicados detectados', len(rem_dups), ''),
    ('Comprobantes duplicados detectados', len(comp_dups), ''),
    ('Remitos analizados de Hoja 1 / Hoja 2', f"{sum(1 for r in local if r['origen']=='Hoja1')} / {sum(1 for r in local if r['origen']=='Hoja2')}", ''),
    ('', '', ''),
    ('Importe conciliado', sum(c['monto'] for c in concs), ''),
    ('Importe pendiente total', sum(r['importe'] or 0 for r in pend), ''),
    ('Importe CRÍTICO (cobrado local sin respaldo financiera)', sum(r['importe'] or 0 for r in crit), '⚠️'),
]
row = 4
ws.cell(row=row, column=1, value='Indicador').font = HFONT
ws.cell(row=row, column=1).fill = HFILL
ws.cell(row=row, column=2, value='Valor').font = HFONT
ws.cell(row=row, column=2).fill = HFILL
ws.cell(row=row, column=3, value='%/Nota').font = HFONT
ws.cell(row=row, column=3).fill = HFILL
row += 1
for label, val, note in metrics:
    ws.cell(row=row, column=1, value=label).font = Font(name=ARIAL, size=10, bold=label.startswith(('Total','Remitos','Importe','Comprob')))
    c2 = ws.cell(row=row, column=2, value=val); c2.font = CELL
    if isinstance(val, (int, float)) and abs(val) >= 1000: c2.number_format = MONEY
    c3 = ws.cell(row=row, column=3, value=note); c3.font = CELL
    if '⚠️' in str(note):
        for cc in (1, 2, 3): ws.cell(row=row, column=cc).fill = PatternFill('solid', fgColor='FFC7CE')
    row += 1
ws.column_dimensions['A'].width = 52; ws.column_dimensions['B'].width = 18; ws.column_dimensions['C'].width = 10

wb.save(OUT)
print(f"\n[Excel generado: {OUT}]  Hojas: {wb.sheetnames}")
