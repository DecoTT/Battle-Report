"""
Setup Script for Game Data Scraper Suite
Inicializa la estructura del proyecto y verifica dependencias
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import shutil

class ProjectSetup:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.errors = []
        self.warnings = []
        
    def print_header(self):
        """Imprime el header del setup"""
        print("=" * 60)
        print("   GAME DATA SCRAPER SUITE - SETUP")
        print("=" * 60)
        print()
        
    def check_python_version(self):
        """Verifica la versión de Python"""
        print("🔍 Verificando versión de Python...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.errors.append("❌ Python 3.8 o superior es requerido")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detectado")
        return True
        
    def create_directories(self):
        """Crea la estructura de directorios"""
        print("\n📁 Creando estructura de directorios...")
        
        directories = [
            "assets/heroes",
            "assets/captains",
            "assets/ui_elements",
            "assets/templates",
            "config",
            "config/backups",
            "data/chat_logs",
            "data/battle_reports",
            "data/excel_reports",
            "logs",
            "modules",
            "tools",
            "core"
        ]
        
        for dir_path in directories:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {dir_path}")
            
    def check_dependencies(self):
        """Verifica las dependencias de Python"""
        print("\n📦 Verificando dependencias...")
        
        required_packages = [
            "opencv-python",
            "pytesseract",
            "numpy",
            "pandas",
            "openpyxl",
            "mss",
            "pyautogui",
            "Pillow",
            "keyboard",
            "python-dateutil"
        ]
        
        optional_packages = [
            "easyocr",
            "customtkinter",
            "scikit-image",
            "matplotlib",
            "colorama"
        ]
        
        missing_required = []
        missing_optional = []
        
        # Verificar paquetes requeridos
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"  ✅ {package}")
            except ImportError:
                missing_required.append(package)
                print(f"  ❌ {package} - REQUERIDO")
                
        # Verificar paquetes opcionales
        for package in optional_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"  ✅ {package}")
            except ImportError:
                missing_optional.append(package)
                print(f"  ⚠️  {package} - Opcional")
                
        if missing_required:
            self.errors.append(f"Paquetes requeridos faltantes: {', '.join(missing_required)}")
            print(f"\n❗ Para instalar los paquetes faltantes, ejecuta:")
            print(f"   pip install {' '.join(missing_required)}")
            
        if missing_optional:
            self.warnings.append(f"Paquetes opcionales faltantes: {', '.join(missing_optional)}")
            
    def check_tesseract(self):
        """Verifica la instalación de Tesseract OCR"""
        print("\n🔍 Verificando Tesseract OCR...")
        
        try:
            import pytesseract
            # Intentar obtener la versión de Tesseract
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract {version} detectado")
            
            # Verificar idiomas disponibles
            try:
                langs = pytesseract.get_languages()
                if 'spa' in langs:
                    print("  ✅ Idioma español disponible")
                else:
                    self.warnings.append("Idioma español no disponible en Tesseract")
                    print("  ⚠️  Idioma español no disponible")
                    
                if 'eng' in langs:
                    print("  ✅ Idioma inglés disponible")
                else:
                    self.warnings.append("Idioma inglés no disponible en Tesseract")
                    print("  ⚠️  Idioma inglés no disponible")
                    
            except:
                self.warnings.append("No se pudieron verificar los idiomas de Tesseract")
                
        except Exception as e:
            self.errors.append("Tesseract OCR no está instalado o no está en el PATH")
            print("❌ Tesseract OCR no encontrado")
            print("\n📥 Para instalar Tesseract:")
            print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   Linux: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
            print("   Mac: brew install tesseract tesseract-lang")
            
    def create_sample_files(self):
        """Crea archivos de ejemplo"""
        print("\n📝 Creando archivos de ejemplo...")
        
        # Crear un archivo de log de chat de ejemplo
        sample_chat = {
            "date": "2025-10-27",
            "chat_name": "Dommy Monday Example",
            "marker_position": "line_1",
            "participants": [
                {
                    "name": "Player1",
                    "raw_message": "Mi contribución: 45b silver",
                    "parsed_silver": 45000000000,
                    "parse_success": True,
                    "timestamp": "14:23:45"
                },
                {
                    "name": "Player2",
                    "raw_message": "15 + 20 + 10 = 45",
                    "parsed_silver": 45000000000,
                    "parse_success": True,
                    "timestamp": "14:24:12"
                }
            ]
        }
        
        sample_chat_path = self.base_dir / "data" / "chat_logs" / "DC_20251027_example.json"
        with open(sample_chat_path, 'w', encoding='utf-8') as f:
            json.dump(sample_chat, f, indent=4, ensure_ascii=False)
        print(f"  ✅ Chat de ejemplo: {sample_chat_path.name}")
        
        # Crear un reporte de batalla de ejemplo
        sample_battle = {
            "date": "2025-10-27",
            "battle_type": "CP Run",
            "participants": [
                {
                    "name": "Player1",
                    "artifacts_used": False,
                    "forbidden_captains": [],
                    "participated": True
                },
                {
                    "name": "Player2",
                    "artifacts_used": False,
                    "forbidden_captains": ["Amanitore"],
                    "participated": True
                }
            ],
            "total_participants": 2,
            "violations": 1
        }
        
        sample_battle_path = self.base_dir / "data" / "battle_reports" / "BR_20251027_example.json"
        with open(sample_battle_path, 'w', encoding='utf-8') as f:
            json.dump(sample_battle, f, indent=4, ensure_ascii=False)
        print(f"  ✅ Reporte de batalla de ejemplo: {sample_battle_path.name}")
        
    def create_shortcuts(self):
        """Crea accesos directos para las herramientas"""
        print("\n🔗 Creando archivos de inicio rápido...")
        
        # Crear batch files para Windows
        if sys.platform == "win32":
            # Main app
            batch_content = f'@echo off\ncd /d "{self.base_dir}"\npython main.py\npause'
            batch_file = self.base_dir / "Start_Main_App.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            print(f"  ✅ {batch_file.name}")
            
            # Asset Extractor
            batch_content = f'@echo off\ncd /d "{self.base_dir}"\npython tools/asset_extractor.py\npause'
            batch_file = self.base_dir / "Start_Asset_Extractor.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            print(f"  ✅ {batch_file.name}")
            
            # Coord Finder
            batch_content = f'@echo off\ncd /d "{self.base_dir}"\npython tools/coord_finder.py\npause'
            batch_file = self.base_dir / "Start_Coord_Finder.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            print(f"  ✅ {batch_file.name}")
            
            # Asset Manager
            batch_content = f'@echo off\ncd /d "{self.base_dir}"\npython tools/asset_manager.py\npause'
            batch_file = self.base_dir / "Start_Asset_Manager.bat"
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            print(f"  ✅ {batch_file.name}")
            
    def check_config_files(self):
        """Verifica que los archivos de configuración existen"""
        print("\n⚙️ Verificando archivos de configuración...")
        
        config_files = [
            "config/app_config.json",
            "config/coordinates.json",
            "config/heroes_list.json",
            "config/forbidden_caps.json"
        ]
        
        for config_file in config_files:
            file_path = self.base_dir / config_file
            if file_path.exists():
                print(f"  ✅ {config_file}")
            else:
                self.warnings.append(f"Archivo de configuración faltante: {config_file}")
                print(f"  ⚠️  {config_file} - No encontrado")
                
    def install_requirements(self):
        """Opción para instalar requirements automáticamente"""
        print("\n📦 ¿Deseas instalar las dependencias automáticamente?")
        response = input("   (s/n): ").lower()
        
        if response == 's':
            requirements_file = self.base_dir / "requirements.txt"
            if requirements_file.exists():
                print("\n🔄 Instalando dependencias...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
                    print("✅ Dependencias instaladas correctamente")
                except subprocess.CalledProcessError:
                    self.errors.append("Error instalando dependencias")
                    print("❌ Error instalando dependencias")
            else:
                self.errors.append("Archivo requirements.txt no encontrado")
                print("❌ Archivo requirements.txt no encontrado")
                
    def print_summary(self):
        """Imprime el resumen del setup"""
        print("\n" + "=" * 60)
        print("   RESUMEN DEL SETUP")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORES ENCONTRADOS:")
            for error in self.errors:
                print(f"   • {error}")
                
        if self.warnings:
            print("\n⚠️  ADVERTENCIAS:")
            for warning in self.warnings:
                print(f"   • {warning}")
                
        if not self.errors:
            print("\n✅ Setup completado exitosamente!")
            print("\n🚀 Para iniciar la aplicación:")
            print("   python main.py")
            print("\n📚 Para más información, consulta README.md")
        else:
            print("\n❗ Por favor, resuelve los errores antes de continuar")
            
    def run(self):
        """Ejecuta el proceso de setup"""
        self.print_header()
        
        # Verificaciones
        if not self.check_python_version():
            print("\n❌ Setup abortado debido a versión de Python incompatible")
            return
            
        self.create_directories()
        self.check_dependencies()
        self.check_tesseract()
        self.check_config_files()
        self.create_sample_files()
        self.create_shortcuts()
        
        # Preguntar si instalar requirements
        if self.errors:
            print("\n" + "=" * 60)
            self.install_requirements()
            
        self.print_summary()
        
if __name__ == "__main__":
    setup = ProjectSetup()
    setup.run()
    
    input("\nPresiona Enter para salir...")
