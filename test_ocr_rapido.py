"""
Test rápido del OCR con las imágenes capturadas
"""

import cv2
import sys
import os
from pathlib import Path

# Agregar path de core
sys.path.insert(0, str(Path(__file__).parent / 'core'))

try:
    from ocr_engine import OCREngine
    print("✅ ocr_engine importado correctamente")
except ImportError as e:
    print(f"❌ Error importando ocr_engine: {e}")
    print("Asegúrate de ejecutar desde el directorio principal")
    sys.exit(1)

# Crear engine
print("\n📦 Inicializando OCREngine...")
ocr = OCREngine()
print("✅ OCREngine inicializado")

# Buscar imágenes en debug_ocr
debug_dir = Path("debug_ocr")
if not debug_dir.exists():
    print("❌ Carpeta debug_ocr/ no existe")
    sys.exit(1)

# Buscar las últimas 3 imágenes originales
images = sorted(debug_dir.glob("gametag_*_original.jpg"), reverse=True)[:3]

if not images:
    print("❌ No hay imágenes en debug_ocr/")
    sys.exit(1)

print(f"\n🔍 Encontradas {len(images)} imágenes para probar")
print("=" * 60)

success_count = 0
fail_count = 0

for img_path in images:
    print(f"\n📄 Procesando: {img_path.name}")
    
    # Cargar imagen
    img = cv2.imread(str(img_path))
    if img is None:
        print("   ❌ Error cargando imagen")
        fail_count += 1
        continue
    
    print(f"   Dimensiones: {img.shape[1]}x{img.shape[0]} px")
    
    # Extraer texto con threshold 0
    results = ocr.extract_text(img, confidence_threshold=0.0)
    
    if results:
        print(f"   ✅ OCR detectó {len(results)} resultado(s):")
        for r in results:
            print(f"      • '{r.text}' (confianza: {r.confidence:.1f}%)")
        success_count += 1
    else:
        print(f"   ❌ OCR no retornó resultados")
        fail_count += 1
        
        # Debug adicional
        print(f"   🔧 Intentando con image_to_string directo...")
        import pytesseract
        processed = ocr.preprocess_image(img)
        try:
            text = pytesseract.image_to_string(processed, lang='eng', config=ocr.tesseract_config)
            if text.strip():
                print(f"      ℹ️ image_to_string retornó: '{text.strip()}'")
            else:
                print(f"      ⚠️ image_to_string también retornó vacío")
        except Exception as e:
            print(f"      ❌ Error: {e}")

print("\n" + "=" * 60)
print(f"📊 RESULTADO FINAL:")
print(f"   ✅ Exitosos: {success_count}/{len(images)}")
print(f"   ❌ Fallidos: {fail_count}/{len(images)}")

if success_count > 0:
    print(f"\n🎉 ¡OCR FUNCIONA! Detectó texto en {success_count} imagen(es)")
    print("   Puedes ejecutar el programa principal")
else:
    print(f"\n⚠️ OCR NO FUNCIONA")
    print("   Posibles causas:")
    print("   1. Tesseract no instalado o ruta incorrecta")
    print("   2. Archivo ocr_engine.py no actualizado")
    print("   3. Problema con configuración de Tesseract")
    
print("\n" + "=" * 60)
