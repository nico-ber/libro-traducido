#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analizar_densidad_caracter.py — Calcula densidad visual de letras individuales.

Usa:
- OCR por líneas (ocr_lineas.json)
- OCR por letras (pytesseract.image_to_boxes)
- PDF original escaneado
- Etiquetas manuales de líneas en negrita (negrita_lineas.json)

Salida:
- perfil_densidad_letras.json con densidades separadas por letra y estilo (normal/negrita)
"""

import json
import argparse
from collections import defaultdict
from pathlib import Path

import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
from PIL import Image
import numpy as np

def cargar_lineas_ocr(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def cargar_etiquetas(path):
    with open(path, "r", encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items()}

def intersecta(bbox_char, bbox_linea):
    # Ambos en formato [x0, y0, x1, y1]
    cx0, cy0, cx1, cy1 = bbox_char
    lx0, ly0, lx1, ly1 = bbox_linea
    return not (cx1 < lx0 or cx0 > lx1 or cy1 < ly0 or cy0 > ly1)

def bbox_tesseract_to_xyxy(b, altura_img):
    # Convierte bbox de Tesseract (x0, y0, x1, y1) con coordenadas invertidas
    x0, y0, x1, y1 = b
    return [x0, altura_img - y1, x1, altura_img - y0]

def calcular_densidad(crop):
    binaria = crop.convert("L").point(lambda p: p < 128 and 255)
    np_binaria = np.array(binaria)
    tinta = np.sum(np_binaria == 255)
    area = np_binaria.shape[0] * np_binaria.shape[1]
    return tinta / area if area > 0 else 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="PDF escaneado")
    parser.add_argument("lineas_json", help="Archivo ocr_lineas.json")
    parser.add_argument("etiquetas_json", help="Archivo negrita_palabras.json")
    parser.add_argument("--pages", nargs="+", type=int, help="Páginas a procesar (1-indexadas)")
    parser.add_argument("--out", default="perfil_densidad_letras.json", help="Archivo de salida")
    args = parser.parse_args()

    lineas_ocr = cargar_lineas_ocr(args.lineas_json)
    etiquetas = cargar_etiquetas(args.etiquetas_json)

    paginas = sorted({l["pagina"] for l in lineas_ocr})
    if args.pages:
        paginas = [p for p in args.pages if p in paginas]

    imagenes = convert_from_path(args.pdf, dpi=300, first_page=min(paginas), last_page=max(paginas))

    perfil = defaultdict(lambda: {"normal": [], "negrita": []})

    for i, pagina in enumerate(paginas):
        pil = imagenes[pagina - min(paginas)]
        ancho, alto = pil.size

        boxes_str = pytesseract.image_to_boxes(pil, lang="deu", config="", output_type=Output.STRING)
        for linea_ocr_idx, linea in enumerate(l for l in lineas_ocr if l["pagina"] == pagina):
            bbox_linea = linea["bbox"]  # x0, y0, x1, y1
            estilo = "negrita" if linea_ocr_idx in etiquetas.get(pagina, []) else "normal"

            for box_line in boxes_str.strip().split("\n"):
                partes = box_line.split()
                if len(partes) != 6:
                    continue
                letra, x0, y0, x1, y1, _ = partes
                x0, y0, x1, y1 = map(int, [x0, y0, x1, y1])
                bbox = bbox_tesseract_to_xyxy([x0, y0, x1, y1], alto)

                if intersecta(bbox, bbox_linea):
                    crop = pil.crop(bbox)
                    densidad = calcular_densidad(crop)
                    perfil[letra][estilo].append(densidad)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)

    print(f"✅ Perfil generado: {args.out}")

if __name__ == "__main__":
    main()
