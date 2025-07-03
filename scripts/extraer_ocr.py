#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_ocr.py — Extrae líneas OCR de un PDF, añade tamaños de fuente y normaliza globalmente.

▸ Cada línea incluye:
    - altura_px: altura base en píxeles
    - grupo_fuente: tipo de caracter usado como referencia (core, mayuscula, etc.)
    - font_size_pt: tamaño estimado en puntos
    - font_size_pt_norm: agrupado globalmente
"""

from pathlib import Path
import argparse, json, logging, re, time

import pdfplumber
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output, image_to_boxes
import random
from PIL import Image
from statistics import mean

def estimar_altura_letras(image: Image.Image, bbox: list, lang: str, texto: str, dpi: int = 400, debug=False):
    import numpy as np

    grupos = {
        "core": set("acemnorsuvwxz"),
        "ascendente": set("bdfhktl"),
        "descendente": set("gjpqy"),
        "digito": set("0123456789"),
        "mayuscula": set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    }

    recorte = image.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
    h = recorte.size[1]
    boxes = image_to_boxes(recorte, lang=lang)

    # Limitar la cantidad de caracteres analizados
    MAX_CARACTERES_ANALIZADOS = 10
    box_lines = boxes.strip().splitlines()
    if len(box_lines) > MAX_CARACTERES_ANALIZADOS:
        box_lines = random.sample(box_lines, MAX_CARACTERES_ANALIZADOS)

    if not boxes.strip():
        logging.warning(f"[warn] sin boxes OCR en '{texto}'")
        # fallback: usar altura del bbox directamente
        altura_fallback = bbox[3] - bbox[1]
        if altura_fallback > 0:
            logging.debug(f"[debug] fallback activo: altura = {altura_fallback} px (desde bbox)")
            grupo_fallback = "digito" if texto.isdigit() else "fallback"
            return altura_fallback, grupo_fallback
        else:
            logging.debug(f"[debug] fallback fallido: sin altura detectable")
            return 0, "max"

    alturas = {k: [] for k in list(grupos.keys()) + ["otro"]}

    for b in box_lines:
        parts = b.split()
        if len(parts) != 6:
            continue
        char, x1, y1, x2, y2, _ = parts
        try:
            y1 = int(y1)
            y2 = int(y2)
            altura = abs(y2 - y1)
            c = char.strip()
            grupo = next((g for g, letras in grupos.items() if c in letras), "otro")
            alturas[grupo].append(altura)
        except:
            continue

    if debug:
        logging.debug(f"[debug] texto analizado: '{texto}' ({recorte.size[0]}x{recorte.size[1]} px)")
        logging.debug(f"[debug] caracteres detectados por grupo:")
        for g in ["core", "ascendente", "mayuscula", "digito", "descendente", "otro"]:
            logging.debug(f"  - {g}: {len(alturas[g])}")

    if len(alturas["core"]) >= 3:
        base = np.median(alturas["core"])
        fuente = "core"
    elif len(alturas["ascendente"]) >= 3:
        base = np.mean(alturas["ascendente"])
        fuente = "ascendente"
    elif len(alturas["mayuscula"]) >= 3:
        base = np.median(alturas["mayuscula"])
        fuente = "mayuscula"
    elif len(alturas["digito"]) >= 3:
        base = np.mean(alturas["digito"])
        fuente = "digito"
    else:
        todas = sum(alturas.values(), [])
        base = max(todas) if todas else 0
        fuente = "max"

    FACTOR_POR_TIPO = {
        "core": 1.7,
        "ascendente": 1.3,
        "mayuscula": 1.0,
        "digito": 1.2,
        "max": 0.95,
        "fallback": 1.0,
        "fallback_digito": 1.2,
    }
    factor = FACTOR_POR_TIPO.get("fallback_digito" if fuente == "digito" and texto.isdigit() else fuente, 1.0)
    font_size_pt = base * 72 / dpi * factor

    if debug:
        logging.debug(f"[debug] grupo seleccionado como base: {fuente}")
        logging.debug(f"[debug] altura base utilizada: {round(base, 1)} px")
        logging.debug(f"[debug] factor aplicado: {factor}")
        logging.debug(f"[debug] tamaño estimado: {round(font_size_pt, 2)} pt")

    return base, fuente

def agrupar_por_tolerancia(valores, tolerancia=0.6):
    valores_ordenados = sorted(valores)
    grupos = []
    actual = []
    for v in valores_ordenados:
        if not actual:
            actual.append(v)
        elif abs(v - mean(actual)) <= tolerancia:
            actual.append(v)
        else:
            grupos.append(actual)
            actual = [v]
    if actual:
        grupos.append(actual)
    return [mean(g) for g in grupos]

def asignar_cluster(val, grupos):
    return min(grupos, key=lambda g: abs(g - val))

def cli():
    ap = argparse.ArgumentParser("OCR índice limpio")
    ap.add_argument("--pdf", type=Path, default=Path("datos/original.pdf"))
    ap.add_argument("--out", "-o", type=Path, default=Path("datos/ocr_lineas.json"))
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--lang", "-l", default="deu-frak+deu")
    ap.add_argument("--psm", type=int, default=4, help="PSM para páginas normales")
    ap.add_argument("--index-pages", nargs="*", type=int, help="Páginas índice 1-based")
    ap.add_argument("--pages", nargs="*", type=int, help="Procesar sólo estas páginas")
    ap.add_argument("--debug", action="store_true")
    return ap.parse_args()

def ocr(pil: Image.Image, lang: str, psm: int):
    cfg = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    return image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg)

def process_normal(pil: Image.Image, lang: str, psm: int, page_no: int, dpi: int, clusters, debug=False):
    d = ocr(pil, lang, psm)
    groups = {}
    for i, txt in enumerate(d["text"]):
        if txt.strip():
            k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            groups.setdefault(k, []).append(i)

    out = []
    for idxs in groups.values():
        xs = [d["left"][i] for i in idxs]
        ys = [d["top"][i]  for i in idxs]
        ws = [d["width"][i] for i in idxs]
        hs = [d["height"][i] for i in idxs]

        linea_texto = " ".join(d["text"][i].strip() for i in idxs)

        altura_px, grupo_fuente = estimar_altura_letras(pil, [min(xs), min(ys), max(x + w for x, w in zip(xs, ws)), max(y + h for y, h in zip(ys, hs))], lang, texto=linea_texto, dpi=dpi, debug=debug)
        FACTOR_POR_TIPO = {"core": 1.7, "ascendente": 1.3, "mayuscula": 1.0, "digito": 1.2, "max": 0.95}
        factor = FACTOR_POR_TIPO.get(grupo_fuente, 1.0)
        font_size_pt = altura_px * 72 / dpi * factor

        font_size_pt_norm = asignar_cluster(font_size_pt, clusters)

        linea = {
            "bbox": [min(xs), min(ys),
                     max(x + w for x, w in zip(xs, ws)),
                     max(y + h for y, h in zip(ys, hs))],
            "texto": linea_texto,
            "tipo": "linea",
            "pagina": page_no,
            "altura_px": altura_px,
            "grupo_fuente": grupo_fuente,
            "font_size_pt": round(font_size_pt, 2),
            "font_size_pt_norm": round(font_size_pt_norm)
        }
        out.append(linea)
    return out

def image_blocks(pdf: Path, page: int):
    out = []
    with pdfplumber.open(pdf) as doc:
        for img in doc.pages[page-1].images:
            out.append({
                "bbox": [img["x0"], img["top"], img["x1"], img["bottom"]],
                "tipo": "imagen",
                "pagina": page
            })
    return out

def main():
    t0_total = time.time()
    import logging
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    logging.getLogger("pdf2image").setLevel(logging.WARNING)

    args = cli()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler("ocr_debug.log", mode="w", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    total = pdfinfo_from_path(args.pdf)["Pages"]
    pages = args.pages or range(1, total + 1)

    salida, t0 = [], time.time()

    all_heights_pt = []
    for p in pages:
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        d = ocr(pil, args.lang, args.psm)
        heights_px = [d["height"][i] for i, txt in enumerate(d["text"]) if txt.strip()]
        all_heights_pt.extend([h * 72 / args.dpi for h in heights_px])

    clusters = agrupar_por_tolerancia(all_heights_pt, tolerancia=0.6)
    clusters = [round(c) for c in clusters]

    if args.debug:
        print("\n[debug] tamaños normalizados globales:")
        for c in sorted(set(clusters)):
            print(f"  - {c} pt")
        print("")

    for p in pages:
        logging.info("Procesando página %s (normal)", p)
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        salida.extend(process_normal(pil, args.lang, args.psm, p, dpi=args.dpi, clusters=clusters, debug=args.debug))
        salida.extend(image_blocks(args.pdf, p))

    args.out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), "utf-8")
    logging.info("✅ %s items → %s (%.1f s)", len(salida), args.out, time.time() - t0)
    logging.info("⏱️ Tiempo total de ejecución: %.2f s", time.time() - t0_total)

if __name__ == "__main__":
    main()
