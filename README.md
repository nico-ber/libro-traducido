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
venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt


## 🧠 Uso

### Rehacer OCR

Genera un archivo `ocr_lineas.json` con el texto línea por línea.

```powershell
python scripts/extraer_ocr.py datos/original.pdf `
  --o datos/ocr_lineas.json `
  --lang deu-frak+deu `
  --debug

  python scripts/extraer_ocr.py datos/original.pdf `
  --out datos/ocr_lineas.json `
  --dpi 350 `
  --lang deu-frak+deu `
  --psm 4 `
  --pages 9 10 11 12 `
  --debug




### Extraer bloques visuales (texto, imágenes)

Genera salida.json con la información estructurada de los bloques detectados (párrafos, notas, imágenes, etc.).

python scripts/extraer_bloques.py datos/ocr_lineas.json `
    --debug


### Para extraer ciertas páginas de un PDF

python extract_pages.py original.pdf salida.pdf 4-11