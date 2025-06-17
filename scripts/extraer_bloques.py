#!/usr/bin/env python
# extraer_bloques.py — v8.0-b
# ---------------------------
# • Márgenes globales por página (percentil 5 y 95).
# • Alineación interna con tolerancia --tol-px (default 4 px).
# • --debug-align imprime distancias y texto por línea.
# -----------------------------------------------------------

import argparse, json, statistics, time, sys
from pathlib import Path
from typing import List, Dict, Set

h = lambda b: b[3] - b[1]
w = lambda b: b[2] - b[0]

def parse_page_set(spec: str) -> Set[int]:
    pages=set()
    for part in spec.split(","):
        part=part.strip()
        if not part: continue
        if "-" in part:
            a,b=map(int,part.split("-",1))
            pages.update(range(a,b+1))
        else:
            pages.add(int(part))
    return pages

def internal_align(l, page_left, page_right, tol, debug=False):
    left_g  = abs(l["bbox"][0]  - page_left)
    right_g = abs(page_right    - l["bbox"][2])
    left_ok  = left_g  <= tol
    right_ok = right_g <= tol
    if left_ok and right_ok:
        align="justificado"
    elif right_ok:
        align="derecha"
    elif left_ok:
        align="izquierda"
    elif abs(left_g - right_g) <= tol:
        align="centro"
    else:
        align="izquierda"
    if debug and not l.get("_dbg_done"):
        snippet=l["texto"].replace("\n"," ")[:60]
        print(f"[dbg] pág {l['pagina']:>3} y={l['bbox'][1]:>4} "
              f"L{left_g:>3} R{right_g:>3} tol={tol:>2} → {align} «{snippet}»")
        l["_dbg_done"] = True
    return align

def group_lines(lines: List[dict], args, page_left, page_right):
    if not lines: return []
    med_h=statistics.median(h(l["bbox"]) for l in lines)
    p=lines[0]
    cur={"parts":[p["texto"]],"bbox":list(p["bbox"]),"fs":h(p["bbox"]),
         "indent":p["bbox"][0],
         "align":internal_align(p,page_left,page_right,args.tol_px,args.debug_align)}
    blocks=[]
    for ln in lines[1:]:
        gap_ok=(ln["bbox"][1]-p["bbox"][3])<=args.max_gap*med_h
        new_align=internal_align(ln,page_left,page_right,args.tol_px,args.debug_align)
        indent_ok=abs(ln["bbox"][0]-cur["indent"])<=args.indent_threshold or len(cur["parts"])<2
        join=gap_ok and indent_ok
        if join:
            cur["parts"].append(ln["texto"])
            x0,y0,x1,y1=cur["bbox"]; lx0,ly0,lx1,ly1=ln["bbox"]
            cur["bbox"]=[min(x0,lx0),min(y0,ly0),max(x1,lx1),max(y1,ly1)]
            cur["fs"]=max(cur["fs"],h(ln["bbox"]))
            cur["indent"]=min(cur["indent"],ln["bbox"][0])
            cur["align"]="justificado" if cur["align"]=="justificado" or new_align=="justificado" else cur["align"]
        else:
            blocks.append(cur)
            cur={"parts":[ln["texto"]],"bbox":list(ln["bbox"]),
                 "fs":h(ln["bbox"]),"indent":ln["bbox"][0],
                 "align":new_align}
        p=ln
    blocks.append(cur)

    res=[]
    for b in blocks:
        text=" ".join(b["parts"]).strip()
        kind="titulo" if b["fs"]>args.title_factor*med_h or text.isupper() else "parrafo"
        res.append({"texto":text,"bbox":b["bbox"],"font_size":b["fs"],
                    "tipo":kind,"alineacion":b["align"]})
    return res

def build_parser():
    ap=argparse.ArgumentParser(description="extraer_bloques v8.0-b")
    ap.add_argument("input"); ap.add_argument("-o","--out",default="bloques.json")
    ap.add_argument("--pages")
    ap.add_argument("--max-gap",type=float,default=1.2)
    ap.add_argument("--indent-threshold",type=int,default=25)
    ap.add_argument("--title-factor",type=float,default=1.4)
    ap.add_argument("--tol-px",type=int,default=4,help="Tolerancia en px (default 4)")
    ap.add_argument("--debug-align",action="store_true")
    return ap

def main():
    args=build_parser().parse_args()
    try:
        data=json.loads(Path(args.input).read_text("utf-8"))
    except Exception as e:
        sys.exit(f"❌ No se pudo leer {args.input}: {e}")

    pages: Dict[int,List[dict]]={}
    for ln in data:
        pages.setdefault(ln["pagina"],[]).append(ln)

    sel=parse_page_set(args.pages) if args.pages else None
    todo=[p for p in sorted(pages) if sel is None or p in sel]
    if not todo:
        sys.exit("⚠️  Sin páginas seleccionadas o presentes en el archivo.")

    out=[]
    for pg in todo:
        lines=pages[pg]
        xs=[l["bbox"][0] for l in lines]+[l["bbox"][2] for l in lines]
        xs_sorted=sorted(xs)
        page_left = xs_sorted[int(0.05 * len(xs_sorted))]
        page_right= xs_sorted[int(0.95 * len(xs_sorted))]
        lines_sorted=sorted(lines,key=lambda l:(l["bbox"][1],l["bbox"][0]))
        out.extend(group_lines(lines_sorted,args,page_left,page_right))

    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2),"utf-8")
    print(f"🌟 Guardado {len(out)} bloques en {args.out}")

if __name__=="__main__":
    main()
