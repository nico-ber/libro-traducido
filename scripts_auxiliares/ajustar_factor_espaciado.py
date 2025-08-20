#!/usr/bin/env python3
import fitz
import json
import numpy as np
import subprocess
import os
import sys

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
    distancias_maquetado = extraer_distancias_pdf("Salida/maquetado.pdf", page_index=0)
    
    # Calcular factor de escala usando el mínimo de distancias
    min_dist = min(len(espacios_original), len(distancias_maquetado))
    
    if min_dist > 0:
        factores = []
        for i in range(min_dist):
            if distancias_maquetado[i] > 0:
                factor = espacios_original[i] / distancias_maquetado[i]
                factores.append(factor)
        
        if factores:
            factor_promedio = np.mean(factores)
            return factor_promedio
    
    return None

def actualizar_factor_en_maquetar_pdf(nuevo_factor):
    """Actualiza el factor de escala en el script de maquetación."""
    
    # Leer el archivo
    with open("scripts/maquetar_pdf.py", "r", encoding="utf-8") as f:
        contenido = f.read()
    
    # Reemplazar la línea del factor de espaciado
    import re
    patron = r'ESPACIADO_ESCALA_VISUAL = [0-9.]+'
    nueva_linea = f'ESPACIADO_ESCALA_VISUAL = {nuevo_factor:.3f}'
    contenido = re.sub(patron, nueva_linea, contenido)
    
    # Escribir el archivo
    with open("scripts/maquetar_pdf.py", "w", encoding="utf-8") as f:
        f.write(contenido)
    
    print(f"✅ Factor actualizado en scripts/maquetar_pdf.py: {nuevo_factor:.3f}")

def ajustar_factor_espaciado():
    """Ajusta iterativamente el factor de escala del espaciado."""
    
    print("=== AJUSTE ITERATIVO DEL FACTOR DE ESCALA DEL ESPACIADO ===")
    
    # Factor inicial
    factor_actual = 0.488
    max_iteraciones = 5
    tolerancia = 0.01
    
    for iteracion in range(max_iteraciones):
        print(f"\n--- ITERACIÓN {iteracion + 1} ---")
        print(f"Factor actual: {factor_actual:.3f}")
        
        # Actualizar el factor en el script
        actualizar_factor_en_maquetar_pdf(factor_actual)
        
        # Regenerar el PDF
        print("Regenerando PDF...")
        resultado = subprocess.run([
            sys.executable, "scripts/maquetar_pdf.py",
            "--bloques", "Salida/bloques.json",
            "--pdf_original", "Estatico/original.pdf",
            "--salida", "Salida/maquetado.pdf",
            "--pages", "16"
        ], capture_output=True, text=True, encoding='utf-8')
        
        if resultado.returncode != 0:
            print(f"❌ Error al generar PDF: {resultado.stderr}")
            return None
        
        # Calcular nuevo factor
        nuevo_factor = calcular_factor_espaciado()
        
        if nuevo_factor is None:
            print("❌ No se pudo calcular el factor")
            return None
        
        print(f"Nuevo factor calculado: {nuevo_factor:.3f}")
        
        # Verificar si convergió
        diferencia = abs(nuevo_factor - factor_actual)
        print(f"Diferencia: {diferencia:.3f}")
        
        if diferencia < tolerancia:
            print(f"✅ Convergencia alcanzada en {iteracion + 1} iteraciones")
            print(f"Factor final: {nuevo_factor:.3f}")
            return nuevo_factor
        
        # Actualizar factor para la siguiente iteración
        factor_actual = nuevo_factor
    
    print(f"⚠️ No se alcanzó convergencia en {max_iteraciones} iteraciones")
    print(f"Factor final: {factor_actual:.3f}")
    return factor_actual

if __name__ == "__main__":
    factor_final = ajustar_factor_espaciado()
    if factor_final:
        print(f"\n🎯 FACTOR DE ESCALA FINAL DEL ESPACIADO: {factor_final:.3f}")
    else:
        print("\n❌ No se pudo determinar el factor final")
