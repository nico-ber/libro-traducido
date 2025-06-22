# Flujo recomendado para la traducción y maquetado

1. **OCR de líneas**  
   `extraer_ocr.py` → `ocr_lineas.json`
   *300 dpi+, preprocesado, idioma `deu-frak+deu`*

2. **Agrupado en párrafos**  
   `extraer_bloques.py --merge-cross-page` → `bloques.json`  
   *Funde líneas, detecta títulos, sangría FLI, alinea y cose párrafos que cruzan de página.*

3. **Control de calidad (opcional)**  
   `verificar_ocr.py` → `ocr_check.csv`  
   *Lista de líneas con baja confianza o caracteres dudosos para revisión manual.*

4. **Traducción**  
   `traducir_json.py --engine argos|deepl|openai` → `bloques_trad.json`  
   *Traduce cada **párrafo completo** conservando `pagina(s)` y metadatos.*

5. **Maquetado del libro traducido**  
   - **EPUB/HTML (fluido):** convertir `bloques_trad.json` a capítulos y hojas de estilo.
   - **PDF nuevo:** usar ReportLab o LaTeX; colocar imágenes extraídas del PDF original, aplicar estilos (tamaños, alineación) basados en los metadatos.

6. **Revisión final**  
   - Correcciones de estilo y ortografía en el EPUB/PDF.  
   - Generación de índice y front‑matter si procede.

---

> **Tip:** mantiene en cada bloque `"paginas": [7,8]` cuando cruza páginas para referencia a la fuente original (útil en citas o notas).

