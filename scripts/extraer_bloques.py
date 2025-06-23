#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_bloques.py — Agrupa líneas OCR en bloques.

Novedad clave
-------------
Las líneas **índice** ya no almacenan los puntos de relleno.  El bloque
resultante contiene:

    {
      "pagina": 11,
      "texto": {                # ⟵ objeto con 2 campos
        "titulo": "Bildbeilage Nr. 1",
        "pag": "17"
      },
      "alineacion": "indice",
      "unilinea": true
    }

En maquetación se usará tab+leader o flex-box para colocar `pag`
contra el margen derecho.

Resto de características: orden fijo de claves, unilinea, refs_pie, etc.
"""

import argparse, json, re
from pathlib import Path
from collections import OrderedDict
from typing import List, Dict, Any

DOT_RE  = re.compile(r'[.·]{3,}')
ENDNUM  = re.compile(r'\d{1,3}\s*$')
FOOT_RE = re.compile(r'(?:\[(\d{1,3})\]|(\d{1,3})\)|([⁰¹²³⁴⁵⁶⁷⁸⁹]+))')


def bbox(l: Dict[str, Any]) -> List[int]:
    return l.get('bbox') or [l['x'], l['y'], l['x'] + l['w'], l['y'] + l['h']]

_x = lambda l: l.get('x', bbox(l)[0])
_y = lambda l: l.get('y', bbox(l)[1])
fsize = lambda l: bbox(l)[3] - bbox(l)[1]


def refs(text: str) -> List[str]:
    return [g for m in FOOT_RE.finditer(text) for g in m.groups() if g]


def split_index(text: str) -> Dict[str, str]:
    """Devuelve {'titulo':…, 'pag':…} si coincide patrón índice."""
    m = ENDNUM.search(text)
    if not m:
        return {}
    pag = m.group().strip()
    titulo = text[:m.start()].rstrip('.· ').rstrip()
    return {"titulo": titulo, "pag": pag}


def align(l: Dict[str, Any], minx: int, maxx: int, indent: int, rtol: int) -> str:
    ri = maxx - bbox(l)[2]
    txt = l.get('texto', l.get('text', ''))
    if ri <= rtol and (DOT_RE.search(txt) or ENDNUM.search(txt)):
        return 'indice'
    li = _x(l) - minx
    if ri <= rtol and li > indent:
        return 'derecha'
    if li <= indent and ri <= rtol:
        return 'justificado'
    if li <= indent:
        return 'izquierda'
    return 'centrado'


def mk_block(lines: List[Dict[str, Any]]) -> OrderedDict:
    f = lines[0]
    bl = OrderedDict()
    bl['pagina'] = f['pagina']
    if f['align'] == 'indice':
        txt = f.get('texto', f.get('text', ''))
        bl['texto'] = split_index(txt) or {"titulo": txt, "pag": ""}
    else:
        texts = [l.get('texto', l.get('text', '')) for l in lines]
        bl['texto'] = " ".join(texts)
    bl['alineacion'] = f['align']
    refs_list = sum((refs(l.get('texto', l.get('text', ''))) for l in lines), [])
    if refs_list:
        bl['refs_pie'] = refs_list
    bl['y_top'] = bbox(f)[1]
    bl['y_bottom'] = bbox(lines[-1])[3]
    bl['font_size'] = sum(fsize(l) for l in lines) / len(lines)
    bl['x_left'] = min(_x(l) for l in lines)
    bl['x_right'] = max(bbox(l)[2] for l in lines)
    if len(lines) == 1:
        bl['unilinea'] = True
    else:
        bl['lines'] = lines
    return bl


def agrupar(ls: List[Dict[str, Any]], tol: int, gap: float, indent: int, rtol: int, debug: bool):
    ls.sort(key=lambda v: (v['pagina'], _y(v), _x(v)))
    out = []
    cur = []
    pag = None
    prev = 0
    minx = maxx = None
    for ln in ls:
        if ln['pagina'] != pag:
            if cur:
                out.append(mk_block(cur))
                cur = []
            pag = ln['pagina']
            page = [l for l in ls if l['pagina'] == pag]
            minx = min(_x(l) for l in page)
            maxx = max(bbox(l)[2] for l in page)
        ln['align'] = align(ln, minx, maxx, indent, rtol)
        if debug:
            txt = ln.get('texto', ln.get('text', ''))
            print(f"[dbg] pág {pag} y={_y(ln):>4} {ln['align']:<9} {txt[:60]}")
        if not cur:
            cur.append(ln)
            prev = bbox(ln)[3]
            continue
        same = ln['align'] == cur[0]['align'] and ln['align'] not in {'centrado', 'indice'}
        dy = _y(ln) - prev
        if same and (abs(dy) <= tol or dy / fsize(ln) <= gap):
            cur.append(ln)
            prev = bbox(ln)[3]
        else:
            out.append(mk_block(cur))
            cur = [ln]
            prev = bbox(ln)[3]
    if cur:
        out.append(mk_block(cur))
    return out


def load(path: Path) -> List[Dict[str, Any]]:
    dat = json.loads(path.read_text('utf-8'))
    for l in dat:
        if 'texto' not in l and 'text' in l:
            l['texto'] = l.pop('text')
        l['align'] = l.pop('alineacion', l.get('align', 'izquierda'))
    return dat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_ocr', type=Path)
    ap.add_argument('--output', '-o', type=Path)
    ap.add_argument('--pages', nargs='*', type=int)
    ap.add_argument('--tol', type=int, default=4)
    ap.add_argument('--gap', type=float, default=1.3)
    ap.add_argument('--indent', type=int, default=25)
    ap.add_argument('--right-tol', dest='right_tol', type=int, default=50)
    ap.add_argument('--debug', action='store_true')
    a = ap.parse_args()
    ls = load(a.json_ocr)
    if a.pages:
        ls = [l for l in ls if l['pagina'] in a.pages]
    blocks = agrupar(ls, a.tol, a.gap, a.indent, a.right_tol, a.debug)
    out = json.dumps(blocks, ensure_ascii=False, indent=2)
    if a.output:
        a.output.write_text(out, 'utf-8')
    else:
        auto = a.json_ocr.with_name('bloques.json')
        auto.write_text(out, 'utf-8')
        print(out)

if __name__ == '__main__':
    main()
