#!/usr/bin/env python3
"""
Script de debug para analizar la división silábica y verificar el salto de línea.
"""

import fitz  # PyMuPDF
import re

def analizar_division_silabica():
    """Analiza el PDF maquetado para verificar la división silábica y saltos de línea."""
    
    print("=== DEBUG: ANÁLISIS DETALLADO DE DIVISIÓN SILÁBICA ===\n")
    
    # Abrir el PDF maquetado
    doc = fitz.open("Salida/maquetado.pdf")
    
    if len(doc) == 0:
        print("❌ No se pudo abrir el PDF maquetado")
        return
    
    # Analizar cada página
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"--- PÁGINA {page_num + 1} ---")
        
        # Extraer texto con información de posición
        text_dict = page.get_text("dict")
        
        # Buscar bloques de texto
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    # Buscar líneas que contengan guiones
                    if "-" in line_text:
                        print(f"🔍 LÍNEA CON GUION: '{line_text.strip()}'")
                        
                        # Verificar si hay espacios después del guión
                        guion_index = line_text.find("-")
                        if guion_index != -1:
                            after_guion = line_text[guion_index + 1:]
                            print(f"   Después del guión: '{after_guion}'")
                            
                            # Verificar si hay espacios al inicio después del guión
                            if after_guion.startswith(" "):
                                print(f"   ⚠️  HAY ESPACIO después del guión")
                            else:
                                print(f"   ✅ NO hay espacio después del guión")
                        
                        # Verificar si esta línea termina con guión
                        if line_text.rstrip().endswith("-"):
                            print(f"   ✅ Línea termina con guión (debería forzar salto)")
                        else:
                            print(f"   ❌ Línea NO termina con guión")
                        
                        print()
        
        print()
    
    doc.close()

if __name__ == "__main__":
    analizar_division_silabica()
