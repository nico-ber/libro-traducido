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

### Flujo de trabajo recomendado

El proceso de OCR se ha dividido en dos pasos para mayor eficiencia:

#### Opción 1: Proceso completo automatizado
```powershell
python scripts/ejecutar_ocr_completo.py
```

#### Opción 2: Proceso paso a paso

**Paso 1: Normalizar tamaños de fuente**
```powershell
python scripts/normalizar_fuentes.py --pdf datos/extracto.pdf --debug
```

**Paso 2: Extraer OCR con normalización**
```powershell
python scripts/extraer_ocr.py --pdf datos/extracto.pdf --debug
```

### Uso directo (sin normalización)
Si prefieres usar el script original sin normalización:

```powershell
python scripts/extraer_ocr.py --no-images --pages 6-8 --visual-style --debug


### Extraer bloques visuales (texto, imágenes)
Genera salida.json con la información estructurada de los bloques detectados (párrafos, notas, imágenes, etc.).

python scripts/extraer_bloques.py datos/ocr_lineas.json `
    --debug


### Para extraer ciertas páginas de un PDF
python extract_pages.py original.pdf salida.pdf 4-11