#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_bloques.py — Agrupa líneas OCR en bloques visuales.

▸ Entrada: líneas OCR JSON (producidas por extraer_ocr.py)

▸ Cada bloque incluye:
    - pagina: número de página
    - text: texto unificado
    - alineacion: tipo de alineación (izquierda, justificado, centrado, etc.)
    - font_size: promedio entre líneas del bloque (usa font_size_pt_norm o font_size_pt)
    - bbox derivado: x_left, x_right, y_top, y_bottom
    - tipo: línea o imagen
    - unilinea: true si es una sola línea
    - lines: solo si es multilínea
    - refs_pie: referencias numéricas a notas al pie detectadas (opcional)
    - estirar_por_letras: si es una línea unilinea en mayúsculas y justificada

▸ Lógica de agrupamiento:
    - No agrupa líneas centradas (bloques unilínea)
    - Une líneas adyacentes con alineación compatible y distancia vertical dentro de tolerancia
    - Detecta referencias a notas al pie con expresiones regulares

▸ Parámetros CLI:
    --json_ocr        Ruta al JSON de líneas OCR
    --output, -o      Ruta de salida
    --pages           Páginas a procesar
    --indent          Tolerancia para sangrías (25 px por defecto)
    --right-tol       Tolerancia para margen derecho (50 px por defecto)
    --tol-px          Tolerancia de alineación horizontal (default 4)
    --max-gap         Tolerancia vertical relativa
    --debug           Modo detallado
"""

import argparse
import json
import re
from pathlib import Path
from collections import OrderedDict
from typing import List, Dict, Any

DISTANCIA_VERTICAL_MAX = 150
DOT_RE = re.compile(r'[.\u00b7]{3,}')
END_NUM_RE = re.compile(r'\d{1,3}\s*$')
FOOTNOTE_RE = re.compile(r'(?:\[(\d{1,3})\]|(\d{1,3})\)|([⁰¹²³⁴⁵⁶⁷⁸⁹]+))')

def bbox(line: Dict[str, Any]) -> List[int]:
    if 'bbox' in line and isinstance(line['bbox'], (list, tuple)) and len(line['bbox']) == 4:
        return line['bbox']
    if {'x', 'y', 'w', 'h'} <= line.keys():
        return [line['x'], line['y'], line['x'] + line['w'], line['y'] + line['h']]
    if {'x1', 'y1', 'x2', 'y2'} <= line.keys():
        return [line['x1'], line['y1'], line['x2'], line['y2']]
    return [0, 0, 0, 0]

def _x(line): return line.get('x', line['bbox'][0])
def _y(line): return line.get('y', line['bbox'][1])

def font_size(line):
    if "font_size_pt_norm" in line:
        return line["font_size_pt_norm"]
    if "font_size_pt" in line:
        return line["font_size_pt"]
    # Fallback visual
    return bbox(line)[3] - bbox(line)[1]

def refs_pie(text: str) -> List[str]:
    return [g for m in FOOTNOTE_RE.finditer(text) for g in m.groups() if g]

def detect_align(line, min_x1, max_x2, indent, right_tol):
    if 'texto' not in line:
        return None

    x1, _, x2, _ = bbox(line)
    li = x1 - min_x1
    ri = max_x2 - x2
    ancho = x2 - x1
    txt = line['texto']

    if ancho > 0 and li / ancho < 0.15 and ri / ancho < 0.15:
        return 'justificado'
    if ri <= right_tol and (DOT_RE.search(txt) or END_NUM_RE.search(txt)):
        return 'indice'
    if li <= indent and ri <= right_tol:
        return 'justificado'
    if li <= indent:
        return 'izquierda'
    if ri <= right_tol and li > indent * 2:
        return 'derecha'
    return 'centrado'

def make_block(ls: List[Dict[str, Any]]) -> Dict[str, Any]:
    first = ls[0]
    b = OrderedDict()
    b['pagina'] = first['pagina']
    b['text'] = " ".join(l['texto'] for l in ls if 'texto' in l)
    b['alineacion'] = first.get('align', 'izquierda')
    if (r := [r for l in ls if 'texto' in l for r in refs_pie(l['texto'])]):
        b['refs_pie'] = r
    b['y_top'] = bbox(first)[1]
    b['y_bottom'] = bbox(ls[-1])[3]
    fs = [font_size(l) for l in ls if 'texto' in l]
    b['font_size'] = sum(fs)/len(fs) if fs else 0
    b['x_left'] = min(_x(l) for l in ls)
    b['x_right'] = max(bbox(l)[2] for l in ls)
    b['tipo'] = first.get('tipo', 'linea')
    if len(ls) == 1:
        b['unilinea'] = True
        if b['alineacion'] == 'justificado' and b['text'].strip().isupper():
            b['estirar_por_letras'] = True
    else:
        b['lines'] = ls
        for l in ls:
            l['tipo'] = b['tipo']
    return b

def agrupar(lines: List[Dict[str, Any]], tol, gap, indent, right_tol, debug):
    out, cur, pag, prev_bottom = [], [], None, None
    lines.sort(key=lambda l: (l['pagina'], _y(l), _x(l)))
    for i, ln in enumerate(lines):
        if pag != ln['pagina']:
            if cur:
                out.append(make_block(cur))
                cur = []
            pag = ln['pagina']
            page_lines = [l for l in lines if l['pagina'] == pag]
            min_x1 = min(_x(l) for l in page_lines)
            max_x2 = max(bbox(l)[2] for l in page_lines)

        ln['align'] = detect_align(ln, min_x1, max_x2, indent, right_tol) if 'texto' in ln else None

        if debug:
            txt = ln.get('texto', '')
            print(f"[dbg] pág {pag} y={_y(ln):>4} align={str(ln['align']):<10} {txt[:60]}")

        if ln['align'] == 'centrado':
            if cur:
                out.append(make_block(cur))
                cur = []
            out.append(make_block([ln]))
            continue

        if not cur:
            cur.append(ln)
            prev_bottom = bbox(ln)[3]
            continue

        prev_ln = cur[-1]
        dy = _y(ln) - prev_bottom
        same_align = (
            ln['align'] == prev_ln['align'] or
            (prev_ln['align'] == 'justificado' and ln['align'] == 'izquierda') or
            (prev_ln['align'] == 'derecha' and ln['align'] in {'justificado', 'izquierda'} and abs(prev_ln['bbox'][2] - ln['bbox'][2]) <= right_tol)
        )

        if same_align and dy <= DISTANCIA_VERTICAL_MAX:
            cur.append(ln)
            prev_bottom = bbox(ln)[3]
        else:
            out.append(make_block(cur))
            cur = [ln]
            prev_bottom = bbox(ln)[3]

    if cur:
        out.append(make_block(cur))
    return out

def load_lines(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    for l in data:
        l['bbox'] = l.get('bbox') or [l['x'], l['y'], l['x']+l['w'], l['y']+l['h']]
        l['align'] = l.pop('alineacion', l.get('align','izquierda'))
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json_ocr', type=Path, default='datos/ocr_lineas.json')
    ap.add_argument('--output','-o', type=Path)
    ap.add_argument('--pages', nargs='*', type=int)
    ap.add_argument('--tol-px', type=int, default=4)
    ap.add_argument('--max-gap', type=float, default=1.3)
    ap.add_argument('--indent', type=int, default=25)
    ap.add_argument('--right-tol', type=int, default=50)
    ap.add_argument('--debug', action='store_true')
    args = ap.parse_args()

    lines = load_lines(args.json_ocr)
    if args.pages:
        lines = [l for l in lines if l['pagina'] in args.pages]

    bloques = agrupar(lines, args.tol_px, args.max_gap, args.indent, args.right_tol, args.debug)
    salida = json.dumps(bloques, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(salida, encoding='utf-8')
    else:
        Path('datos/bloques.json').write_text(salida, encoding='utf-8')

if __name__ == '__main__':
    main()
