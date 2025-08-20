#!/usr/bin/env python3
"""
Script simplificado para visualizar las etapas del proceso de justificación
usando fuentes del sistema para evitar problemas de rutas.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import black, red, blue, green, orange

def dibujar_linea_con_espaciado_visualizado(c, texto, x, y, width, font_size, mostrar_espaciado=True):
    """
    Dibuja una línea de texto con visualización del espaciado entre palabras.
    """
    palabras = texto.split()
    
    if len(palabras) <= 1:
        # Solo una palabra, dibujar sin justificar
        c.setFont("Helvetica", font_size)
        c.drawString(x, y, texto)
        return
    
    # Calcular espaciado
    ancho_palabras = sum(pdfmetrics.stringWidth(p, "Helvetica", font_size) for p in palabras)
    espacio_disponible = width - ancho_palabras
    num_espacios = len(palabras) - 1
    
    if num_espacios > 0:
        espaciado = espacio_disponible / num_espacios
    else:
        espaciado = 0
    
    # Dibujar palabras con espaciado
    x_pos = x
    for i, palabra in enumerate(palabras):
        c.setFont("Helvetica", font_size)
        c.drawString(x_pos, y, palabra)
        
        # Dibujar línea de espaciado si no es la última palabra
        if i < len(palabras) - 1 and mostrar_espaciado:
            x_espacio = x_pos + pdfmetrics.stringWidth(palabra, "Helvetica", font_size)
            
            # Color según el espaciado
            espacio_ideal = pdfmetrics.stringWidth(' ', "Helvetica", font_size)
            multiplicador = espaciado / espacio_ideal if espacio_ideal > 0 else 0
            
            if multiplicador <= 1.5:
                color_espacio = green  # Verde: espaciado aceptable
            elif multiplicador <= 2.0:
                color_espacio = orange  # Naranja: espaciado moderado
            else:
                color_espacio = red  # Rojo: espaciado excesivo
            
            c.setStrokeColor(color_espacio)
            c.setLineWidth(2)
            
            # Línea vertical en el centro del espacio
            y_centro = y + font_size/2
            c.line(x_espacio + espaciado/2, y_centro - 10, x_espacio + espaciado/2, y_centro + 10)
            
            # Línea horizontal que marca el espacio
            c.line(x_espacio, y_centro, x_espacio + espaciado, y_centro)
            
            # Texto con el multiplicador
            c.setFont("Helvetica", 8)
            c.setFillColor(color_espacio)
            c.drawString(x_espacio + espaciado/2 - 10, y_centro + 15, f"{multiplicador:.1f}x")
            
            # Restaurar color negro
            c.setStrokeColor(black)
            c.setFillColor(black)
        
        x_pos += pdfmetrics.stringWidth(palabra, "Helvetica", font_size) + espaciado

def generar_capturas_etapas():
    """Genera capturas visuales de cada etapa del proceso"""
    
    # Configuración
    font_size = 12
    max_width = 458.30
    page_width, page_height = A4
    
    # Texto de ejemplo
    linea_original = "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische"
    linea_dividida = "Ich betone zwei Tatsachen nochmals: 1. Das koper-"
    
    # Crear PDF con las tres etapas
    c = canvas.Canvas("Salida/visualizacion_espaciado_etapas.pdf", pagesize=A4)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, page_height - 50, "VISUALIZACIÓN DE ESPACIADO - ETAPAS DEL PROCESO")
    
    # Etapa 1: Línea alineada a la izquierda
    y_etapa1 = page_height - 120
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_etapa1, "ETAPA 1: Línea alineada a la izquierda")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, y_etapa1 - 20, f"Texto: '{linea_original}'")
    
    # Dibujar línea alineada a la izquierda
    x_inicio = 50
    y_texto = y_etapa1 - 50
    c.setFont("Helvetica", font_size)
    c.drawString(x_inicio, y_texto, linea_original)
    
    # Línea de referencia para el ancho disponible
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_inicio, y_texto - 10, x_inicio + max_width, y_texto - 10)
    c.setStrokeColor(black)
    
    # Etapa 2: Línea justificada (sin división)
    y_etapa2 = y_etapa1 - 150
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_etapa2, "ETAPA 2: Línea justificada (espaciado excesivo)")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, y_etapa2 - 20, f"Ancho disponible: {max_width:.1f}pt")
    
    # Dibujar línea justificada con visualización de espaciado
    dibujar_linea_con_espaciado_visualizado(c, linea_original, x_inicio, y_etapa2 - 50, max_width, font_size)
    
    # Línea de referencia
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_inicio, y_etapa2 - 60, x_inicio + max_width, y_etapa2 - 60)
    c.setStrokeColor(black)
    
    # Etapa 3: Línea con división silábica
    y_etapa3 = y_etapa2 - 150
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_etapa3, "ETAPA 3: Línea con división silábica")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, y_etapa3 - 20, f"Texto dividido: '{linea_dividida}'")
    
    # Dibujar línea dividida con visualización de espaciado
    dibujar_linea_con_espaciado_visualizado(c, linea_dividida, x_inicio, y_etapa3 - 50, max_width, font_size)
    
    # Línea de referencia
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(x_inicio, y_etapa3 - 60, x_inicio + max_width, y_etapa3 - 60)
    c.setStrokeColor(black)
    
    # Leyenda
    y_leyenda = y_etapa3 - 120
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_leyenda, "LEYENDA:")
    
    c.setFont("Helvetica", 10)
    y_leyenda -= 20
    
    # Verde
    c.setFillColor(green)
    c.drawString(50, y_leyenda, "● Verde: Espaciado ≤ 1.5x (aceptable)")
    y_leyenda -= 15
    
    # Naranja
    c.setFillColor(orange)
    c.drawString(50, y_leyenda, "● Naranja: Espaciado 1.5x - 2.0x (moderado)")
    y_leyenda -= 15
    
    # Rojo
    c.setFillColor(red)
    c.drawString(50, y_leyenda, "● Rojo: Espaciado > 2.0x (excesivo)")
    y_leyenda -= 15
    
    # Azul
    c.setFillColor(blue)
    c.drawString(50, y_leyenda, "● Línea azul: Ancho disponible para la línea")
    
    # Restaurar color negro
    c.setFillColor(black)
    
    # Información adicional
    y_info = y_leyenda - 40
    c.setFont("Helvetica", 10)
    c.drawString(50, y_info, "INFORMACIÓN:")
    y_info -= 15
    c.drawString(50, y_info, f"• Espacio ideal (1x): {pdfmetrics.stringWidth(' ', 'Helvetica', font_size):.2f}pt")
    y_info -= 15
    c.drawString(50, y_info, f"• Límite máximo (1.5x): {pdfmetrics.stringWidth(' ', 'Helvetica', font_size) * 1.5:.2f}pt")
    y_info -= 15
    c.drawString(50, y_info, f"• Ancho total palabras original: {sum(pdfmetrics.stringWidth(p, 'Helvetica', font_size) for p in linea_original.split()):.2f}pt")
    y_info -= 15
    c.drawString(50, y_info, f"• Ancho total palabras divididas: {sum(pdfmetrics.stringWidth(p, 'Helvetica', font_size) for p in linea_dividida.split()):.2f}pt")
    
    c.save()
    print("✅ PDF generado: Salida/visualizacion_espaciado_etapas.pdf")

def generar_captura_detallada_espaciado():
    """Genera una captura más detallada mostrando el espaciado palabra por palabra"""
    
    # Configuración
    font_size = 12
    max_width = 458.30
    page_width, page_height = A4
    
    # Texto
    linea = "Ich betone zwei Tatsachen nochmals: 1. Das kopernikanische"
    palabras = linea.split()
    
    # Crear PDF detallado
    c = canvas.Canvas("Salida/visualizacion_espaciado_detallado.pdf", pagesize=A4)
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, page_height - 50, "ANÁLISIS DETALLADO DE ESPACIADO PALABRA POR PALABRA")
    
    # Calcular espaciado
    ancho_palabras = sum(pdfmetrics.stringWidth(p, "Helvetica", font_size) for p in palabras)
    espacio_disponible = max_width - ancho_palabras
    num_espacios = len(palabras) - 1
    espaciado = espacio_disponible / num_espacios if num_espacios > 0 else 0
    espacio_ideal = pdfmetrics.stringWidth(' ', "Helvetica", font_size)
    multiplicador = espaciado / espacio_ideal if espacio_ideal > 0 else 0
    
    # Información general
    y_info = page_height - 100
    c.setFont("Helvetica", 12)
    c.drawString(50, y_info, f"Línea: '{linea}'")
    y_info -= 20
    c.drawString(50, y_info, f"Ancho disponible: {max_width:.1f}pt")
    y_info -= 20
    c.drawString(50, y_info, f"Ancho palabras: {ancho_palabras:.1f}pt")
    y_info -= 20
    c.drawString(50, y_info, f"Espacio disponible: {espacio_disponible:.1f}pt")
    y_info -= 20
    c.drawString(50, y_info, f"Número de espacios: {num_espacios}")
    y_info -= 20
    c.drawString(50, y_info, f"Espaciado por espacio: {espaciado:.1f}pt")
    y_info -= 20
    c.drawString(50, y_info, f"Espacio ideal (1x): {espacio_ideal:.1f}pt")
    y_info -= 20
    c.drawString(50, y_info, f"Multiplicador: {multiplicador:.1f}x")
    
    # Dibujar línea con análisis detallado
    y_linea = y_info - 50
    x_pos = 50
    
    for i, palabra in enumerate(palabras):
        # Dibujar palabra
        c.setFont("Helvetica", font_size)
        c.drawString(x_pos, y_linea, palabra)
        
        # Marcar el ancho de la palabra
        ancho_palabra = pdfmetrics.stringWidth(palabra, "Helvetica", font_size)
        c.setStrokeColor(blue)
        c.setLineWidth(1)
        c.line(x_pos, y_linea - 5, x_pos + ancho_palabra, y_linea - 5)
        
        # Texto con el ancho de la palabra
        c.setFont("Helvetica", 8)
        c.setFillColor(blue)
        c.drawString(x_pos, y_linea - 15, f"{ancho_palabra:.1f}pt")
        
        # Si no es la última palabra, mostrar el espacio
        if i < len(palabras) - 1:
            x_espacio = x_pos + ancho_palabra
            
            # Color del espacio según el multiplicador
            if multiplicador <= 1.5:
                color_espacio = green
            elif multiplicador <= 2.0:
                color_espacio = orange
            else:
                color_espacio = red
            
            # Línea del espacio
            c.setStrokeColor(color_espacio)
            c.setLineWidth(3)
            c.line(x_espacio, y_linea + font_size/2, x_espacio + espaciado, y_linea + font_size/2)
            
            # Texto del multiplicador
            c.setFont("Helvetica", 10)
            c.setFillColor(color_espacio)
            c.drawString(x_espacio + espaciado/2 - 15, y_linea + font_size + 10, f"{multiplicador:.1f}x")
            
            # Restaurar colores
            c.setStrokeColor(black)
            c.setFillColor(black)
        
        x_pos += ancho_palabra + espaciado
    
    # Línea de referencia del ancho total
    c.setStrokeColor(red)
    c.setLineWidth(2)
    c.line(50, y_linea - 25, 50 + max_width, y_linea - 25)
    c.setStrokeColor(black)
    
    # Leyenda
    y_leyenda = y_linea - 80
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_leyenda, "LEYENDA:")
    
    c.setFont("Helvetica", 10)
    y_leyenda -= 20
    
    c.setFillColor(blue)
    c.drawString(50, y_leyenda, "● Línea azul: Ancho de cada palabra")
    y_leyenda -= 15
    
    c.setFillColor(green)
    c.drawString(50, y_leyenda, "● Línea verde: Espaciado ≤ 1.5x (aceptable)")
    y_leyenda -= 15
    
    c.setFillColor(orange)
    c.drawString(50, y_leyenda, "● Línea naranja: Espaciado 1.5x - 2.0x (moderado)")
    y_leyenda -= 15
    
    c.setFillColor(red)
    c.drawString(50, y_leyenda, "● Línea roja: Espaciado > 2.0x (excesivo)")
    y_leyenda -= 15
    
    c.setFillColor(red)
    c.drawString(50, y_leyenda, "● Línea roja gruesa: Ancho total disponible")
    
    c.setFillColor(black)
    
    c.save()
    print("✅ PDF generado: Salida/visualizacion_espaciado_detallado.pdf")

def main():
    """Función principal"""
    print("🔍 Generando visualizaciones de espaciado...")
    
    # Generar capturas
    generar_capturas_etapas()
    generar_captura_detallada_espaciado()
    
    print("✅ Visualizaciones completadas")

if __name__ == "__main__":
    main()
