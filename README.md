# 📘 libro-traducido

Proyecto para automatizar el proceso de extracción, traducción y maquetado de libros escaneados o digitalizados en PDF. Permite:

- Rehacer el OCR del PDF original para mejorar la calidad del texto.
- Extraer los bloques visuales del contenido (párrafos, imágenes, notas).
- Preparar el contenido para traducción y maquetado posterior.

## 🔧 Requisitos

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) instalado y accesible en el sistema.
- Modelo OCR de idioma **`deu-frak.traineddata`** descargado y ubicado correctamente en la carpeta `tessdata`.

### Instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate        # En Windows
source venv/bin/activate    # En Linux/macOS

pip install -r requirements.txt


🧠 Uso
Rehacer OCR (Genera un archivo salida_ocr.json en la raíz del proyecto.)
python scripts/extraer_ocr.py datos/original.pdf

Extraer bloques visuales (texto, imágenes)
python scripts/extraer_bloques.py datos/original.pdf -o datos/salida.json