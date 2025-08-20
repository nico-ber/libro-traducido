#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
medir_espaciado_linea.py — Mide el espaciado ideal y actual de una línea específica.
"""

import fitz  # PyMuPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json

# Configuración de fuentes
GARAMOND_REGULAR_PATH = "Estatico/Fuentes/EBGaramond-Medium.ttf"
GARAMOND_REGULAR_NAME = "EBGaramond-Medium"

def registrar_fuentes():
    """Registra las fuentes necesarias."""
    pdfmetrics.registerFont(TTFont(GARAMOND_REGULAR_NAME, GARAMOND_REGULAR_PATH))

def medir_espaciado_ideal(font_size):
    """Mide el espaciado ideal (1x) para un tamaño de fuente dado."""
    espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
    return espacio_ideal

def analizar_linea_especifica():
    """Analiza la línea específica 'Ich betone zwei Tatsachen nochmals: 1. Das koper-'"""
    
    # Registrar fuentes
    registrar_fuentes()
    
    # Tamaño de fuente típico (ajustar según sea necesario)
    font_size = 15.8  # Basado en el debug anterior
    
    # Ancho disponible (basado en el debug anterior)
    ancho_disponible = 458.3  # max_width del debug anterior
    
    # Medir espacio ideal
    espacio_ideal = medir_espaciado_ideal(font_size)
    print(f"📏 ESPACIADO IDEAL (1x): {espacio_ideal:.2f} puntos")
    
    # Línea específica a analizar (ORIGINAL, sin división silábica)
    linea_original = "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische"
    linea_dividida = "Ich betone zwei Tatsachen nochmals: 1. Das koper-"
    
    print(f"📝 LÍNEA ORIGINAL: '{linea_original}'")
    print(f"📝 LÍNEA DESPUÉS DE DIVISIÓN: '{linea_dividida}'")
    
    # Analizar línea original
    palabras_original = linea_original.split()
    palabras_dividida = linea_dividida.split()
    
    print(f"\n📊 LÍNEA ORIGINAL:")
    print(f"   Número de palabras: {len(palabras_original)}")
    print(f"   Palabras: {palabras_original}")
    
    print(f"\n📊 LÍNEA DESPUÉS DE DIVISIÓN:")
    print(f"   Número de palabras: {len(palabras_dividida)}")
    print(f"   Palabras: {palabras_dividida}")
    
    # Calcular ancho total de palabras ORIGINAL
    ancho_palabras_original = 0
    for palabra in palabras_original:
        ancho_palabra = pdfmetrics.stringWidth(palabra, GARAMOND_REGULAR_NAME, font_size)
        ancho_palabras_original += ancho_palabra
        print(f"   '{palabra}': {ancho_palabra:.2f}pt")
    
    print(f"\n📏 ANCHO TOTAL DE PALABRAS ORIGINAL: {ancho_palabras_original:.2f} puntos")
    
    # Verificar si la línea original cabía
    if ancho_palabras_original > ancho_disponible:
        print(f"❌ La línea original NO cabía ({ancho_palabras_original:.2f}pt > {ancho_disponible:.2f}pt)")
        print(f"✅ La división silábica era NECESARIA")
    else:
        print(f"✅ La línea original SÍ cabía ({ancho_palabras_original:.2f}pt <= {ancho_disponible:.2f}pt)")
        print(f"❓ La división silábica podría no haber sido necesaria")
    
    # Ahora analizar la línea dividida
    palabras = palabras_dividida
    
    print(f"\n📝 LÍNEA A ANALIZAR: '{linea_dividida}'")
    print(f"📊 Número de palabras: {len(palabras)}")
    print(f"📊 Palabras: {palabras}")
    
    # Calcular ancho total de palabras
    ancho_palabras = 0
    for palabra in palabras:
        ancho_palabra = pdfmetrics.stringWidth(palabra, GARAMOND_REGULAR_NAME, font_size)
        ancho_palabras += ancho_palabra
        print(f"   '{palabra}': {ancho_palabra:.2f}pt")
    
    print(f"\n📏 ANCHO TOTAL DE PALABRAS: {ancho_palabras:.2f} puntos")
    
    print(f"📏 ANCHO DISPONIBLE: {ancho_disponible:.2f} puntos")
    
    # Calcular espacio disponible para distribuir
    espacio_disponible = ancho_disponible - ancho_palabras
    print(f"📏 ESPACIO DISPONIBLE: {espacio_disponible:.2f} puntos")
    
    # Calcular espaciado actual
    num_espacios = len(palabras) - 1
    if num_espacios > 0:
        espaciado_actual = espacio_disponible / num_espacios
        print(f"📏 ESPACIADO ACTUAL: {espaciado_actual:.2f} puntos")
        
        # Calcular multiplicador
        multiplicador = espaciado_actual / espacio_ideal
        print(f"📊 MULTIPLICADOR: {multiplicador:.2f}x")
        
        # Evaluar si está dentro del límite
        limite_actual = 1.5
        print(f"📊 LÍMITE ACTUAL: {limite_actual}x")
        
        if multiplicador <= limite_actual:
            print(f"✅ El espaciado está dentro del límite ({multiplicador:.2f}x <= {limite_actual}x)")
        else:
            print(f"❌ El espaciado excede el límite ({multiplicador:.2f}x > {limite_actual}x)")
            
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        if multiplicador > 1.3:
            print(f"   - Considerar reducir el límite a 1.3x para mejor legibilidad")
        if multiplicador > 1.5:
            print(f"   - La línea necesita división silábica")
            
    else:
        print("❌ No hay espacios para distribuir (solo una palabra)")

def main():
    print("=== MEDICIÓN DE ESPACIADO DE LÍNEA ESPECÍFICA ===\n")
    analizar_linea_especifica()

if __name__ == '__main__':
    main()
