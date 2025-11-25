"""
📸 TEMPLATE CAPTURE TOOL
========================
Herramienta para capturar templates correctamente desde el juego

CARACTERÍSTICAS:
- Captura el área exacta donde aparecen las cards
- Permite guardar múltiples templates en secuencia
- Preview en tiempo real
- Guarda automáticamente en assets/heroes/ o assets/captains/

USO:
    1. Posiciona el cursor sobre una card
    2. Presiona ESPACIO para capturar
    3. Escribe el nombre (sin extensión)
    4. Repite para más cards
    5. Presiona ESC para salir

CONTROLES:
    ESPACIO = Capturar card bajo el cursor
    H       = Cambiar a modo Heroes
    C       = Cambiar a modo Capitanes  
    P       = Toggle Preview
    ESC     = Salir
"""

import cv2
import numpy as np
import mss
import pyautogui
import time
from pathlib import Path
from datetime import datetime

# ===================================================================
# CONFIGURACIÓN
# ===================================================================

# Tamaños de captura (aprox)
HERO_SIZE = (90, 110)      # Ancho x Alto de heroes
CAPTAIN_SIZE = (70, 90)    # Ancho x Alto de capitanes

# Preview config
PREVIEW_SCALE = 3.0        # Zoom del preview
PREVIEW_UPDATE_MS = 100    # Actualizar cada 100ms

# ===================================================================
# CLASE PRINCIPAL
# ===================================================================

class TemplateCapturer:
    def __init__(self):
        self.mode = 'hero'  # 'hero' o 'captain'
        self.preview_enabled = True
        self.capture_count = 0
        
        # Crear directorios si no existen
        Path("assets/heroes").mkdir(parents=True, exist_ok=True)
        Path("assets/captains").mkdir(parents=True, exist_ok=True)
        
        print("="*70)
        print("📸 TEMPLATE CAPTURE TOOL")
        print("="*70)
        print("\n⌨️  CONTROLES:")
        print("   ESPACIO = Capturar card bajo el cursor")
        print("   H       = Modo Heroes")
        print("   C       = Modo Capitanes")
        print("   P       = Toggle Preview")
        print("   ESC     = Salir")
        print("\n📁 Directorios:")
        print("   Heroes:    assets/heroes/")
        print("   Capitanes: assets/captains/")
        print("="*70)
    
    def get_capture_size(self):
        """Retorna el tamaño de captura según el modo"""
        return HERO_SIZE if self.mode == 'hero' else CAPTAIN_SIZE
    
    def get_save_directory(self):
        """Retorna el directorio donde guardar según el modo"""
        return Path("assets") / ("heroes" if self.mode == 'hero' else "captains")
    
    def capture_at_cursor(self):
        """Captura el área bajo el cursor"""
        # Obtener posición del cursor
        x, y = pyautogui.position()
        width, height = self.get_capture_size()
        
        # Calcular área (centrado en cursor)
        left = x - width // 2
        top = y - height // 2
        
        # Capturar
        with mss.mss() as sct:
            region = {
                'left': left,
                'top': top,
                'width': width,
                'height': height
            }
            screenshot = np.array(sct.grab(region))
            img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        
        return img, (left, top, width, height)
    
    def show_preview_window(self):
        """Muestra preview continuo del área bajo el cursor"""
        last_update = 0
        
        while True:
            current_time = time.time()
            
            # Actualizar preview cada PREVIEW_UPDATE_MS
            if (current_time - last_update) * 1000 >= PREVIEW_UPDATE_MS:
                if self.preview_enabled:
                    # Capturar área bajo cursor
                    img, region = self.capture_at_cursor()
                    
                    # Hacer zoom para preview
                    preview_w = int(img.shape[1] * PREVIEW_SCALE)
                    preview_h = int(img.shape[0] * PREVIEW_SCALE)
                    preview = cv2.resize(img, (preview_w, preview_h), 
                                        interpolation=cv2.INTER_NEAREST)
                    
                    # Agregar información
                    info = preview.copy()
                    
                    # Modo actual
                    mode_text = f"MODO: {self.mode.upper()}"
                    mode_color = (0, 255, 0) if self.mode == 'hero' else (255, 0, 0)
                    cv2.putText(info, mode_text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
                    
                    # Tamaño
                    size_text = f"Tamano: {img.shape[1]}x{img.shape[0]}"
                    cv2.putText(info, size_text, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Cursor position
                    x, y = pyautogui.position()
                    pos_text = f"Cursor: ({x}, {y})"
                    cv2.putText(info, pos_text, (10, 85),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Instrucciones
                    cv2.putText(info, "ESPACIO=Capturar | H=Heroes | C=Captains", 
                               (10, info.shape[0] - 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                    cv2.putText(info, "P=Toggle Preview | ESC=Salir", 
                               (10, info.shape[0] - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                    
                    # Crosshair en el centro
                    center_x = info.shape[1] // 2
                    center_y = info.shape[0] // 2
                    cv2.line(info, (center_x - 20, center_y), (center_x + 20, center_y), 
                            (0, 255, 255), 2)
                    cv2.line(info, (center_x, center_y - 20), (center_x, center_y + 20), 
                            (0, 255, 255), 2)
                    
                    cv2.imshow("📸 Preview - Posiciona y presiona ESPACIO", info)
                
                last_update = current_time
            
            # Procesar eventos de teclado
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                return 'quit'
            elif key == ord(' '):  # ESPACIO
                return 'capture'
            elif key == ord('h') or key == ord('H'):
                self.mode = 'hero'
                print(f"\n🎯 Modo cambiado a: HEROES")
            elif key == ord('c') or key == ord('C'):
                self.mode = 'captain'
                print(f"\n🎯 Modo cambiado a: CAPITANES")
            elif key == ord('p') or key == ord('P'):
                self.preview_enabled = not self.preview_enabled
                if not self.preview_enabled:
                    cv2.destroyWindow("📸 Preview - Posiciona y presiona ESPACIO")
                print(f"\n👁️ Preview: {'ON' if self.preview_enabled else 'OFF'}")
    
    def save_template(self, img: np.ndarray, name: str):
        """Guarda el template capturado"""
        save_dir = self.get_save_directory()
        
        # Crear nombre de archivo único si ya existe
        base_name = name
        counter = 1
        filepath = save_dir / f"{name}.jpg"
        
        while filepath.exists():
            name = f"{base_name}_{counter}"
            filepath = save_dir / f"{name}.jpg"
            counter += 1
        
        # Guardar
        cv2.imwrite(str(filepath), img)
        
        return filepath, name
    
    def capture_workflow(self):
        """Workflow de captura"""
        # Capturar imagen
        img, region = self.capture_at_cursor()
        
        # Mostrar captura
        preview_w = int(img.shape[1] * PREVIEW_SCALE * 1.5)
        preview_h = int(img.shape[0] * PREVIEW_SCALE * 1.5)
        preview = cv2.resize(img, (preview_w, preview_h), 
                            interpolation=cv2.INTER_NEAREST)
        
        # Agregar info
        info = preview.copy()
        cv2.putText(info, "Captura OK - Introduce nombre:", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(info, f"Tamano: {img.shape[1]}x{img.shape[0]}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("✅ Capturado - Ingresa nombre", info)
        cv2.waitKey(1)
        
        # Pedir nombre por consola
        print(f"\n{'='*70}")
        print(f"✅ CAPTURA EXITOSA")
        print(f"   Modo: {self.mode.upper()}")
        print(f"   Tamaño: {img.shape[1]}x{img.shape[0]}")
        print(f"   Región: {region}")
        print(f"{'='*70}")
        
        while True:
            name = input("\n📝 Nombre del template (sin .jpg): ").strip()
            
            if not name:
                print("   ⚠️ Nombre no puede estar vacío")
                continue
            
            # Validar caracteres
            if not name.replace('_', '').replace('-', '').isalnum():
                print("   ⚠️ Solo letras, números, _ y -")
                continue
            
            break
        
        # Guardar
        filepath, final_name = self.save_template(img, name)
        
        self.capture_count += 1
        
        print(f"\n✅ GUARDADO: {filepath}")
        print(f"   Capturas totales: {self.capture_count}")
        
        # Cerrar ventana de captura
        cv2.destroyWindow("✅ Capturado - Ingresa nombre")
        
        # Pequeña pausa
        time.sleep(0.5)
    
    def run(self):
        """Ejecuta el capturador"""
        print(f"\n🎬 Iniciando capturador...")
        print(f"   Posiciona el cursor sobre una card y presiona ESPACIO")
        
        time.sleep(1)
        
        try:
            while True:
                action = self.show_preview_window()
                
                if action == 'quit':
                    break
                elif action == 'capture':
                    self.capture_workflow()
        
        except KeyboardInterrupt:
            print("\n\n🛑 Ctrl+C detectado")
        
        finally:
            cv2.destroyAllWindows()
            
            print(f"\n{'='*70}")
            print(f"📊 RESUMEN:")
            print(f"   Templates capturados: {self.capture_count}")
            print(f"{'='*70}")
            
            if self.capture_count > 0:
                print(f"\n✅ Templates guardados en:")
                print(f"   • assets/heroes/")
                print(f"   • assets/captains/")
                print(f"\n💡 Usa 'template_diagnostic.py' para verificar calidad")
            
            print(f"\n✅ Capturador finalizado\n")

# ===================================================================
# MAIN
# ===================================================================

def main():
    capturer = TemplateCapturer()
    capturer.run()

if __name__ == "__main__":
    main()
