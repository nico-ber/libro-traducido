#!/usr/bin/env python3
import fitz
import json

def verificar_separacion_parrafos():
    """Verifica que la separación de párrafos en la página 16 esté funcionando correctamente."""
    
    print("=== VERIFICACIÓN DE SEPARACIÓN DE PÁRRAFOS - PÁGINA 16 ===")
    
    # Cargar el JSON de bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16
    bloques_pagina_16 = [b for b in bloques if b.get('pagina') == 16]
    
    print(f"BLOQUES EN LA PÁGINA 16:")
    print(f"  Total encontrados: {len(bloques_pagina_16)}")
    
    # Buscar específicamente el bloque que contiene "Ich betone"
    bloque_ich_betone = None
    for bloque in bloques_pagina_16:
        if "Ich betone" in bloque.get('text', ''):
            bloque_ich_betone = bloque
            break
    
    if bloque_ich_betone:
        print(f"\n✅ BLOQUE 'ICH BETONE' ENCONTRADO:")
        print(f"  Texto: '{bloque_ich_betone.get('text', '')[:100]}...'")
        print(f"  Tipo: {bloque_ich_betone.get('tipo')}")
        print(f"  Alineación: {bloque_ich_betone.get('alineacion')}")
        print(f"  Es bloque separado: {'✅ SÍ' if bloque_ich_betone.get('tipo') == 'parrafo' else '❌ NO'}")
        
        # Verificar si es un bloque independiente (no parte de un bloque más grande)
        if len(bloque_ich_betone.get('text', '')) < 200:  # Si es un bloque pequeño, probablemente está separado
            print(f"  ✅ Probablemente separado correctamente (texto corto)")
        else:
            print(f"  ⚠️ Texto muy largo, podría estar incluido en un bloque mayor")
    else:
        print(f"\n❌ BLOQUE 'ICH BETONE' NO ENCONTRADO")
    
    # Mostrar todos los bloques de la página 16
    print(f"\nTODOS LOS BLOQUES DE LA PÁGINA 16:")
    for i, bloque in enumerate(bloques_pagina_16):
        texto = bloque.get('text', '')[:80]
        print(f"  Bloque {i+1}:")
        print(f"    Texto: '{texto}...'")
        print(f"    Tipo: {bloque.get('tipo')}")
        print(f"    Alineación: {bloque.get('alineacion')}")
        print(f"    Longitud: {len(bloque.get('text', ''))} caracteres")
        print()
    
    # Verificar el PDF maquetado
    print(f"VERIFICANDO PDF MAQUETADO...")
    
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
                        text = line.get('spans', [{}])[0].get('text', '')
                        lineas_maquetado.append({
                            'bbox': bbox,
                            'ancho': ancho,
                            'x_inicio': x_inicio,
                            'text': text
                        })
    
    # Buscar la línea "Ich betone" en el PDF maquetado
    linea_ich_betone = None
    for linea in lineas_maquetado:
        if "Ich betone" in linea['text']:
            linea_ich_betone = linea
            break
    
    if linea_ich_betone:
        print(f"\n✅ LÍNEA 'ICH BETONE' ENCONTRADA EN PDF:")
        print(f"  Texto: '{linea_ich_betone['text']}'")
        print(f"  X inicio: {linea_ich_betone['x_inicio']:.2f} puntos")
        print(f"  Ancho: {linea_ich_betone['ancho']:.2f} puntos")
        
        # Verificar si tiene sangría (debería estar más a la derecha que las líneas normales)
        margen_izq = 75  # Según la configuración
        sangria_esperada = 20  # SANGRIO_PARRAFO
        
        if linea_ich_betone['x_inicio'] > margen_izq + sangria_esperada - 5:  # Tolerancia de 5 puntos
            print(f"  ✅ Tiene sangría (inicio de párrafo)")
        else:
            print(f"  ❌ No tiene sangría (no es inicio de párrafo)")
    else:
        print(f"\n❌ LÍNEA 'ICH BETONE' NO ENCONTRADA EN PDF")
    
    doc_maquetado.close()

if __name__ == "__main__":
    verificar_separacion_parrafos()
