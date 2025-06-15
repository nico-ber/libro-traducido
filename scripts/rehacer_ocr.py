# rehacer_ocr.py

import os
import sys
import subprocess

def instalar_dependencias():
    try:
        import pytesseract
        import pdf2image
        import PIL
    except ImportError:
        print("🔧 Instalando dependencias necesarias...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract", "pdf2image", "Pillow"])

def verificar_tesseract():
    if not shutil.which("tesseract"):
        raise EnvironmentError("❌ Tesseract no está instalado o no está en el PATH.")

def rehacer_ocr(pdf_path, idioma="deu-frak", dpi=300, output_text="ocr_texto.json"):
    from pdf2image import convert_from_path
    import pytesseract
    import json

    images = convert_from_path(pdf_path, dpi=dpi)
    ocr_resultado = []

    for i, image in enumerate(images):
        texto = pytesseract.image_to_string(image, lang=idioma)
        ocr_resultado.append({
            "pagina": i + 1,
            "texto": texto.strip()
        })
        print(f"📝 OCR completado para página {i + 1}")

    with open(output_text, "w", encoding="utf-8") as f:
        json.dump(ocr_resultado, f, ensure_ascii=False, indent=2)

    print(f"✅ OCR terminado. Resultado guardado en {output_text}")

if __name__ == "__main__":
    import shutil
    import argparse

    instalar_dependencias()
    verificar_tesseract()

    parser = argparse.ArgumentParser(description="Rehacer OCR de un PDF utilizando Tesseract")
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("-l", "--lang", default="deu-frak", help="Idioma OCR (por defecto: deu-frak)")
    parser.add_argument("-o", "--output", default="ocr_texto.json", help="Archivo de salida del texto OCR")
    args = parser.parse_args()

    rehacer_ocr(args.pdf, idioma=args.lang, output_text=args.output)
