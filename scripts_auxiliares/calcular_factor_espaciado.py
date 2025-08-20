#!/usr/bin/env python3
import fitz
import json
import numpy as np

def extraer_distancias_pdf(pdf_path, page_index=0):
    """Extrae las distancias entre bloques de texto de un PDF."""
    
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
            
            # Si la distancia es pequeña (< 20 puntos), es parte del mismo bloque
            if distancia < 20:
                bloque_actual.append(block)
            else:
                # Es un nuevo bloque
                bloques_agrupados.append(bloque_actual)
                bloque_actual = [block]
    
    # Agregar el último bloque
    if bloque_actual:
        bloques_agrupados.append(bloque_actual)
    
    # Calcular distancias entre bloques
    distancias = []
    for i in range(len(bloques_agrupados) - 1):
        bloque_actual = bloques_agrupados[i]
        bloque_siguiente = bloques_agrupados[i + 1]
        
        # Obtener coordenadas del final del bloque actual y inicio del siguiente
        y_bottom_actual = bloque_actual[-1]["bbox"][3]  # y1 (bottom) de la última línea del bloque
        y_top_siguiente = bloque_siguiente[0]["bbox"][1]  # y0 (top) de la primera línea del siguiente bloque
        
        distancia = y_top_siguiente - y_bottom_actual
        distancias.append(distancia)
    
    doc.close()
    return distancias

def calcular_factor_espaciado():
    """Calcula el factor de escala del espaciado entre bloques."""
    
    print("=== CÁLCULO DEL FACTOR DE ESCALA DEL ESPACIADO ===")
    
    # Cargar bloques del JSON
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16
    bloques_pagina_16 = [b for b in bloques if b.get('pagina') == 16]
    bloques_pagina_16.sort(key=lambda b: b.get('y_top', 0))
    
    # Obtener valores de espacio_despues del JSON (valores originales)
    espacios_original = []
    for i in range(len(bloques_pagina_16) - 1):
        espacio = bloques_pagina_16[i].get('espacio_despues', 0)
        espacios_original.append(espacio)
    
    # Extraer distancias del PDF maquetado
    print("Extrayendo distancias del PDF maquetado...")
    distancias_maquetado = extraer_distancias_pdf("Salida/maquetado.pdf", page_index=0)
    
    print(f"\nDISTANCIAS ENCONTRADAS:")
    print(f"  Original (espacio_despues): {len(espacios_original)} distancias")
    print(f"  Maquetado: {len(distancias_maquetado)} distancias")
    
    # Mostrar las distancias
    print(f"\nDISTANCIAS ORIGINAL (espacio_despues):")
    for i, dist in enumerate(espacios_original):
        print(f"  {i+1}: {dist}pt")
    
    print(f"\nDISTANCIAS MAQUETADO:")
    for i, dist in enumerate(distancias_maquetado):
        print(f"  {i+1}: {dist:.1f}pt")
    
    # Calcular factor de escala usando el mínimo de distancias
    min_dist = min(len(espacios_original), len(distancias_maquetado))
    
    if min_dist > 0:
        factores = []
        for i in range(min_dist):
            if distancias_maquetado[i] > 0:
                factor = espacios_original[i] / distancias_maquetado[i]
                factores.append(factor)
                print(f"  Distancia {i+1}: {espacios_original[i]} / {distancias_maquetado[i]:.1f} = {factor:.3f}")
        
        if factores:
            factor_promedio = np.mean(factores)
            factor_mediana = np.median(factores)
            factor_std = np.std(factores)
            
            print(f"\nFACTOR DE ESCALA CALCULADO:")
            print(f"  Promedio: {factor_promedio:.3f}")
            print(f"  Mediana: {factor_mediana:.3f}")
            print(f"  Desviación estándar: {factor_std:.3f}")
            
            # Comparar con el factor de tipografía
            TIPOGRAFIA_ESCALA_VISUAL = 1.58
            print(f"\nCOMPARACIÓN CON FACTOR DE TIPOGRAFÍA:")
            print(f"  Factor tipografía: {TIPOGRAFIA_ESCALA_VISUAL}")
            print(f"  Factor espaciado: {factor_promedio:.3f}")
            print(f"  Diferencia: {abs(factor_promedio - TIPOGRAFIA_ESCALA_VISUAL):.3f}")
            
            if abs(factor_promedio - TIPOGRAFIA_ESCALA_VISUAL) < 0.1:
                print(f"  ✅ Los factores son similares. Se puede usar el mismo factor.")
            else:
                print(f"  ⚠️ Los factores son diferentes. Se necesita un factor separado.")
            
            return factor_promedio
    else:
        print(f"❌ Error: No se encontraron distancias válidas")
        return None

if __name__ == "__main__":
    calcular_factor_espaciado()
