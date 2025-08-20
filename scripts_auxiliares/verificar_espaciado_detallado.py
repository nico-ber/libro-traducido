#!/usr/bin/env python3
"""
Script para verificar en detalle el espaciado de una línea específica
y mostrar métricas exactas de justificación y división silábica.
"""

import json
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import sys
import os

# Agregar el directorio padre al path para importar funciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funciones del script principal
from scripts.maquetar_pdf import (
    GARAMOND_REGULAR_NAME, GARAMOND_BOLD_NAME, GARAMOND_ITALIC_NAME, GARAMOND_BOLDITALIC_NAME,
    dividir_silabas_aleman, calcular_division_optima_para_espaciado,
    ESPACIADO_MAXIMO_MULTIPLICADOR, LONGITUD_MINIMA_PALABRA_DIVIDIR, LONGITUD_MINIMA_PARTE_DIVIDIDA
)

def registrar_fuentes():
    """Registra las fuentes EB Garamond"""
    try:
        pdfmetrics.registerFont(TTFont(GARAMOND_REGULAR_NAME, "Estatico/fuentes/EBGaramond-Regular.ttf"))
        pdfmetrics.registerFont(TTFont(GARAMOND_BOLD_NAME, "Estatico/fuentes/EBGaramond-Bold.ttf"))
        pdfmetrics.registerFont(TTFont(GARAMOND_ITALIC_NAME, "Estatico/fuentes/EBGaramond-Italic.ttf"))
        pdfmetrics.registerFont(TTFont(GARAMOND_BOLDITALIC_NAME, "Estatico/fuentes/EBGaramond-BoldItalic.ttf"))
        print("✅ Fuentes registradas correctamente")
    except Exception as e:
        print(f"❌ Error registrando fuentes: {e}")
        return False
    return True

def analizar_linea_especifica():
    """Analiza la línea específica que está causando problemas de espaciado"""
    
    # Configuración
    font_size = 12
    max_width = 458.30  # Ancho disponible para la línea
    
    # Línea original (antes de división)
    linea_original = "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische"
    
    # Línea después de división (como aparece en el PDF)
    linea_dividida = "Ich betone zwei Tatsachen nochmals: 1. Das koper-"
    
    # Palabra que fue dividida
    palabra_dividida = "kopernikanische"
    
    print("=" * 80)
    print("ANÁLISIS DETALLADO DE ESPACIADO")
    print("=" * 80)
    
    # 1. Análisis de la línea original
    print("\n1. ANÁLISIS DE LA LÍNEA ORIGINAL:")
    print("-" * 40)
    palabras_original = linea_original.split()
    ancho_palabras_original = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_original)
    espacio_disponible_original = max_width - ancho_palabras_original
    num_espacios_original = len(palabras_original) - 1
    
    print(f"Línea original: '{linea_original}'")
    print(f"Ancho total de palabras: {ancho_palabras_original:.2f}pt")
    print(f"Espacio disponible: {espacio_disponible_original:.2f}pt")
    print(f"Número de espacios: {num_espacios_original}")
    
    if num_espacios_original > 0:
        espaciado_original = espacio_disponible_original / num_espacios_original
        espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
        multiplicador_original = espaciado_original / espacio_ideal
        
        print(f"Espaciado resultante: {espaciado_original:.2f}pt")
        print(f"Espacio ideal (1x): {espacio_ideal:.2f}pt")
        print(f"Multiplicador: {multiplicador_original:.2f}x")
        print(f"¿Excede el límite 1.5x? {'SÍ' if multiplicador_original > ESPACIADO_MAXIMO_MULTIPLICADOR else 'NO'}")
        
        if multiplicador_original > ESPACIADO_MAXIMO_MULTIPLICADOR:
            print(f"❌ PROBLEMA: El espaciado original ({multiplicador_original:.2f}x) excede el límite ({ESPACIADO_MAXIMO_MULTIPLICADOR}x)")
        else:
            print(f"✅ La línea original NO necesitaba división")
    
    # 2. Análisis de la línea dividida
    print("\n2. ANÁLISIS DE LA LÍNEA DESPUÉS DE DIVISIÓN:")
    print("-" * 40)
    palabras_dividida = linea_dividida.split()
    ancho_palabras_dividida = sum(pdfmetrics.stringWidth(p, GARAMOND_REGULAR_NAME, font_size) for p in palabras_dividida)
    espacio_disponible_dividida = max_width - ancho_palabras_dividida
    num_espacios_dividida = len(palabras_dividida) - 1
    
    print(f"Línea dividida: '{linea_dividida}'")
    print(f"Ancho total de palabras: {ancho_palabras_dividida:.2f}pt")
    print(f"Espacio disponible: {espacio_disponible_dividida:.2f}pt")
    print(f"Número de espacios: {num_espacios_dividida}")
    
    if num_espacios_dividida > 0:
        espaciado_dividida = espacio_disponible_dividida / num_espacios_dividida
        espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
        multiplicador_dividida = espaciado_dividida / espacio_ideal
        
        print(f"Espaciado resultante: {espaciado_dividida:.2f}pt")
        print(f"Espacio ideal (1x): {espacio_ideal:.2f}pt")
        print(f"Multiplicador: {multiplicador_dividida:.2f}x")
        print(f"¿Excede el límite 1.5x? {'SÍ' if multiplicador_dividida > ESPACIADO_MAXIMO_MULTIPLICADOR else 'NO'}")
        
        if multiplicador_dividida > ESPACIADO_MAXIMO_MULTIPLICADOR:
            print(f"❌ PROBLEMA: El espaciado después de división ({multiplicador_dividida:.2f}x) AÚN excede el límite ({ESPACIADO_MAXIMO_MULTIPLICADOR}x)")
        else:
            print(f"✅ La división resolvió el problema de espaciado")
    
    # 3. Análisis de la palabra dividida
    print("\n3. ANÁLISIS DE LA PALABRA DIVIDIDA:")
    print("-" * 40)
    print(f"Palabra original: '{palabra_dividida}'")
    
    # Obtener todas las posibles divisiones
    divisiones_posibles = dividir_silabas_aleman(palabra_dividida)
    print(f"Divisiones posibles: {divisiones_posibles}")
    
    # Simular la división aplicada
    parte1 = "koper"
    parte2 = "nikanische"
    print(f"División aplicada: '{parte1}-{parte2}'")
    
    # Calcular cuánto espacio se ganó
    ancho_palabra_completa = pdfmetrics.stringWidth(palabra_dividida, GARAMOND_REGULAR_NAME, font_size)
    ancho_parte1 = pdfmetrics.stringWidth(parte1 + "-", GARAMOND_REGULAR_NAME, font_size)
    espacio_ganado = ancho_palabra_completa - ancho_parte1
    
    print(f"Ancho palabra completa: {ancho_palabra_completa:.2f}pt")
    print(f"Ancho parte1 + guión: {ancho_parte1:.2f}pt")
    print(f"Espacio ganado: {espacio_ganado:.2f}pt")
    
    # 4. Cálculo de reducción necesaria
    print("\n4. CÁLCULO DE REDUCCIÓN NECESARIA:")
    print("-" * 40)
    
    if num_espacios_original > 0:
        espacio_ideal = pdfmetrics.stringWidth(' ', GARAMOND_REGULAR_NAME, font_size)
        limite_maximo = espacio_ideal * ESPACIADO_MAXIMO_MULTIPLICADOR
        
        # Calcular cuánto espacio se necesita reducir por cada espacio
        reduccion_por_espacio = espaciado_original - limite_maximo
        reduccion_total_necesaria = reduccion_por_espacio * num_espacios_original
        
        print(f"Espaciado original: {espaciado_original:.2f}pt")
        print(f"Límite máximo (1.5x): {limite_maximo:.2f}pt")
        print(f"Reducción necesaria por espacio: {reduccion_por_espacio:.2f}pt")
        print(f"Reducción total necesaria: {reduccion_total_necesaria:.2f}pt")
        print(f"Espacio ganado con división: {espacio_ganado:.2f}pt")
        
        if espacio_ganado >= reduccion_total_necesaria:
            print(f"✅ La división es suficiente para resolver el espaciado")
        else:
            print(f"❌ La división NO es suficiente. Se necesitan {reduccion_total_necesaria - espacio_ganado:.2f}pt más")
    
    # 5. Verificar si la división fue óptima
    print("\n5. VERIFICACIÓN DE DIVISIÓN ÓPTIMA:")
    print("-" * 40)
    
    # Simular la función calcular_division_optima_para_espaciado
    palabras_linea = linea_original.split()
    division_optima = calcular_division_optima_para_espaciado(
        palabra_dividida, palabras_linea, max_width, font_size
    )
    
    if division_optima and division_optima[0] is not None:
        parte1_optima, parte2_optima = division_optima[0], division_optima[1]
        print(f"División óptima calculada: '{parte1_optima}-{parte2_optima}'")
        print(f"División aplicada: '{parte1}-{parte2}'")
        
        if parte1_optima == parte1 and parte2_optima == parte2:
            print("✅ La división aplicada coincide con la óptima")
        else:
            print("❌ La división aplicada NO coincide con la óptima")
            print(f"   Se debería haber dividido en: '{parte1_optima}-{parte2_optima}'")
    else:
        print("❌ No se encontró división óptima válida")
    
    print("\n" + "=" * 80)
    print("FIN DEL ANÁLISIS")
    print("=" * 80)

def main():
    """Función principal"""
    print("🔍 Iniciando análisis detallado de espaciado...")
    
    # Registrar fuentes
    if not registrar_fuentes():
        return
    
    # Analizar la línea específica
    analizar_linea_especifica()

if __name__ == "__main__":
    main()
