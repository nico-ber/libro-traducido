#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
maquetar_pdf.py — Genera un PDF maquetado a partir de bloques OCR.

Requiere:
- datos/bloques.json con estructura esperada (text, tipo, alineacion, bbox, etc.)
- datos/original.pdf para extraer imágenes originales por bloque (si tipo = imagen)
- datos/CA Moskow has a plan W00 Reg.ttf como tipografía embebida

Funcionalidades:
- Inserta imágenes desde el PDF original
- Inserta texto con alineación izquierda, derecha, centrado y justificado
- Usa márgenes detectados automáticamente de las primeras 20 páginas
- Ubica bloques verticalmente como flujo, respetando espacio entre ellos

Uso:
  python scripts/maquetar_pdf.py --bloques datos/bloques.json --pdf_original datos/original.pdf --salida prueba_maquetado.pdf --pages 4 5 6
"""

import json
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
import os

# --- CONFIG ---
CUSTOM_FONT_PATH = "datos/CA Moskow has a plan W00 Reg.ttf"
CUSTOM_FONT_NAME = "CA_Moskow"
NUM_PAGINAS_MUESTRA = 20
ESPACIO_ENTRE_BLOQUES = 8
TIPOGRAFIA_ESCALA_VISUAL = 1.5  # Ajuste por diferencia con altura visual original
MARGEN_INTERNO_SUP = 0.18  # proporción del font_size
INTERLINEADO = 1.15  # Multiplicador de font_size para espacio entre líneas

# --- FUNCIONES ---
def detectar_margenes(pdf_path, num_paginas=10):
    doc = fitz.open(pdf_path)
    lefts, rights, tops, bottoms = [], [], [], []
    for i in range(min(len(doc), num_paginas)):
        page = doc[i]
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            if b.get("type") != 0:  # solo texto
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    x0, y0, x1, y1 = s.get("bbox", [0, 0, 0, 0])
                    lefts.append(x0)
                    rights.append(x1)
                    tops.append(y0)
                    bottoms.append(y1)
    doc.close()
    if not lefts:
        return 50, 50, 50, 50
    return min(lefts), max(rights), min(tops), max(bottoms)

def extract_image_from_pdf(pdf_path, page_num, bbox, out_img_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    pix = page.get_pixmap(clip=fitz.Rect(bbox))
    pix.save(out_img_path)
    doc.close()

def draw_image(c, pdf_path, bloque, page_height):
    page_num = bloque.get('pagina', 1) - 1
    bbox = bloque.get('bbox') or [
        bloque.get('x_left', 0),
        bloque.get('y_top', 0),
        bloque.get('x_right', 0),
        bloque.get('y_bottom', 0),
    ]
    x0, y0, x1, y1 = bbox
    if x0 >= x1 or y0 >= y1:
        return
    width = x1 - x0
    height = y1 - y0
    y_draw = page_height - y1
    img_path = f"temp_img_{page_num+1}_{x0}_{y0}.png"
    try:
        extract_image_from_pdf(pdf_path, page_num, bbox, img_path)
        c.drawImage(img_path, x0, y_draw, width=width, height=height)
        os.remove(img_path)
    except Exception as e:
        print(f"[ERROR] No se pudo insertar imagen {img_path}: {e}")

def draw_text(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf):
    salto_pagina_ocurrio = False
    texto = bloque.get('text') or bloque.get('texto', '')
    if not texto.strip():
        return y_actual  # se sale antes de usar font_size si no hay texto
    font_size = bloque.get('font_size', 12) * TIPOGRAFIA_ESCALA_VISUAL
    c.setFont(CUSTOM_FONT_NAME, font_size)
    pagina = bloque.get('pagina', '?')
    max_width = page_width - margen_izq - margen_der
    lineas = simpleSplit(texto, CUSTOM_FONT_NAME, font_size, max_width)
    alineacion = (bloque.get('alineacion', 'izquierda') or '').lower()
    print(f"[BLOQUE] pág={pagina}, font={font_size:.1f}, líneas estimadas={len(lineas)}")
    line_height = font_size * INTERLINEADO
    altura_total = len(lineas) * line_height

    y = y_actual - font_size
    for i, linea in enumerate(lineas):
        if y - line_height < margen_inf:
            print(f"[SALTO AUTOMÁTICO] Salto de página en medio de bloque en página actual")
            salto_pagina_ocurrio = True
            c.showPage()
            c.setFont(CUSTOM_FONT_NAME, font_size)
            y = page_height - margen_sup - font_size
        es_ultima = (i == len(lineas) - 1)
        if alineacion in ['centrado', 'centro', 'center']:
            c.drawCentredString(page_width / 2, y, linea)
        elif alineacion in ['derecha', 'right']:
            c.drawRightString(page_width - margen_der, y, linea)
        elif alineacion == 'justificado' and bloque.get('unilinea') and texto.isupper():
            draw_justified_letters(c, texto, margen_izq, y, max_width, font_size)
        elif alineacion == 'justificado' and len(linea.strip().split()) > 1 and not es_ultima:
            draw_justified(c, linea, margen_izq, y, max_width, font_size)
        else:
            c.drawString(margen_izq, y, linea)
        y -= line_height

    return y, True, salto_pagina_ocurrio  # devuelve posición vertical final

def draw_justified(c, text, x, y, width, font_size):
    words = text.strip().split()
    if len(words) <= 1:
        c.drawString(x, y, text)
        return
    total_text_width = sum(pdfmetrics.stringWidth(w, CUSTOM_FONT_NAME, font_size) for w in words)
    space_width = (width - total_text_width) / (len(words) - 1)
    x_pos = x
    for word in words:
        c.drawString(x_pos, y, word)
        x_pos += pdfmetrics.stringWidth(word, CUSTOM_FONT_NAME, font_size) + space_width

def draw_justified_letters(c, text, x, y, width, font_size):
    chars = list(text.strip())
    if len(chars) <= 1:
        c.drawString(x, y, text)
        return
    total_width = sum(pdfmetrics.stringWidth(ch, CUSTOM_FONT_NAME, font_size) for ch in chars)
    spacing = (width - total_width) / (len(chars) - 1)
    x_pos = x
    for ch in chars:
        c.drawString(x_pos, y, ch)
        x_pos += pdfmetrics.stringWidth(ch, CUSTOM_FONT_NAME, font_size) + spacing

# --- MAIN ---
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bloques', default='datos/bloques.json')
    parser.add_argument('--pdf_original', default='datos/original.pdf')
    parser.add_argument('--salida', default='datos/maquetado.pdf')
    parser.add_argument('--pages', nargs='+', type=int)
    args = parser.parse_args()

    # Cargar y registrar fuente
    pdfmetrics.registerFont(TTFont(CUSTOM_FONT_NAME, CUSTOM_FONT_PATH))

    # Medidas base del PDF
    doc = fitz.open(args.pdf_original)
    page = doc.load_page(0)
    page_width = page.rect.width
    page_height = page.rect.height
    doc.close()

    margen_izq, margen_der, margen_sup, margen_inf = detectar_margenes(args.pdf_original, NUM_PAGINAS_MUESTRA)
    MARGEN_SUPERIOR_PX = page_height * 0.05
    MARGEN_INFERIOR_PX = page_height * 0.05

    with open(args.bloques, 'r', encoding='utf-8') as f:
        bloques = json.load(f)
    bloques = [b for b in bloques if b.get('tipo') != 'numero_pagina' and not b.get('omitido')]

    if args.pages:
        bloques = [b for b in bloques if b.get('pagina') in args.pages]

    bloques.sort(key=lambda b: (b.get('pagina', 1), b.get('y_top', 0)))

    min_y_ocr = min(b.get('y_top', 0) for b in bloques)
    max_y_ocr = max(b.get('y_bottom', 0) for b in bloques)
    alto_ocr = max_y_ocr - min_y_ocr
    rel_font = page_height / alto_ocr if alto_ocr else 1.0

    print("---- Diagnóstico vertical ----")
    print(f"page_height = {page_height}")
    print(f"min_y_ocr = {min_y_ocr}")
    print(f"alto_ocr = {alto_ocr}")
    print(f"rel_font = {rel_font}\n")

    c = canvas.Canvas(args.salida, pagesize=(page_width, page_height))

    pagina_actual = None
    y_cursor = page_height - MARGEN_SUPERIOR_PX
    pagina_forzada = False

    for bloque in bloques:
        pagina = bloque.get('pagina', 1)
        tipo = (bloque.get('tipo', '') or '').lower()

        if pagina != pagina_actual:
            if not pagina_forzada and pagina_actual is not None:
                c.showPage()
            pagina_actual = pagina
            if not pagina_forzada:
                y_cursor = page_height - MARGEN_SUPERIOR_PX
            pagina_forzada = False  # se resetea siempre

        if tipo == 'imagen':
            draw_image(c, args.pdf_original, bloque, page_height)
        elif tipo in ['linea', 'encabezado', 'titulo', 'cita', 'indice', 'parrafo']:
            font_size = bloque.get('font_size', 12) * TIPOGRAFIA_ESCALA_VISUAL
            y_cursor, dibujado, pagina_forzada = draw_text(c, bloque, page_width, y_cursor, rel_font, margen_izq, page_width - margen_der, page_height, MARGEN_SUPERIOR_PX, MARGEN_INFERIOR_PX)
            espacio = bloque.get("espacio_despues", ESPACIO_ENTRE_BLOQUES)
            
        # Saltar página si el bloque requiere salto explícito
        
        print("bloque evaluado", bloque["pagina"])
    y_cursor -= espacio * rel_font

    c.save()
    print(f"PDF maquetado generado: {args.salida}")

if __name__ == '__main__':
    main()
