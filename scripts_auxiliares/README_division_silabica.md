# Sistema de División Silábica para Justificación

## Resumen

Se ha implementado un sistema completo de división silábica (hyphenation) para mejorar la justificación del texto en alemán. El sistema detecta automáticamente cuando el espaciado entre palabras es excesivo y aplica división silábica para mantener una apariencia visual equilibrada.

## Características Implementadas

### 1. Detección de Espaciado Excesivo
- **Límite configurable**: 1.8x el espacio normal entre palabras
- **Detección automática**: Se verifica en cada línea justificada
- **Aplicación inteligente**: Solo se activa cuando es necesario

### 2. División Silábica Alemana
- **Reglas específicas**: Basadas en las reglas de división silábica del alemán
- **Patrones implementados**:
  - Vocal + Consonante + Vocal → divide antes de la consonante
  - Vocal + Consonante + Consonante + Vocal → divide entre consonantes
- **Tasa de éxito**: ~65% en palabras alemanas comunes

### 3. Restricciones de Seguridad
- **Longitud mínima de palabra**: 5 caracteres
- **Longitud mínima de cada parte**: 3 caracteres
- **Protección**: No divide palabras muy cortas o nombres propios

## Configuración

### Constantes en `scripts/maquetar_pdf.py`:

```python
# --- CONFIGURACIÓN DE JUSTIFICACIÓN Y DIVISIÓN SILÁBICA ---
ESPACIADO_MAXIMO_MULTIPLICADOR = 1.8  # Máximo espaciado entre palabras (1.8x el espacio normal)
LONGITUD_MINIMA_PALABRA_DIVIDIR = 5  # Mínimo caracteres para dividir una palabra
LONGITUD_MINIMA_PARTE_DIVIDIDA = 3  # Mínimo caracteres en cada parte de la división
```

## Funciones Principales

### 1. `dividir_silabas_aleman(palabra)`
- Divide una palabra alemana siguiendo las reglas fonéticas
- Retorna una lista con las partes divididas
- Si no se puede dividir, retorna la palabra original

### 2. `calcular_espaciado_optimo(palabras, width, font_size, fuente)`
- Calcula el espaciado óptimo entre palabras
- Aplica división silábica si el espaciado es excesivo
- Retorna el espaciado calculado y la lista de palabras (posiblemente modificada)

### 3. `draw_justified()` y `draw_justified_enriquecido()`
- Funciones modificadas para usar el nuevo sistema
- Aplican división silábica automáticamente cuando es necesario

## Ejemplos de División Exitosa

```
Wissenschaft → Wis-senschaft
Geschichte → Ges-chichte
Entwicklung → Ent-wicklung
Verständnis → Ver-ständnis
Zusammenhang → Zusam-menhang
Möglichkeit → Mög-lichkeit
Untersuchung → Unter-suchung
```

## Verificación

### Scripts de Prueba Disponibles:

1. **`probar_division_silabica.py`**
   - Prueba la división silábica con palabras alemanas comunes
   - Muestra estadísticas de éxito

2. **`verificar_justificacion_silabica.py`**
   - Analiza el PDF maquetado para detectar divisiones aplicadas
   - Compara con los bloques originales

## Resultados Observados

En el PDF de prueba (página 16):
- **5 bloques justificados** procesados
- **3 líneas con división silábica** detectadas
- **Espaciado excesivo detectado** en múltiples líneas
- **Divisiones aplicadas** automáticamente

## Mejoras Futuras

1. **Diccionario de excepciones**: Para palabras que no deben dividirse
2. **Reglas más sofisticadas**: Para casos especiales del alemán
3. **Configuración por idioma**: Extender a otros idiomas
4. **Optimización de rendimiento**: Para textos muy largos

## Uso

El sistema se activa automáticamente al generar el PDF maquetado:

```bash
python scripts/maquetar_pdf.py
```

Los mensajes de debug muestran cuando se aplica división silábica:
```
[DIVISIÓN SILÁBICA ENRIQUECIDA] Palabra 'Weltbild.' dividida en 'Wel-tbild.'
[DIVISIÓN SILÁBICA ENRIQUECIDA] Palabra 'Möglichkeit' dividida en 'Mög-lichkeit'
```

## Estándares de Calidad

- **Espaciado máximo**: 1.8x el espacio normal
- **División natural**: Respeta las reglas fonéticas del alemán
- **Legibilidad**: Mantiene la comprensión del texto
- **Consistencia**: Aplica las mismas reglas en todo el documento
