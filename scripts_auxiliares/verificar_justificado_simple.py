#!/usr/bin/env python3
import fitz
import json

def verificar_justificado_simple():
    """Verifica el justificado de forma simple comparando anchos de líneas."""
    
    print("=== VERIFICACIÓN SIMPLE DE JUSTIFICADO ===")
    
    # Cargar el JSON de bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Buscar bloques justificados
    bloques_justificados = [b for b in bloques if b.get('alineacion') == 'justificado']
    
    print(f"BLOQUES JUSTIFICADOS EN JSON:")
    print(f"  Total encontrados: {len(bloques_justificados)}")
    
    if bloques_justificados:
        print(f"\nPRIMER BLOQUE JUSTIFICADO:")
        bloque = bloques_justificados[0]
        print(f"  Página: {bloque.get('pagina')}")
        print(f"  Texto: '{bloque.get('text', '')[:100]}...'")
        print(f"  Alineación: {bloque.get('alineacion')}")
        print(f"  X izquierda: {bloque.get('x_left', 0):.2f}")
        print(f"  X derecha: {bloque.get('x_right', 0):.2f}")
        print(f"  Ancho total: {bloque.get('x_right', 0) - bloque.get('x_left', 0):.2f} puntos")
        
        # Analizar las líneas del bloque
        if 'lines' in bloque:
            print(f"\nLÍNEAS DEL BLOQUE:")
            for i, linea in enumerate(bloque['lines'][:3]):  # Solo primeras 3 líneas
                bbox = linea.get('bbox', [])
                if len(bbox) >= 4:
                    ancho_linea = bbox[2] - bbox[0]
                    print(f"  Línea {i+1}: ancho = {ancho_linea:.2f} puntos")
                    print(f"    Texto: '{linea.get('texto', '')[:50]}...'")
                    print(f"    Alineación: {linea.get('align', 'N/A')}")
    
    # Verificar el PDF maquetado
    print(f"\nVERIFICANDO PDF MAQUETADO...")
    
    doc_maquetado = fitz.open("Salida/maquetado.pdf")
    page_maquetado = doc_maquetado[0]  # Primera página
    
    # Obtener todas las líneas del PDF
    raw_maquetado = page_maquetado.get_text("rawdict")
    
    lineas_maquetado = []
    for block in raw_maquetado.get('blocks', []):
        if block.get('type') == 0:  # Solo texto
            for line in block.get('lines', []):
                if line.get('spans'):
                    bbox = line.get('bbox')
                    if bbox:
                        ancho = bbox[2] - bbox[0]
                        lineas_maquetado.append({
                            'bbox': bbox,
                            'ancho': ancho,
                            'text': line.get('spans', [{}])[0].get('text', '')
                        })
    
    # Ordenar por ancho para encontrar las más anchas (probablemente justificadas)
    lineas_ordenadas = sorted(lineas_maquetado, key=lambda x: x['ancho'], reverse=True)
    
    print(f"LÍNEAS MÁS ANCHAS EN PDF MAQUETADO:")
    for i, linea in enumerate(lineas_ordenadas[:5]):
        print(f"  {i+1}. Ancho: {linea['ancho']:.2f} puntos")
        print(f"     Texto: '{linea['text'][:50]}...'")
    
    # Verificar si hay líneas que ocupan casi todo el ancho de página
    ancho_pagina = page_maquetado.rect.width
    margen_izq = 75  # Según la configuración
    margen_der = 62  # Según la configuración
    ancho_disponible = ancho_pagina - margen_izq - margen_der
    
    print(f"\nANÁLISIS DE ANCHOS:")
    print(f"  Ancho de página: {ancho_pagina:.2f} puntos")
    print(f"  Ancho disponible: {ancho_disponible:.2f} puntos")
    print(f"  Margen izquierdo: {margen_izq} puntos")
    print(f"  Margen derecho: {margen_der} puntos")
    
    # Contar líneas que ocupan más del 90% del ancho disponible
    lineas_justificadas = [l for l in lineas_maquetado if l['ancho'] > ancho_disponible * 0.9]
    
    print(f"\nLÍNEAS PROBABLEMENTE JUSTIFICADAS (>90% del ancho disponible):")
    print(f"  Total: {len(lineas_justificadas)} líneas")
    
    if lineas_justificadas:
        print(f"  ✅ JUSTIFICADO DETECTADO:")
        print(f"  Se encontraron {len(lineas_justificadas)} líneas que ocupan casi todo el ancho disponible")
        print(f"  El justificado se está aplicando correctamente")
    else:
        print(f"  ⚠️  JUSTIFICADO NO DETECTADO:")
        print(f"  No se encontraron líneas que ocupen más del 90% del ancho disponible")
    
    doc_maquetado.close()

if __name__ == "__main__":
    verificar_justificado_simple()
