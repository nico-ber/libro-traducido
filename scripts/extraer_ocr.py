import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output
from PIL import Image
import json
import io
import os
import argparse
import tempfile

def cargar_configuracion(config_path='config.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def procesar_pagina(pagina, dpi=300, lang="eng", pagina_idx=0):
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = pagina.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    ocr_data = pytesseract.image_to_data(img, lang=lang, output_type=Output.DICT)

    bloques = []
    for i in range(len(ocr_data["text"])):
        texto = ocr_data["text"][i].strip()
        if texto:
            x, y, w, h = (ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i])
            bbox = [round(x, 2), round(y, 2), round(x + w, 2), round(y + h, 2)]

            bloques.append({
                "pagina": pagina_idx + 1,
                "bbox": bbox,
                "texto": texto,
                "font_size": None,
                "alineacion": "izquierda",
                "tipo": "parrafo"
            })

    return bloques

def procesar_pdf(path_pdf, config):
    doc = fitz.open(path_pdf)
    todos_bloques = []

    for idx, pagina in enumerate(doc):
        print(f"🔍 Procesando página {idx + 1}/{len(doc)}...")
        bloques = procesar_pagina(pagina, dpi=config["dpi"], lang=config["ocr_language"], pagina_idx=idx)
        todos_bloques.extend(bloques)

    return todos_bloques

def guardar_json(data, path_salida):
    with open(path_salida, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer OCR de un PDF con Tesseract.")
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("-c", "--config", default="config.json", help="Ruta al archivo de configuración")

    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"❌ No se encontró el archivo PDF: {args.pdf}")
        exit(1)
    if not os.path.exists(args.config):
        print(f"❌ No se encontró el archivo de configuración: {args.config}")
        exit(1)

    config = cargar_configuracion(args.config)
    resultado = procesar_pdf(args.pdf, config)
    guardar_json(resultado, config["output_json"])

    print(f"✅ OCR guardado en: {config['output_json']}")
