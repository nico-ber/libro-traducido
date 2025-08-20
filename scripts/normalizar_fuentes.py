#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
normalizar_fuentes.py — Analiza todas las páginas de un PDF para crear clusters de tamaños de fuente normalizados.

Este script extrae las alturas de texto de todas las páginas del PDF y las agrupa en clusters
para normalizar los tamaños de fuente. Los clusters se guardan en un archivo JSON que puede
ser usado por extraer_ocr.py para asignar tamaños normalizados.

▸ Salida:
    - clusters.json: Lista de tamaños de fuente normalizados en puntos
    - debug: Información detallada sobre el proceso de agrupación

▸ Parámetros CLI:
    --pdf             Ruta al archivo PDF de entrada
    --out, -o         Ruta de salida para los clusters (default: clusters.json)
    --dpi             Resolución de rasterizado (default: 400)
    --lang, -l        Idioma OCR (Tesseract)
    --psm             Page segmentation mode (default: 4)
    --pages           Páginas específicas o rangos (e.g. 5-8 10)
    --tolerancia      Tolerancia para agrupación (default: 0.6)
    --debug           Muestra logs detallados
"""

from pathlib import Path
import argparse, json, logging, time
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output
from statistics import mean
import numpy as np

def expand_pages(pagelist):
    """Expande rangos de páginas (e.g. '5-8') en listas de números."""
    if not pagelist:
        return []
    result = []
    for p in pagelist:
        if isinstance(p, str) and '-' in p:
            start, end = map(int, p.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(p))
    return sorted(set(result))

def agrupar_por_tolerancia(valores, tolerancia=0.6):
    """Agrupa valores numéricos por tolerancia."""
    valores_ordenados = sorted(valores)
    grupos, actual = [], []
    for v in valores_ordenados:
        if not actual or abs(v - mean(actual)) <= tolerancia:
            actual.append(v)
        else:
            grupos.append(actual)
            actual = [v]
    if actual:
        grupos.append(actual)
    return [mean(g) for g in grupos]

def ocr(pil, lang: str, psm: int):
    """Ejecuta OCR en una imagen."""
    cfg = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    return image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg)

def cli():
    """Configura los argumentos de línea de comandos."""
    ap = argparse.ArgumentParser(description="Normaliza tamaños de fuente de un PDF")
    ap.add_argument("--pdf", type=Path, default=Path("./datos/original.pdf"))
    ap.add_argument("--out", "-o", type=Path, default=Path("./datos/clusters.json"))
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--lang", "-l", default="deu-frak+deu")
    ap.add_argument("--psm", type=int, default=4)
    ap.add_argument("--pages", nargs="*", type=str)
    ap.add_argument("--tolerancia", type=float, default=0.6)
    ap.add_argument("--debug", action="store_true", default=True)
    return ap.parse_args()

def main():
    """Función principal que ejecuta la normalización."""
    t0_total = time.time()
    args = cli()

    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler("normalizacion_debug.log", mode="w", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    # Obtener información del PDF
    total = pdfinfo_from_path(args.pdf)["Pages"]
    pages = expand_pages(args.pages) or range(1, total + 1)
    
    logging.info(f"📄 PDF: {args.pdf} ({total} páginas)")
    logging.info(f"📋 Páginas a procesar: {list(pages)}")
    logging.info(f"🎯 Tolerancia de agrupación: {args.tolerancia}")

    # Extraer alturas de todas las páginas
    all_heights_pt = []
    
    for p in pages:
        t0 = time.time()
        logging.info(f"Procesando página {p} para normalización...")
        
        # Convertir página a imagen
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        
        # Ejecutar OCR
        d = ocr(pil, args.lang, args.psm)
        
        # Extraer alturas de texto
        heights_px = [d["height"][i] for i, txt in enumerate(d["text"]) if txt.strip()]
        heights_pt = [h * 72 / args.dpi for h in heights_px]
        all_heights_pt.extend(heights_pt)
        
        logging.info(f"⏱️ Página {p}: {len(heights_pt)} elementos en {time.time() - t0:.2f}s")

    # Crear clusters
    logging.info(f"📊 Total de alturas extraídas: {len(all_heights_pt)}")
    
    if not all_heights_pt:
        logging.warning("⚠️ No se encontraron elementos de texto para normalizar")
        clusters = []
    else:
        clusters = [round(c) for c in agrupar_por_tolerancia(all_heights_pt, tolerancia=args.tolerancia)]
        
        if args.debug:
            logging.info("\n[debug] Distribución de tamaños:")
            for c in sorted(set(clusters)):
                count = sum(1 for h in all_heights_pt if abs(h - c) <= args.tolerancia)
                logging.info(f"  - {c} pt: {count} elementos")
    
    # Guardar clusters
    output_data = {
        "clusters": clusters,
        "metadata": {
            "pdf": str(args.pdf),
            "total_pages": total,
            "pages_processed": list(pages),
            "dpi": args.dpi,
            "lang": args.lang,
            "tolerancia": args.tolerancia,
            "total_elements": len(all_heights_pt),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    args.out.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), "utf-8")
    
    logging.info(f"✅ Clusters guardados: {len(clusters)} tamaños → {args.out}")
    logging.info(f"⏱️ Tiempo total: {time.time() - t0_total:.2f}s")
    
    if clusters:
        logging.info(f"📏 Tamaños normalizados: {sorted(clusters)}")

if __name__ == "__main__":
    main()
