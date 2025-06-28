import fitz  # PyMuPDF
import os
from pathlib import Path
from PIL import Image
import torch
import torchvision.transforms as T
from torchvision import models
import json
import numpy as np

# --- CONFIG ---
PDF_PATH = "datos/original.pdf"
OUT_DIR = Path("datos/imagenes_tipografia")
OUT_DIR.mkdir(parents=True, exist_ok=True)
MAX_IMAGES = 1000
FONT_EMB_PATH = "datos/tipografias_vectores.json"
KNOWN_FONTS_DIR = Path("datos/fuentes_referencia")  # Debe contener subcarpetas por fuente con imágenes
SIMILARITY_OUT = "datos/tipografias_similitud.json"

# --- CARGAR MODELO BASE ---
print("Cargando modelo ResNet18 base para extracción de embeddings...")
model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
model.fc = torch.nn.Identity()  # eliminamos capa final de clasificación
model.eval()

# --- PREPROCESADO DE IMAGEN ---
transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225])
])

# --- PROCESAR PDF ---
print("Extrayendo regiones de texto y generando embeddings visuales...")
doc = fitz.open(PDF_PATH)
count = 0
results = []

for page_index in range(len(doc)):
    page = doc[page_index]
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                bbox = span.get("bbox")
                text = span.get("text", "").strip()
                if not text or not bbox:
                    continue
                r = fitz.Rect(bbox)
                w, h = r.width, r.height
                if w < 30 or h < 20:
                    continue
                img_path = OUT_DIR / f"img_{count:04}.png"
                if not img_path.exists():
                    pix = page.get_pixmap(clip=r, dpi=150)
                    pix.save(img_path)

                image = Image.open(img_path).convert("RGB")
                input_tensor = transform(image).unsqueeze(0)
                with torch.no_grad():
                    features = model(input_tensor).squeeze().tolist()

                results.append({
                    "pagina": page_index + 1,
                    "bbox": list(bbox),
                    "text": text,
                    "embedding": features
                })

                count += 1
                if count >= MAX_IMAGES:
                    break
            if count >= MAX_IMAGES:
                break
        if count >= MAX_IMAGES:
            break
    if count >= MAX_IMAGES:
        break

doc.close()

# --- GUARDAR RESULTADOS ---
with open(FONT_EMB_PATH, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Se procesaron {count} regiones de texto")
print(f"Embeddings visuales guardados en {FONT_EMB_PATH}")

# --- COMPARAR CONTRA FUENTES DE REFERENCIA ---
print("Comparando contra fuentes conocidas...")
def cargar_fuentes_referencia():
    fuentes = {}
    for carpeta in KNOWN_FONTS_DIR.iterdir():
        if carpeta.is_dir():
            embeddings = []
            for img_file in carpeta.glob("*.png"):
                image = Image.open(img_file).convert("RGB")
                input_tensor = transform(image).unsqueeze(0)
                with torch.no_grad():
                    emb = model(input_tensor).squeeze().numpy()
                    embeddings.append(emb)
            if embeddings:
                fuentes[carpeta.name] = np.mean(embeddings, axis=0)
    return fuentes

font_refs = cargar_fuentes_referencia()

similitudes = []
for r in results:
    vec = np.array(r["embedding"])
    mejor = None
    max_sim = -1
    for font_name, ref_vec in font_refs.items():
        sim = np.dot(vec, ref_vec) / (np.linalg.norm(vec) * np.linalg.norm(ref_vec))
        if sim > max_sim:
            max_sim = sim
            mejor = font_name
    r["font_simil"] = mejor
    r["score"] = round(float(max_sim), 4)
    similitudes.append(r)

with open(SIMILARITY_OUT, "w", encoding="utf-8") as f:
    json.dump(similitudes, f, indent=2, ensure_ascii=False)

print(f"Resultado de similitud guardado en {SIMILARITY_OUT}")
