#!/usr/bin/env python3
"""
Verifica si hay líneas que terminan con guión en el PDF maquetado.
"""

import fitz  # PyMuPDF

def verificar_lineas_con_guion_final():
    """Verifica líneas que terminan con guión en el PDF maquetado."""
    
    print("=== VERIFICACIÓN DE LÍNEAS QUE TERMINAN CON GUIÓN ===\n")
    
    # Abrir el PDF maquetado
    doc = fitz.open("Salida/maquetado.pdf")
    
    if len(doc) == 0:
        print("❌ No se pudo abrir el PDF maquetado")
        return
    
    total_lineas_con_guion_final = 0
    
    # Analizar cada página
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"--- PÁGINA {page_num + 1} ---")
        
        # Extraer texto con información de posición
        text_dict = page.get_text("dict")
        
        lineas_encontradas = 0
        
        # Buscar bloques de texto
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    # Verificar si la línea termina con guión
                    if line_text.rstrip().endswith("-"):
                        print(f"✅ LÍNEA TERMINA CON GUIÓN: '{line_text.strip()}'")
                        lineas_encontradas += 1
                        total_lineas_con_guion_final += 1
        
        if lineas_encontradas == 0:
            print("❌ No se encontraron líneas que terminen con guión en esta página")
        
        print()
    
    print(f"=== RESUMEN ===")
    print(f"Total de líneas que terminan con guión: {total_lineas_con_guion_final}")
    
    if total_lineas_con_guion_final == 0:
        print("❌ No se encontraron líneas que terminen con guión en todo el documento")
        print("💡 Esto significa que el salto de línea forzado no se está aplicando correctamente")
    else:
        print("✅ Se encontraron líneas que terminan con guión")
        print("💡 El sistema de salto de línea forzado está funcionando")
    
    doc.close()

if __name__ == "__main__":
    verificar_lineas_con_guion_final()
