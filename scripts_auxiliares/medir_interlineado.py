#!/usr/bin/env python3
import fitz
from PIL import Image, ImageDraw
import numpy as np

def medir_interlineado():
    """Mide el interlineado entre líneas de texto en ambos PDFs."""
    
    print("=== MEDICIÓN DE INTERLINEADO CORREGIDA ===")
    
    # 1. PDF Original
    doc_original = fitz.open("Estatico/original.pdf")
    page_original = doc_original[15]  # Página 16
    
    # 2. PDF Maquetado final
    doc_maquetado = fitz.open("Salida/maquetado.pdf")
    page_maquetado = doc_maquetado[0]  # Primera página
    
    # Obtener datos de ambos
    raw_original = page_original.get_text("rawdict")
    raw_maquetado = page_maquetado.get_text("rawdict")
    
    # Buscar líneas de texto en ambos
    lineas_original = []
    lineas_maquetado = []
    
    # Extraer líneas del original
    for block in raw_original.get('blocks', []):
        if block.get('type') == 0:  # Solo texto
            for line in block.get('lines', []):
                if line.get('spans'):
                    bbox = line.get('bbox')
                    if bbox:
                        lineas_original.append(bbox)
    
    # Extraer líneas del maquetado
    for block in raw_maquetado.get('blocks', []):
        if block.get('type') == 0:  # Solo texto
            for line in block.get('lines', []):
                if line.get('spans'):
                    bbox = line.get('bbox')
                    if bbox:
                        lineas_maquetado.append(bbox)
    
    print(f"LÍNEAS ENCONTRADAS:")
    print(f"  Original: {len(lineas_original)} líneas")
    print(f"  Maquetado: {len(lineas_maquetado)} líneas")
    
    # Calcular interlineado CORREGIDO (desde altura ascendente hasta base)
    interlineados_original = []
    interlineados_maquetado = []
    
    # Original - medir desde altura ascendente hasta base
    for i in range(len(lineas_original) - 1):
        linea_actual = lineas_original[i]
        linea_siguiente = lineas_original[i + 1]
        # Distancia desde la altura ascendente de la línea actual hasta la base de la siguiente
        # Altura ascendente = y0 de la línea actual
        # Base = y1 de la línea siguiente
        distancia = linea_siguiente[3] - linea_actual[1]  # y1_siguiente - y0_actual
        interlineados_original.append(distancia)
    
    # Maquetado - medir desde altura ascendente hasta base
    for i in range(len(lineas_maquetado) - 1):
        linea_actual = lineas_maquetado[i]
        linea_siguiente = lineas_maquetado[i + 1]
        # Distancia desde la altura ascendente de la línea actual hasta la base de la siguiente
        distancia = linea_siguiente[3] - linea_actual[1]  # y1_siguiente - y0_actual
        interlineados_maquetado.append(distancia)
    
    # Calcular promedios
    if interlineados_original:
        promedio_original = sum(interlineados_original) / len(interlineados_original)
        print(f"\nINTERLINEADO ORIGINAL (ascendente a base):")
        print(f"  Valores: {[f'{x:.2f}' for x in interlineados_original[:5]]}...")
        print(f"  Promedio: {promedio_original:.2f} puntos")
    
    if interlineados_maquetado:
        promedio_maquetado = sum(interlineados_maquetado) / len(interlineados_maquetado)
        print(f"\nINTERLINEADO MAQUETADO (ascendente a base):")
        print(f"  Valores: {[f'{x:.2f}' for x in interlineados_maquetado[:5]]}...")
        print(f"  Promedio: {promedio_maquetado:.2f} puntos")
    
    # Calcular factor de escala para interlineado
    if interlineados_original and interlineados_maquetado:
        factor_interlineado = promedio_original / promedio_maquetado
        print(f"\nFACTOR DE ESCALA PARA INTERLINEADO:")
        print(f"  Factor calculado: {factor_interlineado:.4f}")
        print(f"  Diferencia: {abs(promedio_original - promedio_maquetado):.2f} puntos")
    
    # Generar imágenes con líneas marcadas
    print(f"\nGENERANDO IMÁGENES CON LÍNEAS MARCADAS...")
    
    # Generar imagen del original
    mat = fitz.Matrix(2, 2)  # Zoom 2x para mejor visualización
    pix_original = page_original.get_pixmap(matrix=mat)
    img_original = Image.frombytes("RGB", [pix_original.width, pix_original.height], pix_original.samples)
    draw_original = ImageDraw.Draw(img_original)
    
    # Dibujar líneas en original
    for i, bbox in enumerate(lineas_original[:10]):  # Solo primeras 10 líneas
        x0 = int(bbox[0] * 2)
        y0 = int(bbox[1] * 2)  # Altura ascendente
        x1 = int(bbox[2] * 2)
        y1 = int(bbox[3] * 2)  # Base
        
        # Línea superior (azul) - altura ascendente
        draw_original.line([(x0, y0), (x1, y0)], fill="blue", width=2)
        # Línea inferior (roja) - base
        draw_original.line([(x0, y1), (x1, y1)], fill="red", width=2)
        
        # Marcar distancia al siguiente si existe
        if i < len(lineas_original) - 1:
            bbox_siguiente = lineas_original[i + 1]
            y_base_siguiente = int(bbox_siguiente[3] * 2)  # Base de la siguiente línea
            # Línea de distancia (verde) - desde altura ascendente hasta base siguiente
            draw_original.line([(x0, y0), (x0, y_base_siguiente)], fill="green", width=3)
            # Texto con distancia
            distancia = interlineados_original[i]
            draw_original.text((x0 + 5, (y0 + y_base_siguiente) // 2), f"{distancia:.1f}pt", fill="green")
    
    # Generar imagen del maquetado
    pix_maquetado = page_maquetado.get_pixmap(matrix=mat)
    img_maquetado = Image.frombytes("RGB", [pix_maquetado.width, pix_maquetado.height], pix_maquetado.samples)
    draw_maquetado = ImageDraw.Draw(img_maquetado)
    
    # Dibujar líneas en maquetado
    for i, bbox in enumerate(lineas_maquetado[:10]):  # Solo primeras 10 líneas
        x0 = int(bbox[0] * 2)
        y0 = int(bbox[1] * 2)  # Altura ascendente
        x1 = int(bbox[2] * 2)
        y1 = int(bbox[3] * 2)  # Base
        
        # Línea superior (azul) - altura ascendente
        draw_maquetado.line([(x0, y0), (x1, y0)], fill="blue", width=2)
        # Línea inferior (roja) - base
        draw_maquetado.line([(x0, y1), (x1, y1)], fill="red", width=2)
        
        # Marcar distancia al siguiente si existe
        if i < len(lineas_maquetado) - 1:
            bbox_siguiente = lineas_maquetado[i + 1]
            y_base_siguiente = int(bbox_siguiente[3] * 2)  # Base de la siguiente línea
            # Línea de distancia (verde) - desde altura ascendente hasta base siguiente
            draw_maquetado.line([(x0, y0), (x0, y_base_siguiente)], fill="green", width=3)
            # Texto con distancia
            distancia = interlineados_maquetado[i]
            draw_maquetado.text((x0 + 5, (y0 + y_base_siguiente) // 2), f"{distancia:.1f}pt", fill="green")
    
    # Guardar imágenes
    img_original.save("interlineado_original_corregido.png")
    img_maquetado.save("interlineado_maquetado_corregido.png")
    
    print(f"IMÁGENES GUARDADAS:")
    print(f"  interlineado_original_corregido.png")
    print(f"  interlineado_maquetado_corregido.png")
    print(f"\nLEYENDA:")
    print(f"  Azul: Altura ascendente de cada línea de texto")
    print(f"  Rojo: Base de cada línea de texto")
    print(f"  Verde: Distancia desde altura ascendente hasta base siguiente")
    
    doc_original.close()
    doc_maquetado.close()
    
    return factor_interlineado if interlineados_original and interlineados_maquetado else None

if __name__ == "__main__":
    factor = medir_interlineado()
    if factor:
        print(f"\nRECOMENDACIÓN:")
        print(f"  Aplicar factor de escala al interlineado: {factor:.4f}")
        print(f"  Actualizar INTERLINEADO en scripts/maquetar_pdf.py")
