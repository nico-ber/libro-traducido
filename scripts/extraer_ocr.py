
"""extraer_ocr.py – Versión con progreso también durante la conversión
=======================================================================
• Procesa **página por página**: evita que `convert_from_path` cargue todo el PDF
  en memoria antes de empezar el OCR.
• Muestra barra de progreso desde la primera etapa (render del PDF).
"""

import argparse
import json
import logging
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from pytesseract import image_to_data, Output

DEFAULT_DPI = 400
LOG = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="OCR a PDF completo → JSON agrupado por líneas")
    ap.add_argument("pdf", help="Ruta al PDF de entrada")
    ap.add_argument("--out", "-o", default="ocr_result.json", help="Archivo JSON de salida")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI al convertir páginas a imagen")
    ap.add_argument("--lang", "-l", help="Idioma(s) de Tesseract (ej. deu-frak+deu)")
    ap.add_argument("--psm", type=int, default=4, help="Page‑Segmentation‑Mode de Tesseract (1‑13)")
    ap.add_argument("--debug", action="store_true", help="Guarda PNG y TSV intermedios en ./debug_ocr/")
    ap.add_argument("--no-preproc", action="store_true", help="Desactiva el preprocesamiento de la imagen")
    ap.add_argument("--first", type=int, help="Página inicial (1‑based)")
    ap.add_argument("--last", type=int, help="Página final (incluida)")
    return ap.parse_args()


def load_language(cli_lang: str | None = None) -> str:
    if cli_lang:
        return cli_lang
    cfg_path = Path("config.json")
    if cfg_path.exists():
        return json.loads(cfg_path.read_text("utf-8")).get("ocr_language", "eng")
    return "eng"


def preprocess_img(pil_img: Image.Image) -> Image.Image:
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 15)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((1, 1), np.uint8), 1)
    return Image.fromarray(opened)


def ocr_image(img: Image.Image, language: str, psm: int, debug_dir: Path | None, page_num: int) -> list[dict]:
    cfg = f"--psm {psm} --oem 3 -c preserve_interword_spaces=1"
    data = image_to_data(img, lang=language, output_type=Output.DICT, config=cfg)

    if debug_dir:
        tsv_path = debug_dir / f"page_{page_num:04d}.tsv"
        keys = data.keys()
        with tsv_path.open("w", encoding="utf-8") as fh:
            fh.write("\t".join(keys) + "\n")
            for i in range(len(data["level"])):  # type: ignore
                fh.write("\t".join(str(data[k][i]) for k in keys) + "\n")

    lines = {}
    for i in range(len(data["level"])):  # type: ignore
        txt = data["text"][i].strip()
        if not txt:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        bbox = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
        lines.setdefault(key, []).append((*bbox, txt))

    resultado = []
    for words in lines.values():
        words.sort(key=lambda w: w[0])
        texto = " ".join(w[4] for w in words)
        x0 = min(w[0] for w in words); y0 = min(w[1] for w in words)
        x1 = max(w[0] + w[2] for w in words); y1 = max(w[1] + w[3] for w in words)
        resultado.append({"bbox": [x0, y0, x1, y1], "texto": texto,
                          "alineacion": "izquierda", "tipo": "linea"})
    return resultado


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    lang = load_language(args.lang)
    LOG.info("Idioma: %s", lang)

    info = pdfinfo_from_path(args.pdf, userpw=None, poppler_path=None)
    total_pages = info["Pages"]
    first = args.first or 1
    last = args.last or total_pages
    LOG.info("Páginas a procesar: %s‑%s de %s", first, last, total_pages)

    debug_dir = Path("debug_ocr")
    if args.debug:
        shutil.rmtree(debug_dir, ignore_errors=True)
        debug_dir.mkdir()

    salida = []
    t0_total = time.time()
    for p in range(first, last + 1):
        t0 = time.time()
        print(f"\r🖼️  Render pág {p}/{total_pages}…", end="", flush=True)
        page_img = convert_from_path(
            args.pdf, dpi=args.dpi, first_page=p, last_page=p, thread_count=1
        )[0]

        if not args.no_preproc:
            page_img = preprocess_img(page_img)
        if args.debug:
            page_img.save(debug_dir / f"page_{p:04d}.png")

        print(f"  📝 OCR…", end="", flush=True)
        bloques = ocr_image(page_img, lang, args.psm, debug_dir if args.debug else None, p)
        for b in bloques:
            b["pagina"] = p
            salida.append(b)
        print(f"  ✔️  ({time.time()-t0:.1f}s)", end="", flush=True)

    Path(args.out).write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ OCR listo → {args.out}  Líneas: {len(salida)}  Tiempo total: {(time.time()-t0_total)/60:.1f} min")


if __name__ == "__main__":
    main()
