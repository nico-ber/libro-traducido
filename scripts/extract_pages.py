#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_pages.py — Extrae un rango de páginas de un PDF y lo guarda en otro archivo.

Uso:
  python extract_pages.py input.pdf output.pdf 4-11
  python extract_pages.py input.pdf output.pdf 2 5 7   # páginas sueltas
  python extract_pages.py input.pdf output.pdf 1-3 6 9-12

Argumentos:
  input.pdf   → archivo de entrada
  output.pdf  → archivo de salida
  rangos      → páginas o rangos separados por espacio (ej: 1-3 5 7-9)

Nota:
  - Las páginas se numeran desde 1.
  - Se pueden mezclar páginas sueltas y rangos.
"""

import sys
from PyPDF2 import PdfReader, PdfWriter

def parse_ranges(range_strs):
    pages = []
    for r in range_strs:
        if "-" in r:
            start, end = r.split("-")
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(r))
    return sorted(set(pages))

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    range_strs = sys.argv[3:]

    pages_to_extract = parse_ranges(range_strs)

    reader = PdfReader(open(input_pdf, "rb"))
    writer = PdfWriter()

    for p in pages_to_extract:
        if 1 <= p <= len(reader.pages):
            writer.add_page(reader.pages[p-1])
        else:
            print(f"⚠️ Página {p} fuera de rango (máximo {len(reader.pages)})")

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"✅ {len(pages_to_extract)} páginas extraídas a {output_pdf}")

if __name__ == "__main__":
    main()
