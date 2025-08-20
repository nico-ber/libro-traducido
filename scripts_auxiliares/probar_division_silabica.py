#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la división silábica alemana.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.maquetar_pdf import dividir_silabas_aleman, calcular_espaciado_optimo

def probar_division_silabica():
    """Prueba la división silábica con palabras alemanas comunes."""
    
    # Palabras alemanas para probar
    palabras_prueba = [
        "Wissenschaft",      # ciencia
        "Geschichte",        # historia
        "Entwicklung",       # desarrollo
        "Verständnis",       # comprensión
        "Zusammenhang",      # conexión
        "Beispiel",          # ejemplo
        "Möglichkeit",       # posibilidad
        "Untersuchung",      # investigación
        "Bedeutung",         # significado
        "Verhältnis",        # relación
        "Arbeit",            # trabajo
        "Zeit",              # tiempo
        "Mensch",            # persona
        "Welt",              # mundo
        "Leben",             # vida
        "Problem",           # problema
        "Frage",             # pregunta
        "Antwort",           # respuesta
        "Theorie",           # teoría
        "Praxis",            # práctica
    ]
    
    print("=== PRUEBA DE DIVISIÓN SILÁBICA ALEMANA ===\n")
    
    for palabra in palabras_prueba:
        partes = dividir_silabas_aleman(palabra)
        if len(partes) > 1:
            print(f"✅ '{palabra}' → '{'-'.join(partes)}'")
        else:
            print(f"❌ '{palabra}' → No se pudo dividir")
    
    print("\n=== RESUMEN DE DIVISIÓN SILÁBICA ===\n")
    
    palabras_divididas = 0
    palabras_no_divididas = 0
    
    for palabra in palabras_prueba:
        partes = dividir_silabas_aleman(palabra)
        if len(partes) > 1:
            palabras_divididas += 1
        else:
            palabras_no_divididas += 1
    
    print(f"Palabras divididas exitosamente: {palabras_divididas}")
    print(f"Palabras no divididas: {palabras_no_divididas}")
    print(f"Tasa de éxito: {palabras_divididas / len(palabras_prueba) * 100:.1f}%")
    
    print("\n=== REGLAS DE DIVISIÓN IMPLEMENTADAS ===")
    print("✅ Vocal + Consonante + Vocal → divide antes de la consonante")
    print("✅ Vocal + Consonante + Consonante + Vocal → divide entre consonantes")
    print("✅ Longitud mínima de palabra: 5 caracteres")
    print("✅ Longitud mínima de cada parte: 3 caracteres")
    print("✅ Espaciado máximo: 1.8x el espacio normal")

if __name__ == "__main__":
    probar_division_silabica()
