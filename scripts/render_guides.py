#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_guides.py – Dibuja guías verticales etiquetadas

Uso de ejemplo:
  python render_guides.py original.pdf 9 \
         --dpi 400 --step 200 --out pagina9_guias.png
"""

import argparse
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt

def parse_cli():
    ap = argparse.ArgumentParser(description="Renderiza página con guías y etiquetas")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("page", type=int, help="Página (1-based)")
    ap.add_argument("--dpi",  type=int, default=300,  help="Resolución DPI")
    ap.add_argument("--step", type=int, default=200, help="Paso entre guías px")
    ap.add_argument("--out",  type=Path, default=Path("guides.png"))
    ap.add_argument("--font", type=str, help="Ruta a .ttf para las etiquetas")
    ap.add_argument("--size", type=int, default=28, help="Tamaño de fuente px")
    return ap.parse_args()

def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """Compatibilidad Pillow <10 y ≥10."""
    try:                      # Pillow ≥10
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w, h
    except AttributeError:    # Pillow <10
        return draw.textsize(text, font=font)

def main():
    args = parse_cli()
    # 1) PDF → imagen
    pil = convert_from_path(args.pdf, dpi=args.dpi,
                            first_page=args.page, last_page=args.page)[0]
    w, h = pil.size
    draw = ImageDraw.Draw(pil)

    # 2) fuente
    try:
        font = ImageFont.truetype(args.font, args.size) if args.font else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # 3) dibujar guías + etiqueta
    for x in range(0, w, args.step):
        draw.line([(x, 0), (x, h)], fill="red", width=2)
        label = str(x)
        tw, th = text_size(draw, label, font)
        # fondo blanco translúcido para legibilidad
        draw.rectangle([x - tw // 2 - 4, 0, x + tw // 2 + 4, th + 4],
                       fill=(255, 255, 255, 200))
        draw.text((x - tw // 2, 2), label, fill="blue", font=font)

    # 4) guardar y mostrar
    pil.save(args.out)
    print(f"Imagen con guías guardada en {args.out.resolve()}")

    plt.figure(figsize=(10, 14))
    plt.imshow(pil)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
