#!/usr/bin/env python3
import fitz
import json

def verificar_sangria_primera_linea():
    """Verifica que la sangría solo se aplique a la primera línea de los párrafos."""
    
    print("=== VERIFICACIÓN DE SANGRÍA EN PRIMERA LÍNEA ===")
    
    # Cargar el JSON de bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16 que tengan inicio_parrafo
    bloques_inicio_parrafo = [b for b in bloques if b.get('pagina') == 16 and b.get('inicio_parrafo', False)]
    
    print(f"BLOQUES CON INICIO DE PÁRRAFO EN PÁGINA 16:")
    print(f"  Total encontrados: {len(bloques_inicio_parrafo)}")
    
    for i, bloque in enumerate(bloques_inicio_parrafo):
        print(f"\n  Bloque {i+1}:")
        print(f"    Texto: {bloque.get('text', '')[:100]}...")
        print(f"    Alineación: {bloque.get('alineacion', 'N/A')}")
        print(f"    Tipo: {bloque.get('tipo', 'N/A')}")
        print(f"    Inicio párrafo: {bloque.get('inicio_parrafo', False)}")
        
        # Verificar si tiene múltiples líneas
        if 'lines' in bloque:
            print(f"    Número de líneas: {len(bloque['lines'])}")
            for j, linea in enumerate(bloque['lines']):
                print(f"      Línea {j+1}: {linea.get('texto', '')[:50]}...")
        else:
            print(f"    Bloque unilínea")
    
    # Analizar el PDF maquetado para verificar posiciones X
    print(f"\n=== ANÁLISIS DEL PDF MAQUETADO ===")
    
    doc = fitz.open("Salida/maquetado.pdf")
    print(f"Páginas en el PDF: {len(doc)}")
    if len(doc) > 15:
        page = doc[15]  # Página 16 (índice 15)
    else:
        page = doc[len(doc)-1]  # Última página disponible
    
    # Extraer bloques de texto del PDF
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [b for b in blocks if b.get("type") == 0]  # Solo bloques de texto
    
    print(f"BLOQUES DE TEXTO EN EL PDF MAQUETADO:")
    print(f"  Total encontrados: {len(text_blocks)}")
    
    margen_izq_esperado = 75  # Margen izquierdo detectado
    sangria_esperada = 20     # SANGRIO_PARRAFO
    
    for i, block in enumerate(text_blocks):
        bbox = block["bbox"]
        x0, y0, x1, y1 = bbox
        text = block.get("text", "").strip()
        
        print(f"\n  Bloque {i+1}:")
        print(f"    Texto: {text[:50]}...")
        print(f"    Posición X: {x0:.2f}")
        print(f"    Ancho: {x1 - x0:.2f}")
        
        if text and "Ich betone" in text:
            print(f"    🎯 BLOQUE CON 'ICH BETONE':")
            print(f"    Margen esperado: {margen_izq_esperado}")
            print(f"    Sangría esperada: {sangria_esperada}")
            print(f"    Posición esperada con sangría: {margen_izq_esperado + sangria_esperada}")
            
            # Verificar si es la primera línea (debería tener sangría)
            if abs(x0 - (margen_izq_esperado + sangria_esperada)) < 5:
                print(f"    ✅ PRIMERA LÍNEA: Sangría aplicada correctamente")
            elif abs(x0 - margen_izq_esperado) < 5:
                print(f"    ❌ PRIMERA LÍNEA: Sin sangría (error)")
            else:
                print(f"    ⚠️  Posición inesperada: {x0}")
        
        # Verificar si hay otras líneas del mismo párrafo (no deberían tener sangría)
        elif text and any(palabra in text for palabra in ["Weltbild", "kopernikanische", "Erdwelt-Theorie"]):
            print(f"    📝 LÍNEA SIGUIENTE DEL PÁRRAFO:")
            if abs(x0 - margen_izq_esperado) < 5:
                print(f"    ✅ LÍNEA SIGUIENTE: Sin sangría (correcto)")
            else:
                print(f"    ❌ LÍNEA SIGUIENTE: Con sangría (error)")
    
    doc.close()
    print(f"\n=== FIN DE VERIFICACIÓN ===")

if __name__ == "__main__":
    verificar_sangria_primera_linea()
