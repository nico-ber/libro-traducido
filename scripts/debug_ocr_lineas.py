#!/usr/bin/env python3
# debug_ocr_lineas.py
#   python debug_ocr_lineas.py original.pdf 9 --dpi 600 --lang deu-frak+deu

import argparse, json
from pathlib import Path
from pdf2image import convert_from_path
from pytesseract import image_to_data, Output
from PIL import Image, ImageDraw

def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("page", type=int)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--lang", default="deu-frak+deu")
    return ap.parse_args()

def main():
    a=cli()
    pil = convert_from_path(a.pdf, dpi=a.dpi,
                            first_page=a.page, last_page=a.page)[0]
    d = image_to_data(pil, lang=a.lang, output_type=Output.DICT,
                      config="--psm 6 --oem 1")
    print(f"{'ln':>3}  {'x':>5}  {'h':>3}  text")
    print("-"*40)
    for i, txt in enumerate(d["text"]):
        if txt.strip():
            ln = d["line_num"][i]
            x  = d["left"][i]
            h  = d["height"][i]
            isnum = " <num>" if txt.strip().isdigit() else ""
            print(f"{ln:>3}  {x:>5}  {h:>3}  {txt.strip()}{isnum}")

if __name__ == "__main__":
    main()
