import json
import fitz  # PyMuPDF

def analizar_bloques(bloques, pdf_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pdf_height = page.rect.height
    doc.close()

    altos_bbox = []
    altos_font = []
    for bloque in bloques:
        if 'bbox' in bloque:
            altos_bbox.append(bloque['bbox'][3])
        for k in ['font_size', 'fontsize', 'tamano_fuente', 'size']:
            if k in bloque:
                altos_font.append(bloque[k])

    max_bbox = max(altos_bbox) if altos_bbox else None
    max_font = max(altos_font) if altos_font else None

    print(f"Alto PDF (pt): {pdf_height}")
    print(f"Máximo Y bbox en bloques: {max_bbox}")
    print(f"Máximo font_size en bloques: {max_font}")

    if abs(pdf_height - max_bbox) < 2:
        print("-> El bbox está en escala de puntos PDF. ¡Podés usar font_size directamente!")
    else:
        print("-> El bbox NO está en escala de puntos PDF. Necesitás escalar font_size.")
        print("  Usa font_size_pt = font_size_bloque * (pdf_height / alto_pagina_px)")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bloques', required=True)
    parser.add_argument('--pdf_original', required=True)
    args = parser.parse_args()

    with open(args.bloques, 'r', encoding='utf-8') as f:
        bloques = json.load(f)

    analizar_bloques(bloques, args.pdf_original)
