#!/usr/bin/env python3
import json

def verificar_espacio_despues():
    """Verifica que los valores de espacio_despues estén correctamente calculados y redondeados."""
    
    print("=== VERIFICACIÓN DE ESPACIO_DESPUES ===")
    
    # Cargar el JSON de bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16
    bloques_pagina_16 = [b for b in bloques if b.get('pagina') == 16]
    
    print(f"BLOQUES EN LA PÁGINA 16:")
    print(f"  Total encontrados: {len(bloques_pagina_16)}")
    
    # Ordenar por posición vertical
    bloques_pagina_16.sort(key=lambda b: b.get('y_top', 0))
    
    print(f"\nANÁLISIS DE ESPACIADO:")
    for i, bloque in enumerate(bloques_pagina_16):
        texto = bloque.get('text', '')[:50] + "..." if len(bloque.get('text', '')) > 50 else bloque.get('text', '')
        y_top = bloque.get('y_top', 0)
        y_bottom = bloque.get('y_bottom', 0)
        espacio_despues = bloque.get('espacio_despues', 0)
        
        print(f"\n  Bloque {i+1}:")
        print(f"    Texto: {texto}")
        print(f"    y_top: {y_top:.2f}")
        print(f"    y_bottom: {y_bottom:.2f}")
        print(f"    espacio_despues: {espacio_despues}")
        
        # Verificar si el valor está redondeado
        if isinstance(espacio_despues, int):
            print(f"    ✅ Valor redondeado correctamente")
        else:
            print(f"    ❌ Valor NO redondeado: {espacio_despues}")
        
        # Verificar si hay un bloque siguiente para calcular la distancia real
        if i < len(bloques_pagina_16) - 1:
            siguiente = bloques_pagina_16[i + 1]
            distancia_real = siguiente.get('y_top', 0) - y_bottom
            print(f"    Distancia real al siguiente: {distancia_real:.2f}")
            
            if distancia_real >= 0:
                print(f"    ✅ Distancia válida (no negativa)")
            else:
                print(f"    ❌ Distancia negativa (error)")
    
    # Verificar valores únicos de espacio_despues
    valores_espacio = [b.get('espacio_despues', 0) for b in bloques_pagina_16]
    valores_unicos = sorted(set(valores_espacio))
    
    print(f"\nVALORES ÚNICOS DE ESPACIO_DESPUES:")
    print(f"  Valores encontrados: {valores_unicos}")
    print(f"  Total de valores únicos: {len(valores_unicos)}")
    
    # Verificar que todos los valores sean enteros
    valores_enteros = [v for v in valores_espacio if isinstance(v, int)]
    print(f"  Valores enteros: {len(valores_enteros)}/{len(valores_espacio)}")
    
    if len(valores_enteros) == len(valores_espacio):
        print(f"  ✅ Todos los valores están redondeados correctamente")
    else:
        print(f"  ❌ Algunos valores no están redondeados")
    
    print(f"\n=== FIN DE VERIFICACIÓN ===")

if __name__ == "__main__":
    verificar_espacio_despues()
