#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_ocr.py — Extrae líneas OCR de un PDF, añade tamaños de fuente y normaliza globalmente.

▸ Cada línea incluye:
    - font_size (px)
    - font_size_pt: tamaño estimado en puntos (corrige si es mayúsculas)
    - font_size_pt_norm: agrupado globalmente
    - font_size_pt_orig: solo si se aplicó corrección (texto todo en mayúsculas)
"""

from pathlib import Path
import argparse, json, logging, re, time, unicodedata

import pdfplumber
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output
from PIL import Image

from collections import Counter
from statistics import mean, median

# Nueva función para estimar la altura de la fuente tomando las primeras palabras
def estimar_altura_letras(image: Image.Image, bbox: list, lang: str, dpi: int = 400, debug=False) -> float:
    from pytesseract import image_to_boxes
    import numpy as np

    grupos = {
        "core": set("acemnorsuvwxz"),
        "ascendente": set("bdfhktl"),
        "descendente": set("gjpqy"),
        "digito": set("0123456789"),
        "mayuscula": set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    }

    FACTOR_POR_TIPO = {
        "core": 1.35,
        "ascendente": 1.1,
        "mayuscula": 1.0,
        "digito": 1.15,
        "max": 1.2,
    }

    recorte = image.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
    h = recorte.size[1]
    boxes = image_to_boxes(recorte, lang=lang)

    alturas = {
        "core": [],
        "ascendente": [],
        "descendente": [],
        "digito": [],
        "mayuscula": [],
        "otro": [],
    }

    for b in boxes.strip().splitlines():
        parts = b.split()
        if len(parts) != 6:
            continue
        char, x1, y1, x2, y2, _ = parts
        try:
            y1 = int(y1)
            y2 = int(y2)
            altura = abs(y2 - y1)
            c = char.strip()
            grupo = None
            for g, letras in grupos.items():
                if c in letras:
                    grupo = g
                    break
            if not grupo:
                grupo = "otro"
            alturas[grupo].append(altura)
        except:
            continue

    resumen = {k: len(v) for k, v in alturas.items()}

    if debug:
        print(f"[debug] caracteres detectados: {resumen}")

    # Selección del grupo más representativo
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

    factor = FACTOR_POR_TIPO.get(fuente, 1.2)
    font_size_pt = base * 72 / dpi * factor

    if debug:
        print(f"[debug] altura base seleccionada ({fuente}): {round(base, 1)} px × factor {factor} → {round(font_size_pt, 2)} pt")

    return font_size_pt

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

    heights_px = [d["height"][i] for i, txt in enumerate(d["text"]) if txt.strip()]
    heights = [h * 72 / dpi for h in heights_px]

    out = []
    for idxs in groups.values():
        xs = [d["left"][i] for i in idxs]
        ys = [d["top"][i]  for i in idxs]
        ws = [d["width"][i] for i in idxs]
        hs = [d["height"][i] for i in idxs]

        # Usamos la función estimar_altura_letras para calcular el font_size_px
        font_size_px = estimar_altura_letras(pil, [
            min(xs), min(ys),
            max(x + w for x, w in zip(xs, ws)),
            max(y + h for y, h in zip(ys, hs))
        ], lang)

        font_size_pt_orig = font_size_px * 72 / dpi * 1.3  # factor de corrección por x-height

        linea_texto = " ".join(d["text"][i].strip() for i in idxs)
        if linea_texto.isupper():
            font_size_pt = font_size_pt_orig / 0.75
        else:
            font_size_pt = font_size_pt_orig
        font_size_pt_norm = asignar_cluster(font_size_pt, clusters)

        linea = {
            "bbox": [min(xs), min(ys),
                     max(x + w for x, w in zip(xs, ws)),
                     max(y + h for y, h in zip(ys, hs))],
            "texto": linea_texto,
            "tipo": "linea",
            "pagina": page_no,
            "font_size": font_size_px,
            "font_size_pt": font_size_pt,
            "font_size_pt_norm": round(font_size_pt_norm)
        }
        if linea_texto.isupper():
            linea["font_size_pt_orig"] = font_size_pt_orig
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
    args = cli()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    total = pdfinfo_from_path(args.pdf)["Pages"]
    pages = args.pages or range(1, total + 1)

    salida, t0 = [], time.time()

    # 🔁 Recolectar alturas de todo el documento
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

    # 🔁 OCR por página
    for p in pages:
        logging.info("Procesando página %s (normal)", p)
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        salida.extend(process_normal(pil, args.lang, args.psm, p, dpi=args.dpi, clusters=clusters, debug=args.debug))
        salida.extend(image_blocks(args.pdf, p))

    args.out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), "utf-8")
    logging.info("✅ %s items → %s (%.1f s)", len(salida), args.out, time.time() - t0)

if __name__ == "__main__":
    main()
