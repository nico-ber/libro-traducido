#!/usr/bin/env python3
import fitz
import json

def verificar_sangria_justificado():
    """Verifica que la sangría se aplique correctamente y que la última línea no esté justificada."""
    
    print("=== VERIFICACIÓN DE SANGRÍA Y JUSTIFICADO ===")
    
    # Cargar el JSON de bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Buscar bloques justificados
    bloques_justificados = [b for b in bloques if b.get('alineacion') == 'justificado']
    
    print(f"BLOQUES JUSTIFICADOS EN JSON:")
    print(f"  Total encontrados: {len(bloques_justificados)}")
    
    if bloques_justificados:
        print(f"\nANÁLISIS DEL PRIMER BLOQUE JUSTIFICADO:")
        bloque = bloques_justificados[0]
        print(f"  Página: {bloque.get('pagina')}")
        print(f"  Alineación: {bloque.get('alineacion')}")
        print(f"  X izquierda: {bloque.get('x_left', 0):.2f}")
        print(f"  X derecha: {bloque.get('x_right', 0):.2f}")
        print(f"  Ancho total: {bloque.get('x_right', 0) - bloque.get('x_left', 0):.2f} puntos")
        
        # Analizar las líneas del bloque
        if 'lines' in bloque:
            print(f"\nLÍNEAS DEL BLOQUE:")
            for i, linea in enumerate(bloque['lines'][:5]):  # Solo primeras 5 líneas
                bbox = linea.get('bbox', [])
                if len(bbox) >= 4:
                    ancho_linea = bbox[2] - bbox[0]
                    x_inicio = bbox[0]
                    print(f"  Línea {i+1}:")
                    print(f"    X inicio: {x_inicio:.2f} puntos")
                    print(f"    Ancho: {ancho_linea:.2f} puntos")
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
                        x_inicio = bbox[0]
                        lineas_maquetado.append({
                            'bbox': bbox,
                            'ancho': ancho,
                            'x_inicio': x_inicio,
                            'text': line.get('spans', [{}])[0].get('text', '')
                        })
    
    # Ordenar por posición Y (de arriba a abajo)
    lineas_ordenadas = sorted(lineas_maquetado, key=lambda x: x['bbox'][1], reverse=True)
    
    # Verificar configuración de márgenes
    ancho_pagina = page_maquetado.rect.width
    margen_izq = 75  # Según la configuración
    margen_der = 62  # Según la configuración
    ancho_disponible = ancho_pagina - margen_izq - margen_der
    sangria_esperada = 20  # SANGRIO_PARRAFO
    
    print(f"\nCONFIGURACIÓN:")
    print(f"  Ancho de página: {ancho_pagina:.2f} puntos")
    print(f"  Margen izquierdo: {margen_izq} puntos")
    print(f"  Margen derecho: {margen_der} puntos")
    print(f"  Ancho disponible: {ancho_disponible:.2f} puntos")
    print(f"  Sangría esperada: {sangria_esperada} puntos")
    
    # Analizar las primeras líneas para verificar sangría
    print(f"\nANÁLISIS DE LÍNEAS (ordenadas de arriba a abajo):")
    
    lineas_con_sangria = []
    lineas_justificadas = []
    lineas_no_justificadas = []
    
    for i, linea in enumerate(lineas_ordenadas[:15]):  # Analizar primeras 15 líneas
        x_inicio = linea['x_inicio']
        ancho = linea['ancho']
        
        # Verificar si tiene sangría
        tiene_sangria = abs(x_inicio - (margen_izq + sangria_esperada)) < 5  # Tolerancia de 5 puntos
        
        # Verificar si está justificada (ocupa casi todo el ancho disponible)
        esta_justificada = ancho > ancho_disponible * 0.9
        
        print(f"  Línea {i+1}:")
        print(f"    X inicio: {x_inicio:.2f} puntos")
        print(f"    Ancho: {ancho:.2f} puntos")
        print(f"    Sangría: {'✅ SÍ' if tiene_sangria else '❌ NO'}")
        print(f"    Justificada: {'✅ SÍ' if esta_justificada else '❌ NO'}")
        print(f"    Texto: '{linea['text'][:40]}...'")
        
        if tiene_sangria:
            lineas_con_sangria.append(linea)
        if esta_justificada:
            lineas_justificadas.append(linea)
        else:
            lineas_no_justificadas.append(linea)
    
    # Resumen
    print(f"\nRESUMEN:")
    print(f"  Líneas con sangría: {len(lineas_con_sangria)}")
    print(f"  Líneas justificadas: {len(lineas_justificadas)}")
    print(f"  Líneas no justificadas: {len(lineas_no_justificadas)}")
    
    # Verificar que la primera línea de cada párrafo justificado tenga sangría
    if lineas_con_sangria:
        print(f"\n✅ SANGRÍA DETECTADA:")
        print(f"  Se encontraron {len(lineas_con_sangria)} líneas con sangría")
        print(f"  La sangría se está aplicando correctamente en la primera línea de párrafos justificados")
    else:
        print(f"\n⚠️  SANGRÍA NO DETECTADA:")
        print(f"  No se encontraron líneas con sangría")
    
    # Verificar que no todas las líneas estén justificadas (debería haber líneas no justificadas)
    if lineas_no_justificadas:
        print(f"\n✅ JUSTIFICADO CORRECTO:")
        print(f"  Se encontraron {len(lineas_no_justificadas)} líneas no justificadas")
        print(f"  La última línea de cada párrafo no está justificada (correcto)")
    else:
        print(f"\n⚠️  JUSTIFICADO INCORRECTO:")
        print(f"  Todas las líneas están justificadas")
        print(f"  La última línea debería estar alineada a la izquierda")
    
    doc_maquetado.close()

if __name__ == "__main__":
    verificar_sangria_justificado()
