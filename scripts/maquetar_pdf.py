#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
maquetar_pdf.py — Genera un PDF maquetado a partir de bloques OCR.

Requiere:
- datos/bloques.json con estructura esperada (text, tipo, alineacion, bbox, etc.)
- datos/original.pdf para extraer imágenes originales por bloque (si tipo = imagen)
- datos/CA Moskow has a plan W00 Reg.ttf como tipografía embebida

Funcionalidades:
- Inserta imágenes desde el PDF original
- Inserta texto con alineación izquierda, derecha, centrado y justificado
- Usa márgenes detectados automáticamente de las primeras 20 páginas
- Ubica bloques verticalmente como flujo, respetando espacio entre ellos

Uso:
  python scripts/maquetar_pdf.py --bloques datos/bloques.json --pdf_original datos/original.pdf --salida prueba_maquetado.pdf --pages 4 5 6
"""

import json
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
from reportlab.lib.colors import black
import os
import re

# --- CONFIG ---
# Fuentes EB Garamond
GARAMOND_REGULAR_PATH = "Estatico/Fuentes/EBGaramond-Medium.ttf"
GARAMOND_BOLD_PATH = "Estatico/Fuentes/EBGaramond-Bold.ttf"
GARAMOND_ITALIC_PATH = "Estatico/Fuentes/EBGaramond-MediumItalic.ttf"
GARAMOND_BOLDITALIC_PATH = "Estatico/Fuentes/EBGaramond-BoldItalic.ttf"
GARAMOND_REGULAR_NAME = "EBGaramond-Medium"
GARAMOND_BOLD_NAME = "EBGaramond-Bold"
GARAMOND_ITALIC_NAME = "EBGaramond-MediumItalic"
GARAMOND_BOLDITALIC_NAME = "EBGaramond-BoldItalic"
# Fuente del sistema para caracteres Unicode especiales
SYSTEM_FONT_NAME = "Helvetica"
NUM_PAGINAS_MUESTRA = 20
TIPOGRAFIA_ESCALA_VISUAL = 1.58  # Factor de escala para que altura_tinta_maquetado = altura_tinta_original
ESPACIADO_ESCALA_VISUAL = 0.5477  # Factor de escala para que espaciado_maquetado = espaciado_original
MARGEN_INTERNO_SUP = 0.18  # proporción del font_size
INTERLINEADO = 1.15 * 1.3441 * 0.8086  # Multiplicador de font_size para espacio entre líneas (ajustado para coincidir exactamente con original: 39.70pt)
SANGRIO_PARRAFO = 20  # Sangría para párrafos en puntos

# --- CONFIGURACIÓN DE JUSTIFICACIÓN Y DIVISIÓN SILÁBICA ---
ESPACIADO_MAXIMO_MULTIPLICADOR = 1.5  # Máximo espaciado entre palabras (1.5x el espacio normal)
LONGITUD_MINIMA_PALABRA_DIVIDIR = 6  # Mínimo caracteres para dividir una palabra (recomendación tipográfica)
LONGITUD_MINIMA_PARTE_DIVIDIDA = 3  # Mínimo caracteres en cada parte de la división

# --- FUNCIONES AUXILIARES COMUNES ---
def seleccionar_fuente_garamond(tipo_texto, estilo=""):
    """
    Selecciona la fuente EB Garamond apropiada basada en el tipo de texto y estilo.
    
    Args:
        tipo_texto: Tipo de texto ('titulo', 'encabezado', 'parrafo', etc.)
        estilo: Estilo específico (set de estilos como {'b', 'i'})
    
    Returns:
        Nombre de la fuente EB Garamond a usar
    """
    # Por defecto usar Regular
    fuente = GARAMOND_REGULAR_NAME
    
    # Aplicar estilos específicos
    if isinstance(estilo, set):
        if 'b' in estilo and 'i' in estilo:  # Bold + Italic
            fuente = GARAMOND_BOLDITALIC_NAME
        elif 'b' in estilo:  # Bold
            fuente = GARAMOND_BOLD_NAME
        elif 'i' in estilo:  # Italic
            fuente = GARAMOND_ITALIC_NAME
    elif isinstance(estilo, str):
        if 'bold' in estilo.lower() and 'italic' in estilo.lower():
            fuente = GARAMOND_BOLDITALIC_NAME
        elif 'bold' in estilo.lower() or 'negrita' in estilo.lower():
            fuente = GARAMOND_BOLD_NAME
        elif 'italic' in estilo.lower() or 'cursiva' in estilo.lower():
            fuente = GARAMOND_ITALIC_NAME
    
    # Aplicar tipos de texto específicos
    if tipo_texto in ['titulo', 'encabezado']:
        fuente = GARAMOND_BOLD_NAME
    elif tipo_texto in ['cita']:
        fuente = GARAMOND_ITALIC_NAME
    
    return fuente

# --- FUNCIONES DE DIVISIÓN SILÁBICA ---
def actualizar_json_con_division_silabica(bloque, palabra_original, palabra_dividida):
    """
    Función deprecada - ya no se modifica el JSON de bloques.
    La división silábica se aplica solo durante el procesamiento.
    """
    pass

def dividir_silabas_aleman(palabra):
    """
    Divide una palabra alemana en sílabas siguiendo las reglas del alemán.
    Basado en las reglas de división silábica del alemán.
    
    Recomendaciones tipográficas:
    - No dividir palabras de menos de 6 caracteres
    - Cada parte debe tener al menos 3 caracteres
    - Evitar dividir palabras de una sílaba
    """
    if len(palabra) < LONGITUD_MINIMA_PALABRA_DIVIDIR:
        return [palabra]
    
    # Reglas básicas de división silábica alemana
    # 1. Una consonante entre vocales va con la vocal siguiente
    # 2. Dos consonantes se dividen entre ellas
    # 3. Tres o más consonantes: la primera va con la vocal anterior, las demás con la siguiente
    # 4. No dividir después de una vocal corta seguida de una consonante
    
    # Patrones de división silábica alemana (simplificados)
    # Buscar consonantes entre vocales para dividir
    vocales = 'aeiouäöüAEIOUÄÖÜ'
    consonantes = 'bcdfghjklmnpqrstvwxyzß'
    
    # Buscar patrones de división
    for i in range(1, len(palabra) - 1):
        # Patrón: vocal + consonante + vocal
        if (palabra[i-1] in vocales and 
            palabra[i] in consonantes and 
            palabra[i+1] in vocales):
            
            # Verificar longitudes mínimas
            parte1 = palabra[:i]
            parte2 = palabra[i:]
            
            if len(parte1) >= LONGITUD_MINIMA_PARTE_DIVIDIDA and len(parte2) >= LONGITUD_MINIMA_PARTE_DIVIDIDA:
                return [parte1, parte2]
        
        # Patrón: vocal + dos consonantes + vocal
        elif (i < len(palabra) - 2 and
              palabra[i-1] in vocales and 
              palabra[i] in consonantes and 
              palabra[i+1] in consonantes and
              palabra[i+2] in vocales):
            
            # Dividir entre las dos consonantes
            parte1 = palabra[:i+1]
            parte2 = palabra[i+1:]
            
            if len(parte1) >= LONGITUD_MINIMA_PARTE_DIVIDIDA and len(parte2) >= LONGITUD_MINIMA_PARTE_DIVIDIDA:
                return [parte1, parte2]
    

    
    # Si no se puede dividir con patrones, intentar división simple
    if len(palabra) >= 8:  # Solo dividir palabras largas
        mitad = len(palabra) // 2
        # Buscar una consonante cerca del centro
        for i in range(mitad - 2, mitad + 3):
            if 0 < i < len(palabra) - 1:
                if palabra[i] in 'bcdfghjklmnpqrstvwxyzß':
                    parte1 = palabra[:i]
                    parte2 = palabra[i:]
                    if len(parte1) >= LONGITUD_MINIMA_PARTE_DIVIDIDA and len(parte2) >= LONGITUD_MINIMA_PARTE_DIVIDIDA:
                        return [parte1, parte2]
    
    return [palabra]

def calcular_division_optima_para_espaciado(palabra_candidata, palabras_linea, ancho_max, font_size):
    """
    Calcula cuántas sílabas de la palabra candidata traer para reducir el espaciado a ≤ 1.5x
    """
    # 1. Calcular espaciado actual
    ancho_palabras_actual = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_linea)
    espacio_disponible_actual = ancho_max - ancho_palabras_actual
    num_espacios_actual = len(palabras_linea) - 1
    
    if num_espacios_actual <= 0:
        return None, None
    
    espaciado_actual = espacio_disponible_actual / num_espacios_actual
    
    # 2. Calcular espacio normal y límite máximo
    espacio_normal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    limite_maximo = espacio_normal * ESPACIADO_MAXIMO_MULTIPLICADOR
    
    # 3. Si ya está dentro del límite, no hacer nada
    if espaciado_actual <= limite_maximo:
        return None, None
    
    print(f"[DIVISIÓN ÓPTIMA] Espaciado actual: {espaciado_actual:.1f}pt, Límite: {limite_maximo:.1f}pt")
    print(f"[DIVISIÓN ÓPTIMA] Palabra candidata: '{palabra_candidata}'")
    
    # 4. Obtener todas las posibles divisiones de la palabra candidata
    divisiones_posibles = dividir_silabas_aleman(palabra_candidata)
    
    # 5. Probar cada división y calcular cuánto reduce el espaciado
    mejor_division = None
    mejor_espaciado_final = float('inf')
    
    for division in divisiones_posibles:
        if len(division) == 1:  # No se pudo dividir
            continue
            
        parte1, parte2 = division[0], division[1]
        
        # Crear línea tentativa con la primera parte
        palabras_tentativas = palabras_linea.copy()
        palabras_tentativas.append(parte1 + "-")
        
        # Calcular nuevo espaciado
        ancho_palabras_nuevo = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_tentativas)
        espacio_disponible_nuevo = ancho_max - ancho_palabras_nuevo
        num_espacios_nuevo = len(palabras_tentativas) - 1
        
        if num_espacios_nuevo > 0:
            espaciado_nuevo = espacio_disponible_nuevo / num_espacios_nuevo
            
            print(f"[DIVISIÓN ÓPTIMA] Probando '{parte1}-{parte2}': espaciado = {espaciado_nuevo:.1f}pt")
            
            # Si el nuevo espaciado es mejor y está dentro del límite
            if espaciado_nuevo <= limite_maximo and espaciado_nuevo < mejor_espaciado_final:
                mejor_espaciado_final = espaciado_nuevo
                mejor_division = (parte1, parte2)
                print(f"[DIVISIÓN ÓPTIMA] ✅ Nueva mejor división: '{parte1}-{parte2}' (espaciado: {espaciado_nuevo:.1f}pt)")
    
    if mejor_division:
        print(f"[DIVISIÓN ÓPTIMA] División seleccionada: '{mejor_division[0]}-{mejor_division[1]}'")
    else:
        print(f"[DIVISIÓN ÓPTIMA] No se encontró división válida")
    
    return mejor_division

def calcular_espaciado_optimo_enriquecido(palabras, width, font_size, bloque):
    """
    Calcula el espaciado óptimo entre palabras enriquecidas, aplicando división silábica si es necesario.
    Retorna (espaciado, palabras_finales, forzar_salto_linea)
    """
    # Variable global para rastrear si se hizo división silábica
    global division_silabica_realizada
    division_silabica_realizada = False
    # Calcular ancho total de palabras
    total_width = 0
    for palabra in palabras:
        palabra_width = 0
        for char in palabra["texto"]:
            estilo = palabra["estilo"]
            fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
            char_font_size = font_size
            if "sup" in estilo:
                char_font_size = font_size * 0.5
            palabra_width += pdfmetrics.stringWidth(char, fuente, char_font_size)
        total_width += palabra_width
    
    # Calcular espacio disponible
    espacio_disponible = width - total_width
    
    # Si no hay espacio disponible, no se puede justificar
    if espacio_disponible <= 0:
        return None, palabras, False
    
    # Calcular espaciado normal
    num_espacios = len(palabras) - 1
    if num_espacios == 0:
        return 0, palabras, False
    
    espaciado_normal = espacio_disponible / num_espacios
    
    # Verificar si el espaciado es excesivo
    espacio_normal_esperado = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    
    if espaciado_normal <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
        return espaciado_normal, palabras, False
    
    # El espaciado es excesivo, intentar división silábica
    print(f"[DIVISIÓN SILÁBICA ENRIQUECIDA] Espaciado excesivo detectado: {espaciado_normal:.1f}pt")
    
    # Buscar la palabra más larga para dividir
    palabras_con_indices = [(i, palabra) for i, palabra in enumerate(palabras)]
    palabras_con_indices.sort(key=lambda x: len(x[1]["texto"]), reverse=True)
    
    for idx, palabra_obj in palabras_con_indices:
        palabra_texto = palabra_obj["texto"]
        if len(palabra_texto) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
            # Intentar dividir esta palabra
            partes = dividir_silabas_aleman(palabra_texto)
            if len(partes) > 1:
                # Crear nuevas palabras con la división
                nuevas_palabras = palabras.copy()
                nuevas_palabras[idx] = {"texto": partes[0] + "-", "estilo": palabra_obj["estilo"]}
                nuevas_palabras.insert(idx + 1, {"texto": partes[1], "estilo": palabra_obj["estilo"]})
                
                # Recalcular ancho total
                nuevo_total_width = 0
                for nueva_palabra in nuevas_palabras:
                    palabra_width = 0
                    for char in nueva_palabra["texto"]:
                        estilo = nueva_palabra["estilo"]
                        fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
                        char_font_size = font_size
                        if "sup" in estilo:
                            char_font_size = font_size * 0.5
                        palabra_width += pdfmetrics.stringWidth(char, fuente, char_font_size)
                    nuevo_total_width += palabra_width
                
                # Recalcular espaciado
                nuevo_espacio_disponible = width - nuevo_total_width
                nuevo_num_espacios = len(nuevas_palabras) - 1
                
                if nuevo_num_espacios > 0:
                    nuevo_espaciado = nuevo_espacio_disponible / nuevo_num_espacios
                    
                    # Verificar si el nuevo espaciado es aceptable
                    if nuevo_espaciado <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
                         print(f"[DIVISIÓN SILÁBICA ENRIQUECIDA] Palabra '{palabra_texto}' dividida en '{partes[0]}-{partes[1]}'")
                         # Agregar marcador de salto de línea forzado después del guión y espacio
                         nuevas_palabras[idx]["texto"] = partes[0] + "- ||BREAK||"
                         print(f"[DEBUG] ✅ Marcador ||BREAK|| agregado: '{nuevas_palabras[idx]['texto']}'")
                         return nuevo_espaciado, nuevas_palabras, True  # Forzar salto de línea
    
    # Si no se puede mejorar con división, usar el espaciado original
    return espaciado_normal, palabras, False

def calcular_espaciado_optimo(palabras, width, font_size, fuente=GARAMOND_REGULAR_NAME):
    """
    Calcula el espaciado óptimo entre palabras, aplicando división silábica si es necesario.
    Retorna (espaciado, palabras_finales, forzar_salto_linea)
    """
    # Calcular ancho total de palabras
    total_width = sum(pdfmetrics.stringWidth(w, fuente, font_size) for w in palabras)
    
    # Calcular espacio disponible
    espacio_disponible = width - total_width
    
    # Si no hay espacio disponible, no se puede justificar
    if espacio_disponible <= 0:
        print(f"[DEBUG] No hay espacio disponible para justificar: {espacio_disponible:.1f}pt")
        return None, palabras, False
    
    # Calcular espaciado normal
    num_espacios = len(palabras) - 1
    if num_espacios == 0:
        print(f"[DEBUG] Solo una palabra, no hay espacios para distribuir")
        return 0, palabras, False
    
    espaciado_normal = espacio_disponible / num_espacios
    
    # Verificar si el espaciado es excesivo
    espacio_normal_esperado = pdfmetrics.stringWidth(' ', fuente, font_size)
    print(f"[DEBUG] Espaciado calculado: {espaciado_normal:.1f}pt, Espacio normal: {espacio_normal_esperado:.1f}pt, Límite: {espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:.1f}pt")
    print(f"[DEBUG] Palabras: {palabras}")
    
    if espaciado_normal <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
        print(f"[DEBUG] Espaciado aceptable, no se necesita división silábica")
        return espaciado_normal, palabras, False
    
    # El espaciado es excesivo, intentar división silábica
    print(f"[DIVISIÓN SILÁBICA] Espaciado excesivo detectado: {espaciado_normal:.1f}pt (máximo: {espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:.1f}pt)")
    
    # Buscar la palabra más larga para dividir
    palabras_con_indices = [(i, palabra) for i, palabra in enumerate(palabras)]
    palabras_con_indices.sort(key=lambda x: len(x[1]), reverse=True)
    
    for idx, palabra in palabras_con_indices:
        if len(palabra) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
            print(f"[DEBUG] Intentando dividir palabra: '{palabra}' (longitud: {len(palabra)})")
            # Intentar dividir esta palabra
            partes = dividir_silabas_aleman(palabra)
            if len(partes) > 1:
                print(f"[DEBUG] Palabra dividida exitosamente: {partes}")
                # Crear nueva lista de palabras con la división
                nuevas_palabras = palabras.copy()
                nuevas_palabras[idx] = partes[0] + "-"  # Agregar solo guión a la primera parte
                nuevas_palabras.insert(idx + 1, partes[1])
                
                # Recalcular espaciado
                nuevo_total_width = sum(pdfmetrics.stringWidth(w, fuente, font_size) for w in nuevas_palabras)
                nuevo_espacio_disponible = width - nuevo_total_width
                nuevo_num_espacios = len(nuevas_palabras) - 1
                
                if nuevo_num_espacios > 0:
                    nuevo_espaciado = nuevo_espacio_disponible / nuevo_num_espacios
                    print(f"[DEBUG] Nuevo espaciado después de división: {nuevo_espaciado:.1f}pt")
                    
                    # Verificar si el nuevo espaciado es aceptable
                    if nuevo_espaciado <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
                        print(f"[DIVISIÓN SILÁBICA] Palabra '{palabra}' dividida en '{partes[0]}-{partes[1]}'")
                        # Agregar marcador de salto de línea forzado después del guión y espacio
                        nuevas_palabras[idx] = partes[0] + "- ||BREAK||"
                        print(f"[DEBUG] ✅ Marcador ||BREAK|| agregado (texto normal): '{nuevas_palabras[idx]}'")
                        return nuevo_espaciado, nuevas_palabras, True  # Forzar salto de línea
                    else:
                        print(f"[DEBUG] Nuevo espaciado sigue siendo excesivo: {nuevo_espaciado:.1f}pt")
            else:
                print(f"[DEBUG] No se pudo dividir la palabra: '{palabra}'")
    
    # Si no se puede mejorar con división, usar el espaciado original
    print(f"[DIVISIÓN SILÁBICA] No se pudo mejorar el espaciado, usando valor original")
    return espaciado_normal, palabras, False

def calcular_posicion_y_inicial(y_actual, font_size, usar_correccion_margen=True):
    """
    Calcula la posición Y inicial para dibujar texto.
    
    Args:
        y_actual: Posición Y actual del cursor (en coordenadas ReportLab, desde abajo)
        font_size: Tamaño de fuente
        usar_correccion_margen: Si True, calcula posición correcta para línea base
    
    Returns:
        Posición Y inicial para dibujar texto (línea base en coordenadas ReportLab)
    """
    if usar_correccion_margen:
        # En ReportLab, la posición Y es la línea base del texto
        # y_actual ya está en coordenadas ReportLab (desde abajo)
        # Para que el borde superior del texto coincida con y_actual,
        # necesitamos posicionar la línea base por debajo
        return y_actual - font_size
    else:
        return y_actual - font_size  # Comportamiento original

def calcular_posicion_y_salto_pagina(page_height, margen_sup, font_size, usar_correccion_margen=True):
    """
    Calcula la posición Y después de un salto de página.
    
    Args:
        page_height: Altura de la página
        margen_sup: Margen superior (en coordenadas ReportLab, desde abajo)
        font_size: Tamaño de fuente
        usar_correccion_margen: Si True, calcula posición correcta para línea base
    
    Returns:
        Posición Y inicial en la nueva página (línea base en coordenadas ReportLab)
    """
    if usar_correccion_margen:
        # margen_sup ya está en coordenadas ReportLab (desde abajo)
        # Para que el borde superior del texto coincida con el margen superior,
        # necesitamos posicionar la línea base por debajo del margen
        return margen_sup - font_size
    else:
        return margen_sup - font_size

def verificar_salto_pagina(y, line_height, margen_inf, page_height):
    """
    Verifica si es necesario hacer un salto de página.
    
    Args:
        y: Posición Y actual (en coordenadas ReportLab, desde abajo)
        line_height: Altura de línea
        margen_inf: Margen inferior (en coordenadas ReportLab, desde abajo)
        page_height: Altura de la página
    
    Returns:
        True si se necesita salto de página, False en caso contrario
    """
    # margen_inf ya está en coordenadas ReportLab (desde abajo)
    return y - line_height < margen_inf

def dibujar_linea_texto(c, linea, alineacion, margen_izq, margen_der, page_width, max_width, y, font_size, bloque=None):
    """
    Dibuja una línea de texto con la alineación especificada.
    
    Args:
        c: Canvas de ReportLab
        linea: Texto de la línea a dibujar
        alineacion: Tipo de alineación ('izquierda', 'centrado', 'derecha', 'justificado')
        margen_izq: Margen izquierdo
        margen_der: Margen derecho
        page_width: Ancho de la página
        max_width: Ancho máximo disponible para el texto
        y: Posición Y
        font_size: Tamaño de fuente
        bloque: Bloque completo (para casos especiales como justificación)
    
    Returns:
        None
    """
    # Determinar si es la primera o última línea del párrafo
    es_primera_linea = bloque.get('es_primera_linea', False) if bloque else False
    es_ultima_linea = bloque.get('es_ultima_linea', False) if bloque else False
    
    # Calcular sangría para la primera línea de párrafos justificados
    sangria_aplicar = 0
    if alineacion == 'justificado' and es_primera_linea and bloque.get('inicio_parrafo', False):
        sangria_aplicar = SANGRIO_PARRAFO
    elif alineacion in ['izquierda', 'left'] and bloque and bloque.get('tipo') in ['parrafo', 'linea']:
        # Aplicar sangría solo a la primera línea del párrafo
        if es_primera_linea:
            sangria_aplicar = SANGRIO_PARRAFO
    
    if alineacion in ['centrado', 'centro', 'center']:
        c.drawCentredString(page_width / 2, y, linea)
    elif alineacion in ['derecha', 'right']:
        c.drawRightString(page_width - margen_der, y, linea)
    elif alineacion == 'justificado' and bloque and bloque.get('unilinea') and bloque.get('text', '').isupper():
        # Para texto unilínea en mayúsculas (títulos), siempre justificar
        draw_justified_letters(c, linea, margen_izq + sangria_aplicar, y, max_width - sangria_aplicar, font_size)
    elif alineacion == 'justificado' and len(linea.strip().split()) > 1 and not es_ultima_linea:
        # Para párrafos justificados, no justificar la última línea
        draw_justified(c, linea, margen_izq + sangria_aplicar, y, max_width - sangria_aplicar, font_size)
    else:
        # Alineación izquierda (por defecto) o última línea de párrafo justificado
        c.drawString(margen_izq + sangria_aplicar, y, linea)

def procesar_bloque_texto_comun(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf, usar_texto_enriquecido=False):
    """
    Función común para procesar bloques de texto, tanto normales como enriquecidos.
    
    Args:
        c: Canvas de ReportLab
        bloque: Bloque de texto a procesar
        page_width: Ancho de la página
        y_actual: Posición Y actual
        rel_font: Factor de escala de fuente
        margen_izq: Margen izquierdo
        margen_der: Margen derecho
        page_height: Altura de la página
        margen_sup: Margen superior
        margen_inf: Margen inferior
        usar_texto_enriquecido: Si True, usa la lógica de texto enriquecido
    
    Returns:
        Tuple (y_final, dibujado, salto_pagina_ocurrio)
    """
    texto = bloque.get('text') or bloque.get('texto', '')
    # Limpiar el texto de símbolos especiales
    texto = limpiar_texto(texto)
    if not texto.strip():
        return y_actual, False, False
    
    font_size = bloque.get('font_size', 12) * TIPOGRAFIA_ESCALA_VISUAL
    line_height = font_size * INTERLINEADO
    max_width = page_width - margen_izq - margen_der
    alineacion = (bloque.get('alineacion', 'izquierda') or '').lower()
    

    pagina = bloque.get('pagina', '?')
    
    # La división silábica se aplicará línea por línea durante el procesamiento
    
    print(f"[BLOQUE{' ENRIQUECIDO' if usar_texto_enriquecido else ''}] pág={pagina}, font={font_size:.1f}, max_width={max_width:.1f}")
    
    y = calcular_posicion_y_inicial(y_actual, font_size)
    salto_pagina_ocurrio = False
    
    # Reservar ancho para sangría en primera línea si corresponde (antes de justificar)
    necesita_sangria_en_primera = (alineacion == 'justificado' and (bloque.get('inicio_parrafo', False)))

    if usar_texto_enriquecido:
        # Lógica específica para texto enriquecido
        texto_limpio = re.sub(r'<[^>]+>', '', texto)
        
        print(f"[DEBUG] Texto original: '{texto[:100]}...'")
        print(f"[DEBUG] Texto limpio: '{texto_limpio[:100]}...'")

        # Reconstruir el texto con etiquetas para cada línea, respetando sangría en la primera línea
        palabras_originales = texto.split()
        palabras_limpias = texto_limpio.split()

        linea_actual = ""
        lineas_con_estilos = []

        ancho_primera_linea = max_width - (SANGRIO_PARRAFO if necesita_sangria_en_primera else 0)
        es_primera = True

        for i, palabra_limpia in enumerate(palabras_limpias):
            # Encontrar la palabra original correspondiente
            palabra_original = None
            for palabra in palabras_originales:
                if re.sub(r'<[^>]+>', '', palabra) == palabra_limpia:
                    palabra_original = palabra
                    break
            
            if palabra_original:
                linea_tentativa = linea_actual + " " + palabra_original if linea_actual else palabra_original
                linea_limpia_tentativa = re.sub(r'<[^>]+>', '', linea_tentativa)
                
                ancho_max = ancho_primera_linea if es_primera else max_width
                
                # Verificar si la línea actual termina con guión o tiene marcador de salto forzado
                linea_termina_con_guion = (linea_actual.rstrip().endswith('-') or '||BREAK||' in linea_actual) if linea_actual else False
                
                if linea_termina_con_guion:
                    print(f"[DEBUG] 🔍 Línea termina con guión detectada: '{linea_actual}'")
                    print(f"[DEBUG] 🔍 Contiene ||BREAK||: {'||BREAK||' in linea_actual}")
                    print(f"[DEBUG] 🔍 Termina con guión: {linea_actual.rstrip().endswith('-')}")
                    # Si la línea actual termina con guión, forzar salto de línea
                    if linea_actual:
                        lineas_con_estilos.append(linea_actual)
                    linea_actual = palabra_original
                    es_primera = False
                elif pdfmetrics.stringWidth(linea_limpia_tentativa, GARAMOND_REGULAR_NAME, font_size) <= ancho_max:
                    # Verificar si el espaciado sería excesivo
                    palabras_propuesta = linea_limpia_tentativa.split()
                    if len(palabras_propuesta) > 1:
                        # Calcular ancho total de palabras
                        ancho_palabras = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_propuesta)
                        espacio_disponible = ancho_max - ancho_palabras
                        num_espacios = len(palabras_propuesta) - 1
                        espaciado_actual = espacio_disponible / num_espacios
                        espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
                        
                        # Si el espaciado sería excesivo, intentar división silábica
                        if espaciado_actual > espacio_ideal * ESPACIADO_MAXIMO_MULTIPLICADOR:
                            print(f"[DIVISIÓN ÓPTIMA ENRIQUECIDA] Espaciado excesivo detectado: {espaciado_actual:.1f}pt > {espacio_ideal * ESPACIADO_MAXIMO_MULTIPLICADOR:.1f}pt")
                            
                            # Buscar la siguiente palabra para dividir
                            if i < len(palabras_limpias) - 1:
                                palabra_siguiente = palabras_limpias[i + 1]
                                
                                # Verificar si la palabra siguiente es lo suficientemente larga para dividir
                                if len(palabra_siguiente) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
                                    division = calcular_division_optima_para_espaciado(
                                        palabra_siguiente, palabras_propuesta[:-1], ancho_max, font_size
                                    )
                                    
                                    if division and division[0] is not None:
                                        parte1, parte2 = division
                                        print(f"[DIVISIÓN APLICADA] '{palabra_siguiente}' -> '{parte1}-{parte2}'")
                                        # Agregar la primera parte a la línea actual
                                        linea_actual = linea_tentativa + " " + parte1 + "-"
                                        # Marcar que la siguiente palabra ya fue procesada
                                        palabras_limpias[i + 1] = parte2
                                        continue
                                else:
                                    print(f"[DIVISIÓN RECHAZADA] Palabra '{palabra_siguiente}' demasiado corta ({len(palabra_siguiente)} < {LONGITUD_MINIMA_PALABRA_DIVIDIR})")
                                    # Dejar la línea como está, sin división
                    
                    linea_actual = linea_tentativa
                else:
                    # La línea es demasiado larga, hacer salto normal
                    print(f"[DEBUG] Línea demasiado larga, salto normal: '{linea_actual}'")
                    if linea_actual:
                        lineas_con_estilos.append(linea_actual)
                    linea_actual = palabra_original
                    es_primera = False
        
        if linea_actual:
            lineas_con_estilos.append(linea_actual)
        
        lineas_a_procesar = lineas_con_estilos
    else:
        # Lógica para texto normal, respetando sangría en primera línea si corresponde
        palabras = texto.split()
        lineas = []
        linea_actual = ""
        es_primera = True
        ancho_primera_linea = max_width - (SANGRIO_PARRAFO if necesita_sangria_en_primera else 0)

        for i, palabra in enumerate(palabras):
            propuesta = linea_actual + " " + palabra if linea_actual else palabra
            ancho_max = ancho_primera_linea if es_primera else max_width
            
            # Verificar si la línea actual termina con guión o tiene marcador de salto forzado
            linea_termina_con_guion = (linea_actual.rstrip().endswith('-') or '||BREAK||' in linea_actual) if linea_actual else False
            
            if linea_termina_con_guion:
                print(f"[DEBUG] 🔍 Línea termina con guión detectada (texto normal): '{linea_actual}'")
                print(f"[DEBUG] 🔍 Contiene ||BREAK||: {'||BREAK||' in linea_actual}")
                print(f"[DEBUG] 🔍 Termina con guión: {linea_actual.rstrip().endswith('-')}")
                # Si la línea actual termina con guión, forzar salto de línea
                if linea_actual:
                    lineas.append(linea_actual)
                linea_actual = palabra
                es_primera = False
            elif pdfmetrics.stringWidth(propuesta, GARAMOND_REGULAR_NAME, font_size) <= ancho_max:
                # Verificar si el espaciado sería excesivo
                palabras_propuesta = propuesta.split()
                if len(palabras_propuesta) > 1:
                    # Calcular ancho total de palabras
                    ancho_palabras = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_propuesta)
                    espacio_disponible = ancho_max - ancho_palabras
                    num_espacios = len(palabras_propuesta) - 1
                    espaciado_actual = espacio_disponible / num_espacios
                    espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
                    
                    # Si el espaciado sería excesivo, intentar división silábica
                    if espaciado_actual > espacio_ideal * ESPACIADO_MAXIMO_MULTIPLICADOR:
                        print(f"[DIVISIÓN ÓPTIMA] Espaciado excesivo detectado: {espaciado_actual:.1f}pt > {espacio_ideal * ESPACIADO_MAXIMO_MULTIPLICADOR:.1f}pt")
                        
                        # Buscar la siguiente palabra para dividir
                        if i < len(palabras) - 1:
                            palabra_siguiente = palabras[i + 1]
                            
                            # Verificar si la palabra siguiente es lo suficientemente larga para dividir
                            if len(palabra_siguiente) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
                                division = calcular_division_optima_para_espaciado(
                                    palabra_siguiente, palabras_propuesta[:-1], ancho_max, font_size
                                )
                                
                                if division and division[0] is not None:
                                    parte1, parte2 = division
                                    print(f"[DIVISIÓN APLICADA] '{palabra_siguiente}' -> '{parte1}-{parte2}'")
                                    # Agregar la primera parte a la línea actual
                                    linea_actual = propuesta + " " + parte1 + "-"
                                    # Marcar que la siguiente palabra ya fue procesada
                                    palabras[i + 1] = parte2
                                    continue
                            else:
                                print(f"[DIVISIÓN RECHAZADA] Palabra '{palabra_siguiente}' demasiado corta ({len(palabra_siguiente)} < {LONGITUD_MINIMA_PALABRA_DIVIDIR})")
                                # Dejar la línea como está, sin división
                
                linea_actual = propuesta
            else:
                # La línea es demasiado larga, hacer salto normal
                print(f"[DEBUG] Línea demasiado larga (texto normal), salto normal: '{linea_actual}'")
                if linea_actual:
                    lineas.append(linea_actual)
                linea_actual = palabra
                es_primera = False

        if linea_actual:
            lineas.append(linea_actual)

        lineas_a_procesar = lineas
    
    # Procesar cada línea
    for i, linea in enumerate(lineas_a_procesar):
        if usar_texto_enriquecido:
            if verificar_salto_pagina(y, line_height, margen_inf, page_height):
                print("[SALTO AUTOMÁTICO] En bloque enriquecido")
                salto_pagina_ocurrio = True
                return y, False, True
        else:
            if verificar_salto_pagina(y, line_height, margen_inf, page_height):
                print(f"[SALTO AUTOMÁTICO] Salto de página en medio de bloque en página actual")
                salto_pagina_ocurrio = True
                c.showPage()
                c.setFont(GARAMOND_REGULAR_NAME, font_size)
                y = calcular_posicion_y_salto_pagina(page_height, margen_sup, font_size)
        
        es_ultima = (i == len(lineas_a_procesar) - 1)
        
        # Marcar si es la primera o última línea del párrafo para aplicar sangría y justificado
        if bloque and bloque.get('tipo') in ['parrafo', 'linea']:
            bloque['es_primera_linea'] = (i == 0)
            bloque['es_ultima_linea'] = es_ultima
        
        if usar_texto_enriquecido:
            # Lógica específica para dibujar texto enriquecido
            dibujar_texto_enriquecido_linea(c, linea, alineacion, margen_izq, margen_der, page_width, max_width, y, font_size, bloque)
        else:
            # Lógica para texto normal
            dibujar_linea_texto(c, linea, alineacion, margen_izq, margen_der, page_width, max_width, y, font_size, bloque)
        
        # Solo aplicar line_height si no es la última línea del bloque
        if i < len(lineas_a_procesar) - 1:
            y -= line_height
        # Si es la última línea del bloque, no aplicar interlineado adicional
    
    return y, True, salto_pagina_ocurrio

def dibujar_texto_enriquecido_linea(c, linea, alineacion, margen_izq, margen_der, page_width, max_width, y, font_size, bloque):
    """
    Dibuja una línea de texto enriquecido con estilos HTML.
    """
    # Determinar si es la primera o última línea del párrafo
    es_primera_linea = bloque.get('es_primera_linea', False)
    es_ultima_linea = bloque.get('es_ultima_linea', False)
    
    # Calcular sangría para la primera línea de párrafos justificados
    sangria_aplicar = 0
    if alineacion == 'justificado' and es_primera_linea and bloque.get('inicio_parrafo', False):
        sangria_aplicar = SANGRIO_PARRAFO
    
    # Para texto unilínea en mayúsculas (títulos), siempre justificar
    if alineacion == 'justificado' and bloque.get('unilinea') and bloque.get('text', '').isupper():
        draw_justified_letters_enriquecido(c, linea, margen_izq + sangria_aplicar, y, max_width - sangria_aplicar, font_size)
        return
    
    # Para párrafos justificados, no justificar la última línea
    if alineacion == 'justificado' and len(linea.strip().split()) > 1 and not es_ultima_linea:
        draw_justified_enriquecido(c, linea, margen_izq + sangria_aplicar, y, max_width - sangria_aplicar, font_size, bloque)
        return
    
    # Manejar diferentes alineaciones para texto enriquecido
    if alineacion in ['centrado', 'centro', 'center']:
        # Calcular el ancho total de la línea con estilos
        ancho_total = 0
        fragmentos = parse_text_with_styles(linea)
        for frag in fragmentos:
            estilo = frag["estilo"]
            fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
            
            # Calcular ancho carácter por carácter para manejar superíndices
            frag_text = frag["texto"]
            for char in frag_text:
                char_fuente = fuente
                char_font_size = font_size
                
                # Si está dentro de etiqueta <sup>, usar tamaño reducido
                if "sup" in estilo:
                    char_font_size = font_size * 0.5
                
                ancho_total += pdfmetrics.stringWidth(char, char_fuente, char_font_size)
        
        # Centrar la línea
        x = margen_izq + (max_width - ancho_total) / 2
        
    elif alineacion in ['derecha', 'right']:
        # Calcular el ancho total de la línea con estilos
        ancho_total = 0
        fragmentos = parse_text_with_styles(linea)
        for frag in fragmentos:
            estilo = frag["estilo"]
            fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
            
            # Calcular ancho carácter por carácter para manejar superíndices
            frag_text = frag["texto"]
            for char in frag_text:
                char_fuente = fuente
                char_font_size = font_size
                
                # Si está dentro de etiqueta <sup>, usar tamaño reducido
                if "sup" in estilo:
                    char_font_size = font_size * 0.5
                
                ancho_total += pdfmetrics.stringWidth(char, char_fuente, char_font_size)
        
        # Alinear a la derecha
        x = margen_izq + max_width - ancho_total
        
    else:
        # Alineación izquierda (por defecto) o última línea de párrafo justificado
        x = margen_izq + sangria_aplicar
    
    # Dibujar fragmentos con la posición x calculada
    fragmentos = parse_text_with_styles(linea)
    for frag in fragmentos:
        estilo = frag["estilo"]
        fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
        
        frag_text = frag["texto"]
        
        # Procesar carácter por carácter para manejar superíndices
        for char in frag_text:
            # Determinar la fuente y formato para este carácter específico
            char_fuente = fuente
            char_font_size = font_size
            char_y_offset = 0
            
            # Si está dentro de etiqueta <sup>, aplicar formato de superíndice
            if "sup" in estilo:
                char_font_size = font_size * 0.5  # 50% del tamaño normal
                char_y_offset = font_size * 0.25  # Elevación calculada: (1 - 0.5) * font_size para alinear partes superiores
                char_fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)  # Usar la fuente apropiada
            
            c.setFont(char_fuente, char_font_size)
            c.drawString(x, y + char_y_offset, char)
            x += pdfmetrics.stringWidth(char, char_fuente, char_font_size)

# --- FUNCIONES ---
def detectar_margenes(pdf_path, num_paginas=20):
    """
    Detecta márgenes globales del PDF analizando las primeras páginas.
    Devuelve coordenadas en sistema ReportLab (desde borde inferior).
    """
    doc = fitz.open(pdf_path)
    lefts, rights, tops, bottoms = [], [], [], []
    page_width = 0
    page_height = 0
    
    # Analizar las primeras num_paginas para determinar márgenes globales
    paginas_analizadas = min(len(doc), num_paginas)
    print(f"Analizando {paginas_analizadas} paginas para detectar margenes globales...")
    
    for i in range(paginas_analizadas):
        page = doc[i]
        page_width = page.rect.width  # Obtener el ancho de la página
        page_height = page.rect.height  # Obtener el alto de la página
        blocks = page.get_text("dict").get("blocks", [])
        
        for b in blocks:
            if b.get("type") != 0:  # solo texto
                continue
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    x0, y0, x1, y1 = s.get("bbox", [0, 0, 0, 0])
                    # Filtrar elementos que probablemente no son texto principal
                    # (números de página, encabezados, pies de página, etc.)
                    ancho_span = x1 - x0
                    alto_span = y1 - y0
                    
                    # Ignorar spans muy pequeños (posibles números de página)
                    if ancho_span < 50 or alto_span < 10:
                        continue
                    
                    # Ignorar spans muy cerca de los bordes (posibles encabezados/pies)
                    if x0 < 20 or x1 > page_width - 20:
                        continue
                    
                    # Ignorar spans muy arriba o muy abajo (fuera del área principal)
                    if y0 < page_height * 0.05 or y1 > page_height * 0.95:  # Menos restrictivo en la parte inferior
                        continue
                    
                    lefts.append(x0)
                    rights.append(x1)
                    tops.append(y0)
                    bottoms.append(y1)
    
    doc.close()
    
    if not lefts:
        print("⚠️ No se encontraron elementos de texto para detectar márgenes. Usando valores por defecto.")
        return 50, 50, 50, 50
    
    # Calcular márgenes globales basados en todas las páginas analizadas
    margen_izq = round(min(lefts))
    margen_der = round(page_width - max(rights))  # Margen derecho = ancho_pagina - posición_más_derecha_del_texto
    
    # Convertir coordenadas Y de PyMuPDF (desde arriba) a ReportLab (desde abajo)
    margen_sup_pymupdf = round(min(tops))  # Desde borde superior
    margen_sup_reportlab = round(page_height - margen_sup_pymupdf)  # Desde borde inferior
    
    # Para el margen inferior, usar el percentil 90 para evitar elementos marginales
    # Convertir a coordenadas ReportLab (desde abajo)
    import numpy as np
    margen_inf_pymupdf = round(np.percentile(bottoms, 90))  # Desde borde superior
    margen_inf_reportlab = round(page_height - margen_inf_pymupdf)  # Desde borde inferior
    
    print(f"Margenes globales detectados:")
    print(f"   Izquierdo: {margen_izq} puntos")
    print(f"   Derecho: {margen_der} puntos")
    print(f"   Superior: {margen_sup_reportlab} puntos (desde abajo)")
    print(f"   Inferior: {margen_inf_reportlab} puntos (desde abajo)")
    
    return margen_izq, margen_der, margen_sup_reportlab, margen_inf_reportlab

def extract_image_from_pdf(pdf_path, page_num, bbox, out_img_path):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    pix = page.get_pixmap(clip=fitz.Rect(bbox))
    pix.save(out_img_path)
    doc.close()

def draw_image(c, pdf_path, bloque, page_height):
    """
    Dibuja una imagen extraída del PDF original.
    Las coordenadas Y se convierten del sistema del PDF original (desde arriba) a ReportLab (desde abajo).
    """
    page_num = bloque.get('pagina', 1) - 1
    bbox = bloque.get('bbox') or [
        bloque.get('x_left', 0),
        bloque.get('y_top', 0),
        bloque.get('x_right', 0),
        bloque.get('y_bottom', 0),
    ]
    x0, y0, x1, y1 = bbox
    if x0 >= x1 or y0 >= y1:
        return
    width = x1 - x0
    height = y1 - y0
    # Convertir coordenadas Y del PDF original (desde arriba) a ReportLab (desde abajo)
    y_draw = page_height - y1
    img_path = f"temp_img_{page_num+1}_{x0}_{y0}.png"
    try:
        extract_image_from_pdf(pdf_path, page_num, bbox, img_path)
        c.drawImage(img_path, x0, y_draw, width=width, height=height)
        os.remove(img_path)
    except Exception as e:
        print(f"[ERROR] No se pudo insertar imagen {img_path}: {e}")

def draw_text(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf):
    """
    Dibuja texto normal usando la función común.
    """
    return procesar_bloque_texto_comun(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf, usar_texto_enriquecido=False)

def draw_justified(c, text, x, y, width, font_size):
    print(f"[DEBUG] draw_justified llamado con texto: '{text[:50]}...' (ancho: {width:.1f}pt)")
    words = text.strip().split()
    if len(words) <= 1:
        print(f"[DEBUG] Solo una palabra, dibujando sin justificar")
        c.drawString(x, y, text)
        return
    
    # Calcular espaciado óptimo con división silábica si es necesario
    space_width, palabras_finales, forzar_salto = calcular_espaciado_optimo(words, width, font_size, GARAMOND_REGULAR_NAME)
    
    if space_width is None:
        # No se puede justificar, dibujar como texto normal
        print(f"[DEBUG] No se puede justificar, dibujando como texto normal")
        c.drawString(x, y, text)
        return
    
    print(f"[DEBUG] Espaciado final aplicado: {space_width:.1f}pt")
    # Dibujar palabras con el espaciado calculado
    x_pos = x
    for i, word in enumerate(palabras_finales):
        # Limpiar marcadores especiales antes de dibujar
        word_clean = word.replace("||BREAK||", "")
        c.drawString(x_pos, y, word_clean)
        if i < len(palabras_finales) - 1 and not word_clean.endswith("-"):  # No agregar espacio después de la última palabra o si termina con guión
            x_pos += pdfmetrics.stringWidth(word_clean, GARAMOND_REGULAR_NAME, font_size) + space_width
        elif word_clean.endswith("-"):
            # Si termina con guión, no agregar espacio adicional ya que ya tiene un espacio después del guión
            x_pos += pdfmetrics.stringWidth(word_clean, GARAMOND_REGULAR_NAME, font_size)
        else:
            x_pos += pdfmetrics.stringWidth(word_clean, GARAMOND_REGULAR_NAME, font_size)

def draw_justified_letters(c, text, x, y, width, font_size):
    chars = list(text.strip())
    if len(chars) <= 1:
        c.drawString(x, y, text)
        return
    total_width = sum(pdfmetrics.stringWidth(ch, GARAMOND_REGULAR_NAME, font_size) for ch in chars)
    spacing = (width - total_width) / (len(chars) - 1)
    x_pos = x
    for ch in chars:
        c.drawString(x_pos, y, ch)
        x_pos += pdfmetrics.stringWidth(ch, GARAMOND_REGULAR_NAME, font_size) + spacing

def draw_justified_letters_enriquecido(c, text, x, y, width, font_size):
    # Versión enriquecida que maneja estilos HTML
    fragmentos = parse_text_with_styles(text)
    chars = []
    estilos_chars = []
    
    for frag in fragmentos:
        for ch in frag["texto"]:
            chars.append(ch)
            estilos_chars.append(frag["estilo"])
    
    if len(chars) <= 1:
        c.drawString(x, y, text)
        return
    
    # Calcular ancho total considerando estilos
    total_width = 0
    for i, ch in enumerate(chars):
        estilo = estilos_chars[i]
        fuente = seleccionar_fuente_garamond('', estilo)
        # Por ahora usamos solo la fuente normal ya que no tenemos las variantes
        # if "b" in estilo and "i" in estilo:
        #     fuente += "_BoldItalic"
        # elif "b" in estilo:
        #     fuente += "_Bold"
        # elif "i" in estilo:
        #     fuente += "_Italic"
        
        # Si el carácter es un superíndice Unicode, usar fuente del sistema
        if ch in ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']:
            fuente = SYSTEM_FONT_NAME
        
        total_width += pdfmetrics.stringWidth(ch, fuente, font_size)
    
    spacing = (width - total_width) / (len(chars) - 1)
    x_pos = x
    
    for i, ch in enumerate(chars):
        estilo = estilos_chars[i]
        fuente = seleccionar_fuente_garamond('', estilo)
        # Por ahora usamos solo la fuente normal ya que no tenemos las variantes
        # if "b" in estilo and "i" in estilo:
        #     fuente += "_BoldItalic"
        # elif "b" in estilo:
        #     fuente += "_Bold"
        # elif "i" in estilo:
        #     fuente += "_Italic"
        
        # Si el carácter es un superíndice Unicode, usar fuente del sistema
        if ch in ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']:
            fuente = SYSTEM_FONT_NAME
        
        c.setFont(fuente, font_size)
        c.drawString(x_pos, y, ch)
        x_pos += pdfmetrics.stringWidth(ch, fuente, font_size) + spacing

def draw_justified_enriquecido(c, text, x, y, width, font_size, bloque):
    """
    Dibuja texto justificado con estilos HTML, distribuyendo el espacio entre palabras.
    """
    # Parsear el texto con estilos
    fragmentos = parse_text_with_styles(text)
    
    # Extraer palabras manteniendo los estilos
    palabras = []
    for frag in fragmentos:
        # Dividir el fragmento en palabras
        palabras_frag = frag["texto"].split()
        for palabra in palabras_frag:
            palabras.append({
                "texto": palabra,
                "estilo": frag["estilo"]
            })
    
    if len(palabras) <= 1:
        # Si solo hay una palabra, dibujar normalmente
        dibujar_fragmento_con_estilos(c, fragmentos, x, y, font_size, bloque)
        return
    
    # Calcular espaciado óptimo con división silábica si es necesario
    space_width, palabras, forzar_salto = calcular_espaciado_optimo_enriquecido(palabras, width, font_size, bloque)
    
    if space_width is None:
        # No se puede justificar, dibujar como texto normal
        dibujar_fragmento_con_estilos(c, fragmentos, x, y, font_size, bloque)
        return
    x_pos = x
    
    # Dibujar cada palabra
    for palabra in palabras:
        # Limpiar marcadores especiales antes de dibujar
        texto_palabra = palabra["texto"].replace("||BREAK||", "")
        
        # Dibujar la palabra carácter por carácter
        for char in texto_palabra:
            estilo = palabra["estilo"]
            fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
            char_font_size = font_size
            char_y_offset = 0
            
            # Si está dentro de etiqueta <sup>, aplicar formato de superíndice
            if "sup" in estilo:
                char_font_size = font_size * 0.5
                char_y_offset = font_size * 0.25
            
            c.setFont(fuente, char_font_size)
            c.drawString(x_pos, y + char_y_offset, char)
            x_pos += pdfmetrics.stringWidth(char, fuente, char_font_size)
        
        # Agregar espacio entre palabras (excepto después de la última o si la palabra termina con guión)
        if palabra != palabras[-1] and not texto_palabra.endswith("-"):
            x_pos += space_width
        elif texto_palabra.endswith("-"):
            # Si termina con guión, no agregar espacio adicional ya que ya tiene un espacio después del guión
            pass

def dibujar_fragmento_con_estilos(c, fragmentos, x, y, font_size, bloque):
    """
    Función auxiliar para dibujar fragmentos con estilos.
    """
    x_pos = x
    for frag in fragmentos:
        estilo = frag["estilo"]
        fuente = seleccionar_fuente_garamond(bloque.get('tipo', ''), estilo)
        
        frag_text = frag["texto"]
        
        # Procesar carácter por carácter para manejar superíndices
        for char in frag_text:
            char_fuente = fuente
            char_font_size = font_size
            char_y_offset = 0
            
            # Si está dentro de etiqueta <sup>, aplicar formato de superíndice
            if "sup" in estilo:
                char_font_size = font_size * 0.5
                char_y_offset = font_size * 0.25
            
            c.setFont(char_fuente, char_font_size)
            c.drawString(x_pos, y + char_y_offset, char)
            x_pos += pdfmetrics.stringWidth(char, char_fuente, char_font_size)

def aplicar_division_silabica_a_texto_completo(texto, font_size, max_width):
    """
    Aplica división silábica al texto completo y retorna el texto modificado con marcadores de salto.
    """
    if not texto or len(texto.split()) <= 1:
        return texto
    
    palabras = texto.split()
    
    # Calcular ancho total de palabras
    total_width = sum(pdfmetrics.stringWidth(w, GARAMOND_REGULAR_NAME, font_size) for w in palabras)
    
    # Calcular espacio disponible
    espacio_disponible = max_width - total_width
    
    # Si no hay espacio disponible o es suficiente, no hacer nada
    if espacio_disponible <= 0:
        return texto
    
    # Calcular espaciado normal
    num_espacios = len(palabras) - 1
    if num_espacios == 0:
        return texto
    
    espaciado_normal = espacio_disponible / num_espacios
    
    # Verificar si el espaciado es excesivo
    espacio_normal_esperado = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    
    if espaciado_normal <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
        return texto
    
    # El espaciado es excesivo, intentar división silábica
    palabras_con_indices = [(i, palabra) for i, palabra in enumerate(palabras)]
    palabras_con_indices.sort(key=lambda x: len(x[1]), reverse=True)
    
    for idx, palabra in palabras_con_indices:
        if len(palabra) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
            # Intentar dividir esta palabra
            partes = dividir_silabas_aleman(palabra)
            if len(partes) > 1:
                # Crear nueva lista de palabras con la división
                nuevas_palabras = palabras.copy()
                nuevas_palabras[idx] = partes[0] + "- ||BREAK||"
                nuevas_palabras.insert(idx + 1, partes[1])
                
                # Recalcular espaciado
                nuevo_total_width = sum(pdfmetrics.stringWidth(w.replace('||BREAK||', ''), GARAMOND_REGULAR_NAME, font_size) for w in nuevas_palabras)
                nuevo_espacio_disponible = max_width - nuevo_total_width
                nuevo_num_espacios = len(nuevas_palabras) - 1
                
                if nuevo_num_espacios > 0:
                    nuevo_espaciado = nuevo_espacio_disponible / nuevo_num_espacios
                    
                    # Verificar si el nuevo espaciado es aceptable
                    if nuevo_espaciado <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
                        # Retornar el texto modificado con la división
                        return " ".join(nuevas_palabras)
    
    # Si no se puede mejorar con división, retornar el texto original
    return texto

def limpiar_texto(texto):
    """
    Limpia el texto de símbolos especiales que no deben aparecer en el PDF final.
    """
    if not texto:
        return texto
    
    # Eliminar símbolos de punto y aparte (|)
    texto = texto.replace('|', '')
    
    # Eliminar marcadores de salto forzado
    texto = texto.replace('||BREAK||', '')
    
    # Eliminar espacios múltiples que puedan quedar
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def aplicar_division_silabica_a_texto(texto, font_size, max_width):
    """
    Aplica división silábica al texto y retorna el texto modificado con guiones.
    """
    if not texto or len(texto.split()) <= 1:
        return texto
    
    palabras = texto.split()
    
    # Calcular ancho total de palabras
    total_width = sum(pdfmetrics.stringWidth(w, GARAMOND_REGULAR_NAME, font_size) for w in palabras)
    
    # Calcular espacio disponible
    espacio_disponible = max_width - total_width
    
    # Si no hay espacio disponible o es suficiente, no hacer nada
    if espacio_disponible <= 0:
        return texto
    
    # Calcular espaciado normal
    num_espacios = len(palabras) - 1
    if num_espacios == 0:
        return texto
    
    espaciado_normal = espacio_disponible / num_espacios
    
    # Verificar si el espaciado es excesivo
    espacio_normal_esperado = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    
    if espaciado_normal <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
        return texto
    
    # El espaciado es excesivo, intentar división silábica
    palabras_con_indices = [(i, palabra) for i, palabra in enumerate(palabras)]
    palabras_con_indices.sort(key=lambda x: len(x[1]), reverse=True)
    
    for idx, palabra in palabras_con_indices:
        if len(palabra) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
            # Intentar dividir esta palabra
            partes = dividir_silabas_aleman(palabra)
            if len(partes) > 1:
                # Crear nueva lista de palabras con la división
                nuevas_palabras = palabras.copy()
                nuevas_palabras[idx] = partes[0] + "-"
                nuevas_palabras.insert(idx + 1, partes[1])
                
                # Recalcular espaciado
                nuevo_total_width = sum(pdfmetrics.stringWidth(w, GARAMOND_REGULAR_NAME, font_size) for w in nuevas_palabras)
                nuevo_espacio_disponible = max_width - nuevo_total_width
                nuevo_num_espacios = len(nuevas_palabras) - 1
                
                if nuevo_num_espacios > 0:
                    nuevo_espaciado = nuevo_espacio_disponible / nuevo_num_espacios
                    
                    # Verificar si el nuevo espaciado es aceptable
                    if nuevo_espaciado <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
                        # Retornar el texto modificado con la división
                        return " ".join(nuevas_palabras)
    
    # Si no se puede mejorar con división, retornar el texto original
    return texto

def aplicar_division_silabica_a_texto_enriquecido(texto, font_size, max_width):
    """
    Aplica división silábica al texto enriquecido y retorna el texto modificado con guiones.
    """
    if not texto or len(texto.split()) <= 1:
        return texto
    
    # Parsear el texto con estilos
    fragmentos = parse_text_with_styles(texto)
    
    # Extraer palabras manteniendo los estilos
    palabras = []
    for frag in fragmentos:
        # Dividir el fragmento en palabras
        palabras_frag = frag["texto"].split()
        for palabra in palabras_frag:
            palabras.append({
                "texto": palabra,
                "estilo": frag["estilo"]
            })
    
    if len(palabras) <= 1:
        return texto
    
    # Calcular ancho total de palabras
    total_width = 0
    for palabra in palabras:
        palabra_width = 0
        for char in palabra["texto"]:
            estilo = palabra["estilo"]
            fuente = seleccionar_fuente_garamond('', estilo)
            char_font_size = font_size
            if "sup" in estilo:
                char_font_size = font_size * 0.5
            palabra_width += pdfmetrics.stringWidth(char, fuente, char_font_size)
        total_width += palabra_width
    
    # Calcular espacio disponible
    espacio_disponible = max_width - total_width
    
    # Si no hay espacio disponible o es suficiente, no hacer nada
    if espacio_disponible <= 0:
        return texto
    
    # Calcular espaciado normal
    num_espacios = len(palabras) - 1
    if num_espacios == 0:
        return texto
    
    espaciado_normal = espacio_disponible / num_espacios
    
    # Verificar si el espaciado es excesivo
    espacio_normal_esperado = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    
    if espaciado_normal <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
        return texto
    
    # El espaciado es excesivo, intentar división silábica
    palabras_con_indices = [(i, palabra) for i, palabra in enumerate(palabras)]
    palabras_con_indices.sort(key=lambda x: len(x[1]["texto"]), reverse=True)
    
    for idx, palabra_obj in palabras_con_indices:
        palabra_texto = palabra_obj["texto"]
        if len(palabra_texto) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
            # Intentar dividir esta palabra
            partes = dividir_silabas_aleman(palabra_texto)
            if len(partes) > 1:
                # Crear nuevas palabras con la división
                nuevas_palabras = palabras.copy()
                nuevas_palabras[idx] = {"texto": partes[0] + "-", "estilo": palabra_obj["estilo"]}
                nuevas_palabras.insert(idx + 1, {"texto": partes[1], "estilo": palabra_obj["estilo"]})
                
                # Recalcular ancho total
                nuevo_total_width = 0
                for nueva_palabra in nuevas_palabras:
                    palabra_width = 0
                    for char in nueva_palabra["texto"]:
                        estilo = nueva_palabra["estilo"]
                        fuente = seleccionar_fuente_garamond('', estilo)
                        char_font_size = font_size
                        if "sup" in estilo:
                            char_font_size = font_size * 0.5
                        palabra_width += pdfmetrics.stringWidth(char, fuente, char_font_size)
                    nuevo_total_width += palabra_width
                
                # Recalcular espaciado
                nuevo_espacio_disponible = max_width - nuevo_total_width
                nuevo_num_espacios = len(nuevas_palabras) - 1
                
                if nuevo_num_espacios > 0:
                    nuevo_espaciado = nuevo_espacio_disponible / nuevo_num_espacios
                    
                    # Verificar si el nuevo espaciado es aceptable
                    if nuevo_espaciado <= espacio_normal_esperado * ESPACIADO_MAXIMO_MULTIPLICADOR:
                         # Reconstruir el texto con las palabras divididas
                         texto_modificado = ""
                         for palabra in nuevas_palabras:
                             if texto_modificado:
                                 texto_modificado += " "
                             texto_modificado += palabra["texto"]
                         return texto_modificado
    
    # Si no se puede mejorar con división, retornar el texto original
    return texto

def parse_text_with_styles(text):
    # Limpiar el texto antes de procesarlo
    text = limpiar_texto(text)
    
    tag_regex = re.compile(r'<(/?)(b|i|sup)>')
    pos = 0
    current_styles = set()
    result = []
    for match in tag_regex.finditer(text):
        start, end = match.span()
        if start > pos:
            result.append({
                "texto": text[pos:start],
                "estilo": current_styles.copy()
            })
        tag_type = match.group(2)
        is_closing = match.group(1) == '/'
        if is_closing:
            current_styles.discard(tag_type)
        else:
            current_styles.add(tag_type)
        pos = end
    if pos < len(text):
        result.append({
            "texto": text[pos:], "estilo": current_styles.copy()
        })
    return result



def draw_text_enriquecido(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf):
    """
    Dibuja texto enriquecido usando la función común.
    """
    return procesar_bloque_texto_comun(c, bloque, page_width, y_actual, rel_font, margen_izq, margen_der, page_height, margen_sup, margen_inf, usar_texto_enriquecido=True)

def calcular_espacio_pies_pagina(bloques_pagina, rel_font, dibujar_pies=False):
    """
    Calcula el espacio necesario para los pies de página de una página.
    """
    # Recolectar todos los pies de página de los bloques de la página
    pies_pagina = []
    for bloque in bloques_pagina:
        if "pie_de_pagina" in bloque:
            pies_pagina.extend(bloque["pie_de_pagina"])
    
    if not pies_pagina or not dibujar_pies:
        return 0
    
    # Ordenar pies de página por número de referencia
    pies_pagina.sort(key=lambda p: int(p.get('numero', 0)))
    
    espacio_total = 0
    
    # Espacio para separar del último bloque (arriba de la línea horizontal)
    espacio_total += 30  # 30px de separación (aumentado)
    
    # Espacio para la línea horizontal
    espacio_total += 2  # 2px para la línea horizontal
    
    # Espacio para separar la línea del texto (abajo de la línea horizontal)
    espacio_total += 15  # 15px de separación (aumentado)
    
    # Calcular espacio para cada pie de página
    for pie in pies_pagina:
        texto_pie = pie.get('texto', '')
        if not texto_pie:
            continue
        
        # Usar el tamaño de fuente del bloque que contiene el pie de página
        font_size = 12 * TIPOGRAFIA_ESCALA_VISUAL
        
        # Calcular cuántas líneas necesita el pie de página
        max_width = 458.2  # Mismo ancho que se usa en draw_text_enriquecido
        
        # Usar la misma lógica que draw_text_enriquecido para calcular líneas
        from reportlab.lib.utils import simpleSplit
        
        # Limpiar etiquetas HTML para el cálculo de líneas
        texto_limpio = re.sub(r'<[^>]+>', '', texto_pie)
        palabras = simpleSplit(texto_limpio, GARAMOND_REGULAR_NAME, font_size, max_width)
        lineas = len(palabras)
        
        # Espacio para este pie de página (alineado contra el margen inferior)
        espacio_pie = lineas * font_size * 1.2  # 1.2 es el interlineado más compacto
        espacio_total += espacio_pie
    
    return espacio_total

def dibujar_lineas_guia(c, page_width, page_height, margen_izq, margen_der, margen_sup, margen_inf, margen_inf_ajustado=None):
    """
    Dibuja las líneas guía de la página: márgenes (verde) y separador de pie de página (azul).
    Todas las coordenadas Y se manejan desde el borde inferior de la página.
    """
    # Configurar colores
    from reportlab.lib.colors import green, blue
    
    # Dibujar márgenes (verde)
    c.setStrokeColor(green)
    c.setLineWidth(1)
    
    # Margen izquierdo
    c.line(margen_izq, 0, margen_izq, page_height)
    
    # Margen derecho (convertir desde distancia desde borde a posición absoluta)
    margen_der_pos = page_width - margen_der
    c.line(margen_der_pos, 0, margen_der_pos, page_height)
    
    # Margen superior (ya está en coordenadas ReportLab desde abajo)
    margen_sup_guia = max(margen_sup, page_height * 0.08)  # Mínimo 8% para líneas guía
    c.line(0, margen_sup_guia, page_width, margen_sup_guia)
    
    # Margen inferior (ya está en coordenadas ReportLab desde abajo)
    margen_inf_guia = max(margen_inf, page_height * 0.15)  # Mínimo 15% desde borde inferior para líneas guía
    margen_inf_actual = margen_inf_ajustado if margen_inf_ajustado is not None else margen_inf_guia
    c.line(0, margen_inf_actual, page_width, margen_inf_actual)
    
    # Dibujar separador de pie de página (azul) si hay margen ajustado
    if margen_inf_ajustado is not None and margen_inf_ajustado > margen_inf:
        c.setStrokeColor(blue)
        c.setLineWidth(2)
        # Línea horizontal que separa el pie de página
        c.line(0, margen_inf, page_width, margen_inf)
    
    # Restaurar color negro
    c.setStrokeColor(black)


def dibujar_pies_de_pagina(c, bloques_pagina, page_width, page_height, margen_izq, margen_der, margen_inf, rel_font, dibujar_pies=False):
    """
    Dibuja todos los pies de página al final de la página con una línea horizontal.
    Todas las coordenadas Y se manejan desde el borde inferior de la página.
    """
    # Recolectar todos los pies de página de los bloques de la página
    pies_pagina = []
    for bloque in bloques_pagina:
        if "pie_de_pagina" in bloque:
            pies_pagina.extend(bloque["pie_de_pagina"])
    
    if not pies_pagina or not dibujar_pies:
        return
    
    # Ordenar pies de página por número de referencia
    pies_pagina.sort(key=lambda p: int(p.get('numero', 0)))
    
    # Calcular altura total de los pies de página para dibujar desde abajo hacia arriba
    altura_total_pies = 0
    for pie in pies_pagina:
        texto_pie = pie.get('texto', '')
        if not texto_pie:
            continue
        
        font_size = 12 * TIPOGRAFIA_ESCALA_VISUAL
        texto_limpio = re.sub(r'<[^>]+>', '', texto_pie)
        palabras = simpleSplit(texto_limpio, GARAMOND_REGULAR_NAME, font_size, 458.2)
        lineas = len(palabras)
        altura_total_pies += lineas * font_size * 1.2
    
    # Posición para dibujar los pies de página (desde abajo hacia arriba)
    # margen_inf ya está en coordenadas ReportLab (desde abajo)
    y_pies = margen_inf + altura_total_pies + 15  # 15px de separación de la línea
    
    # Dibujar línea horizontal
    c.setStrokeColorRGB(0, 0, 0)  # Negro
    c.setLineWidth(1)
    y_linea = y_pies + 15  # 15px arriba del texto
    c.line(margen_izq, y_linea, page_width - margen_der, y_linea)
    
    # Dibujar cada pie de página desde abajo hacia arriba
    for pie in reversed(pies_pagina):  # Reversar para dibujar desde abajo
        texto_pie = pie.get('texto', '')
        if not texto_pie:
            continue
        
        font_size = 12 * TIPOGRAFIA_ESCALA_VISUAL
        
        # Calcular altura de este pie de página
        texto_limpio = re.sub(r'<[^>]+>', '', texto_pie)
        palabras = simpleSplit(texto_limpio, GARAMOND_REGULAR_NAME, font_size, 458.2)
        lineas = len(palabras)
        altura_pie = lineas * font_size * 1.2
        
        # Posición Y para este pie de página (línea base del texto)
        y_pie = y_pies - altura_pie + font_size  # Alinear contra el margen inferior (ya en coordenadas ReportLab)
        
        # Procesar el texto con etiquetas HTML
        fragmentos = parse_text_with_styles(texto_pie)
        x = margen_izq
        
        for frag in fragmentos:
            fragmento = frag["texto"]
            estilo = frag["estilo"]
            
            # Aplicar formato de superíndice si es necesario
            char_font_size = font_size
            char_y_offset = 0
            if "sup" in estilo:
                char_font_size = font_size * 0.5
                char_y_offset = font_size * 0.25
            
            # Dibujar carácter por carácter para manejar superíndices
            for char in fragmento:
                c.setFont(GARAMOND_REGULAR_NAME, char_font_size)
                c.drawString(x, y_pie + char_y_offset, char)
                x += pdfmetrics.stringWidth(char, GARAMOND_REGULAR_NAME, char_font_size)
        
        y_pies -= altura_pie  # Mover hacia arriba para el siguiente pie

# --- MAIN ---
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bloques', default='Salida/bloques.json')
    parser.add_argument('--pdf_original', default='Salida/extracto.pdf')
    parser.add_argument('--salida', default='Salida/maquetado.pdf')
    parser.add_argument('--pages', nargs='+', type=int)
    parser.add_argument('--dibujar_pies', action='store_true', help='Dibujar pies de página con línea horizontal')
    parser.add_argument('--dibujar_guias', action='store_true', help='Dibujar líneas guía de márgenes y separadores', default=False)
    args = parser.parse_args()

    # Cargar y registrar fuentes EB Garamond
    pdfmetrics.registerFont(TTFont(GARAMOND_REGULAR_NAME, GARAMOND_REGULAR_PATH))
    pdfmetrics.registerFont(TTFont(GARAMOND_BOLD_NAME, GARAMOND_BOLD_PATH))
    pdfmetrics.registerFont(TTFont(GARAMOND_ITALIC_NAME, GARAMOND_ITALIC_PATH))
    pdfmetrics.registerFont(TTFont(GARAMOND_BOLDITALIC_NAME, GARAMOND_BOLDITALIC_PATH))

    # Medidas base del PDF
    doc = fitz.open(args.pdf_original)
    page = doc.load_page(0)
    page_width = page.rect.width
    page_height = page.rect.height
    doc.close()

    margen_izq, margen_der, margen_sup, margen_inf = detectar_margenes(args.pdf_original, NUM_PAGINAS_MUESTRA)
    


    # Usar los márgenes detectados (ya en coordenadas ReportLab desde abajo)
    MARGEN_SUPERIOR_PX = margen_sup  # Margen superior en coordenadas ReportLab (desde abajo)
    MARGEN_INFERIOR_PX = margen_inf  # Margen inferior en coordenadas ReportLab (desde abajo)

    with open(args.bloques, 'r', encoding='utf-8') as f:
        bloques = json.load(f)
    bloques = [b for b in bloques if b.get('tipo') != 'numero_pagina' and not b.get('omitido')]

    if args.pages:
        bloques = [b for b in bloques if b.get('pagina') in args.pages]

    bloques.sort(key=lambda b: (b.get('pagina', 1), b.get('y_top', 0)))

    min_y_ocr = min(b.get('y_top', 0) for b in bloques)
    max_y_ocr = max(b.get('y_bottom', 0) for b in bloques)
    alto_ocr = max_y_ocr - min_y_ocr
    rel_font = page_height / alto_ocr if alto_ocr else 1.0

    print("---- Diagnóstico vertical ----")
    print(f"page_height = {page_height}")
    print(f"min_y_ocr = {min_y_ocr}")
    print(f"alto_ocr = {alto_ocr}")
    print(f"rel_font = {rel_font}\n")

    c = canvas.Canvas(args.salida, pagesize=(page_width, page_height))

    pagina_actual = None
    # Inicializar y_cursor en coordenadas ReportLab (desde abajo)
    # MARGEN_SUPERIOR_PX ya está en coordenadas ReportLab (desde abajo)
    y_cursor = MARGEN_SUPERIOR_PX


    pagina_forzada = False
    bloques_por_pagina = {}
    margen_inf_ajustado = MARGEN_INFERIOR_PX  # Inicializar para la primera página
    pies_dibujados_por_pagina = set()  # Rastrear qué páginas ya tienen pies dibujados

    # Agrupar bloques por página
    for bloque in bloques:
        pagina = bloque.get('pagina', 1)
        if pagina not in bloques_por_pagina:
            bloques_por_pagina[pagina] = []
        bloques_por_pagina[pagina].append(bloque)

    for bloque in bloques:
        pagina = bloque.get('pagina', 1)
        tipo = (bloque.get('tipo', '') or '').lower()

        if pagina != pagina_actual:
                # Dibujar pies de página de la página anterior antes de cambiar
                if pagina_actual is not None and pagina_actual not in pies_dibujados_por_pagina:
                    dibujar_pies_de_pagina(c, bloques_por_pagina.get(pagina_actual, []), page_width, page_height, margen_izq, margen_der, margen_inf_ajustado, rel_font, args.dibujar_pies)
                    pies_dibujados_por_pagina.add(pagina_actual)
                
                if not pagina_forzada and pagina_actual is not None:
                    c.showPage()
                pagina_actual = pagina
                if not pagina_forzada:
                    # Reinicializar y_cursor en coordenadas ReportLab (desde abajo)
                    y_cursor = MARGEN_SUPERIOR_PX
                pagina_forzada = False  # se resetea siempre
                
                # Calcular espacio necesario para pies de página de esta página
                bloques_pagina_actual = bloques_por_pagina.get(pagina, [])
                espacio_pies = calcular_espacio_pies_pagina(bloques_pagina_actual, rel_font, args.dibujar_pies)
                margen_inf_ajustado = MARGEN_INFERIOR_PX + espacio_pies
                
                # Dibujar líneas guía si está habilitado
                if args.dibujar_guias:
                    dibujar_lineas_guia(c, page_width, page_height, margen_izq, margen_der, MARGEN_SUPERIOR_PX, MARGEN_INFERIOR_PX, margen_inf_ajustado)

        if tipo == 'imagen':
            draw_image(c, args.pdf_original, bloque, page_height)
        elif tipo in ['linea', 'encabezado', 'titulo', 'cita', 'indice', 'parrafo', 'pie_de_pagina']:
            y_cursor, dibujado, pagina_forzada = draw_text_enriquecido(c, bloque, page_width, y_cursor, rel_font, margen_izq, margen_der, page_height, MARGEN_SUPERIOR_PX, margen_inf_ajustado)
            
            # Usar solo el espacio_despues del JSON (calculado desde las coordenadas originales)
            espacio = bloque.get("espacio_despues", 0)
            
            # Aplicar factor de escala del espaciado
            espacio_escalado = espacio * ESPACIADO_ESCALA_VISUAL
            
            # Actualizar y_cursor en coordenadas ReportLab (desde abajo)
            y_cursor -= espacio_escalado
            
            # Si se forzó una nueva página, dibujar los pies de página de la página anterior
            if pagina_forzada and pagina_actual not in pies_dibujados_por_pagina:
                print(f"[dbg] Dibujando pies de página de la página {pagina_actual} antes del salto")
                dibujar_pies_de_pagina(c, bloques_por_pagina.get(pagina_actual, []), page_width, page_height, margen_izq, margen_der, margen_inf_ajustado, rel_font, args.dibujar_pies)
                pies_dibujados_por_pagina.add(pagina_actual)
        
        print("bloque evaluado", bloque["pagina"])

    # Dibujar pies de página de la última página si no se han dibujado
    if pagina_actual is not None and pagina_actual not in pies_dibujados_por_pagina:
        # Dibujar pies de página antes de guardar el PDF
        print(f"[dbg] Dibujando pies de página de la página {pagina_actual} antes de guardar")
        dibujar_pies_de_pagina(c, bloques_por_pagina.get(pagina_actual, []), page_width, page_height, margen_izq, margen_der, margen_inf_ajustado, rel_font, args.dibujar_pies)
        pies_dibujados_por_pagina.add(pagina_actual)

    c.save()
    print(f"PDF maquetado generado: {args.salida}")

if __name__ == '__main__':
    main()
