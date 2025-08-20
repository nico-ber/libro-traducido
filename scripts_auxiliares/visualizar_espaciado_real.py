#!/usr/bin/env python3
"""
Script para visualizar el espaciado real del maquetado sobre el bloque específico
con trazados que respeten exactamente la configuración del maquetado.
"""

import json
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, red, blue, green, orange
import sys
import os
import subprocess

# Agregar el directorio padre al path para importar funciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones del script principal
from scripts.maquetar_pdf import (
    GARAMOND_REGULAR_NAME, GARAMOND_BOLD_NAME, GARAMOND_ITALIC_NAME, GARAMOND_BOLDITALIC_NAME,
    GARAMOND_REGULAR_PATH, GARAMOND_BOLD_PATH, GARAMOND_ITALIC_PATH, GARAMOND_BOLDITALIC_PATH,
    dividir_silabas_aleman, calcular_division_optima_para_espaciado,
    ESPACIADO_MAXIMO_MULTIPLICADOR, LONGITUD_MINIMA_PALABRA_DIVIDIR, LONGITUD_MINIMA_PARTE_DIVIDIDA,
    TIPOGRAFIA_ESCALA_VISUAL, ESPACIADO_ESCALA_VISUAL, SANGRIO_PARRAFO, INTERLINEADO
)

def registrar_fuentes():
    """Registra las fuentes EB Garamond"""
    try:
        # Verificar que los archivos de fuentes existen
        rutas_fuentes = [
            GARAMOND_REGULAR_PATH,
            GARAMOND_BOLD_PATH,
            GARAMOND_ITALIC_PATH,
            GARAMOND_BOLDITALIC_PATH
        ]
        
        for ruta in rutas_fuentes:
            if not os.path.exists(ruta):
                print(f"❌ No se encuentra el archivo de fuente: {ruta}")
                return False
        
        # Registrar las fuentes
        pdfmetrics.registerFont(TTFont(GARAMOND_REGULAR_NAME, GARAMOND_REGULAR_PATH))
        pdfmetrics.registerFont(TTFont(GARAMOND_BOLD_NAME, GARAMOND_BOLD_PATH))
        pdfmetrics.registerFont(TTFont(GARAMOND_ITALIC_NAME, GARAMOND_ITALIC_PATH))
        pdfmetrics.registerFont(TTFont(GARAMOND_BOLDITALIC_NAME, GARAMOND_BOLDITALIC_PATH))
        print("✅ Fuentes registradas correctamente")
        return True
    except Exception as e:
        print(f"❌ Error registrando fuentes: {e}")
        return False

def crear_bloque_prueba():
    """Crea un bloque de prueba con el texto completo para análisis"""
    bloque_prueba = {
        "pagina": 16,
        "text": """Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische Weltbild ist zugegebenermaßen völlig unbewiesen. 2. Die Erdwelt-Theorie ist in der Lage, die gesamte Himmelsmecanik und sämtliche sonstigen Erscheinungen im Weltall ebenfalls einheitlich zu erklären. Es steht somit Erklärung gegen Erklärung, Weltbild gegen Weltbild. Welches davon „wahr" ist, kann somit nur durch wirkliche Beweise gezeigt werden.""",
        "alineacion": "justificado",
        "y_top": 96.64567235859126,
        "y_bottom": 231.44568836712912,
        "font_size": 10,
        "x_left": 78.11044859813084,
        "x_right": 523.1960232137474,
        "tipo": "linea",
        "inicio_parrafo": True,
        "espacio_despues": 9
    }
    
    # Guardar en archivo temporal
    with open("Salida/bloque_prueba.json", "w", encoding="utf-8") as f:
        json.dump([bloque_prueba], f, ensure_ascii=False, indent=2)
    
    print("✅ Bloque de prueba creado: Salida/bloque_prueba.json")
    return bloque_prueba

def ejecutar_maquetado_real():
    """Ejecuta el maquetado real sobre el bloque de prueba"""
    try:
        cmd = [
            sys.executable, "scripts/maquetar_pdf.py",
            "--bloques", "Salida/bloque_prueba.json",
            "--pdf_original", "Salida/original.pdf",
            "--salida", "Salida/maquetado_prueba.pdf",
            "--pages", "16"
        ]
        
        print("🔄 Ejecutando maquetado real...")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='cp1252', errors='ignore')
        
        if result.returncode == 0:
            print("✅ Maquetado real completado: Salida/maquetado_prueba.pdf")
            return True
        else:
            print(f"❌ Error en maquetado: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando maquetado: {e}")
        return False

def obtener_configuracion_maquetado():
    """Obtiene la configuración exacta del maquetado"""
    # Leer el bloque de prueba para obtener configuración
    with open("Salida/bloque_prueba.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    bloque = bloques[0]
    
    # Calcular configuración exacta
    font_size = bloque["font_size"] * TIPOGRAFIA_ESCALA_VISUAL
    max_width = bloque["x_right"] - bloque["x_left"]
    x_left = bloque["x_left"]
    x_right = bloque["x_right"]
    
    # Si es inicio de párrafo, aplicar sangría
    if bloque.get("inicio_parrafo", False):
        x_left += SANGRIO_PARRAFO
        max_width -= SANGRIO_PARRAFO
    
    return {
        "font_size": font_size,
        "max_width": max_width,
        "x_left": x_left,
        "x_right": x_right,
        "texto_original": bloque["text"],
        "linea_especifica": "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische",
        "siguiente_palabra": "Weltbild"
    }

def generar_visualizacion_etapa1_alineada(config):
    """Genera visualización de la línea alineada a la izquierda"""
    c = canvas.Canvas("Salida/etapa1_alineada.pdf", pagesize=A4)
    
    # Configuración
    font_size = config["font_size"]
    x_left = config["x_left"]
    y_pos = 700  # Posición Y fija para visualización
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "ETAPA 1: Línea alineada a la izquierda")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, f"Línea: '{config['linea_especifica']}'")
    c.drawString(50, 715, f"Posición X: {x_left:.1f}pt, Tamaño fuente: {font_size:.1f}pt")
    
    # Dibujar línea alineada a la izquierda
    c.setFont(GARAMOND_REGULAR_NAME, font_size)
    c.drawString(x_left, y_pos, config["linea_especifica"])
    
    # Línea de referencia para el ancho disponible
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_left, y_pos - 10, x_left + config["max_width"], y_pos - 10)
    c.setStrokeColor(black)
    
    # Marcar sangría si aplica
    if x_left > 50:  # Si hay sangría
        c.setStrokeColor(red)
        c.setLineWidth(2)
        c.line(50, y_pos - 20, x_left, y_pos - 20)
        c.setStrokeColor(black)
        
        c.setFont("Helvetica", 8)
        c.setFillColor(red)
        c.drawString(50, y_pos - 30, f"Sangría: {SANGRIO_PARRAFO}pt")
        c.setFillColor(black)
    
    c.save()
    print("✅ PDF generado: Salida/etapa1_alineada.pdf")

def generar_visualizacion_etapa2_justificada(config):
    """Genera visualización de la línea justificada (sin división)"""
    c = canvas.Canvas("Salida/etapa2_justificada.pdf", pagesize=A4)
    
    # Configuración
    font_size = config["font_size"]
    max_width = config["max_width"]
    x_left = config["x_left"]
    y_pos = 700
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "ETAPA 2: Línea justificada (espaciado excesivo)")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, f"Línea: '{config['linea_especifica']}'")
    c.drawString(50, 715, f"Ancho disponible: {max_width:.1f}pt")
    
    # Calcular espaciado
    palabras = config["linea_especifica"].split()
    ancho_palabras = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras)
    espacio_disponible = max_width - ancho_palabras
    num_espacios = len(palabras) - 1
    espaciado = espacio_disponible / num_espacios if num_espacios > 0 else 0
    espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    multiplicador = espaciado / espacio_ideal if espacio_ideal > 0 else 0
    
    c.drawString(50, 700, f"Espaciado: {espaciado:.1f}pt ({multiplicador:.1f}x el ideal)")
    
    # Dibujar línea justificada con visualización de espaciado
    x_pos = x_left
    for i, palabra in enumerate(palabras):
        c.setFont(GARAMOND_REGULAR_NAME, font_size)
        c.drawString(x_pos, y_pos, palabra)
        
        # Marcar el ancho de la palabra
        ancho_palabra = pdfmetrics.stringWidth(palabra, GARAMOND_REGULAR_NAME, font_size)
        c.setStrokeColor(blue)
        c.setLineWidth(1)
        c.line(x_pos, y_pos - 5, x_pos + ancho_palabra, y_pos - 5)
        
        # Si no es la última palabra, mostrar el espacio
        if i < len(palabras) - 1:
            x_espacio = x_pos + ancho_palabra
            
            # Color del espacio según el multiplicador
            if multiplicador <= 1.5:
                color_espacio = green
            elif multiplicador <= 2.0:
                color_espacio = orange
            else:
                color_espacio = red
            
            # Línea del espacio
            c.setStrokeColor(color_espacio)
            c.setLineWidth(3)
            c.line(x_espacio, y_pos + font_size/2, x_espacio + espaciado, y_pos + font_size/2)
            
            # Texto del multiplicador
            c.setFont("Helvetica", 10)
            c.setFillColor(color_espacio)
            c.drawString(x_espacio + espaciado/2 - 15, y_pos + font_size + 10, f"{multiplicador:.1f}x")
            
            # Restaurar colores
            c.setStrokeColor(black)
            c.setFillColor(black)
        
        x_pos += ancho_palabra + espaciado
    
    # Línea de referencia
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_left, y_pos - 15, x_left + max_width, y_pos - 15)
    c.setStrokeColor(black)
    
    c.save()
    print("✅ PDF generado: Salida/etapa2_justificada.pdf")

def generar_visualizacion_etapa3_dividida(config):
    """Genera visualización de la línea con división silábica"""
    c = canvas.Canvas("Salida/etapa3_dividida.pdf", pagesize=A4)
    
    # Configuración
    font_size = config["font_size"]
    max_width = config["max_width"]
    x_left = config["x_left"]
    y_pos = 700
    
    # Proceso real del maquetado
    linea_actual = config["linea_especifica"]  # "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische"
    siguiente_palabra = config["siguiente_palabra"]  # "Weltbild"
    
    # Esta línea ya tiene espaciado excesivo al justificarla
    palabras_linea = linea_actual.split()
    ancho_palabras_linea = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_linea)
    espacio_disponible_linea = max_width - ancho_palabras_linea
    num_espacios_linea = len(palabras_linea) - 1
    espaciado_linea = espacio_disponible_linea / num_espacios_linea if num_espacios_linea > 0 else 0
    espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    multiplicador_linea = espaciado_linea / espacio_ideal if espacio_ideal > 0 else 0
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "ETAPA 3: Línea con división silábica")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, f"Línea actual: '{linea_actual}'")
    c.drawString(50, 715, f"Espaciado actual: {espaciado_linea:.1f}pt ({multiplicador_linea:.1f}x el ideal)")
    c.drawString(50, 700, f"Siguiente palabra disponible: '{siguiente_palabra}'")
    
    # Aplicar división silábica a la siguiente palabra para traer parte de ella
    linea_dividida = linea_actual
    palabra_restante = siguiente_palabra
    if len(siguiente_palabra) >= LONGITUD_MINIMA_PALABRA_DIVIDIR:
        partes = dividir_silabas_aleman(siguiente_palabra)
        if len(partes) > 1:
            # Intentar traer la primera parte de la siguiente palabra
            linea_con_parte = linea_actual + " " + partes[0] + "-"
            # Verificar si esto mejora el espaciado
            palabras_con_parte = linea_con_parte.split()
            ancho_con_parte = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_con_parte)
            if ancho_con_parte <= max_width:
                linea_dividida = linea_con_parte
                palabra_restante = partes[1]
                c.drawString(50, 685, f"Palabra dividida: '{partes[0]}-{partes[1]}'")
                c.drawString(50, 670, f"Se trae: '{partes[0]}-' / Queda: '{partes[1]}'")
    
    c.drawString(50, 655, f"Línea final: '{linea_dividida}'")
    
    # Calcular espaciado de la línea dividida
    palabras_divididas = linea_dividida.split()
    ancho_palabras = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_divididas)
    espacio_disponible = max_width - ancho_palabras
    num_espacios = len(palabras_divididas) - 1
    espaciado = espacio_disponible / num_espacios if num_espacios > 0 else 0
    multiplicador = espaciado / espacio_ideal if espacio_ideal > 0 else 0
    
    c.drawString(50, 640, f"Espaciado después de división: {espaciado:.1f}pt ({multiplicador:.1f}x el ideal)")
    
    # Dibujar línea dividida con visualización de espaciado
    x_pos = x_left
    for i, palabra in enumerate(palabras_divididas):
        c.setFont(GARAMOND_REGULAR_NAME, font_size)
        c.drawString(x_pos, y_pos, palabra)
        
        # Marcar el ancho de la palabra
        ancho_palabra = pdfmetrics.stringWidth(palabra, GARAMOND_REGULAR_NAME, font_size)
        c.setStrokeColor(blue)
        c.setLineWidth(1)
        c.line(x_pos, y_pos - 5, x_pos + ancho_palabra, y_pos - 5)
        
        # Si no es la última palabra, mostrar el espacio
        if i < len(palabras_divididas) - 1:
            x_espacio = x_pos + ancho_palabra
            
            # Color del espacio según el multiplicador
            if multiplicador <= 1.5:
                color_espacio = green
            elif multiplicador <= 2.0:
                color_espacio = orange
            else:
                color_espacio = red
            
            # Línea del espacio
            c.setStrokeColor(color_espacio)
            c.setLineWidth(3)
            c.line(x_espacio, y_pos + font_size/2, x_espacio + espaciado, y_pos + font_size/2)
            
            # Texto del multiplicador
            c.setFont("Helvetica", 10)
            c.setFillColor(color_espacio)
            c.drawString(x_espacio + espaciado/2 - 15, y_pos + font_size + 10, f"{multiplicador:.1f}x")
            
            # Restaurar colores
            c.setStrokeColor(black)
            c.setFillColor(black)
        
        x_pos += ancho_palabra + espaciado
    
    # Línea de referencia
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_left, y_pos - 15, x_left + max_width, y_pos - 15)
    c.setStrokeColor(black)
    
    # Mostrar comparación
    y_comparacion = y_pos - 80
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_comparacion, "COMPARACIÓN:")
    
    c.setFont("Helvetica", 10)
    y_comparacion -= 20
    c.drawString(50, y_comparacion, f"• Línea original: {multiplicador_linea:.1f}x el espaciado ideal")
    y_comparacion -= 15
    c.drawString(50, y_comparacion, f"• Con parte traída: {multiplicador:.1f}x el espaciado ideal")
    y_comparacion -= 15
    c.drawString(50, y_comparacion, f"• Mejora: {multiplicador_linea - multiplicador:.1f}x")
    y_comparacion -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_comparacion, "CONCEPTO CORRECTO:")
    c.setFont("Helvetica", 10)
    y_comparacion -= 15
    c.drawString(50, y_comparacion, "• Se trae PARTE de la palabra siguiente para llenar mejor el espacio")
    y_comparacion -= 15
    c.drawString(50, y_comparacion, "• NO se corta la palabra actual (eso empeoraría el espaciado)")
    
    c.save()
    print("✅ PDF generado: Salida/etapa3_dividida.pdf")

def main():
    """Función principal"""
    print("🔍 Generando visualizaciones de espaciado real...")
    
    # Registrar fuentes
    if not registrar_fuentes():
        return
    
    # Crear bloque de prueba
    crear_bloque_prueba()
    
    # Ejecutar maquetado real
    if not ejecutar_maquetado_real():
        return
    
    # Obtener configuración exacta del maquetado
    config = obtener_configuracion_maquetado()
    print(f"📏 Configuración obtenida: fuente={config['font_size']:.1f}pt, ancho={config['max_width']:.1f}pt")
    
    # Generar visualizaciones de las 3 etapas
    generar_visualizacion_etapa1_alineada(config)
    generar_visualizacion_etapa2_justificada(config)
    generar_visualizacion_etapa3_dividida(config)
    
    print("✅ Visualizaciones reales completadas")

if __name__ == "__main__":
    main()
