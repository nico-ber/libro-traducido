#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraer_ocr.py — Extrae líneas OCR de un PDF, añade tamaños de fuente y detecta estilos (negrita, itálica) usando etiquetas HTML.

▸ Cada línea incluye:
    - bbox: coordenadas de la línea
    - texto: texto enriquecido con etiquetas <b> y <i>
    - altura_px: altura base en píxeles
    - grupo_fuente: grupo de letras usado como referencia
    - font_size_pt: tamaño estimado en puntos
    - font_size_pt_norm: (opcional) tamaño agrupado globalmente usando clusters pre-procesados

▸ Bloques de imagen:
    - Si no se usa --no-images, se añaden bloques {"tipo": "imagen", "pagina": X, "bbox": [...]} con coordenadas de cada imagen

▸ Heurística para detección de estilo:

    - **Negrita (bold)**:
        Basada en la densidad de tinta por píxel, calculada como:
            densidad = (pixeles con tinta) / (pixeles totales)
        Se estima la densidad esperada según el tamaño de fuente:
            densidad_esperada = a * font_size_pt + b
        La palabra se considera en negrita si:
            densidad > densidad_esperada * 1.6 and densidad - densidad_esperada > 0.05
        Esto permite adaptar el umbral dinámicamente a distintos tamaños de fuente.

    - **Itálica (italic)**:
        Detectada mediante el desplazamiento del centro de masa horizontal del texto
        respecto al centro de la palabra. Si el desplazamiento es superior al 10% del ancho,
        se considera texto inclinado.

▸ Agrupación por estilo:
    - Palabras consecutivas con el mismo conjunto de estilos se agrupan bajo una única
      etiqueta HTML, minimizando etiquetas redundantes.

▸ Normalización de tamaños:
    - Requiere ejecutar primero normalizar_fuentes.py para crear clusters de tamaños
    - Los clusters se cargan desde el archivo especificado con --clusters
    - Si no se encuentra el archivo de clusters, se procesa sin normalización

▸ Parámetros CLI principales:
    --pdf             Ruta al archivo PDF de entrada
    --out, -o         Ruta de salida JSON
    --clusters        Archivo con clusters pre-procesados (default: ./datos/clusters.json)
    --dpi             Resolución de rasterizado (default: 400)
    --lang, -l        Idioma OCR (Tesseract)
    --psm             Page segmentation mode (default: 4)
    --pages           Páginas específicas o rangos (e.g. 5-8 10)
    --no-images       Omite bloques de imagen en la salida
    --visual-style    Activa detección visual de estilos (negrita/itálica)
    --debug           Muestra logs detallados

▸ Flujo de trabajo recomendado:
    1. python scripts/normalizar_fuentes.py --pdf datos/extracto.pdf
    2. python scripts/extraer_ocr.py --pdf datos/extracto.pdf
"""

from pathlib import Path
import argparse, json, logging, re, time
import pdfplumber
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract import image_to_data, Output, image_to_boxes
import random
from PIL import Image, ImageEnhance, ImageFilter
from statistics import mean
from PIL import ImageOps
import numpy as np

def estimar_estilo_visual(palabra_img: Image.Image, font_size_pt):
    estilos = set()
    if palabra_img.mode != "L":
        palabra_img = palabra_img.convert("L")
    palabra_img = ImageOps.invert(palabra_img)
    np_img = np.array(palabra_img)
    total_pixels = np_img.shape[0] * np_img.shape[1]
    ink_pixels = np.count_nonzero(np_img > 50)
    densidad = ink_pixels / total_pixels
    # Detección de negrita según fórmula basada en tamaño de fuente
    a = 0.003
    b = 0.20
    densidad_esperada = a * font_size_pt + b
    if densidad > densidad_esperada * 1.6 and densidad - densidad_esperada > 0.05:
        estilos.add("b")
    coords = np.column_stack(np.where(np_img > 50))
    if coords.size > 0:
        x_coords = coords[:, 1]
        x_center = np.mean(x_coords)
        width = np_img.shape[1]
        desplazamiento_rel = (x_center - width / 2) / width
        if abs(desplazamiento_rel) > 0.1:
            estilos.add("i")
    print(f"Densidad: {densidad:.3f}, Esperada: {densidad_esperada:.3f}, Tamaño: {font_size_pt:.2f}")
    return estilos

import numpy as np

def get_etiquetas_estilo(nombre_fuente):
    etiquetas = []
    if not nombre_fuente:
        return etiquetas
    if "Bold" in nombre_fuente:
        etiquetas.append("b")
    if "Italic" in nombre_fuente or "Oblique" in nombre_fuente:
        etiquetas.append("i")
    return etiquetas

def insertar_etiquetas_estilo(textos, fuentes):
    resultado = ""
    estilo_actual = set()
    for palabra, fuente in zip(textos, fuentes):
        nuevo_estilo = set(get_etiquetas_estilo(fuente))
        cierre = "".join(f"</{e}>" for e in reversed(estilo_actual - nuevo_estilo))
        apertura = "".join(f"<{e}>" for e in nuevo_estilo - estilo_actual)
        resultado += cierre + apertura + palabra + " "
        estilo_actual = nuevo_estilo
    if estilo_actual:
        resultado += "".join(f"</{e}>" for e in reversed(estilo_actual))
    return resultado.strip()

def estimar_altura_letras(image: Image.Image, bbox: list, lang: str, texto: str, dpi: int = 400, debug=False):
    grupos = {
        "core": set("acemnorsuvwxz"),
        "ascendente": set("bdfhktl"),
        "descendente": set("gjpqy"),
        "digito": set("0123456789"),
        "mayuscula": set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    }

    recorte = image.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
    h = recorte.size[1]
    boxes = image_to_boxes(recorte, lang=lang)
    box_lines = boxes.strip().splitlines()

    MAX_CARACTERES_ANALIZADOS = 10
    if len(box_lines) > MAX_CARACTERES_ANALIZADOS:
        box_lines = random.sample(box_lines, MAX_CARACTERES_ANALIZADOS)

    if not boxes.strip():
        altura_fallback = bbox[3] - bbox[1]
        grupo_fallback = "digito" if texto.isdigit() else "fallback"
        FACTOR_POR_TIPO = {
            "fallback": 1.0,
            "fallback_digito": 1.2,
        }
        clave = "fallback_digito" if grupo_fallback == "digito" else "fallback"
        factor = FACTOR_POR_TIPO[clave]
        # Calcular el tamaño de fuente usando el DPI original
        font_size_pt = altura_fallback * 72 / dpi * factor
        
        # Aplicar el mismo factor de corrección
        factor_correccion = 4.0
        font_size_pt = font_size_pt * factor_correccion
        return altura_fallback, grupo_fallback, font_size_pt

    alturas = {k: [] for k in list(grupos.keys()) + ["otro"]}
    for b in box_lines:
        parts = b.split()
        if len(parts) != 6:
            continue
        char, _, y1, _, y2, _ = parts
        try:
            y1 = int(y1)
            y2 = int(y2)
            altura = abs(y2 - y1)
            grupo = next((g for g, letras in grupos.items() if char in letras), "otro")
            alturas[grupo].append(altura)
        except:
            continue

    if len(alturas["core"]) >= 3:
        base = np.median(alturas["core"])
        fuente = "core"
    elif len(alturas["ascendente"]) >= 3:
        base = np.mean(alturas["ascendente"])
        fuente = "ascendente"
    elif len(alturas["mayuscula"]) >= 3:
        base = np.median(alturas["mayuscula"])
        fuente = "mayuscula"
    elif len(alturas["digito"]) >= 3:
        base = np.mean(alturas["digito"])
        fuente = "digito"
    else:
        todas = sum(alturas.values(), [])
        base = max(todas) if todas else 0
        fuente = "max"

    FACTOR_POR_TIPO = {
        "core": 1.7,
        "ascendente": 1.3,
        "mayuscula": 1.0,
        "digito": 1.2,
        "max": 0.95,
        "fallback": 1.0,
        "fallback_digito": 1.2,
    }
    factor = FACTOR_POR_TIPO.get("fallback_digito" if fuente == "digito" and texto.isdigit() else fuente, 1.0)
    
    # Calcular el tamaño de fuente usando el DPI original
    font_size_pt = base * 72 / dpi * factor
    
    # Ajustar el tamaño de fuente para que coincida con el PDF original
    # Las fuentes del PDF original van de 2.25 a 16.6 puntos, promedio 10.9
    # Aplicar un factor de corrección basado en el análisis del PDF
    factor_correccion = 4.0  # Ajustar para que coincida con el rango del PDF original
    font_size_pt = font_size_pt * factor_correccion

    return base, fuente, font_size_pt

def agrupar_por_tolerancia(valores, tolerancia=0.6):
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

def asignar_cluster(val, grupos):
    # Redondear al entero más cercano y luego encontrar el cluster más cercano
    val_redondeado = round(val)
    return min(grupos, key=lambda g: abs(g - val_redondeado))


def expand_pages(pagelist):
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

def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--visual-style", action="store_true", help="Detectar estilo visual (negrita/itálica)", default=False)
    ap.add_argument("--pdf", type=Path, default=Path("./datos/extracto.pdf"))
    ap.add_argument("--out", "-o", type=Path, default=Path("./datos/ocr_lineas.json"))
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--lang", "-l", default="deu-frak+deu")
    ap.add_argument("--psm", type=int, default=4)
    ap.add_argument("--index-pages", nargs="*", type=int)
    ap.add_argument("--pages", nargs="*", type=str)
    ap.add_argument("--debug", action="store_true", default=True)
    ap.add_argument("--clusters", type=Path, default=Path("./datos/clusters.json"), help="Archivo con clusters pre-procesados")
    ap.add_argument("--no-images", action="store_true", default=True)
    return ap.parse_args()

def preprocesar_imagen(pil: Image.Image):
    """
    Aplica pre-procesamiento para mejorar el reconocimiento de caracteres pequeños.
    """
    # Convertir a escala de grises si no lo está
    if pil.mode != 'L':
        pil = pil.convert('L')
    
    # Aplicar filtro de nitidez para mejorar caracteres pequeños
    pil = pil.filter(ImageFilter.SHARPEN)
    
    # Mejorar el contraste
    enhancer = ImageEnhance.Contrast(pil)
    pil = enhancer.enhance(1.3)  # Aumentar contraste en 30%
    
    # Mejorar la nitidez
    enhancer = ImageEnhance.Sharpness(pil)
    pil = enhancer.enhance(1.2)  # Aumentar nitidez en 20%
    
    return pil

def detectar_superindices_problematicos(pil: Image.Image, lang: str, psm: int):
    """
    Detecta superíndices problemáticos basándose en geometría y posición.
    Busca caracteres pequeños seguidos de paréntesis de cierre.
    """
    # Usar modo LSTM para detección inicial
    cfg = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    d = image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg)
    
    caracteres_problematicos = []
    
    # DEBUG: Mostrar texto completo para ver qué detecta
    texto_completo = " ".join(d["text"])
    logging.info(f"🔍 Texto completo detectado: {texto_completo[:200]}...")
    
    # Analizar cada token para detectar superíndices geométricamente
    for i, texto in enumerate(d["text"]):
        if not texto.strip():
            continue
        
        # Obtener coordenadas del token actual
        x = d["left"][i]
        y = d["top"][i]
        w = d["width"][i]
        h = d["height"][i]
        conf = d["conf"][i]
        
        # Detección geométrica pura de superíndices
        # Un superíndice típicamente es un número pequeño seguido de paréntesis
        
        # Buscar tokens que contengan caracteres problemáticos inmediatamente antes del paréntesis
        import re
        if re.search(r'[1-9!@#$%^&*]\)', texto):
            # Calcular altura promedio de caracteres en la página para comparar
            alturas = [d["height"][j] for j in range(len(d["text"])) if d["text"][j].strip() and d["conf"][j] > 0]
            if alturas:
                altura_promedio = sum(alturas) / len(alturas)
                
                # DEBUG: Mostrar información del token completo
                logging.info(f"🔍 DEBUG Token '{texto}': altura={h}, altura_promedio={altura_promedio:.1f}")
                
                # Analizar si este token contiene un superíndice
                # Un superíndice típicamente es un número pequeño seguido de paréntesis
                caracteres_problematicos.append((x, y, w, h))
                logging.info(f"🔍 Token con posible superíndice detectado: '{texto}' en posición ({x},{y})")
    
    if not caracteres_problematicos:
        logging.info("🔍 No se detectaron superíndices problemáticos")
    else:
        logging.info(f"🔍 Se detectaron {len(caracteres_problematicos)} superíndices problemáticos")
    
    return caracteres_problematicos

def ocr_hibrido_granular(pil: Image.Image, lang: str, psm: int, caracteres_problematicos, debug=False):
    """
    OCR híbrido granular: usa LSTM para todo, pero legacy para líneas específicas.
    """
    # OCR principal con LSTM
    cfg_lstm = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    d_lstm = image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg_lstm)
    
    # Si no hay caracteres problemáticos, retornar resultado LSTM
    if not caracteres_problematicos:
        return d_lstm
    
    # Combinar resultados: usar LSTM como base, reemplazar solo caracteres problemáticos
    d_final = d_lstm.copy()
    
    # Agrupar caracteres problemáticos por línea
    lineas_problematicas = {}
    for x, y, w, h in caracteres_problematicos:
        # Encontrar la línea que contiene este carácter
        for j, (sx, sy, sw, sh) in enumerate(zip(d_lstm["left"], d_lstm["top"], 
                                               d_lstm["width"], d_lstm["height"])):
            if (abs(sx - x) < 5 and abs(sy - y) < 5 and 
                abs(sw - w) < 5 and abs(sh - h) < 5):
                linea_num = d_lstm["line_num"][j]
                if linea_num not in lineas_problematicas:
                    lineas_problematicas[linea_num] = []
                lineas_problematicas[linea_num].append((x, y, w, h))
                break
    
    # Procesar cada línea problemática
    for linea_num, caracteres in lineas_problematicas.items():
        if debug:
            logging.info(f"🔍 Procesando línea problemática {linea_num} con {len(caracteres)} caracteres")
        
        # Encontrar los límites de la línea
        y_min = min(y for x, y, w, h in caracteres)
        y_max = max(y + h for x, y, w, h in caracteres)
        
        # Expandir para incluir toda la línea (margen de 10px arriba y abajo)
        y1 = max(0, y_min - 10)
        y2 = min(pil.height, y_max + 10)
        
        # Recortar toda la línea
        linea_completa = pil.crop((0, y1, pil.width, y2))
        
        if debug:
            linea_path = f"debug_linea_{linea_num}.png"
            linea_completa.save(linea_path)
            logging.info(f"🔍 Línea guardada: {linea_path} (tamaño: {linea_completa.size})")
        
        # Aplicar Legacy a toda la línea
        cfg_legacy = f"--psm {psm} --oem 0 -c preserve_interword_spaces=1"
        d_linea = image_to_data(linea_completa, lang=lang, output_type=Output.DICT, config=cfg_legacy)
        
        # Obtener el texto de la línea con Legacy
        texto_linea_legacy = " ".join([t for t in d_linea["text"] if t.strip()])
        
        if debug:
            logging.info(f"🔍 Texto Legacy en línea: '{texto_linea_legacy}'")
        
        # Buscar y reemplazar caracteres problemáticos en esta línea
        for x, y, w, h in caracteres:
            # Buscar el token problemático en LSTM
            for j, (sx, sy, sw, sh) in enumerate(zip(d_final["left"], d_final["top"], 
                                                   d_final["width"], d_final["height"])):
                # Verificar si este token está en la región problemática
                if (abs(sx - x) < 5 and abs(sy - y) < 5 and 
                    abs(sw - w) < 5 and abs(sh - h) < 5):
                    
                    texto_original = d_final["text"][j]
                    if debug:
                        logging.info(f"🔍 Encontrado token LSTM: '{texto_original}' en ({sx},{sy})")
                    
                    # Buscar el reemplazo en el texto Legacy de la línea
                    if texto_original in ["!)", "4)"] and "1)" in texto_linea_legacy:
                        d_final["text"][j] = "1)"
                        if debug:
                            logging.info(f"🔧 Reemplazado '{texto_original}' → '1)' en línea {linea_num}")
                    elif "!)" in texto_original and "1)" in texto_linea_legacy:
                        # Reemplazar solo la parte problemática dentro del token
                        nuevo_texto = texto_original.replace("!)", "1)")
                        d_final["text"][j] = nuevo_texto
                        if debug:
                            logging.info(f"🔧 Reemplazado '{texto_original}' → '{nuevo_texto}' en línea {linea_num}")
                    break
    
    return d_final

def ocr(pil: Image.Image, lang: str, psm: int, use_legacy=False):
    """
    OCR con selección automática de modo según necesidad.
    """
    if use_legacy:
        # Usar modo legacy (OEM_TESSERACT_ONLY) para mejor detección de superíndices
        cfg = f"--psm {psm} --oem 0 -c preserve_interword_spaces=1"
    else:
        # Usar modo LSTM moderno para mejor calidad general
        cfg = f"--psm {psm} --oem 1 -c preserve_interword_spaces=1"
    
    return image_to_data(pil, lang=lang, output_type=Output.DICT, config=cfg)

def process_normal(pil: Image.Image, lang: str, psm: int, page_no: int, dpi: int, clusters, debug=False, visual_style=False, pdf_path=None):
    # Enfoque híbrido granular: detectar superíndices problemáticos específicos
    if debug:
        logging.info(f"🔍 Página {page_no}: Detectando superíndices problemáticos...")
    
    # Obtener dimensiones del PDF original para conversión de coordenadas
    pdf_width_pt = None
    pdf_height_pt = None
    if pdf_path:
        try:
            with pdfplumber.open(pdf_path) as doc:
                page = doc.pages[page_no - 1]
                pdf_width_pt = page.width
                pdf_height_pt = page.height
                if debug:
                    logging.info(f"📏 PDF original: {pdf_width_pt:.1f} x {pdf_height_pt:.1f} puntos")
                    logging.info(f"🖼️ Imagen rasterizada: {pil.width} x {pil.height} píxeles")
        except Exception as e:
            logging.warning(f"⚠️ No se pudieron obtener dimensiones del PDF: {e}")
    
    caracteres_problematicos = detectar_superindices_problematicos(pil, lang, psm)
    
    if caracteres_problematicos:
        if debug:
            logging.info(f"🔧 Página {page_no}: Usando OCR híbrido granular para {len(caracteres_problematicos)} caracteres problemáticos")
        d = ocr_hibrido_granular(pil, lang, psm, caracteres_problematicos, debug)
    else:
        if debug:
            logging.info(f"⚡ Página {page_no}: Usando modo LSTM moderno (sin caracteres problemáticos)")
        d = ocr(pil, lang, psm, use_legacy=False)
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

        # Convertir coordenadas de imagen a coordenadas del PDF
        if pdf_width_pt and pdf_height_pt:
            # Calcular factores de escala
            scale_x = pdf_width_pt / pil.width
            scale_y = pdf_height_pt / pil.height
            
            # Convertir coordenadas
            xs_pdf = [x * scale_x for x in xs]
            ys_pdf = [y * scale_y for y in ys]
            ws_pdf = [w * scale_x for w in ws]
            hs_pdf = [h * scale_y for h in hs]
            
            # Calcular bbox en coordenadas del PDF
            bbox = [min(xs_pdf), min(ys_pdf), max(x + w for x, w in zip(xs_pdf, ws_pdf)), max(y + h for y, h in zip(ys_pdf, hs_pdf))]
            
            if debug:
                logging.info(f"🔄 Conversión coordenadas: imagen ({min(xs)}, {min(ys)}) → PDF ({bbox[0]:.1f}, {bbox[1]:.1f})")
        else:
            # Fallback: usar coordenadas de imagen sin conversión
            bbox = [min(xs), min(ys), max(x + w for x, w in zip(xs, ws)), max(y + h for y, h in zip(ys, hs))]
        
        altura_px, grupo_fuente, font_size_pt = estimar_altura_letras(pil, bbox, lang, texto="", dpi=dpi, debug=debug)

        textos = []
        for i in idxs:
            palabra = d["text"][i].strip()
            if not palabra:
                continue
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            recorte = pil.crop((x, y, x + w, y + h))
            estilos = estimar_estilo_visual(recorte, font_size_pt=font_size_pt) if visual_style else set()
            
            # Detectar si es un superíndice (ya detectado previamente)
            es_superindice = re.search(r'[1-9!@#$%^&*]\)', palabra)
            
            # Marcar SOLO el número como superíndice, el paréntesis mantiene tamaño normal
            if es_superindice:
                # Buscar el patrón de número seguido de paréntesis
                match = re.search(r'([1-9!@#$%^&*])\)', palabra)
                if match:
                    numero = match.group(1)
                    # Reemplazar SOLO el número con versión superíndice, paréntesis fuera
                    palabra = palabra.replace(numero + ')', f'<sup>{numero}</sup>)')
            
            apertura = "".join(f"<{e}>" for e in estilos)
            cierre = "".join(f"</{e}>" for e in reversed(list(estilos)))
            
            textos.append(f"{apertura}{palabra}{cierre}")
        texto = " ".join(textos)

        linea = {
            "bbox": bbox,
            "texto": texto,
            "tipo": "linea",
            "pagina": page_no,
            "altura_px": altura_px,
            "grupo_fuente": grupo_fuente,
            "font_size_pt": round(font_size_pt, 2)
        }

        if clusters is not None:
            font_size_pt_norm = asignar_cluster(font_size_pt, clusters)
            linea["font_size_pt_norm"] = round(font_size_pt_norm)

        out.append(linea)
    return out

def image_blocks(pdf: Path, page: int):
    out = []
    with pdfplumber.open(pdf) as doc:
        for img in doc.pages[page-1].images:
            out.append({
                "bbox": [img["x0"], img["top"], img["x1"], img["bottom"]],
                "tipo": "imagen",
                "pagina": page
            })
    return out

def main():
    t0_total = time.time()
    args = cli()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler("ocr_debug.log", mode="w", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    total = pdfinfo_from_path(args.pdf)["Pages"]
    pages = expand_pages(args.pages) or range(1, total + 1)

    salida = []

    # Cargar clusters pre-procesados
    clusters = None
    if args.clusters.exists():
        try:
            clusters_data = json.loads(args.clusters.read_text(encoding="utf-8"))
            clusters = clusters_data.get("clusters", [])
            if args.debug:
                logging.info(f"📊 Clusters cargados: {len(clusters)} tamaños")
                logging.info(f"📏 Tamaños: {sorted(clusters)}")
        except Exception as e:
            logging.warning(f"⚠️ Error cargando clusters: {e}")
            clusters = None
    else:
        logging.warning(f"⚠️ Archivo de clusters no encontrado: {args.clusters}")
        logging.info("💡 Ejecuta primero: python scripts/normalizar_fuentes.py")

    for p in pages:
        t0 = time.time()
        logging.info("Procesando página %s", p)
        pil = convert_from_path(args.pdf, dpi=args.dpi, first_page=p, last_page=p)[0]
        salida.extend(process_normal(pil, args.lang, args.psm, p, dpi=args.dpi, clusters=clusters, debug=args.debug, visual_style=args.visual_style, pdf_path=args.pdf))
        if not args.no_images:
            salida.extend(image_blocks(args.pdf, p))
        logging.info("⏱️ Página %s procesada en %.2fs", p, time.time() - t0)

    # Siempre guardar en ocr_lineas.json
    output_file = "datos/ocr_lineas.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    logging.info("✅ %s items → %s", len(salida), output_file)
    logging.info("⏱️ Tiempo total: %.2f s", time.time() - t0_total)

if __name__ == "__main__":
    main()
