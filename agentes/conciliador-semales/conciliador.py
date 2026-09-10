#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conciliador Semales <-> Control de Remitos
Motor deterministico: importes, fechas, agrupaciones y duplicados se calculan
con codigo (nunca se "estiman"). El resultado es 100% auditable.
"""
import openpyxl, datetime, re, unicodedata, difflib, sys
from itertools import combinations
from collections import defaultdict, Counter

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
    col = {v:k for k,v in hdr.items() if v}
    if 'Fecha/Hora' not in col and not str(hdr.get(1) or '').strip():
        # cabecera de la columna A vino en blanco en la exportacion; la columna
        # A sigue siendo la fecha/hora (verificado por contenido: datetime)
        col['Fecha/Hora'] = 1
    for r in range(2, ws.max_row+1):
        g = lambda name: ws.cell(row=r, column=col[name]).value if name in col else None
        if g('Importe') is None and g('N° Remito') is None: continue
        out.append(_mk(f"H1:{r}", 'Hoja1', g('N° Remito'), g('Cliente'),
                       g('Importe'), g('Fecha/Hora'), g('Estado Pago'), g('Empresa')))
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

# ---------------- clasificacion de estado y grupo ----------------
# Los estados de la planilla local vienen escritos a mano y mezclan mayusculas,
# singular/plural y frases largas ("Pago recibido", "Pago pendiente", "Pagado -
# CVU confirmado...", "Pago con diferencia", "ANULADO"). Se clasifican una sola
# vez aca para que TODO el reporte use el mismo criterio.
def clasificar_estado(estado):
    e = str(estado or '').strip().lower()
    if not e or 'sin estado' in e:      return 'SIN ESTADO'
    if 'anulad' in e:                   return 'ANULADO'
    if 'diferencia' in e:               return 'DIFERENCIA'
    if 'pendiente' in e:                return 'PENDIENTE'   # incluye "Pago pendiente"
    if 'pag' in e or 'recib' in e:      return 'COBRADO'
    return 'SIN ESTADO'

# Cada empresa reporta sus comprobantes en un grupo de WhatsApp distinto.
GRUPOS = {'SEMALEZ SA': 'TRANSFERENCIA FER CHAVEZ', 'BEYDE SRL': 'PAGOS BEYDE'}
def grupo_de(empresa):
    return GRUPOS.get(str(empresa or '').strip().upper(), '(empresa sin identificar)')

# ---------------- cuenta corriente con la financiera ----------------
def _ddmm_de_planilla(p):
    """La financiera codifica la fecha en el nombre de la planilla: '1408 CJ' = 14/08."""
    if p is None: return None
    if isinstance(p, datetime.datetime): return (p.day, p.month)
    s = str(int(p)) if isinstance(p, float) and p.is_integer() else str(p)
    m = re.search(r'(?<!\d)(\d{3,4})(?!\d)', s)
    if not m: return None
    v = m.group(1).zfill(4)
    d, mo = int(v[:2]), int(v[2:])
    return (d, mo) if 1 <= d <= 31 and 1 <= mo <= 12 else None

def _completar_fechas(movs):
    """3 de cada 4 retiros vienen SIN fecha cargada. Se reconstruye desde el codigo
    de planilla y se ancla el año en las filas datadas vecinas (el libro esta en
    orden cronologico). Queda marcado con fecha_est=True: es un dato inferido."""
    datadas = [(i, m['fecha']) for i, m in enumerate(movs)
               if isinstance(m['fecha'], datetime.datetime)]
    for i, m in enumerate(movs):
        if isinstance(m['fecha'], datetime.datetime): continue
        dm = _ddmm_de_planilla(m['planilla'])
        if not dm: continue
        prev = next((f for j, f in reversed(datadas) if j < i), None)
        nxt  = next((f for j, f in datadas if j > i), None)
        base = prev or nxt
        if not base: continue
        TOL = datetime.timedelta(days=20)
        for y in (base.year - 1, base.year, base.year + 1):
            try: cand = datetime.datetime(y, dm[1], dm[0])
            except ValueError: continue
            if (prev is None or cand >= prev - TOL) and (nxt is None or cand <= nxt + TOL):
                m['fecha'], m['fecha_est'] = cand, True
                break
    return movs

def load_movimientos():
    """Todos los movimientos de la cuenta: transferencias de clientes (ARS > 0) y
    retiros (ARS < 0). 'Monto' es el bruto que transfirio el cliente y 'ARS' el
    neto acreditado despues de la comision de la financiera."""
    wb = openpyxl.load_workbook(FIN_FILE, data_only=True); ws = wb[FIN_SHEET]
    out = []
    for r in range(3, ws.max_row+1):
        ars = ws.cell(row=r, column=3).value
        if not isinstance(ars, (int, float)) or ars == 0: continue
        monto = ws.cell(row=r, column=5).value
        out.append(dict(
            fila=r, ars=ars, monto=monto if isinstance(monto,(int,float)) else 0,
            fecha=ws.cell(row=r, column=6).value, fecha_est=False,
            titular=ws.cell(row=r, column=8).value,
            planilla=ws.cell(row=r, column=9).value,
            saldo_declarado=ws.cell(row=r, column=2).value,
            tipo='RETIRO' if ars < 0 else 'INGRESO'))
    return _completar_fechas(out)

def saldo_declarado_planilla():
    """Celda 'SALDO ACTUAL' que la propia financiera publica en su planilla."""
    wb = openpyxl.load_workbook(FIN_FILE, data_only=True); ws = wb[FIN_SHEET]
    v = ws.cell(row=1, column=3).value
    return v if isinstance(v, (int, float)) else None

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
    clase = clasificar_estado(rem['estado'])
    if clase == 'ANULADO':
        return ('Remito ANULADO - no corresponde cobro', 'Alta')
    if clase == 'PENDIENTE':
        return ('Estado local = Pendiente de Pago (aun no cobrado)', 'Alta')
    if clase == 'DIFERENCIA':
        return ('Estado local = Pago con diferencia - el importe cobrado no coincide con el remito', 'Alta')
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
    cobrado = clasificar_estado(r['estado']) == 'COBRADO'
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
criticos = [r for r in pend if clasificar_estado(r['estado']) == 'COBRADO']
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

# ============ CUENTA CORRIENTE CON LA FINANCIERA (que me deben cobrar) ============
movs     = load_movimientos()
ingresos = [m for m in movs if m['tipo'] == 'INGRESO']
retiros  = [m for m in movs if m['tipo'] == 'RETIRO']
tot_bruto    = sum(m['monto'] for m in ingresos)
tot_neto     = sum(m['ars']   for m in ingresos)
tot_comision = tot_bruto - tot_neto
tot_retirado = -sum(m['ars'] for m in retiros)
saldo_cobrar = tot_neto - tot_retirado
saldo_plan   = saldo_declarado_planilla()
desvio_saldo = None if saldo_plan is None else round(saldo_cobrar - saldo_plan, 2)

# Atribucion de cada comprobante a su grupo de WhatsApp, via el remito conciliado.
grupo_por_fila, remito_por_fila = {}, {}
for c in concs:
    gs = sorted({grupo_de(r['empresa']) for r in c['remitos'] if r['empresa']})
    etiqueta = " + ".join(gs) if gs else '(sin identificar)'
    rems = ", ".join(str(r['remito']) for r in c['remitos'])
    for t in c['comps']:
        grupo_por_fila[t['fila']]  = etiqueta
        remito_por_fila[t['fila']] = rems

hasta = dmax + datetime.timedelta(days=VENTANA_DIAS)
en_win = lambda f: isinstance(f, datetime.datetime) and dmin.date() <= f.date() <= hasta.date()
ing_win, ret_win = [m for m in ingresos if en_win(m['fecha'])], [m for m in retiros if en_win(m['fecha'])]
neto_win = sum(m['ars'] for m in ing_win)
retirado_win = -sum(m['ars'] for m in ret_win)

# Verificacion independiente: recalculo el saldo acumulado fila por fila y lo
# comparo con el que declara la financiera. Cualquier desvio = ajuste no explicado.
run, desvios_saldo = 0.0, 0
for m in movs:
    run += m['ars']
    if isinstance(m['saldo_declarado'], (int, float)) and abs(m['saldo_declarado'] - run) > 1.0:
        desvios_saldo += 1

fmt_fecha = lambda f: f.date() if isinstance(f, datetime.datetime) else (f or '')

# --- Hoja: Cuenta corriente (todos los movimientos con saldo) ---
rows = [[fmt_fecha(m['fecha']), m['tipo'],
         'RETIRO POR CAJA' if m['tipo'] == 'RETIRO' else m['titular'],
         grupo_por_fila.get(m['fila'], '' if m['tipo'] == 'RETIRO' else '(comprobante sin conciliar)'),
         remito_por_fila.get(m['fila'], ''),
         m['monto'] if m['tipo'] == 'INGRESO' else '',
         round(m['monto'] - m['ars'], 2) if m['tipo'] == 'INGRESO' else '',
         round(m['ars'], 2), m['saldo_declarado'],
         str(m['planilla'] or ''), m['fila']] for m in movs]
sheet(wb, '7-Cuenta Corriente',
      ['Fecha', 'Tipo', 'Titular / Concepto', 'Grupo WhatsApp', 'Remito(s) asociado(s)',
       'Bruto transferido', 'Comisión financiera', 'Neto a mi favor', 'Saldo acumulado',
       'Planilla', 'Fila fin.'],
      rows, widths=[12, 10, 32, 26, 18, 16, 15, 16, 16, 11, 10], money_cols=(6, 7, 8, 9))

# --- Hoja: Retiros (lo que ya saqué de la financiera) ---
rows = [[fmt_fecha(m['fecha']), 'ESTIMADA del código de planilla' if m['fecha_est'] else 'cargada',
         round(-m['ars'], 2), m['saldo_declarado'], str(m['planilla'] or ''), m['fila']]
        for m in retiros]
ws_ret = sheet(wb, '8-Retiros realizados',
      ['Fecha del retiro', 'Origen de la fecha', 'Monto retirado', 'Saldo que quedó',
       'Planilla', 'Fila fin.'],
      rows, widths=[16, 30, 18, 18, 12, 10], money_cols=(3, 4))
fila_total = ws_ret.max_row + 2
ws_ret.cell(row=fila_total, column=1, value='TOTAL RETIRADO').font = Font(name=ARIAL, bold=True, size=10)
c = ws_ret.cell(row=fila_total, column=2, value=round(tot_retirado, 2))
c.font = Font(name=ARIAL, bold=True, size=10); c.number_format = MONEY

# --- Hoja: Comprobantes por grupo (periodo analizado) ---
rows = []
for m in sorted(ing_win, key=lambda x: (grupo_por_fila.get(x['fila'], 'zzz'), x['fecha'])):
    g = grupo_por_fila.get(m['fila'])
    rows.append([g or '(sin conciliar - grupo no identificado)', fmt_fecha(m['fecha']), m['titular'],
                 m['monto'], round(m['monto'] - m['ars'], 2), round(m['ars'], 2),
                 remito_por_fila.get(m['fila'], ''),
                 'CONCILIADO' if g else 'SIN PEDIDO ASOCIADO', m['fila']])
sheet(wb, '9-Comprobantes por grupo',
      ['Grupo WhatsApp', 'Fecha', 'Titular transferencia', 'Bruto transferido',
       'Comisión', 'Neto a mi favor', 'Remito(s)', 'Estado', 'Fila fin.'],
      rows, widths=[28, 12, 30, 16, 13, 16, 16, 22, 10], money_cols=(4, 5, 6))

# --- Hoja: Resumen Ejecutivo ---
ws = wb.create_sheet('5-Resumen Ejecutivo'); wb.move_sheet(ws, -(len(wb.sheetnames)-1))
ws['A1'] = 'RESUMEN EJECUTIVO - Conciliación Semales / Beyde'; ws['A1'].font = TITLE
ws['A2'] = (f'Remitos analizados: {dmin.date()} a {dmax.date()} (+{VENTANA_DIAS} días de ventana) | '
            f'Regla: importe exacto, sin reutilizar comprobantes | '
            f'Cuenta corriente: histórico completo de la financiera')
ws['A2'].font = Font(name=ARIAL, italic=True, size=9, color='808080')

n_rem  = sum(len(c['remitos']) for c in concs) + len(pend)
n_conc = sum(len(c['remitos']) for c in concs)
clases = Counter(clasificar_estado(r['estado']) for r in local)
crit   = [r for r in pend if clasificar_estado(r['estado']) == 'COBRADO']
pend_real = [r for r in pend if clasificar_estado(r['estado']) == 'PENDIENTE']
pend_dif  = [r for r in pend if clasificar_estado(r['estado']) == 'DIFERENCIA']
pend_anul = [r for r in pend if clasificar_estado(r['estado']) == 'ANULADO']
pend_sin  = [r for r in pend if clasificar_estado(r['estado']) == 'SIN ESTADO']

# desglose por grupo
por_grupo = defaultdict(lambda: dict(rem=0, conc=0, crit=0, imp_crit=0))
for r in local:
    g = por_grupo[grupo_de(r['empresa'])]
    g['rem'] += 1
    if r['usado']: g['conc'] += 1
    elif clasificar_estado(r['estado']) == 'COBRADO':
        g['crit'] += 1; g['imp_crit'] += r['importe'] or 0

pct = lambda n, d: f'{100*n/d:.1f}%' if d else ''
M = [
 ('§A. DINERO: ¿CUÁNTO TENGO QUE COBRAR DE LA FINANCIERA?', '', ''),
 ('Transferencias de clientes recibidas (bruto)', tot_bruto, f'{len(ingresos)} comprob.'),
 ('  (-) Comisión retenida por la financiera', -tot_comision, pct(tot_comision, tot_bruto)),
 ('  (=) Neto acreditado a mi favor', tot_neto, ''),
 ('  (-) Retiros que ya hice de la financiera', -tot_retirado, f'{len(retiros)} retiros'),
 ('SALDO A COBRAR DE LA FINANCIERA (hoy)', saldo_cobrar, '★ ver Hoja 7'),
 ('  Saldo que declara la propia planilla financiera', saldo_plan, ''),
 ('  Desvío entre mi cálculo y el de la financiera', desvio_saldo,
      'OK - coincide' if desvio_saldo is not None and abs(desvio_saldo) < 1 else '⚠️ REVISAR'),
 ('  Filas con saldo acumulado mal encadenado', desvios_saldo,
      'OK - ledger consistente' if desvios_saldo == 0 else '⚠️ REVISAR'),
 ('', '', ''),
 ('§B. MOVIMIENTO DEL PERÍODO ANALIZADO', f'{dmin.date()} a {hasta.date()}', ''),
 ('Transferencias recibidas en el período (neto)', neto_win, f'{len(ing_win)} comprob.'),
 ('Retiros hechos en el período', -retirado_win, f'{len(ret_win)} retiros'),
 ('Variación de saldo del período', neto_win - retirado_win, ''),
 ('', '', ''),
 ('§C. CONCILIACIÓN DE REMITOS CONTRA COMPROBANTES', '', ''),
 ('Total remitos analizados', n_rem, f"Hoja 1: {sum(1 for r in local if r['origen']=='Hoja1')} / Hoja 2: {sum(1 for r in local if r['origen']=='Hoja2')}"),
 ('Remitos CONCILIADOS (tienen su transferencia)', n_conc, pct(n_conc, n_rem)),
 ('  · 1 remito = 1 comprobante', sum(len(c['remitos']) for c in concs if c['tipo']=='1 a 1'), ''),
 ('  · Varios remitos pagados en 1 comprobante', sum(len(c['remitos']) for c in concs if 'varios' in c['tipo']), ''),
 ('  · 1 remito pagado en varios comprobantes', sum(len(c['remitos']) for c in concs if 'un pedido' in c['tipo']), ''),
 ('Importe conciliado', sum(c['monto'] for c in concs), ''),
 ('', '', ''),
 ('§D. REMITOS SIN CONCILIAR - DESGLOSE POR CAUSA', '', ''),
 ('Total sin conciliar', len(pend), pct(len(pend), n_rem)),
 ('  · Aún no cobrados (estado = pendiente de pago)', len(pend_real), 'normal, no es faltante'),
 ('  · CRÍTICO: cobrados en local SIN transferencia', len(crit), '⚠️'),
 ('  · Pago con diferencia (importe no coincide)', len(pend_dif), 'revisar importe'),
 ('  · Anulados', len(pend_anul), 'no corresponde cobro'),
 ('  · Sin estado cargado', len(pend_sin), ''),
 ('IMPORTE CRÍTICO (cobrado en local, sin respaldo)', sum(r['importe'] or 0 for r in crit), '⚠️ ver Hoja 2'),
 ('  · de esos, con candidato fuerte por nombre', n_flex_rescatables, '★ ver Hoja 6'),
 ('Importe pendiente de cobro (aún no pagado)', sum(r['importe'] or 0 for r in pend_real), 'a cobrar al cliente'),
 ('', '', ''),
 ('§E. DESGLOSE POR GRUPO DE WHATSAPP', '', ''),
]
for g in sorted(por_grupo, key=lambda k: -por_grupo[k]['rem']):
    d = por_grupo[g]
    M += [(f'{g}  ·  remitos', d['rem'], pct(d['rem'], n_rem)),
          (f'    conciliados', d['conc'], pct(d['conc'], d['rem'])),
          (f'    críticos (cobrado sin transferencia)', d['crit'],
           f"${d['imp_crit']:,.0f}".replace(',', '.') if d['crit'] else '')]
M += [
 ('', '', ''),
 ('§F. ALERTAS Y CALIDAD DE DATOS', '', ''),
 ('Retiros SIN fecha cargada por la financiera', sum(1 for m in retiros if m['fecha_est']),
  '⚠️' if any(m['fecha_est'] for m in retiros) else ''),
 ('  · importe involucrado (fecha reconstruida del código)',
  sum(-m['ars'] for m in retiros if m['fecha_est']), 'ver Hoja 8'),
 ('Comprobantes de la financiera SIN pedido asociado', len(comp_sin), 'ver Hoja 3'),
 ('Remitos duplicados en la planilla local', len(rem_dups), 'ver Hoja 4' if rem_dups else ''),
 ('Comprobantes duplicados en la financiera', len(comp_dups), 'ver Hoja 4' if comp_dups else ''),
 ('Estados de pago distintos encontrados en la planilla local',
  len({str(r['estado']).strip() for r in local if r['estado']}),
  'unificar redacción'),
]

row = 4
for ci, h in enumerate(['Indicador', 'Valor', 'Nota'], 1):
    c = ws.cell(row=row, column=ci, value=h); c.font = HFONT; c.fill = HFILL
row += 1
for label, val, note in M:
    if str(label).startswith('§'):
        c1 = ws.cell(row=row, column=1, value=str(label)[1:])
        c1.font = Font(name=ARIAL, bold=True, size=11, color='FFFFFF')
        for cc in (1, 2, 3): ws.cell(row=row, column=cc).fill = PatternFill('solid', fgColor='2E75B6')
        ws.cell(row=row, column=2, value=val).font = Font(name=ARIAL, bold=True, size=10, color='FFFFFF')
        row += 1; continue
    destacado = label.startswith(('SALDO A COBRAR', 'IMPORTE CRÍTICO'))
    c1 = ws.cell(row=row, column=1, value=label)
    c1.font = Font(name=ARIAL, size=11 if destacado else 10,
                   bold=destacado or label.startswith(('Total', 'Remitos', 'Importe', 'Transferencias', 'Variación')))
    c2 = ws.cell(row=row, column=2, value=val)
    c2.font = Font(name=ARIAL, size=11 if destacado else 10, bold=destacado)
    if isinstance(val, (int, float)) and abs(val) >= 1000: c2.number_format = MONEY
    c3 = ws.cell(row=row, column=3, value=note); c3.font = CELL
    if destacado:
        for cc in (1, 2, 3): ws.cell(row=row, column=cc).fill = PatternFill('solid', fgColor='FFF2CC')
    elif '⚠️' in str(note):
        for cc in (1, 2, 3): ws.cell(row=row, column=cc).fill = PatternFill('solid', fgColor='FFC7CE')
    elif str(note).startswith('OK'):
        ws.cell(row=row, column=3).fill = PatternFill('solid', fgColor='C6EFCE')
    row += 1
ws.column_dimensions['A'].width = 56; ws.column_dimensions['B'].width = 20; ws.column_dimensions['C'].width = 26
ws.sheet_view.showGridLines = False

print(f"\n=== CUENTA CORRIENTE FINANCIERA ===")
print(f"Recibido bruto: ${tot_bruto:,.0f} | comision: ${tot_comision:,.0f} | neto: ${tot_neto:,.0f}")
print(f"Retirado: ${tot_retirado:,.0f} ({len(retiros)} retiros)")
print(f"SALDO A COBRAR: ${saldo_cobrar:,.2f} | declara planilla: ${saldo_plan:,.2f} | desvio: ${desvio_saldo:,.2f}")

wb.save(OUT)
print(f"\n[Excel generado: {OUT}]  Hojas: {wb.sheetnames}")
