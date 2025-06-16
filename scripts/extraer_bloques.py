import fitz  # PyMuPDF
import json
import numpy as np
import sys
import os

def estimar_margen(doc):
    num_pages = len(doc)
    paginas_centro = range(num_pages // 2 - 5, num_pages // 2 + 5)
    bbox_totales = []

    for i in paginas_centro:
        for b in doc[i].get_text("blocks"):
            if b[4].strip():  # texto no vacío
                bbox_totales.append(b[:4])

    x0s = [b[0] for b in bbox_totales]
    y0s = [b[1] for b in bbox_totales]
    x1s = [b[2] for b in bbox_totales]
    y1s = [b[3] for b in bbox_totales]

    margen = [
        round(float(np.percentile(x0s, 5)), 2),
        round(float(np.percentile(y0s, 5)), 2),
        round(float(np.percentile(x1s, 95)), 2),
        round(float(np.percentile(y1s, 95)), 2),
    ]
    print(f"🟦 Margen estimado: {margen}")
    return margen

def agrupar_en_parrafos(bloques_lineas, tolerancia_dinamica):
    parrafos = []
    bloque_actual = []
    y_anterior = None
    log_lines = []

    for linea in bloques_lineas:
        y_actual = linea["bbox"][1]
        texto = linea["texto"]
        pagina = linea["pagina"]

        log_lines.append(f"[DEBUG] Evaluando línea (página {pagina}): {texto}")

        if y_anterior is not None and abs(y_actual - y_anterior) > tolerancia_dinamica:
            if bloque_actual:
                log_lines.append(f"[DEBUG] → Nuevo párrafo con {len(bloque_actual)} líneas")
                parrafos.append(bloque_actual)
            bloque_actual = []

        bloque_actual.append(linea)
        y_anterior = linea["bbox"][3]

    if bloque_actual:
        log_lines.append(f"[DEBUG] → Último párrafo con {len(bloque_actual)} líneas")
        parrafos.append(bloque_actual)

    with open("log_parrafos.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    bloques_parrafo = []
    for grupo in parrafos:
        if not grupo:
            continue
        x0 = min(l["bbox"][0] for l in grupo)
        y0 = min(l["bbox"][1] for l in grupo)
        x1 = max(l["bbox"][2] for l in grupo)
        y1 = max(l["bbox"][3] for l in grupo)
        texto = "\n".join(l["texto"] for l in grupo)
        bloques_parrafo.append({
            "pagina": grupo[0]["pagina"],
            "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
            "texto": texto,
            "font_size": round(np.mean([l["font_size"] for l in grupo]), 2),
            "alineacion": grupo[0]["alineacion"],
            "tipo": "parrafo"
        })
    return bloques_parrafo

def detectar_alineacion(x0, x1, page_width, margen_izq, margen_der, tolerancia=20):
    centro = page_width / 2
    bloque_centro = abs((x0 + x1) / 2 - centro) < tolerancia
    if bloque_centro:
        return "centro"
    elif abs(x0 - margen_izq) < tolerancia:
        return "izquierda"
    elif abs(x1 - margen_der) < tolerancia:
        return "derecha"
    else:
        return "izquierda"

def procesar_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    margen = estimar_margen(doc)
    bloques = []

    for page_num, page in enumerate(doc, start=1):
        width = page.rect.width
        bloques_lineas = []

        lines = page.get_text("dict")["blocks"]
        alturas = []
        for b in lines:
            if "lines" not in b:
                continue
            for l in b["lines"]:
                for s in l["spans"]:
                    x0, y0, x1, y1 = s["bbox"]
                    texto = s["text"].strip()
                    if not texto:
                        continue
                    altura = y1 - y0
                    alturas.append(altura)
                    bloques_lineas.append({
                        "pagina": page_num,
                        "bbox": [x0, y0, x1, y1],
                        "texto": texto,
                        "font_size": s["size"],
                        "alineacion": detectar_alineacion(x0, x1, width, margen[0], margen[2]),
                        "tipo": "parrafo"
                    })

        if alturas:
            tolerancia = round(float(np.percentile(alturas, 80)), 2)
        else:
            tolerancia = 5.0
        print(f"🟦 Tolerancia dinámica estimada: {tolerancia}")
        parrafos = agrupar_en_parrafos(bloques_lineas, tolerancia)
        bloques.extend(parrafos)

    return bloques

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="Ruta al PDF de entrada")
    parser.add_argument("-o", "--output", default="salida.json", help="Archivo de salida JSON")
    args = parser.parse_args()

    resultado = procesar_pdf(args.pdf)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON generado: {args.output}")
