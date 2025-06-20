#!/usr/bin/env python3
"""
extraer_bloques.py — Agrupa líneas OCR y produce bloques.

Restaurados parámetros eliminados inadvertidamente:
  • --pages N [N ...]      Filtra páginas (1‑based)
  • --debug                Traza alineación y fusiones

Adicional:
  • Bloques de una línea: elimina "lines" y añade "unilinea": true
"""

import argparse, json, re
from pathlib import Path
from typing import List, Dict, Any, Optional

DOT_RE = re.compile(r'[.·]{3,}')
END_NUM_RE = re.compile(r'\d{1,3}\s*$')

def cargar_lineas(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding='utf-8'))
    for ln in data:
        if 'alineacion' not in ln and 'align' in ln:
            ln['alineacion'] = ln.pop('align')
        ln.pop('align', None)
    return data

def guardar(bloques: List[Dict[str, Any]], dst: Optional[Path], src: Path):
    # Simplificar unilíneas
    for b in bloques:
        if len(b.get('lines', [])) == 1:
            b['unilinea'] = True
            b.pop('lines', None)
    if dst is None:
        dst = src.with_name(src.stem + '_bloques.json')
    dst.write_text(json.dumps(bloques, ensure_ascii=False, indent=2), encoding='utf-8')

def bbox(ln):
    if 'bbox' in ln:
        return ln['bbox']
    x, y, w, h = ln['x'], ln['y'], ln['w'], ln['h']
    return [x, y, x + w, y + h]

def font_size(ln): return bbox(ln)[3] - bbox(ln)[1]

def detect_alineacion(ln, min_x1, max_x2, indent, right_tol):
    txt = ln['texto']; right = max_x2 - bbox(ln)[2]
    if right <= right_tol and (DOT_RE.search(txt) or END_NUM_RE.search(txt)):
        return 'indice'
    left = bbox(ln)[0] - min_x1
    if right <= right_tol and left > indent: return 'derecha'
    if left <= indent and right <= right_tol: return 'justificado'
    if left <= indent: return 'izquierda'
    return 'centrado'

def nuevo_bloque(ln):
    b = bbox(ln)
    return {'alineacion': ln['alineacion'],'text': ln['texto'],
            'y_top': b[1],'y_bottom': b[3],'font_size': font_size(ln),
            'lines':[ln]}

def agrupar_lineas(lst, tol, gap):
    blocks=[]
    for ln in lst:
        if ln['alineacion'] in {'centrado','indice'} or not blocks or blocks[-1]['alineacion'] in {'centrado','indice'}:
            blocks.append(nuevo_bloque(ln)); continue
        last=blocks[-1]; dy=bbox(ln)[1]-last['y_bottom']; h=last['y_bottom']-last['y_top'] or 1
        if (abs(dy)<=tol or dy/h<=gap) and ln['alineacion']==last['alineacion']:
            last['text']+=' '+ln['texto']; last['y_bottom']=bbox(ln)[3]; last['lines'].append(ln)
            last['font_size']=(last['font_size']+font_size(ln))/2
        else:
            blocks.append(nuevo_bloque(ln))
    return blocks

def procesar_paginas(lines, *, tol, gap, indent, right_tol, debug):
    by_page: Dict[int,List[Dict[str,Any]]] = {}
    for ln in lines: by_page.setdefault(ln['pagina'],[]).append(ln)
    res=[]
    for pg in sorted(by_page):
        lp=by_page[pg]; minx=min(bbox(l)[0] for l in lp); maxx=max(bbox(l)[2] for l in lp)
        for ln in lp:
            ln['alineacion']=detect_alineacion(ln,minx,maxx,indent,right_tol)
            if debug:
                li=bbox(ln)[0]-minx; ri=maxx-bbox(ln)[2]
                print(f"[dbg] pág {pg:>2} y={bbox(ln)[1]:>4} LI={li:<3} RI={ri:<3} → {ln['alineacion']:<10} {ln['texto'][:60]}")
        lp.sort(key=lambda l:bbox(l)[1])
        res.extend(agrupar_lineas(lp,tol,gap))
    return res

def cli():
    ap=argparse.ArgumentParser(description='Agrupa líneas OCR en bloques.')
    ap.add_argument('json_ocr',type=Path)
    ap.add_argument('--output','-o',type=Path)
    ap.add_argument('--pages',nargs='*',type=int)
    ap.add_argument('--tol',type=int,default=4)
    ap.add_argument('--gap',type=float,default=1.3)
    ap.add_argument('--indent',type=int,default=25)
    ap.add_argument('--right-tol',type=int,default=50)
    ap.add_argument('--debug',action='store_true')
    return ap.parse_args()

def main():
    args=cli(); lines=cargar_lineas(args.json_ocr)
    if args.pages: lines=[l for l in lines if l['pagina'] in args.pages]
    bloques=procesar_paginas(lines,tol=args.tol,gap=args.gap,indent=args.indent,
                             right_tol=args.right_tol,debug=args.debug)
    guardar(bloques,args.output,args.json_ocr)

if __name__=='__main__': main()
