#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ejecutar_ocr_completo.py — Script que ejecuta automáticamente el flujo completo de OCR:
1. Normalización de fuentes (normalizar_fuentes.py)
2. Extracción OCR (extraer_ocr.py)

Este script automatiza el proceso completo para que no tengas que ejecutar
los dos scripts por separado.
"""

import subprocess
import sys
from pathlib import Path

def ejecutar_comando(comando, descripcion):
    """Ejecuta un comando y muestra el resultado."""
    print(f"\n🔄 {descripcion}")
    print(f"📝 Comando: {' '.join(comando)}")
    print("-" * 60)
    
    try:
        resultado = subprocess.run(comando, check=True, capture_output=True, text=True)
        print("✅ Comando ejecutado exitosamente")
        if resultado.stdout:
            print("📤 Salida:")
            print(resultado.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando comando: {e}")
        if e.stdout:
            print("📤 Salida estándar:")
            print(e.stdout)
        if e.stderr:
            print("📤 Error estándar:")
            print(e.stderr)
        return False

def main():
    # Configuración por defecto
    pdf_path = "./datos/extracto.pdf"
    clusters_path = "./datos/clusters.json"
    output_path = "./datos/ocr_lineas.json"
    
    # Verificar que el PDF existe
    if not Path(pdf_path).exists():
        print(f"❌ Error: No se encuentra el archivo PDF en {pdf_path}")
        print("💡 Asegúrate de que el archivo existe o modifica la variable pdf_path")
        sys.exit(1)
    
    print("🚀 Iniciando proceso completo de OCR")
    print(f"📄 PDF: {pdf_path}")
    print(f"📊 Clusters: {clusters_path}")
    print(f"📝 Salida: {output_path}")
    
    # Paso 1: Normalización de fuentes
    comando_normalizacion = [
        sys.executable, "scripts/normalizar_fuentes.py",
        "--pdf", pdf_path,
        "--out", clusters_path,
        "--debug"
    ]
    
    if not ejecutar_comando(comando_normalizacion, "Paso 1: Normalizando tamaños de fuente"):
        print("❌ Falló la normalización. Abortando.")
        sys.exit(1)
    
    # Paso 2: Extracción OCR
    comando_ocr = [
        sys.executable, "scripts/extraer_ocr.py",
        "--pdf", pdf_path,
        "--out", output_path,
        "--clusters", clusters_path,
        "--debug"
    ]
    
    if not ejecutar_comando(comando_ocr, "Paso 2: Extrayendo OCR con normalización"):
        print("❌ Falló la extracción OCR. Abortando.")
        sys.exit(1)
    
    print("\n🎉 ¡Proceso completado exitosamente!")
    print(f"📊 Clusters guardados en: {clusters_path}")
    print(f"📝 OCR guardado en: {output_path}")
    
    # Verificar archivos generados
    if Path(clusters_path).exists():
        print(f"✅ Archivo de clusters verificado: {clusters_path}")
    
    if Path(output_path).exists():
        print(f"✅ Archivo de OCR verificado: {output_path}")

if __name__ == "__main__":
    main()
