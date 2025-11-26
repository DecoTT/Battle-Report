#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Instalación y Verificación
Battle Report Scraper v1.3
"""

import subprocess
import sys

def install_keyboard():
    """Instala el módulo keyboard"""
    print("="*60)
    print("INSTALANDO MÓDULO KEYBOARD")
    print("="*60)
    print("\nEste módulo permite detener la captura presionando ESC")
    print("de forma elegante sin interrumpir el proceso.\n")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
        print("\n✅ Keyboard instalado correctamente")
        return True
    except Exception as e:
        print(f"\n❌ Error instalando keyboard: {e}")
        print("\nIntenta manualmente:")
        print("  pip install keyboard --user")
        return False

def verify_installation():
    """Verifica que todo esté instalado correctamente"""
    print("\n" + "="*60)
    print("VERIFICACIÓN DE DEPENDENCIAS")
    print("="*60 + "\n")
    
    modules = {
        'keyboard': 'Detener con ESC',
        'cv2': 'Procesamiento de imágenes',
        'numpy': 'Operaciones numéricas',
        'pytesseract': 'OCR (Tesseract)',
        'mss': 'Capturas de pantalla',
        'pyautogui': 'Control de mouse/teclado'
    }
    
    results = {}
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"✅ {module:15} - {description}")
            results[module] = True
        except ImportError:
            print(f"❌ {module:15} - {description} [NO INSTALADO]")
            results[module] = False
    
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    
    critical = ['cv2', 'numpy', 'mss', 'pyautogui']
    optional = ['keyboard', 'pytesseract']
    
    critical_ok = all(results.get(m, False) for m in critical)
    
    if critical_ok:
        print("\n✅ Módulos críticos: OK")
    else:
        print("\n❌ Faltan módulos críticos:")
        for m in critical:
            if not results.get(m, False):
                print(f"   - {m}")
    
    print("\nMódulos opcionales:")
    for m in optional:
        if results.get(m, False):
            print(f"   ✅ {m}")
        else:
            print(f"   ⚠️  {m} - Recomendado pero no crítico")
    
    # Verificar Tesseract
    print("\n" + "="*60)
    print("VERIFICACIÓN DE TESSERACT OCR")
    print("="*60)
    
    try:
        import pytesseract
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        print(f"\nRuta de Tesseract: {tesseract_cmd}")
        
        # Intentar ejecutar Tesseract
        subprocess.check_output([tesseract_cmd, '--version'], stderr=subprocess.STDOUT)
        print("✅ Tesseract OCR está instalado y funcionando")
    except Exception as e:
        print("\n⚠️  Tesseract OCR no está instalado o no está en PATH")
        print("\nPara instalarlo:")
        print("  1. Descargar: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  2. Instalar el ejecutable")
        print("  3. Agregar a PATH: C:\\Program Files\\Tesseract-OCR")
        print("\nSIN TESSERACT: El programa usará solo EasyOCR (más lento)")
    
    print("\n" + "="*60)
    
    if critical_ok:
        print("\n🎉 ¡Todo listo para ejecutar el Battle Report Scraper!")
        if not results.get('keyboard', False):
            print("\n💡 TIP: Instala 'keyboard' para poder detener con ESC:")
            print("   pip install keyboard")
    else:
        print("\n⚠️  Faltan módulos críticos. Instala con:")
        print("   pip install opencv-python numpy mss pyautogui")
    
    return critical_ok

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("BATTLE REPORT SCRAPER v1.3")
    print("Setup & Verificación")
    print("="*60 + "\n")
    
    print("¿Qué deseas hacer?")
    print("1. Verificar dependencias")
    print("2. Instalar keyboard (para ESC)")
    print("3. Ambos")
    print("0. Salir")
    
    choice = input("\nOpción: ").strip()
    
    if choice == "1":
        verify_installation()
    elif choice == "2":
        install_keyboard()
        verify_installation()
    elif choice == "3":
        install_keyboard()
        verify_installation()
    elif choice == "0":
        print("\n👋 ¡Hasta luego!")
    else:
        print("\n❌ Opción no válida")
    
    input("\nPresiona ENTER para salir...")

if __name__ == "__main__":
    main()
