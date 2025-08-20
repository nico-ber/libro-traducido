#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_bloques.py — Agrupa líneas OCR en bloques visuales.

▸ Entrada: líneas OCR JSON (producidas por extraer_ocr.py)

▸ Cada bloque incluye:
    - pagina: número de página
    - text: texto unificado
    - alineacion: tipo de alineación (izquierda, justificado, centrado, etc.)
    - font_size: promedio entre líneas del bloque (usa font_size_pt_norm o font_size_pt)
    - bbox derivado: x_left, x_right, y_top, y_bottom
    - tipo: línea o imagen
    - unilinea: true si es una sola línea
    - lines: solo si es multilínea
    - refs_pie: referencias numéricas a notas al pie detectadas (opcional)
    - estirar_por_letras: si es una línea unilinea en mayúsculas y justificada
    - espacio_despues: distancia vertical con respecto al bloque siguiente (misma página)

▸ Lógica de agrupamiento:
    - No agrupa líneas centradas (bloques unilínea)
    - Une líneas adyacentes con alineación compatible y distancia vertical dentro de tolerancia
    - Detecta referencias a notas al pie con expresiones regulares

▸ Parámetros CLI:
    --json_ocr        Ruta al JSON de líneas OCR
    --output, -o      Ruta de salida
    --pages           Páginas a procesar
    --indent          Tolerancia para sangrías (25 px por defecto)
    --right-tol       Tolerancia para margen derecho (50 px por defecto)
    --tol-px          Tolerancia de alineación horizontal (default 4)
    --max-gap         Tolerancia vertical relativa
    --debug           Modo detallado
"""


import argparse
import json
import re
from pathlib import Path
from collections import OrderedDict, defaultdict
from typing import List, Dict, Any
from pdfplumber import open as pdf_open
from typing import List, Dict, Any

DISTANCIA_VERTICAL_MAX = 150
DOT_RE = re.compile(r'[.\u00b7]{3,}')
END_NUM_RE = re.compile(r'\d{1,3}\s*$')
FOOTNOTE_RE = re.compile(r'(?:\[(\d{1,3})\]|(\d{1,3})\)|([⁰¹²³⁴⁵⁶⁷⁸⁹]+))')

def bbox(line: Dict[str, Any]) -> List[int]:
    if 'bbox' in line and isinstance(line['bbox'], (list, tuple)) and len(line['bbox']) == 4:
        return line['bbox']
    if {'x', 'y', 'w', 'h'} <= line.keys():
        return [line['x'], line['y'], line['x'] + line['w'], line['y'] + line['h']]
    if {'x1', 'y1', 'x2', 'y2'} <= line.keys():
        return [line['x1'], line['y1'], line['x2'], line['y2']]
    return [0, 0, 0, 0]

def _x(line): return line.get('x', line['bbox'][0])
def _y(line): return line.get('y', line['bbox'][1])

def font_size(line):
    if "font_size_pt_norm" in line:
        return line["font_size_pt_norm"]
    if "font_size_pt" in line:
        return line["font_size_pt"]
    return bbox(line)[3] - bbox(line)[1]

def refs_pie(text: str) -> List[str]:
    return [g for m in FOOTNOTE_RE.finditer(text) for g in m.groups() if g]

def detect_align(line, min_x1, max_x2, indent, right_tol):
    if 'texto' not in line:
        return None
    x1, _, x2, _ = bbox(line)
    li = x1 - min_x1
    ri = max_x2 - x2
    ancho = x2 - x1
    txt = line['texto']
    if ancho > 0 and li / ancho < 0.15 and ri / ancho < 0.15:
        return 'justificado'
    if ri <= right_tol and (DOT_RE.search(txt) or END_NUM_RE.search(txt)):
        return 'indice'
    if li <= indent and ri <= right_tol:
        return 'justificado'
    if li <= indent:
        return 'izquierda'
    if ri <= right_tol and li > indent * 2:
        return 'derecha'
    return 'centrado'



def make_block(ls: List[Dict[str, Any]], page_height) -> Dict[str, Any]:
    first = ls[0]
    b = OrderedDict()
    b['pagina'] = first['pagina']

    # Excluir líneas que parezcan número de página al construir el texto
    def es_numero_pagina(l):
        if 'texto' not in l:
            return False
        
        # Limpiar etiquetas HTML para verificar si es solo dígitos
        import re
        texto_limpio = re.sub(r'<[^>]+>', '', l['texto'].strip())
        
        return (
            texto_limpio.isdigit() and
            len(texto_limpio) <= 3 and
            bbox(l)[3] > 0.85 * page_height
        )

    lineas_utiles = [l for l in ls if not es_numero_pagina(l)]

    # Construir el texto fusionando cortes por guión
    partes = []
    for idx, l in enumerate(lineas_utiles):
        if 'texto' not in l:
            continue
        texto = l['texto'].strip()
        if partes and partes[-1].endswith('-'):
            partes[-1] = partes[-1][:-1] + texto  # unir sin espacio ni guión
        else:
            partes.append(texto)
    b['text'] = " ".join(partes)

    b['alineacion'] = first.get('align', 'izquierda')

    if (r := [r for l in ls if 'texto' in l for r in refs_pie(l['texto'])]):
        b['refs_pie'] = r

    b['y_top'] = bbox(first)[1]
    b['y_bottom'] = bbox(ls[-1])[3]

    import statistics
    fs = []
    for l in ls:
        if 'texto' in l:
            if 'font_size_pt_norm' in l:
                fs.append(l['font_size_pt_norm'])
            elif 'font_size_pt' in l:
                fs.append(l['font_size_pt'])
            else:
                fs.append(bbox(l)[3] - bbox(l)[1])
    b['font_size'] = statistics.median(fs) if fs else 0
    b['x_left'] = min(_x(l) for l in ls)
    b['x_right'] = max(bbox(l)[2] for l in ls)
    b['tipo'] = first.get('tipo', 'linea')

    # Detectar si es inicio de párrafo (primera línea con sangría)
    if len(ls) > 0:
        primera_linea_x = _x(ls[0])
        # Si la primera línea tiene una posición X significativamente mayor que el margen izquierdo
        # y es un bloque justificado, marcarlo como inicio de párrafo
        if (primera_linea_x > b['x_left'] + 20 and  # Sangría de al menos 20 puntos
            b['alineacion'] == 'justificado'):
            b['inicio_parrafo'] = True

    if len(ls) == 1:
        b['unilinea'] = True
        if b['alineacion'] == 'justificado' and b['text'].strip().isupper():
            b['estirar_por_letras'] = True
    else:
        b['lines'] = lineas_utiles
        for l in ls:
            l['tipo'] = b['tipo']

    # Marcar como número de página si la única línea era una línea de número
    if (
        len(ls) == 1 and
        es_numero_pagina(ls[0])
    ):
        b['tipo'] = 'numero_pagina'
        b['text'] = ls[0].get('texto', '').strip()

    return b

def detectar_punto_aparte(prev_line, current_line, min_x1, indent):
    """
    Detecta si hay un punto de aparte entre dos líneas.
    """
    if not prev_line or not current_line:
        return False
    
    prev_text = prev_line.get('texto', '').strip()
    current_x1 = _x(current_line)
    prev_x1 = _x(prev_line)
    
    # Detectar símbolo de punto de aparte (|)
    if prev_text.endswith('|'):
        return True
    
    # Detectar indentación significativa en la primera línea del párrafo siguiente
    # La indentación debe ser mayor que el margen izquierdo normal
    # Usar una tolerancia más estricta para detectar sangrías reales
    if current_x1 > min_x1 + indent * 1.2:  # Indentación significativa (reducido de 1.5 a 1.2)
        return True
    
    # Detectar cambio brusco en la posición X (sangría)
    # Si la línea actual está significativamente más a la derecha que la anterior
    if current_x1 > prev_x1 + indent * 0.8:  # Nueva condición: sangría relativa
        return True
    
    # Detectar párrafos por distancia vertical mayor
    # Si hay una distancia vertical significativa, es un nuevo párrafo
    prev_y = _y(prev_line)
    current_y = _y(current_line)
    distance_y = current_y - prev_y
    
    # Si la distancia es mayor que 2 líneas de texto, es un nuevo párrafo
    if distance_y > 50:  # Aproximadamente 2 líneas de texto
        return True
    
    return False

def agrupar(lines: List[Dict[str, Any]], tol, gap, indent, right_tol, debug, page_height):
    out, cur, pag, prev_bottom = [], [], None, None
    lines.sort(key=lambda l: (l['pagina'], _y(l), _x(l)))
    for i, ln in enumerate(lines):
        if pag != ln['pagina']:
            if cur:
                out.append(make_block(cur, page_height))
                cur = []
            pag = ln['pagina']
            page_lines = [l for l in lines if l['pagina'] == pag]
            min_x1 = min(_x(l) for l in page_lines)
            max_x2 = max(bbox(l)[2] for l in page_lines)

        ln['align'] = detect_align(ln, min_x1, max_x2, indent, right_tol) if 'texto' in ln else None

        if debug:
            txt = ln.get('texto', '')
            print(f"[dbg] pág {pag} y={_y(ln):>4} align={str(ln['align']):<10} {txt[:60]}")

        if ln['align'] == 'centrado':
            if cur:
                out.append(make_block(cur, page_height))
                cur = []
            out.append(make_block([ln], page_height))
            continue

        if not cur:
            cur.append(ln)
            prev_bottom = bbox(ln)[3]
            continue

        prev_ln = cur[-1]
        dy = _y(ln) - prev_bottom
        same_align = (
            ln['align'] == prev_ln['align'] or
            (prev_ln['align'] == 'justificado' and ln['align'] == 'izquierda') or
            (prev_ln['align'] == 'derecha' and ln['align'] in {'justificado', 'izquierda'} and abs(prev_ln['bbox'][2] - ln['bbox'][2]) <= right_tol)
        )

        # Detectar punto de aparte
        punto_aparte = detectar_punto_aparte(prev_ln, ln, min_x1, indent)
        
        if debug and punto_aparte:
            print(f"[dbg] 🔍 PUNTO DE APARTE detectado: '{prev_ln.get('texto', '')[-20:]}' → '{ln.get('texto', '')[:20]}'")

        if same_align and dy <= DISTANCIA_VERTICAL_MAX and not punto_aparte:
            cur.append(ln)
            prev_bottom = bbox(ln)[3]
        else:
            out.append(make_block(cur, page_height))
            cur = [ln]
            prev_bottom = bbox(ln)[3]

    if cur:
        out.append(make_block(cur, page_height))

    # Importante: no calcular espacio_despues aquí porque los bloques pueden
    # cambiar por fusiones entre páginas y separación de pies de página.
    # Se recalculará al final del pipeline en main().
    return out


def detectar_pies_de_pagina_por_linea_horizontal(bloques, page_height):
    """
    Detecta pies de página basándose en la presencia de líneas horizontales y posición al final de página.
    """
    print("[INFO] Detectando pies de página por líneas horizontales...")
    
    # Patrones de corrección conocidos
    correcciones_ocr = {
        r'!\)': '1)',  # !) -> 1)
        r'4\)': '1)',  # 4) -> 1) (cuando está en contexto de pie de página)
    }
    
    bloques_corregidos = []
    bloques_por_pagina = {}
    
    # Agrupar bloques por página
    for bloque in bloques:
        pagina = bloque.get("pagina", 0)
        if pagina not in bloques_por_pagina:
            bloques_por_pagina[pagina] = []
        bloques_por_pagina[pagina].append(bloque)
    
    # Procesar cada página
    for pagina, bloques_pagina in bloques_por_pagina.items():
        # Ordenar bloques por posición vertical (de arriba a abajo)
        bloques_pagina.sort(key=lambda b: b.get("y_top", 0))
        
        # Buscar líneas horizontales (bloques que podrían ser separadores)
        lineas_horizontales = []
        for i, bloque in enumerate(bloques_pagina):
            texto = bloque.get("text", "").strip()
            # Detectar líneas horizontales (guiones repetidos, líneas, etc.)
            if (re.match(r'^[-_=]{3,}$', texto) or 
                len(texto) < 10 and all(c in '-_=' for c in texto) or
                'Zeichnung' in texto or 'Drawing' in texto):
                lineas_horizontales.append((i, bloque))
        
        # Si hay líneas horizontales, separar el contenido
        if lineas_horizontales:
            for idx_linea, linea in lineas_horizontales:
                # Los bloques después de la línea horizontal son pies de página
                bloques_antes = bloques_pagina[:idx_linea]
                bloques_despues = bloques_pagina[idx_linea + 1:]
                
                # Procesar bloques antes de la línea (texto principal)
                for bloque in bloques_antes:
                    texto_original = bloque.get("text", "")
                    texto_corregido = texto_original
                    
                    # Aplicar correcciones de OCR
                    for patron, reemplazo in correcciones_ocr.items():
                        texto_corregido = re.sub(patron, reemplazo, texto_corregido)
                    
                    if texto_corregido != texto_original:
                        bloque_corregido = bloque.copy()
                        bloque_corregido["text"] = texto_corregido
                        bloques_corregidos.append(bloque_corregido)
                    else:
                        bloques_corregidos.append(bloque)
                
                # Procesar bloques después de la línea (pies de página)
                for bloque in bloques_despues:
                    texto_original = bloque.get("text", "")
                    texto_corregido = texto_original
                    
                    # Aplicar correcciones de OCR
                    for patron, reemplazo in correcciones_ocr.items():
                        texto_corregido = re.sub(patron, reemplazo, texto_corregido)
                    
                    # Marcar como pie de página
                    bloque_pie = bloque.copy()
                    bloque_pie["text"] = texto_corregido
                    bloque_pie["tipo"] = "pie_de_pagina"
                    
                    # Extraer número de referencia si existe
                    match_ref = re.search(r'(\d+)\)', texto_corregido)
                    if match_ref:
                        num_ref = match_ref.group(1)
                        bloque_pie["numero_referencia"] = num_ref
                        print(f"[dbg] 📝 Pie de página detectado: {num_ref}) - {texto_corregido[:50]}...")
                    else:
                        print(f"[dbg] 📝 Pie de página sin referencia: {texto_corregido[:50]}...")
                    
                    bloques_corregidos.append(bloque_pie)
                
                # No incluir la línea horizontal en el resultado final
                break  # Solo procesar la primera línea horizontal encontrada
        else:
            # Si no hay líneas horizontales, detectar y separar pies de página por contenido
            for i, bloque in enumerate(bloques_pagina):
                texto_original = bloque.get("text", "")
                texto_corregido = texto_original
                
                for patron, reemplazo in correcciones_ocr.items():
                    texto_corregido = re.sub(patron, reemplazo, texto_corregido)
                
                # Limpiar etiquetas HTML para la detección
                texto_limpio = re.sub(r'<[^>]+>', '', texto_corregido)
                
                # Detectar si el bloque contiene una nota al pie de página
                # Buscar patrones como "<sup>1</sup>) Siehe: ..." o "1) Siehe: ..." o "<sup>1</sup>) Verlag..."
                match_nota_pie = re.search(r'<sup>(\d+)</sup>\)\s*Siehe:', texto_corregido)
                if not match_nota_pie:
                    match_nota_pie = re.search(r'(\d+)\)\s*Siehe:', texto_corregido)
                if not match_nota_pie:
                    # Buscar cualquier pie de página que contenga <sup>1</sup>) seguido de texto
                    match_nota_pie = re.search(r'<sup>(\d+)</sup>\)\s*[A-Z]', texto_corregido)
                
                if match_nota_pie:
                    # Separar la nota al pie de página del texto principal
                    num_ref = match_nota_pie.group(1)
                    pos_inicio_nota = match_nota_pie.start()
                    
                    # Texto principal (sin la nota al pie)
                    texto_principal = texto_corregido[:pos_inicio_nota].rstrip()
                    
                    # Nota al pie de página
                    nota_pie = texto_corregido[pos_inicio_nota:]
                    
                    # Identificar qué líneas corresponden al texto principal y cuáles a la nota al pie
                    lineas_principales = []
                    lineas_nota_pie = []
                    
                    for linea in bloque.get("lines", []):
                        texto_linea = linea.get("texto", "")
                        # Si la línea contiene la nota al pie, va al bloque de nota al pie
                        if "<sup>" in texto_linea and ("Siehe:" in texto_linea or re.search(r'<sup>\d+</sup>\)\s*[A-Z]', texto_linea)):
                            lineas_nota_pie.append(linea)
                        else:
                            lineas_principales.append(linea)
                    
                    # Modificar el bloque original (sin la nota al pie)
                    bloque["text"] = texto_principal
                    bloque["lines"] = lineas_principales
                    # Actualizar y_top y y_bottom basado en las líneas principales
                    if lineas_principales:
                        bloque["y_top"] = lineas_principales[0]["bbox"][1]
                        bloque["y_bottom"] = lineas_principales[-1]["bbox"][3]
                    
                    # Guardar la información de la nota al pie para asociarla después
                    if "notas_pie_temporales" not in bloque:
                        bloque["notas_pie_temporales"] = []
                    bloque["notas_pie_temporales"].append({
                        "numero": num_ref,
                        "texto": nota_pie,
                        "pagina": bloque.get("pagina")
                    })
                    
                    print(f"[dbg] 📝 Nota al pie quitada del bloque: {num_ref}) - {nota_pie[:50]}...")
                    bloques_corregidos.append(bloque)
                else:
                    # No contiene nota al pie, mantener como está
                    # Solo detectar si hay referencias para asociarlas después
                    refs_encontradas = re.findall(r'\b(\d+)\)', texto_limpio)
                    if refs_encontradas:
                        if "refs_pie" not in bloque:
                            bloque["refs_pie"] = []
                        bloque["refs_pie"].extend(refs_encontradas)
                        print(f"[dbg] 🔗 Bloque con referencia: {texto_limpio[:50]}... (refs: {refs_encontradas})")
                    
                    bloques_corregidos.append(bloque)
    
    return bloques_corregidos


def asociar_pies_de_pagina(bloques):
    """
    Asocia los pies de página con los bloques que los referencian.
    """
    print("[INFO] Asociando pies de página con sus referencias...")
    
    # Detectar bloques que son pies de página
    pies_de_pagina = []
    bloques_con_refs = []
    
    for bloque in bloques:
        # Detectar si es un pie de página (contiene número seguido de paréntesis al inicio o después de texto)
        texto_bloque = bloque.get("text", "").strip()
        if (texto_bloque.startswith(("1)", "2)", "3)", "4)", "5)", "6)", "7)", "8)", "9)", "10)")) or
            re.search(r'\b(?:1|2|3|4|5|6|7|8|9|10)\)', texto_bloque) or
            bloque.get("tipo") == "pie_de_pagina"):
            pies_de_pagina.append(bloque)
            print(f"[dbg] 📝 Pie de página detectado: {bloque.get('text', '')[:50]}...")
        
        # Detectar bloques que tienen referencias
        if "refs_pie" in bloque and bloque["refs_pie"]:
            bloques_con_refs.append(bloque)
            print(f"[dbg] 🔗 Bloque con referencia: {bloque.get('text', '')[:50]}... (refs: {bloque['refs_pie']})")
    
    # Asociar pies de página con sus referencias
    bloques_finales = bloques.copy()
    
    # Primero, procesar las notas temporales que se extrajeron de los bloques
    for bloque in bloques:
        if "notas_pie_temporales" in bloque:
            for nota_temp in bloque["notas_pie_temporales"]:
                num_ref = nota_temp["numero"]
                # Buscar el bloque que tiene esta referencia
                for bloque_ref in bloques_con_refs:
                    if num_ref in bloque_ref["refs_pie"]:
                        # Asociar el pie de página al bloque
                        if "pie_de_pagina" not in bloque_ref:
                            bloque_ref["pie_de_pagina"] = []
                        bloque_ref["pie_de_pagina"].append({
                            "numero": num_ref,
                            "texto": nota_temp["texto"],
                            "pagina": nota_temp["pagina"]
                        })
                        print(f"[dbg] ✅ Nota al pie {num_ref} asociada a bloque")
                        break
            # Limpiar las notas temporales
            del bloque["notas_pie_temporales"]
    
    # Luego, procesar los pies de página independientes (si los hay)
    for pie in pies_de_pagina:
        # Usar el número de referencia ya extraído o extraerlo del texto
        num_ref = pie.get("numero_referencia")
        if not num_ref:
            texto_pie = pie.get("text", "").strip()
            match = re.search(r'\b(\d+)\)', texto_pie)
            if match:
                num_ref = match.group(1)
        
        if num_ref:
            # Buscar el bloque que tiene esta referencia
            for bloque in bloques_con_refs:
                if num_ref in bloque["refs_pie"]:
                    # Asociar el pie de página al bloque
                    if "pie_de_pagina" not in bloque:
                        bloque["pie_de_pagina"] = []
                    bloque["pie_de_pagina"].append({
                        "numero": num_ref,
                        "texto": pie.get("text", ""),
                        "pagina": pie.get("pagina")
                    })
                    print(f"[dbg] ✅ Pie de página {num_ref} asociado a bloque")
                    break
    
    return bloques_finales


def merge_cross_page_blocks(bloques, page_height):
    """
    Fusiona bloques que cruzan entre páginas basándose en criterios de continuidad.
    """
    print("[INFO] Iniciando fusión de bloques entre páginas...")
    
    # Detectar bloques cortados entre páginas
    bloques = [b for b in bloques if not b.get("omitido")]
    bloques.sort(key=lambda b: (b['pagina'], b['y_top']))
    paginas = sorted(set(b['pagina'] for b in bloques))

    for i in range(len(paginas) - 1):
        pag_actual = paginas[i]
        pag_sig = paginas[i + 1]

        bloques_actual = [b for b in bloques if b['pagina'] == pag_actual and b.get('tipo') != 'numero_pagina']
        bloques_sig = [b for b in bloques if b['pagina'] == pag_sig and b.get('tipo') != 'numero_pagina']

        if not bloques_actual or not bloques_sig:
            print(f"[dbg] ❌ No hay bloques válidos para pág {pag_actual} o {pag_sig}")
            continue

        bloque_a = bloques_actual[-1]
        bloque_b = bloques_sig[0]

        print(f"[dbg] ↔ Comparando pág {bloque_a['pagina']} → {bloque_b['pagina']}: "
              f"font_size_a={bloque_a.get('font_size'):.2f}, font_size_b={bloque_b.get('font_size'):.2f}, "
              f"y_bottom_a={bloque_a['y_bottom']}, y_top_b={bloque_b['y_top']}, "
              f"align_a={bloque_a.get('alineacion')}, align_b={bloque_b.get('alineacion')}")

        # Criterios básicos de fusión
        criterio_basico = (
            bloque_a.get("alineacion") == "justificado" and
            bloque_b.get("alineacion") == "justificado" and
            abs(bloque_a.get("font_size", 0) - bloque_b.get("font_size", 0)) < 3.0
        )
        
        # Criterios de exclusión para evitar fusionar bloques con referencias de pie de página
        tiene_refs_pie_a = "refs_pie" in bloque_a and bloque_a["refs_pie"]
        tiene_refs_pie_b = "refs_pie" in bloque_b and bloque_b["refs_pie"]
        tiene_pie_asociado_a = "pie_de_pagina" in bloque_a and bloque_a["pie_de_pagina"]
        tiene_pie_asociado_b = "pie_de_pagina" in bloque_b and bloque_b["pie_de_pagina"]
        
        # No fusionar si alguno de los bloques tiene referencias de pie de página o pies asociados
        if tiene_refs_pie_a or tiene_refs_pie_b or tiene_pie_asociado_a or tiene_pie_asociado_b:
            print(f"[dbg] ❌ No fusionado. Bloque A tiene refs_pie: {tiene_refs_pie_a}, pie_asociado: {tiene_pie_asociado_a}")
            print(f"[dbg] ❌ No fusionado. Bloque B tiene refs_pie: {tiene_refs_pie_b}, pie_asociado: {tiene_pie_asociado_b}")
            continue
        
        # Criterio inteligente: detectar si la última línea está justificada
        def detectar_ultima_linea_justificada(bloque):
            """Detecta si la última línea del bloque está justificada (espaciado expandido)"""
            if "lines" not in bloque or not bloque["lines"]:
                return False
            
            ultima_linea = bloque["lines"][-1]
            texto_ultima_linea = ultima_linea.get("texto", "")
            
            # Si la línea termina con guión, es muy probable que esté cortada
            if texto_ultima_linea.rstrip().endswith("-"):
                return True
            
            # Calcular el ancho de la línea vs el ancho disponible
            # Si la línea ocupa casi todo el ancho disponible, probablemente esté justificada
            ancho_linea = ultima_linea.get("w", 0)
            ancho_disponible = bloque.get("x_right", 0) - bloque.get("x_left", 0)
            
            if ancho_disponible > 0:
                ratio_ocupacion = ancho_linea / ancho_disponible
                # Si ocupa más del 90% del ancho disponible, probablemente esté justificada
                return ratio_ocupacion > 0.9
            
            return False
        
        # Debug adicional para el criterio inteligente
        if criterio_basico:
            ultima_linea_justificada = detectar_ultima_linea_justificada(bloque_a)
            criterio_guion = (
                bloque_a["text"].rstrip().endswith("-") or
                "Welt-" in bloque_a["text"] or
                bloque_b["text"].lstrip().startswith("bild")
            )
            
            print(f"[dbg] 🔍 Criterio inteligente: ultima_linea_justificada={ultima_linea_justificada}, "
                  f"criterio_guion={criterio_guion}")
            
            if "lines" in bloque_a and bloque_a["lines"]:
                ultima_linea = bloque_a["lines"][-1]
                ancho_linea = ultima_linea.get("w", 0)
                ancho_disponible = bloque_a.get("x_right", 0) - bloque_a.get("x_left", 0)
                ratio = ancho_linea / ancho_disponible if ancho_disponible > 0 else 0
                print(f"[dbg] 📏 Ancho línea: {ancho_linea}, ancho disponible: {ancho_disponible}, ratio: {ratio:.2f}")
        
        # Aplicar el criterio inteligente
        ultima_linea_justificada = detectar_ultima_linea_justificada(bloque_a)
        
        # Criterio adicional: texto que termina con guión o palabras específicas
        criterio_guion = (
            bloque_a["text"].rstrip().endswith("-") or
            "Welt-" in bloque_a["text"] or
            bloque_b["text"].lstrip().startswith("bild")
        )
        
        if criterio_basico and (ultima_linea_justificada or criterio_guion):
            print("[dbg] ✅ Fusión aplicada entre páginas")
            bloque_a["fusiona_con_siguiente"] = True
            bloque_b["fusiona_con_anterior"] = True
        else:
            print("[dbg] ❌ No fusionado. Condiciones no cumplidas.")

    # Fusionar texto y líneas de bloques continuados (entre páginas también)
    i = 0
    while i < len(bloques):
        actual = bloques[i]
        if actual.get("fusiona_con_siguiente") and not actual.get("omitido"):
            j = i + 1
            while j < len(bloques):
                siguiente = bloques[j]
                if not siguiente.get("omitido") and siguiente.get("tipo") != "numero_pagina":
                    # Verificar que ninguno de los bloques tenga referencias de pie de página o pies asociados
                    tiene_refs_pie_actual = "refs_pie" in actual and actual["refs_pie"]
                    tiene_refs_pie_siguiente = "refs_pie" in siguiente and siguiente["refs_pie"]
                    tiene_pie_asociado_actual = "pie_de_pagina" in actual and actual["pie_de_pagina"]
                    tiene_pie_asociado_siguiente = "pie_de_pagina" in siguiente and siguiente["pie_de_pagina"]
                    
                    if tiene_refs_pie_actual or tiene_refs_pie_siguiente or tiene_pie_asociado_actual or tiene_pie_asociado_siguiente:
                        print(f"[dbg] ⚠️ Saltando fusión: bloque con refs_pie o pie_asociado detectado")
                        break
                        
                    if siguiente.get("fusiona_con_anterior"):
                        if actual["text"].rstrip().endswith("-"):
                            actual["text"] = actual["text"].rstrip()[:-1] + siguiente["text"].lstrip()
                        else:
                            actual["text"] += " " + siguiente["text"].lstrip()

                        if "lines" in actual and "lines" in siguiente:
                            actual["lines"].extend(siguiente["lines"])

                        actual["y_bottom"] = max(actual["y_bottom"], siguiente["y_bottom"])
                        siguiente["omitido"] = True

                        # Marcar omitidos todos los bloques intermedios
                        for k in range(i + 1, j):
                            bloques[k]["omitido"] = True
                    break
                j += 1
        i += 1

    # Filtrar bloques omitidos
    bloques_finales = [b for b in bloques if not b.get("omitido")]
    print(f"[INFO] Fusión completada. Bloques originales: {len(bloques)}, bloques finales: {len(bloques_finales)}")
    
    return bloques_finales


def load_lines(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    for l in data:
        l['bbox'] = l.get('bbox') or [l['x'], l['y'], l['x']+l['w'], l['y']+l['h']]
        l['align'] = l.pop('alineacion', l.get('align','izquierda'))
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json_ocr', type=Path, default='Salida/ocr_lineas.json')
    ap.add_argument('--output','-o', type=Path, default='Salida/bloques.json')
    ap.add_argument('--pages', nargs='*', type=int)
    ap.add_argument('--indent', type=int, default=25)
    ap.add_argument('--right-tol', type=int, default=50)
    ap.add_argument('--tol-px', type=int, default=4)
    ap.add_argument('--max-gap', type=float, default=1.3)
    ap.add_argument('--debug', action='store_true', default=True)
    ap.add_argument('--merge-cross-page', action='store_true', help='Fusiona párrafos que cruzan entre páginas', default=True)
    args = ap.parse_args()

    lines = load_lines(args.json_ocr)
    if args.pages:
        lines = [l for l in lines if l['pagina'] in args.pages]

    pdf_path = Path("Estatico/original.pdf")
    with pdf_open(pdf_path) as pdf:
        page_height = pdf.pages[0].height

    bloques = agrupar(lines, args.tol_px, args.max_gap, args.indent, args.right_tol, args.debug, page_height)
    
    # Aplicar fusión entre páginas si se solicita
    if args.merge_cross_page:
        print("[INFO] Aplicando fusión de párrafos entre páginas...")
        bloques = merge_cross_page_blocks(bloques, page_height)
    
    # Detectar pies de página por líneas horizontales
    bloques = detectar_pies_de_pagina_por_linea_horizontal(bloques, page_height)
    
    # Asociar pies de página con sus referencias
    bloques = asociar_pies_de_pagina(bloques)

    # Recalcular espacio_despues por página tras todas las transformaciones
    from collections import defaultdict
    bloques_por_pagina = defaultdict(list)
    for b in bloques:
        if b.get('omitido'):
            continue
        bloques_por_pagina[b['pagina']].append(b)
    for pagina, bls in bloques_por_pagina.items():
        bls.sort(key=lambda b: b.get('y_top', 0))
        for i in range(len(bls) - 1):
            actual = bls[i]
            siguiente = bls[i + 1]
            # Distancia vertical en coordenadas del PDF original (PyMuPDF, Y desde arriba)
            distancia = max(0, (siguiente.get('y_top', 0) - actual.get('y_bottom', 0)))
            # Redondear a un valor limpio (puntos). Regla: al entero más cercano
            actual['espacio_despues'] = round(distancia)
    
    salida = json.dumps(bloques, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(salida, encoding='utf-8')
    else:
        Path('Salida/bloques.json').write_text(salida, encoding='utf-8')

if __name__ == '__main__':
    main()