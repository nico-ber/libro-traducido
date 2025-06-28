import fitz  # PyMuPDF
import json

pdf_path = "datos/original.pdf"
doc = fitz.open(pdf_path)

info_por_fuente = {}

for page_num, page in enumerate(doc, start=1):
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font = span.get("font", "?")
                size = span.get("size", 0)
                text = span.get("text", "").strip().replace("\n", " ")
                if not text:
                    continue

                # Acortamos texto para diagnóstico
                snippet = text[:80]
                if font not in info_por_fuente:
                    info_por_fuente[font] = []
                info_por_fuente[font].append({
                    "page": page_num,
                    "size": round(size, 1),
                    "text": snippet
                })

doc.close()

# Guardamos diagnóstico
with open("datos/diagnostico_fuentes.json", "w", encoding="utf-8") as f:
    json.dump(info_por_fuente, f, ensure_ascii=False, indent=2)

print(f"Fuentes detectadas: {len(info_por_fuente)}")
print("Se generó el archivo datos/diagnostico_fuentes.json")
