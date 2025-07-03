#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debug_bbox_linea.py — Dibuja los bounding boxes de los caracteres detectados por pytesseract.image_to_boxes
en una línea específica del PDF OCR procesado, mostrando también la altura individual, mediana y el tamaño en puntos tipográficos estimado.

Uso:
  python debug_bbox_linea.py --pdf datos/original.pdf --ocr datos/ocr_lineas.json --pagina 6 --texto "„Die Sache mag sein, wie sie will, so muß"
"""

import argparse
from pathlib import Path
import json
from pdf2image import convert_from_path
from pytesseract import image_to_boxes
from PIL import Image, ImageDraw
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default='datos/original.pdf')
    parser.add_argument("--ocr", type=Path, default='datos/ocr_lineas.json')
    parser.add_argument("--pagina", type=int, default=4)
    parser.add_argument("--texto", type=str, default="Zweite bedeutend vermehrte und verbesserte Auflage")
    parser.add_argument("--dpi", type=int, default=400)
    parser.add_argument("--lang", type=str, default="deu-frak+deu")
    parser.add_argument("--out", type=Path, default=Path("debug_bbox.png"))
    parser.add_argument("--factor", type=float, default=1.3, help="Factor de corrección tipográfica")
    args = parser.parse_args()

    with open(args.ocr, encoding="utf-8") as f:
        ocr_data = json.load(f)

    try:
        linea = next(
            b for b in ocr_data
            if isinstance(b, dict)
            and "pagina" in b and "texto" in b
            and b["pagina"] == args.pagina
            and b["texto"].strip() == args.texto.strip()
        )
    except StopIteration:
        print(f"❌ No se encontró la línea con texto '{args.texto}' en la página {args.pagina}")
        return

    bbox = linea["bbox"]

    imagen = convert_from_path(args.pdf, dpi=args.dpi, first_page=args.pagina, last_page=args.pagina)[0]
    recorte = imagen.crop(tuple(bbox))

    try:
        boxes_str = image_to_boxes(recorte, lang=args.lang)
    except:
        print("⚠️ No se pudo usar lang especificado. Usando fallback 'eng'.")
        boxes_str = image_to_boxes(recorte, lang="eng")

    draw = ImageDraw.Draw(recorte)
    w, h = recorte.size
    alturas = []

    for line in boxes_str.strip().splitlines():
        parts = line.split()
        if len(parts) == 6:
            char, x1, y1, x2, y2, _ = parts
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
            y1_inv = h - y1
            y2_inv = h - y2
            altura = abs(y2_inv - y1_inv)
            alturas.append(altura)
            draw.rectangle([x1, y2_inv, x2, y1_inv], outline="red", width=1)
            draw.text((x1, y2_inv - 15), f"{char}", fill="blue")
            draw.text((x1, y1_inv + 2), f"{altura}px", fill="green")

    if alturas:
        mediana_px = np.median(alturas)
        font_size_pt = mediana_px * 72 / args.dpi * args.factor
        draw.text((5, 5), f"Altura mediana: {mediana_px:.1f}px", fill="black")
        draw.text((5, 20), f"Tamaño estimado: {font_size_pt:.2f} pt", fill="black")
        print(f"Altura mediana: {mediana_px:.1f}px")
        print(f"Tamaño estimado: {font_size_pt:.2f} pt")

    recorte.save(args.out)
    print(f"✅ Imagen guardada en: {args.out}")

if __name__ == "__main__":
    main()
