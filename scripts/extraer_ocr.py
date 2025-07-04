#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraer_ocr.py — Extrae líneas OCR de un PDF, añade tamaños de fuente y opcionalmente normaliza.

▸ Cada línea incluye:
    - bbox: coordenadas de la línea
    - texto: texto completo de la línea
    - altura_px: altura base en píxeles (según tipo de letra dominante)
    - grupo_fuente: grupo de letras usado como referencia (core, ascendente, etc.)
    - font_size_pt: tamaño estimado en puntos
    - font_size_pt_norm: (opcional) tamaño agrupado globalmente

▸ Bloques de imagen:
    - Si no se usa --no-images, se añaden bloques {"tipo": "imagen", "pagina": X, "bbox": [...]}

▸ Parámetros CLI principales:
    --pdf             Ruta al archivo PDF de entrada
    --out, -o         Ruta de salida JSON
    --dpi             Resolución de rasterizado
    --lang, -l        Idioma OCR (Tesseract)
    --psm             Page segmentation mode
    --pages           Páginas específicas a procesar
    --no-normalize    Desactiva normalización global de tamaños
    --no-images       Omite bloques de imagen en la salida
    --debug           Muestra logs detallados

▸ Notas:
    - font_size_pt siempre se incluye (valor absoluto estimado).
    - Si --no-normalize, no se incluye font_size_pt_norm.
"""

from pathlib import Path
import argparse, json, logging, re, time
import pdfplumber
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output, image_to_boxes
import random
from PIL import Image
from statistics import mean
import numpy as np

def estimar_altura_letras(image: Image.Image, bbox: list, lang: str, texto: str, dpi: int = 400, debug=False):
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
    box_lines = boxes.strip().splitlines()

    MAX_CARACTERES_ANALIZADOS = 10
    if len(box_lines) > MAX_CARACTERES_ANALIZADOS:
        box_lines = random.sample(box_lines, MAX_CARACTERES_ANALIZADOS)

    if not boxes.strip():
        altura_fallback = bbox[3] - bbox[1]
        grupo_fallback = "digito" if texto.isdigit() else "fallback"
        FACTOR_POR_TIPO = {
            "fallback": 1.0,
            "fallback_digito": 1.2,
        }
        clave = "fallback_digito" if grupo_fallback == "digito" else "fallback"
        factor = FACTOR_POR_TIPO[clave]
        font_size_pt = altura_fallback * 72 / dpi * factor
        return altura_fallback, grupo_fallback, font_size_pt

    alturas = {k: [] for k in list(grupos.keys()) + ["otro"]}
    for b in box_lines:
        parts = b.split()
        if len(parts) != 6:
            continue
        char, _, y1, _, y2, _ = parts
        try:
            y1 = int(y1)
            y2 = int(y2)
            altura = abs(y2 - y1)
            grupo = next((g for g, letras in grupos.items() if char in letras), "otro")
            alturas[grupo].append(altura)
        except:
            continue

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

    return base, fuente, font_size_pt

def agrupar_por_tolerancia(valores, tolerancia=0.6):
    valores_ordenados = sorted(valores)
    grupos, actual = [], []
    for v in valores_ordenados:
        if not actual or abs(v - mean(actual)) <= tolerancia:
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, default=Path("datos/original.pdf"))
    ap.add_argument("--out", "-o", type=Path, default=Path("datos/ocr_lineas.json"))
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--lang", "-l", default="deu-frak+deu")
    ap.add_argument("--psm", type=int, default=4)
    ap.add_argument("--index-pages", nargs="*", type=int)
    ap.add_argument("--pages", nargs="*", type=int)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--no-normalize", action="store_true")
    ap.add_argument("--no-images", action="store_true")
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
        texto = " ".join(d["text"][i].strip() for i in idxs)

        bbox = [min(xs), min(ys), max(x + w for x, w in zip(xs, ws)), max(y + h for y, h in zip(ys, hs))]
        altura_px, grupo_fuente, font_size_pt = estimar_altura_letras(pil, bbox, lang, texto=texto, dpi=dpi, debug=debug)

        linea = {
            "bbox": bbox,
            "texto": texto,
            "tipo": "linea",
            "pagina": page_no,
            "altura_px": altura_px,
            "grupo_fuente": grupo_fuente,
            "font_size_pt": round(font_size_pt, 2)
        }

        if clusters is not None:
            font_size_pt_norm = asignar_cluster(font_size_pt, clusters)
            linea["font_size_pt_norm"] = round(font_size_pt_norm)

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

    salida, all_heights_pt = [], []

    if not args.no_normalize:
        for p in pages:
            pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
            d = ocr(pil, args.lang, args.psm)
            heights_px = [d["height"][i] for i, txt in enumerate(d["text"]) if txt.strip()]
            all_heights_pt.extend([h * 72 / args.dpi for h in heights_px])
        clusters = [round(c) for c in agrupar_por_tolerancia(all_heights_pt, tolerancia=0.6)]
        if args.debug:
            print("\n[debug] tamaños normalizados globales:")
            for c in sorted(set(clusters)):
                print(f"  - {c} pt\n")
    else:
        clusters = None

    for p in pages:
        logging.info("Procesando página %s (normal)", p)
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        salida.extend(process_normal(pil, args.lang, args.psm, p, dpi=args.dpi, clusters=clusters, debug=args.debug))
        if not args.no_images:
            salida.extend(image_blocks(args.pdf, p))

    args.out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), "utf-8")
    logging.info("✅ %s items → %s", len(salida), args.out)
    logging.info("⏱️ Tiempo total: %.2f s", time.time() - t0_total)

if __name__ == "__main__":
    main()
