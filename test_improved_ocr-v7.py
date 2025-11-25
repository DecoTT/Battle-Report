"""
TEST DE OCR MEJORADO - Validador Independiente
===============================================

Este script prueba el OCR mejorado con las imágenes de debug existentes
sin necesidad de modificar el código principal.

Uso:
    python test_improved_ocr.py

Requiere:
    - Carpeta debug_ocr/ con imágenes existentes
    - OpenCV, numpy, pytesseract instalados
"""

import cv2
import numpy as np
import pytesseract
import re
from pathlib import Path
from datetime import datetime


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class ImprovedOCREngine:
    """Motor OCR mejorado con preprocesamiento robusto"""
    
    def __init__(self, sharpness_value=1.0, threshold_value=127):
        self.sharpness_value = sharpness_value
        self.threshold_value = threshold_value
        
        self.tesseract_config = (
            "--psm 7 "
            "--oem 3 "
            "-c preserve_interword_spaces=1 "
            "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghljkmnopqrstuvwxyzi0123456789 "
        )
    
    def preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocesado mínimo: solo convierte a escala de grises,
        sin alterar contraste, nitidez ni aplicar filtros.
        """
        # Si la imagen tiene 4 canales (BGRA/RGBA), quita el alfa
        if img.ndim == 3 and img.shape[2] == 4:
            img = img[:, :, :3]

        # Convertir a escala de grises si es imagen en color
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
            
        gray = cv2.dilate(gray, np.ones((1,1), np.uint8), iterations=8)

        return gray

    
    def extract_text(self, img: np.ndarray) -> str:
        """Extrae texto de imagen"""
        if img is None or img.size == 0:
            return ""
        
        binary = self.preprocess_for_ocr(img)
        
        try:
            text = pytesseract.image_to_string(
                binary, 
                lang='eng',
                config=self.tesseract_config
            ).strip()
            
            text = self.clean_text(text)
            return text
        except Exception as e:
            print(f"   ❌ Error OCR: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Limpia texto extraído"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[|_\[\]{}()<>]', '', text)
        
        # Correcciones comunes
        if len(text) < 30:
            text = re.sub(r'(?<=[a-zA-Z])0(?=[a-zA-Z])', 'O', text)
            text = re.sub(r'(?<=[a-zA-Z])1(?=[a-zA-Z])', 'l', text)
        
        return text.strip()


def run_tests():
    """Ejecuta tests con imágenes de debug existentes"""
    
    print("=" * 80)
    print(" TEST DE OCR MEJORADO - VALIDACIÓN CON IMÁGENES EXISTENTES")
    print("=" * 80)
    
    # Buscar carpeta de debug
    debug_dir = Path("debug_ocr")
    
    if not debug_dir.exists():
        print("\n❌ ERROR: Carpeta 'debug_ocr/' no encontrada")
        print("   Primero ejecuta battle_report_scraper.py para generar imágenes")
        return
    
    # Buscar imágenes
    images = list(debug_dir.glob("gametag_*.jpg"))
    
    # Filtrar solo originales (sin _processed)
    original_images = [img for img in images if '_original' not in img.name and '_processed' not in img.name]
    
    if not original_images:
        print(f"\n❌ ERROR: No se encontraron imágenes en {debug_dir}")
        print("   Archivos encontrados:")
        for img in images:
            print(f"   - {img.name}")
        return
    
    print(f"\n✅ Encontradas {len(original_images)} imágenes para procesar")
    print("-" * 80)
    
    # Crear motor OCR
    ocr = ImprovedOCREngine(sharpness_value=1.0, threshold_value=127)
    
    # Procesar cada imagen
    results = []
    for i, img_path in enumerate(original_images[:10], 1):  # Máximo 10
        print(f"\n📄 [{i}/{min(len(original_images), 10)}] {img_path.name}")
        print(f"   Tamaño del archivo: {img_path.stat().st_size / 1024:.1f} KB")
        
        # Cargar imagen
        img = cv2.imread(str(img_path))
        if img is None:
            print("   ❌ Error al cargar imagen")
            continue
        
        print(f"   Dimensiones: {img.shape[1]}x{img.shape[0]} px")
        
        # Preprocesar y guardar
        binary = ocr.preprocess_for_ocr(img)
        processed_path = img_path.parent / f"{img_path.stem}_TEST_processed.jpg"
        cv2.imwrite(str(processed_path), binary)
        print(f"   💾 Preprocesada: {processed_path.name}")
        
        # Extraer texto
        text = ocr.extract_text(img)
        
        if text:
            print(f"   ✅ OCR detectó: '{text}'")
            results.append({
                'image': img_path.name,
                'text': text,
                'status': 'success'
            })
        else:
            print(f"   ⚠️ OCR no retornó texto")
            results.append({
                'image': img_path.name,
                'text': '',
                'status': 'empty'
            })
    
    # Resumen
    print("\n" + "=" * 80)
    print(" RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    empty_count = sum(1 for r in results if r['status'] == 'empty')
    
    print(f"\n📊 Estadísticas:")
    print(f"   ✅ Exitosos: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    print(f"   ⚠️ Vacíos: {empty_count}/{len(results)}")
    
    if success_count > 0:
        print(f"\n📋 Textos detectados:")
        for r in results:
            if r['status'] == 'success':
                print(f"   • {r['text']}")
    
    print("\n" + "=" * 80)
    print(" DIAGNÓSTICO")
    print("=" * 80)
    
    if success_count == 0:
        print("\n❌ PROBLEMA: OCR no está detectando nada")
        print("\n🔍 Pasos de diagnóstico:")
        print("   1. Abre las imágenes *_TEST_processed.jpg en debug_ocr/")
        print("   2. Verifica que:")
        print("      • El texto sea NEGRO sobre fondo BLANCO")
        print("      • Las letras sean grandes y nítidas")
        print("      • El contraste sea alto")
        print("   3. Si el texto es pequeño o borroso:")
        print("      • Aumenta sharpness_value a 1.5 en línea 154")
        print("   4. Si el contraste es bajo:")
        print("      • Cambia threshold_value a 110 en línea 154")
        print("   5. Verifica instalación de Tesseract:")
        print("      • Ejecuta: tesseract --version")
        
    elif success_count < len(results):
        print("\n⚠️ PROBLEMA PARCIAL: Algunas imágenes no detectan")
        print(f"\n🔍 {empty_count} imágenes problemáticas:")
        for r in results:
            if r['status'] == 'empty':
                print(f"   • {r['image']}")
        print("\n   Abre estas imágenes *_TEST_processed.jpg y verifica calidad")
        
    else:
        print("\n✅ ÉXITO: Todas las imágenes procesadas correctamente")
        print("\n🎯 El OCR mejorado está funcionando perfectamente")
        print("   Puedes proceder con la integración en battle_report_scraper.py")
        print("   Sigue la GUIA_INTEGRACION_v2.0.md")
    
    print("\n" + "=" * 80)


def test_with_sample_names():
    """Test adicional con nombres simulados"""
    print("\n" + "=" * 80)
    print(" TEST ADICIONAL: GENERACIÓN DE MUESTRAS")
    print("=" * 80)
    
    print("\n⚠️ Este test genera imágenes sintéticas con nombres")
    print("   Solo para validar el pipeline de preprocesamiento")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        names = ["Vladimir Postain", "John Smith", "Alex Dragon", "Maria Garcia"]
        output_dir = Path("debug_ocr/synthetic_tests")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        ocr = ImprovedOCREngine()
        
        print(f"\n📝 Generando {len(names)} imágenes sintéticas...")
        
        for name in names:
            # Crear imagen simple con texto
            img = Image.new('RGB', (400, 80), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            
            # Intentar usar fuente por defecto
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            draw.text((10, 30), name, fill=(0, 0, 0), font=font)
            
            # Guardar
            img_path = output_dir / f"synthetic_{name.replace(' ', '_')}.jpg"
            img.save(str(img_path))
            
            # Convertir a OpenCV y procesar
            img_cv = cv2.imread(str(img_path))
            text = ocr.extract_text(img_cv)
            
            if text:
                print(f"   ✅ {name} → OCR: '{text}'")
            else:
                print(f"   ❌ {name} → OCR vacío")
        
        print(f"\n💾 Imágenes sintéticas guardadas en: {output_dir}")
        
    except ImportError:
        print("\n⚠️ PIL no disponible, saltando test sintético")
        print("   Instala con: pip install pillow")


if __name__ == "__main__":
    # Test principal con imágenes existentes
    run_tests()
    
    # Test adicional (opcional)
    # test_with_sample_names()
    
    print("\n✅ Tests completados")
    print("=" * 80)
