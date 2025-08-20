#!/usr/bin/env python3
import fitz
import json
import numpy as np

def extraer_primera_distancia_pdf(pdf_path, page_index=0):
    """Extrae la primera distancia entre bloques de texto de un PDF."""
    
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Extraer bloques de texto
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [b for b in blocks if b.get("type") == 0]  # Solo bloques de texto
    

    
    # Agrupar líneas por bloques basándose en la proximidad vertical
    bloques_agrupados = []
    bloque_actual = []
    
    for block in text_blocks:
        if not bloque_actual:
            bloque_actual.append(block)
        else:
            # Calcular distancia vertical con la última línea del bloque actual
            ultima_linea = bloque_actual[-1]
            distancia = block["bbox"][1] - ultima_linea["bbox"][3]  # y0 actual - y1 anterior
            

            
            # Si la distancia es pequeña (< 15 puntos), es parte del mismo bloque
            if distancia < 15:
                bloque_actual.append(block)
            else:
                # Es un nuevo bloque
                bloques_agrupados.append(bloque_actual)
                bloque_actual = [block]
    
    # Agregar el último bloque
    if bloque_actual:
        bloques_agrupados.append(bloque_actual)
    
    # Calcular la primera distancia entre bloques

    if len(bloques_agrupados) >= 2:
        bloque_1 = bloques_agrupados[0]
        bloque_2 = bloques_agrupados[1]
        
        # Obtener coordenadas del final del primer bloque y inicio del segundo
        y_bottom_1 = bloque_1[-1]["bbox"][3]  # y1 (bottom) de la última línea del primer bloque
        y_top_2 = bloque_2[0]["bbox"][1]  # y0 (top) de la primera línea del segundo bloque
        
        distancia = y_top_2 - y_bottom_1

        return distancia
    else:

        return None

def extraer_primera_distancia_json():
    """Extrae la primera distancia del JSON de bloques."""
    
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16
    bloques_pagina_16 = [b for b in bloques if b.get('pagina') == 16]
    
    # Ordenar por posición vertical
    bloques_ordenados = sorted(bloques_pagina_16, key=lambda b: b.get('y_top', 0))
    
    # Obtener la primera distancia
    if len(bloques_ordenados) >= 2:
        bloque_1 = bloques_ordenados[0]
        bloque_2 = bloques_ordenados[1]
        
        y_bottom_1 = bloque_1.get('y_bottom', 0)
        y_top_2 = bloque_2.get('y_top', 0)
        
        distancia = y_top_2 - y_bottom_1
        return distancia
    else:
        return None

def main():
    print("=== CÁLCULO DEL FACTOR DE ESCALA BASADO EN LA PRIMERA DISTANCIA ===")
    
    # Extraer primera distancia del PDF original (usando JSON)
    distancia_original = extraer_primera_distancia_json()
    
    # Extraer primera distancia del PDF maquetado
    distancia_maquetado = extraer_primera_distancia_pdf("Salida/maquetado.pdf", page_index=0)
    
    if distancia_original is None or distancia_maquetado is None:
        print("Error: No se pudo extraer la primera distancia de uno o ambos PDFs")
        return
    
    print(f"\nPRIMERA DISTANCIA:")
    print(f"  Original: {distancia_original:.1f}pt")
    print(f"  Maquetado: {distancia_maquetado:.1f}pt")
    
    # Calcular factor de escala
    factor_actual = 0.477  # Factor actual aplicado
    factor_calculado = distancia_original / distancia_maquetado
    
    print(f"\nFACTOR DE ESCALA:")
    print(f"  Factor actual aplicado: {factor_actual}")
    print(f"  Factor calculado: {factor_calculado:.3f}")
    print(f"  Diferencia: {abs(factor_actual - factor_calculado):.3f}")
    
    # Verificar si el factor actual es correcto
    if abs(factor_actual - factor_calculado) < 0.01:
        print(f"  ✅ El factor actual ({factor_actual}) es correcto")
    else:
        print(f"  ⚠️ El factor actual necesita ajuste")
        print(f"  💡 Factor recomendado: {factor_calculado:.3f}")
    
    # Calcular qué distancia resultaría con el factor calculado
    distancia_esperada = distancia_original / factor_calculado
    print(f"\nVERIFICACIÓN:")
    print(f"  Distancia esperada con factor {factor_calculado:.3f}: {distancia_esperada:.1f}pt")
    print(f"  Distancia real en maquetado: {distancia_maquetado:.1f}pt")
    print(f"  Diferencia: {abs(distancia_esperada - distancia_maquetado):.1f}pt")

if __name__ == "__main__":
    main()
