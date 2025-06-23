#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_ocr.py — índice limpio (título + nº), resto de páginas normal.

▸ Páginas de índice  (–-index-pages):
    • OCR psm 6.
    • Glifos Fraktur mapeados (M→11, B/H→13…).
    • Alfombra filtrada por altura (<25 px).
    • Nº = último token dígito (x ≥ 2750) o, de fallback,
      último grupo \d{1,3} en la línea cruda.
    • Encabezados (“Inhaltsverzeichnis”, “Seite”) se guardan.

▸ Páginas normales: OCR línea-a-línea (psm configurable).
▸ Añade bloques {"tipo":"imagen"} con pdfplumber.
"""

from pathlib import Path
import argparse, json, logging, re, time, unicodedata

import pdfplumber
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output
from PIL import Image

# ── parámetros finos ─────────────────────────────────────────────
DEFAULT_DPI = 400
NUM_COL_X   = 2750   # corte vertical (px) de la columna num.
MIN_H       = 25     # altura mínima (px) para token útil

FRAKTUR_MAP = {"M": "11", "MM": "11", "B": "13", "H": "13"}
DIGIT_RE    = re.compile(r'^\d{1,3}$')
PUNCT_RE    = re.compile(r'^[.:·\-]+$')

# ── CLI ──────────────────────────────────────────────────────────
def cli():
    ap = argparse.ArgumentParser("OCR índice limpio")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", "-o", type=Path)
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--lang", "-l", default="deu-frak+deu")
    ap.add_argument("--psm", type=int, default=4, help="PSM para páginas normales")
    ap.add_argument("--index-pages", nargs="*", type=int, help="Páginas índice 1-based")
    ap.add_argument("--pages", nargs="*", type=int, help="Procesar sólo estas páginas")
    return ap.parse_args()

# ── helpers OCR ─────────────────────────────────────────────────
def ocr(pil: Image.Image, lang: str, psm: int):
    cfg = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    return image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg)

def strip_acc(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii","ignore").decode()

# ── página índice → bloques limpios ────────────────────────────
def process_index(pil: Image.Image, lang: str, page_no: int):
    d = ocr(pil, lang, psm=6)
    groups = {}
    for i, txt in enumerate(d["text"]):
        if txt.strip():
            k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            groups.setdefault(k, []).append(i)

    items = []
    for idxs in groups.values():
        xs = [d["left"][i] for i in idxs]
        ys = [d["top"][i]  for i in idxs]
        ws = [d["width"][i] for i in idxs]
        hs = [d["height"][i] for i in idxs]
        max_x = max(x + w for x, w in zip(xs, ws))
        max_y = max(y + h for y, h in zip(ys, hs))

        # tokens ordenados por X
        idxs.sort(key=lambda j: d["left"][j])
        tokens = [(d["left"][j],
                   d["height"][j],
                   FRAKTUR_MAP.get(d["text"][j].strip(),
                                   d["text"][j].strip()))
                  for j in idxs]

        # candidatos número (altura suficiente)
        cand = [(x, h, w) for x, h, w in tokens
                if h >= MIN_H and DIGIT_RE.fullmatch(w)]
        right = [t for t in cand if t[0] >= NUM_COL_X]
        num_tok = max(right, key=lambda t: t[0]) if right \
                  else (max(cand, key=lambda t: t[0]) if cand else None)

        num = num_x = None
        if num_tok:
            num, num_x = num_tok[2], num_tok[0]
        else:
            raw = " ".join(t[2] for t in tokens)
            m = re.findall(r'\d{1,3}', raw)
            if m:
                num = m[-1]; num_x = max_x

        # encabezado (sin número)
        if not num:
            header = " ".join(strip_acc(t[2]) for t in tokens
                              if t[1] >= MIN_H and not PUNCT_RE.fullmatch(t[2]))
            if header:
                items.append({"bbox": [min(xs), min(ys), max_x, max_y],
                              "texto": header,
                              "alineacion": "centro",
                              "tipo": "encabezado",
                              "pagina": page_no})
            continue

        # título limpio
        titulo = " ".join(t[2] for t in tokens
                          if t[0] < num_x and
                             t[1] >= MIN_H and
                             not PUNCT_RE.fullmatch(t[2]))
        if not titulo:
            continue

        items.append({"bbox": [min(xs), min(ys), max_x, max_y],
                      "texto": f"{titulo} {num}",
                      "alineacion": "indice",
                      "tipo": "linea",
                      "pagina": page_no})
    items.sort(key=lambda it: it["bbox"][1])
    return items

# ── página normal (ocr línea-a-línea) ───────────────────────────
def process_normal(pil: Image.Image, lang: str, psm: int, page_no: int):
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
        out.append({"bbox": [min(xs), min(ys),
                             max(x + w for x, w in zip(xs, ws)),
                             max(y + h for y, h in zip(ys, hs))],
                    "texto": " ".join(d["text"][i].strip() for i in idxs),
                    "alineacion": "izquierda",
                    "tipo": "linea",
                    "pagina": page_no})
    return out

# ── bloques imagen ───────────────────────────────────────────────
def image_blocks(pdf: Path, page: int):
    out = []
    with pdfplumber.open(pdf) as doc:
        for img in doc.pages[page-1].images:
            out.append({"bbox": [img["x0"], img["top"], img["x1"], img["bottom"]],
                        "tipo": "imagen",
                        "pagina": page})
    return out

# ── MAIN ─────────────────────────────────────────────────────────
def main():
    args = cli()
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    total = pdfinfo_from_path(args.pdf)["Pages"]
    pages = args.pages or range(1, total + 1)

    salida, t0 = [], time.time()
    for p in pages:
        # ←——  *** NUEVA LÍNEA DE LOG ***
        logging.info("Procesando página %s (%s)",
                 p,
                 "índice" if args.index_pages and p in args.index_pages else "normal")

        pil = convert_from_path(args.pdf, dpi=args.dpi,
                                first_page=p, last_page=p)[0]
        if args.index_pages and p in args.index_pages:
            salida.extend(process_index(pil, args.lang, p))
        else:
            salida.extend(process_normal(pil, args.lang, args.psm, p))
        salida.extend(image_blocks(args.pdf, p))

    out = args.out or args.pdf.with_stem(args.pdf.stem + "_ocr_lineas.json")
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), "utf-8")
    logging.info("✅ %s items → %s (%.1f s)",
                 len(salida), out, time.time() - t0)


if __name__ == "__main__":
    main()
