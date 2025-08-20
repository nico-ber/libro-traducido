#!/usr/bin/env python3
import fitz
import json
from PIL import Image, ImageDraw, ImageFont
import os

def generar_captura_con_lineas(pdf_path, output_path, bloques_pagina, titulo, page_index=0, usar_coordenadas_reales=False):
    """Genera una captura del PDF con líneas que delimitan las distancias entre bloques."""
    
    doc = fitz.open(pdf_path)
    
    # Verificar que la página existe
    if page_index >= len(doc):
        print(f"Error: La página {page_index} no existe en {pdf_path}. Total de páginas: {len(doc)}")
        doc.close()
        return
    
    page = doc[page_index]
    
    # Renderizar la página como imagen
    mat = fitz.Matrix(2, 2)  # Zoom 2x para mejor calidad
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    
    # Crear imagen PIL
    img = Image.open(io.BytesIO(img_data))
    draw = ImageDraw.Draw(img)
    
    # Configurar fuente para texto
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Agregar título
    draw.text((10, 10), titulo, fill=(255, 0, 0), font=font)
    
    if usar_coordenadas_reales:
        # Extraer coordenadas reales del PDF maquetado
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]  # Solo bloques de texto
        
        # Agrupar líneas por bloques basándose en la proximidad vertical
        # Un bloque se define como líneas que están muy cerca verticalmente
        bloques_agrupados = []
        bloque_actual = []
        
        for i, block in enumerate(text_blocks):
            if not bloque_actual:
                bloque_actual.append(block)
            else:
                # Calcular distancia vertical con la última línea del bloque actual
                ultima_linea = bloque_actual[-1]
                distancia = block["bbox"][1] - ultima_linea["bbox"][3]  # y0 actual - y1 anterior
                
                # Si la distancia es pequeña (< 15 puntos), es parte del mismo bloque
                # Reducido de 20 a 15 para ser más preciso
                if distancia < 15:
                    bloque_actual.append(block)
                else:
                    # Es un nuevo bloque
                    bloques_agrupados.append(bloque_actual)
                    bloque_actual = [block]
        
        # Agregar el último bloque
        if bloque_actual:
            bloques_agrupados.append(bloque_actual)
        
        # Debug: mostrar información de los bloques agrupados
        print(f"Bloques agrupados encontrados: {len(bloques_agrupados)}")
        for i, bloque in enumerate(bloques_agrupados):
            primera_linea = bloque[0]["bbox"]
            ultima_linea = bloque[-1]["bbox"]
            print(f"  Bloque {i+1}: {len(bloque)} líneas, Y: {primera_linea[1]:.1f} - {ultima_linea[3]:.1f}")
        
        # Dibujar líneas solo entre bloques diferentes
        for i in range(len(bloques_agrupados) - 1):
            bloque_actual = bloques_agrupados[i]
            bloque_siguiente = bloques_agrupados[i + 1]
            
            # Obtener coordenadas del final del bloque actual y inicio del siguiente
            y_bottom_actual = bloque_actual[-1]["bbox"][3]  # y1 (bottom) de la última línea del bloque
            y_top_siguiente = bloque_siguiente[0]["bbox"][1]  # y0 (top) de la primera línea del siguiente bloque
            
            # Convertir coordenadas del PDF a coordenadas de la imagen (zoom 2x)
            y1_img = y_bottom_actual * 2
            y2_img = y_top_siguiente * 2
            
            # Dibujar línea horizontal que conecta los bloques
            draw.line([(50, y1_img), (img.width - 50, y1_img)], fill=(255, 0, 0), width=2)
            draw.line([(50, y2_img), (img.width - 50, y2_img)], fill=(255, 0, 0), width=2)
            
            # Dibujar línea vertical que mide la distancia
            x_medida = img.width - 100
            draw.line([(x_medida, y1_img), (x_medida, y2_img)], fill=(0, 255, 0), width=3)
            
            # Calcular distancia
            distancia = y_top_siguiente - y_bottom_actual
            
            # Agregar etiqueta con la distancia
            texto = f"Distancia: {distancia:.1f}pt"
            draw.text((x_medida + 10, (y1_img + y2_img) / 2), texto, fill=(0, 0, 255), font=font)
            
            # Agregar flechas en los extremos
            arrow_size = 5
            # Flecha superior
            draw.polygon([(x_medida - arrow_size, y1_img), (x_medida + arrow_size, y1_img), (x_medida, y1_img - arrow_size)], fill=(0, 255, 0))
            # Flecha inferior
            draw.polygon([(x_medida - arrow_size, y2_img), (x_medida + arrow_size, y2_img), (x_medida, y2_img + arrow_size)], fill=(0, 255, 0))
    else:
        # Usar coordenadas del JSON (para PDF original)
        # Ordenar bloques por posición vertical
        bloques_ordenados = sorted(bloques_pagina, key=lambda b: b.get('y_top', 0))
        
        # Dibujar líneas y etiquetas para cada distancia
        for i in range(len(bloques_ordenados) - 1):
            bloque_actual = bloques_ordenados[i]
            bloque_siguiente = bloques_ordenados[i + 1]
            
            # Obtener coordenadas
            y_bottom_actual = bloque_actual.get('y_bottom', 0)
            y_top_siguiente = bloque_siguiente.get('y_top', 0)
            
            # Convertir coordenadas del PDF a coordenadas de la imagen (zoom 2x)
            y1_img = y_bottom_actual * 2
            y2_img = y_top_siguiente * 2
            
            # Dibujar línea horizontal que conecta los bloques
            draw.line([(50, y1_img), (img.width - 50, y1_img)], fill=(255, 0, 0), width=2)
            draw.line([(50, y2_img), (img.width - 50, y2_img)], fill=(255, 0, 0), width=2)
            
            # Dibujar línea vertical que mide la distancia
            x_medida = img.width - 100
            draw.line([(x_medida, y1_img), (x_medida, y2_img)], fill=(0, 255, 0), width=3)
            
            # Calcular distancia
            distancia = y_top_siguiente - y_bottom_actual
            espacio_despues = bloque_actual.get('espacio_despues', 0)
            
            # Agregar etiqueta con la distancia
            texto = f"Distancia: {distancia:.1f}pt (espacio_despues: {espacio_despues})"
            draw.text((x_medida + 10, (y1_img + y2_img) / 2), texto, fill=(0, 0, 255), font=font)
            
            # Agregar flechas en los extremos
            arrow_size = 5
            # Flecha superior
            draw.polygon([(x_medida - arrow_size, y1_img), (x_medida + arrow_size, y1_img), (x_medida, y1_img - arrow_size)], fill=(0, 255, 0))
            # Flecha inferior
            draw.polygon([(x_medida - arrow_size, y2_img), (x_medida + arrow_size, y2_img), (x_medida, y2_img + arrow_size)], fill=(0, 255, 0))
    
    # Guardar imagen
    img.save(output_path)
    doc.close()
    print(f"Captura guardada: {output_path}")

def verificar_distancias_visual():
    """Verifica las distancias comparando visualmente ambos PDFs."""
    
    print("=== VERIFICACIÓN VISUAL DE DISTANCIAS ===")
    
    # Cargar bloques
    with open("Salida/bloques.json", "r", encoding="utf-8") as f:
        bloques = json.load(f)
    
    # Filtrar bloques de la página 16
    bloques_pagina_16 = [b for b in bloques if b.get('pagina') == 16]
    
    print(f"Generando capturas visuales para comparar distancias...")
    
    # Verificar número de páginas en cada PDF
    doc_original = fitz.open("Estatico/original.pdf")
    doc_maquetado = fitz.open("Salida/maquetado.pdf")
    
    print(f"PDF Original: {len(doc_original)} páginas")
    print(f"PDF Maquetado: {len(doc_maquetado)} páginas")
    
    doc_original.close()
    doc_maquetado.close()
    
    # Generar captura del PDF original (página 16 = índice 15)
    generar_captura_con_lineas(
        "Estatico/original.pdf",
        "Salida/captura_original_con_lineas.png",
        bloques_pagina_16,
        "PDF ORIGINAL - Página 16",
        page_index=15,  # Página 16 (índice 15)
        usar_coordenadas_reales=False  # Usar coordenadas del JSON
    )
    
    # Generar captura del PDF maquetado (página 0)
    generar_captura_con_lineas(
        "Salida/maquetado.pdf",
        "Salida/captura_maquetado_con_lineas.png",
        bloques_pagina_16,
        "PDF MAQUETADO - Página 16",
        page_index=0,  # Primera página del maquetado
        usar_coordenadas_reales=True  # Extraer coordenadas reales del PDF
    )
    
    print(f"\nCapturas generadas:")
    print(f"  Original: Salida/captura_original_con_lineas.png")
    print(f"  Maquetado: Salida/captura_maquetado_con_lineas.png")
    print(f"\nCompara las imágenes para verificar que las distancias coincidan.")
    print(f"Las líneas verdes miden las distancias entre bloques.")
    print(f"Los números azules muestran la distancia calculada.")

if __name__ == "__main__":
    import io
    verificar_distancias_visual()
