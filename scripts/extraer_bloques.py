#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_bloques.py — Agrupa líneas OCR en bloques visuales.

• Orden de campos: pagina, text, alineacion, …
• Bloques unilínea: se marcan con "unilinea": true y omiten "lines".
• Conserva pagina, bbox, font_size para trazabilidad.
• Detección básica de referencias a notas al pie (refs_pie).
• Si no usas -o, crea <nombre>_bloques.json automáticamente.

Uso:
  python extraer_bloques.py datos/ocr_lineas.json --pages 9 10 11 12 --debug
"""

import argparse, json, re
from pathlib import Path
from collections import OrderedDict
from typing import List, Dict, Any

# ── patrones ────────────────────────────────────────────────────────────────
DOT_RE = re.compile(r'[.·]{3,}')
END_NUM_RE = re.compile(r'\d{1,3}\s*$')
FOOTNOTE_RE = re.compile(r'(?:\[(\d{1,3})\]|(\d{1,3})\)|([⁰¹²³⁴⁵⁶⁷⁸⁹]+))')

# ── util geométrico ─────────────────────────────────────────────────────────
def bbox(line: Dict[str, Any]) -> List[int]:
    """Devuelve [x1,y1,x2,y2] aunque falten claves."""
    if 'bbox' in line and isinstance(line['bbox'], (list, tuple)) and len(line['bbox']) == 4:
        return line['bbox']

    # Claves sueltas
    if {'x', 'y', 'w', 'h'} <= line.keys():
        return [line['x'], line['y'], line['x'] + line['w'], line['y'] + line['h']]

    # Si sólo vienen x1,y1,x2,y2…
    if {'x1', 'y1', 'x2', 'y2'} <= line.keys():
        return [line['x1'], line['y1'], line['x2'], line['y2']]

    # Fallback: todo a 0 para no romper el flujo
    return [0, 0, 0, 0]

def _x(line): return line.get('x', line['bbox'][0])
def _y(line): return line.get('y', line['bbox'][1])
def font_size(line): return bbox(line)[3] - bbox(line)[1]

# ── notas al pie ────────────────────────────────────────────────────────────
def refs_pie(text: str) -> List[str]:
    return [g for m in FOOTNOTE_RE.finditer(text) for g in m.groups() if g]

# ── alineación ──────────────────────────────────────────────────────────────
def detect_align(line, min_x1, max_x2, indent, right_tol):
    ri = max_x2 - bbox(line)[2]
    txt = line['texto']
    if ri <= right_tol and (DOT_RE.search(txt) or END_NUM_RE.search(txt)):
        return 'indice'
    li = _x(line) - min_x1
    if ri <= right_tol and li > indent: return 'derecha'
    if li <= indent and ri <= right_tol: return 'justificado'
    if li <= indent: return 'izquierda'
    return 'centrado'

# ── bloque helper ───────────────────────────────────────────────────────────
def make_block(ls: List[Dict[str, Any]]) -> Dict[str, Any]:
    first = ls[0]
    b = OrderedDict()
    b['pagina'] = first['pagina']
    b['text'] = " ".join(l['texto'] for l in ls)
    b['alineacion'] = first['align']
    if (r := [r for l in ls for r in refs_pie(l['texto'])]): b['refs_pie'] = r
    b['y_top'] = bbox(first)[1]
    b['y_bottom'] = bbox(ls[-1])[3]
    b['font_size'] = sum(font_size(l) for l in ls)/len(ls)
    b['x_left'] = min(_x(l) for l in ls)
    b['x_right'] = max(bbox(l)[2] for l in ls)
    if len(ls) == 1:
        b['unilinea'] = True
    else:
        b['lines'] = ls
    return b

# ── agrupación ──────────────────────────────────────────────────────────────
def agrupar(lines: List[Dict[str, Any]], tol, gap, indent, right_tol, debug):
    lines.sort(key=lambda l: (l['pagina'], _y(l), _x(l)))
    out, cur, pag, prev_bottom = [], [], None, None
    for ln in lines:
        if pag != ln['pagina']:
            if cur: out.append(make_block(cur)); cur = []
            pag = ln['pagina']
            page_lines = [l for l in lines if l['pagina']==pag]
            min_x1 = min(_x(l) for l in page_lines)
            max_x2 = max(bbox(l)[2] for l in page_lines)
        ln['align'] = detect_align(ln, min_x1, max_x2, indent, right_tol)
        if debug:
            print(f"[dbg] pág {pag} y={_y(ln):>4} align={ln['align']:<10} {ln['texto'][:60]}")
        if not cur:
            cur.append(ln); prev_bottom=bbox(ln)[3]; continue
        same_align = ln['align']==cur[0]['align'] and ln['align'] not in {'centrado','indice'}
        dy = _y(ln) - prev_bottom
        if same_align and (abs(dy)<=tol or dy/font_size(ln)<=gap):
            cur.append(ln); prev_bottom=bbox(ln)[3]
        else:
            out.append(make_block(cur)); cur=[ln]; prev_bottom=bbox(ln)[3]
    if cur: out.append(make_block(cur))
    return out

# ── carga JSON OCR ──────────────────────────────────────────────────────────
def load_lines(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    for l in data:
        l['bbox'] = l.get('bbox') or [l['x'], l['y'], l['x']+l['w'], l['y']+l['h']]
        l['align'] = l.pop('alineacion', l.get('align','izquierda'))
    return data

# ── CLI ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_ocr', type=Path)
    ap.add_argument('--output','-o', type=Path)
    ap.add_argument('--pages', nargs='*', type=int)
    ap.add_argument('--tol-px', type=int, default=4)
    ap.add_argument('--max-gap', type=float, default=1.3)
    ap.add_argument('--indent', type=int, default=25)
    ap.add_argument('--right-tol', type=int, default=50)
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    lines = load_lines(args.json_ocr)
    if args.pages: lines = [l for l in lines if l['pagina'] in args.pages]

    bloques = agrupar(lines, args.tol_px, args.max_gap, args.indent, args.right_tol, args.debug)

    salida = json.dumps(bloques, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(salida, encoding='utf-8')
    else:
        # crea archivo _bloques.json y también imprime en pantalla
        auto = args.json_ocr.with_name(args.json_ocr.stem + '_bloques.json')
        auto.write_text(salida, encoding='utf-8')
        # print(salida)

if __name__ == '__main__':
    main()
