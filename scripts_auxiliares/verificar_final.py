#!/usr/bin/env python3
import fitz
from PIL import Image, ImageDraw
import numpy as np

def verificar_final():
    """Verifica la medición final con el factor 1.58 para obtener factor real = 1.0."""
    
    print("=== VERIFICACIÓN FINAL CON FACTOR 1.58 ===")
    
    # 1. PDF Original
    doc_original = fitz.open("Estatico/original.pdf")
    page_original = doc_original[15]  # Página 16
    
    # 2. PDF Maquetado final
    doc_maquetado = fitz.open("Salida/maquetado.pdf")
    page_maquetado = doc_maquetado[0]  # Primera página
    
    # Obtener datos de ambos
    raw_original = page_original.get_text("rawdict")
    raw_maquetado = page_maquetado.get_text("rawdict")
    
    # Buscar el primer carácter 'd' en ambos
    char_original = None
    char_maquetado = None
    
    for block in raw_original.get('blocks', []):
        if block.get('type') == 0:
            lines = block.get('lines', [])
            if lines:
                spans = lines[0].get('spans', [])
                if spans:
                    chars = spans[0].get('chars', [])
                    for char in chars:
                        if char.get('c') == 'd':
                            char_original = char
                            break
                    if char_original:
                        break
            if char_original:
                break
    
    for block in raw_maquetado.get('blocks', []):
        if block.get('type') == 0:
            lines = block.get('lines', [])
            if lines:
                spans = lines[0].get('spans', [])
                if spans:
                    chars = spans[0].get('chars', [])
                    for char in chars:
                        if char.get('c') == 'd':
                            char_maquetado = char
                            break
                    if char_maquetado:
                        break
            if char_maquetado:
                break
    
    if char_original and char_maquetado:
        bbox_original = char_original.get('bbox')
        bbox_maquetado = char_maquetado.get('bbox')
        
        print(f"CARÁCTER 'd' ENCONTRADO:")
        print(f"  ORIGINAL: Bbox {bbox_original}")
        print(f"  MAQUETADO FINAL: Bbox {bbox_maquetado}")
        
        # Generar imágenes de alta resolución
        mat = fitz.Matrix(6, 6)  # Zoom 6x para mejor precisión
        
        # 1. Original
        pix_original = page_original.get_pixmap(matrix=mat)
        img_original = Image.frombytes("RGB", [pix_original.width, pix_original.height], pix_original.samples)
        
        # Convertir coordenadas al zoom
        x0_orig = int(bbox_original[0] * 6)
        y0_orig = int(bbox_original[1] * 6)
        x1_orig = int(bbox_original[2] * 6)
        y1_orig = int(bbox_original[3] * 6)
        
        # Recortar solo el carácter
        crop_original = img_original.crop((x0_orig, y0_orig, x1_orig, y1_orig))
        
        # 2. Maquetado final
        pix_maquetado = page_maquetado.get_pixmap(matrix=mat)
        img_maquetado = Image.frombytes("RGB", [pix_maquetado.width, pix_maquetado.height], pix_maquetado.samples)
        
        # Convertir coordenadas al zoom
        x0_maq = int(bbox_maquetado[0] * 6)
        y0_maq = int(bbox_maquetado[1] * 6)
        x1_maq = int(bbox_maquetado[2] * 6)
        y1_maq = int(bbox_maquetado[3] * 6)
        
        # Recortar solo el carácter
        crop_maquetado = img_maquetado.crop((x0_maq, y0_maq, x1_maq, y1_maq))
        
        # Convertir a escala de grises para análisis
        gray_original = crop_original.convert('L')
        gray_maquetado = crop_maquetado.convert('L')
        
        # Convertir a arrays numpy
        arr_original = np.array(gray_original)
        arr_maquetado = np.array(gray_maquetado)
        
        # Encontrar límites de tinta (píxeles oscuros)
        threshold = 128  # Umbral para considerar píxel como "tinta"
        
        # Original
        rows_with_ink_orig = np.any(arr_original < threshold, axis=1)
        if np.any(rows_with_ink_orig):
            first_ink_row_orig = np.where(rows_with_ink_orig)[0][0]
            last_ink_row_orig = np.where(rows_with_ink_orig)[0][-1]
            altura_tinta_orig = last_ink_row_orig - first_ink_row_orig + 1
        else:
            altura_tinta_orig = 0
        
        # Maquetado final
        rows_with_ink_maq = np.any(arr_maquetado < threshold, axis=1)
        if np.any(rows_with_ink_maq):
            first_ink_row_maq = np.where(rows_with_ink_maq)[0][0]
            last_ink_row_maq = np.where(rows_with_ink_maq)[0][-1]
            altura_tinta_maq = last_ink_row_maq - first_ink_row_maq + 1
        else:
            altura_tinta_maq = 0
        
        # Dibujar límites en original
        draw_original = ImageDraw.Draw(crop_original)
        # Línea superior de tinta (roja)
        draw_original.line([(0, first_ink_row_orig), (crop_original.width, first_ink_row_orig)], fill="red", width=2)
        # Línea inferior de tinta (roja)
        draw_original.line([(0, last_ink_row_orig), (crop_original.width, last_ink_row_orig)], fill="red", width=2)
        
        # Dibujar límites en maquetado final
        draw_maquetado = ImageDraw.Draw(crop_maquetado)
        # Línea superior de tinta (roja)
        draw_maquetado.line([(0, first_ink_row_maq), (crop_maquetado.width, first_ink_row_maq)], fill="red", width=2)
        # Línea inferior de tinta (roja)
        draw_maquetado.line([(0, last_ink_row_maq), (crop_maquetado.width, last_ink_row_maq)], fill="red", width=2)
        
        # Convertir a puntos (dividir por zoom)
        altura_tinta_orig_pts = altura_tinta_orig / 6
        altura_tinta_maq_pts = altura_tinta_maq / 6
        
        print(f"\nVERIFICACIÓN FINAL:")
        print(f"  ORIGINAL:")
        print(f"    Altura tinta (píxeles): {altura_tinta_orig}")
        print(f"    Altura tinta (puntos): {altura_tinta_orig_pts:.2f}")
        print(f"    Primera fila con tinta: {first_ink_row_orig}")
        print(f"    Última fila con tinta: {last_ink_row_orig}")
        
        print(f"  MAQUETADO FINAL:")
        print(f"    Altura tinta (píxeles): {altura_tinta_maq}")
        print(f"    Altura tinta (puntos): {altura_tinta_maq_pts:.2f}")
        print(f"    Primera fila con tinta: {first_ink_row_maq}")
        print(f"    Última fila con tinta: {last_ink_row_maq}")
        
        # Calcular factor
        if altura_tinta_maq_pts > 0:
            factor_real = altura_tinta_orig_pts / altura_tinta_maq_pts
            print(f"\nFACTOR REAL:")
            print(f"  Factor basado en tinta real: {factor_real:.4f}")
            print(f"  Factor aplicado en código: 1.58")
            print(f"  Diferencia: {abs(factor_real - 1.0):.4f}")
            
            if abs(factor_real - 1.0) < 0.1:
                print(f"  ✅ FACTOR CORRECTO - Las alturas de tinta coinciden")
            else:
                print(f"  ⚠️  FACTOR INCORRECTO - Las alturas de tinta no coinciden")
        else:
            print(f"\nERROR: No se detectó tinta en el maquetado")
        
        # Guardar imágenes con límites dibujados
        crop_original.save("verificacion_original.png")
        crop_maquetado.save("verificacion_maquetado.png")
        print(f"\nIMÁGENES GUARDADAS:")
        print(f"  verificacion_original.png")
        print(f"  verificacion_maquetado.png")
        
    else:
        print("No se encontró el carácter 'd' en uno o ambos PDFs")
    
    doc_original.close()
    doc_maquetado.close()

if __name__ == "__main__":
    verificar_final()
