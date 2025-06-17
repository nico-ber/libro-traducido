
#!/usr/bin/env python3
"""extraer_bloques.py — Agrupa líneas OCR en bloques/párrafos.

Cambios clave:
  • --merge-cross-page: fusiona bloques contiguos entre páginas.
  • --right-tol (por defecto 50 px): tolerancia para considerar que
    la línea llega al margen derecho aun si el OCR recorta unos
    píxeles.
  • Soporta JSON con clave `bbox` ([x1, y1, x2, y2]) —ya no exige
    campos 'x', 'y', 'w', 'h'.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

def cargar_lineas(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def guardar(bloques: List[Dict[str, Any]], destino: Optional[Path], input_path: Path) -> None:
    if destino is None:
        destino = input_path.with_suffix('').with_name(input_path.stem + '_bloques.json')
    destino.write_text(json.dumps(bloques, ensure_ascii=False, indent=2), encoding='utf-8')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def coords(ln: Dict[str, Any]):
    """Devuelve x1, y1, x2, y2, ancho, alto (acepta bbox o x/y/w/h)."""
    if "bbox" in ln:
        x1, y1, x2, y2 = ln["bbox"]
        w = x2 - x1
        h = y2 - y1
    else:
        x1 = ln["x"]; y1 = ln["y"]; w = ln["w"]; h = ln["h"]
        x2, y2 = x1 + w, y1 + h
    return x1, y1, x2, y2, w, h

def detect_align(ln, min_x1, max_x2, indent_threshold, right_tol):
    x1, _, x2, _, _, _ = coords(ln)
    li = x1 - min_x1
    ri = max_x2 - x2
    if ri <= right_tol and li > indent_threshold:
        return "derecha"
    if li <= indent_threshold and ri <= right_tol:
        return "justificado"
    if li <= indent_threshold:
        return "izquierda"
    return "centrado"

# ---------------------------------------------------------------------------
# Agrupación
# ---------------------------------------------------------------------------

def nuevo_bloque(ln):
    x1, y1, x2, y2, _, _ = coords(ln)
    return {
        "align": ln["align"],
        "text": ln["texto"],
        "y_top": y1,
        "y_bottom": y2,
        "lines": [ln],
    }


def agrupar_lineas(lineas, tol_px, max_gap):
    """Agrupa líneas en párrafos con regla de primera línea indentada a la derecha.

    Si el primer renglón de un bloque está alineado a la derecha pero la(s)
    siguiente(s) línea(s) están alineadas a la izquierda o justificado y
    cumplen el criterio de gap, lo consideramos un único párrafo. El bloque
    final toma la justificación predominante (la de la segunda línea).
    """
    bloques = []
    for ln in lineas:
        if not bloques:
            bloques.append(nuevo_bloque(ln))
            continue

        ultimo = bloques[-1]
        _, y1, _, y2, _, _ = coords(ln)
        gap = y1 - ultimo["y_bottom"]
        altura = ultimo["y_bottom"] - ultimo["y_top"] or 1
        mismo_align = ln["align"] == ultimo["align"]

        union_mismo_parrafo = (abs(gap) <= tol_px or gap / altura <= max_gap)

        if union_mismo_parrafo:
            # Caso especial: la primera línea (derecha) y la segunda (izq/just)
            if not mismo_align and ultimo["align"] == "derecha" and len(ultimo["lines"]) == 1 and ln["align"] in {"izquierda", "justificado"}:
                # Reetiquetar el bloque completo al alineado del segundo renglón
                ultimo["align"] = ln["align"]
                mismo_align = True  # ahora son compatibles

            if mismo_align:
                ultimo["text"] += " " + ln["texto"]
                ultimo["y_bottom"] = y2
                ultimo["lines"].append(ln)
                continue

        # Si no pudo unirse, crear nuevo bloque
        bloques.append(nuevo_bloque(ln))
    return bloques

def agrupar_en_bloques(lineas, *, tol_px, max_gap, indent_threshold, right_tol, merge_cross_page, debug_align=False):
    por_pag = {}
    for ln in lineas:
        por_pag.setdefault(ln["pagina"], []).append(ln)

    final = []
    pags = sorted(por_pag.keys())
    for i, pag in enumerate(pags):
        lp = por_pag[pag]
        min_x1 = min(coords(l)[0] for l in lp)
        max_x2 = max(coords(l)[2] for l in lp)

        for ln in lp:
            ln["align"] = detect_align(ln, min_x1, max_x2, indent_threshold, right_tol)
            if debug_align:
                li = coords(ln)[0] - min_x1
                ri = max_x2 - coords(ln)[2]
                print(f"[dbg] pág {pag:>2} y={coords(ln)[1]:>4} LI={li:<4} RI={ri:<4} → {ln['align']}  {ln['texto'][:60]}")
        lp.sort(key=lambda l: coords(l)[1])

        bloques = agrupar_lineas(lp, tol_px, max_gap)

        if merge_cross_page and final and bloques and final[-1]["align"] == bloques[0]["align"]:
            gap = bloques[0]["y_top"] - final[-1]["y_bottom"]
            altura = final[-1]["y_bottom"] - final[-1]["y_top"] or 1
            if gap/altura <= max_gap:
                if debug_align:
                    print(f"[dbg] Fusionando pág {pags[i-1]}→{pag} gap={gap}")
                final[-1]["text"] += " " + bloques[0]["text"]
                final[-1]["y_bottom"] = bloques[0]["y_bottom"]
                final[-1]["lines"].extend(bloques[0]["lines"])
                bloques.pop(0)

        final.extend(bloques)
    return final

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cli():
    ap = argparse.ArgumentParser(description="Agrupa líneas OCR en bloques.")
    ap.add_argument("json_ocr", type=Path)
    ap.add_argument("--output", "-o", type=Path)
    ap.add_argument("--pages", nargs="*", type=int)
    ap.add_argument("--tol-px", type=int, default=4)
    ap.add_argument("--max-gap", type=float, default=1.3)
    ap.add_argument("--indent-threshold", type=int, default=25)
    ap.add_argument("--right-tol", type=int, default=50)
    ap.add_argument("--merge-cross-page", action="store_true")
    ap.add_argument("--debug-align", action="store_true")
    return ap.parse_args()

def main():
    args = cli()
    lineas = cargar_lineas(args.json_ocr)
    if args.pages:
        lineas = [l for l in lineas if l["pagina"] in args.pages]

    bloques = agrupar_en_bloques(
        lineas,
        tol_px=args.tol_px,
        max_gap=args.max_gap,
        indent_threshold=args.indent_threshold,
        right_tol=args.right_tol,
        merge_cross_page=args.merge_cross_page,
        debug_align=args.debug_align,
    )
    guardar(bloques, args.output, args.json_ocr)

if __name__ == "__main__":
    main()
