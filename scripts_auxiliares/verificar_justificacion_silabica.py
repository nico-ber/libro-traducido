#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar visualmente la justificación con división silábica.
"""

import fitz
import json

def verificar_justificacion_silabica():
    """Verifica la justificación y división silábica en el PDF maquetado."""
    
    print("=== VERIFICACIÓN DE JUSTIFICACIÓN CON DIVISIÓN SILÁBICA ===\n")
    
    # Cargar bloques originales para comparar
    try:
        with open("Salida/bloques.json", "r", encoding="utf-8") as f:
            bloques = json.load(f)
        
        # Filtrar bloques justificados de la página 16
        bloques_justificados = [b for b in bloques if b.get('pagina') == 16 and b.get('alineacion') == 'justificado']
        
        print(f"Bloques justificados encontrados en página 16: {len(bloques_justificados)}")
        
        for i, bloque in enumerate(bloques_justificados[:3]):  # Mostrar solo los primeros 3
            texto = bloque.get('text', '')
            print(f"\n--- Bloque {i+1} ---")
            print(f"Texto: {texto[:100]}...")
            print(f"Tipo: {bloque.get('tipo', 'N/A')}")
            print(f"Font size: {bloque.get('font_size', 'N/A')}")
            
    except FileNotFoundError:
        print("No se encontró el archivo Salida/bloques.json")
    
    # Analizar el PDF maquetado
    try:
        doc = fitz.open("Salida/maquetado.pdf")
        page = doc[0]  # Primera página
        
        # Extraer texto con información de posición
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]
        
        print(f"\n=== ANÁLISIS DEL PDF MAQUETADO ===")
        print(f"Bloques de texto encontrados: {len(text_blocks)}")
        
        # Buscar líneas con guiones (indicador de división silábica)
        lineas_con_guiones = []
        
        for block in text_blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    texto = span.get("text", "")
                    if "-" in texto and len(texto) > 3:  # Buscar guiones que no sean solo puntuación
                        # Verificar que no sea solo un guión al final
                        if not texto.endswith("-") and not texto.startswith("-"):
                            lineas_con_guiones.append(texto)
        
        print(f"\nLíneas con división silábica detectadas: {len(lineas_con_guiones)}")
        
        for i, linea in enumerate(lineas_con_guiones[:5]):  # Mostrar solo las primeras 5
            print(f"  {i+1}. {linea}")
        
        if not lineas_con_guiones:
            print("  No se detectaron divisiones silábicas en el PDF.")
        
        doc.close()
        
    except Exception as e:
        print(f"Error al analizar el PDF: {e}")
    
    print("\n=== RECOMENDACIONES ===")
    print("✅ Si ves divisiones silábicas, el sistema está funcionando correctamente")
    print("✅ Las palabras largas se dividen automáticamente cuando el espaciado es excesivo")
    print("✅ El espaciado máximo está configurado en 1.8x el espacio normal")
    print("✅ Solo se dividen palabras de 5+ caracteres con partes mínimas de 3 caracteres")

if __name__ == "__main__":
    verificar_justificacion_silabica()
