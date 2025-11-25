"""
🎯 TESTER DEBUG V3.0 - VISUAL EN TIEMPO REAL
================================================
Muestra en tiempo real cómo el sistema detecta heroes y capitanes
SIN hacer scroll, para debuggear por qué algunos heroes no son reconocidos

CARACTERÍSTICAS:
- Detección en tiempo real de heroes y capitanes
- Visualización con colores: 🟢 VERDE=Heroes | 🔵 AZUL=Capitanes
- Muestra coordenadas exactas del click estimado
- Threshold configurable (default 0.78 como battle_report_scraper)
- Multi-scale detection ON
- NO hace scroll
- ESC para salir
"""

import cv2
import numpy as np
import mss
import time
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# ===================================================================
# CONFIGURACIÓN (100% IGUAL A BATTLE_REPORT_SCRAPER)
# ===================================================================

# Área del log donde aparecen las cards
LOG_AREA = {
    'left': 490,
    'top': 441,
    'width': 444,
    'height': 380
}

# Configuración de detección
DETECTION_CONFIG = {
    'threshold': 0.78,          # 🎯 IGUAL que battle_report_scraper
    'multi_scale': True,        # Multi-scale detection ON
    'min_scale': 0.9,
    'max_scale': 1.1,
    'scale_step': 0.05,
    'nms_threshold': 45,        # Non-Maximum Suppression
}

# Colores para visualización (BGR)
COLORS = {
    'hero': (0, 255, 0),         # 🟢 VERDE
    'captain': (255, 0, 0),      # 🔵 AZUL (BGR, así que es azul)
    'text': (255, 255, 255),     # ⚪ BLANCO
    'click_point': (255, 255, 255),  # ⚪ BLANCO
}

# ===================================================================
# TEMPLATE MATCHER SIMPLIFICADO
# ===================================================================

class SimpleTemplateMatcher:
    """Template matcher simplificado para el tester"""
    
    def __init__(self):
        self.templates: Dict[str, np.ndarray] = {}
        self.config = DETECTION_CONFIG
        
    def load_templates_from_directory(self, category: str) -> Dict[str, np.ndarray]:
        """Carga templates desde assets/{category}/"""
        templates = {}
        templates_dir = Path("assets") / category
        
        if not templates_dir.exists():
            print(f"❌ No existe: {templates_dir}")
            print(f"   Crea el directorio y agrega archivos .jpg de {category}")
            return templates
        
        print(f"\n📁 Cargando {category}...")
        for img_file in templates_dir.glob("*.jpg"):
            img = cv2.imread(str(img_file))
            if img is not None:
                templates[img_file.stem] = img
                print(f"   ✅ {img_file.stem} - {img.shape}")
            else:
                print(f"   ❌ Error leyendo: {img_file.name}")
        
        print(f"✅ Total {category}: {len(templates)}")
        return templates
    
    def match_template_multiscale(self, image: np.ndarray, template: np.ndarray) -> List[Tuple[int, int, float, float]]:
        """Detecta template con multi-scale"""
        matches = []
        
        if not self.config['multi_scale']:
            # Single-scale
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= self.config['threshold'])
            for pt in zip(*locations[::-1]):
                conf = result[pt[1], pt[0]]
                matches.append((pt[0], pt[1], conf, 1.0))
            return matches
        
        # Multi-scale
        scales = np.arange(
            self.config['min_scale'],
            self.config['max_scale'] + self.config['scale_step'],
            self.config['scale_step']
        )
        
        for scale in scales:
            # Redimensionar template
            new_w = int(template.shape[1] * scale)
            new_h = int(template.shape[0] * scale)
            
            if new_w < 10 or new_h < 10 or new_w > image.shape[1] or new_h > image.shape[0]:
                continue
            
            resized_template = cv2.resize(template, (new_w, new_h))
            
            # Template matching
            result = cv2.matchTemplate(image, resized_template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= self.config['threshold'])
            
            for pt in zip(*locations[::-1]):
                conf = result[pt[1], pt[0]]
                matches.append((pt[0], pt[1], conf, scale))
        
        return matches
    
    def find_all_templates(self, image: np.ndarray, templates: Dict[str, np.ndarray]) -> Dict[str, List[Tuple[int, int, float]]]:
        """Encuentra todas las instancias de todos los templates"""
        all_matches = {}
        
        for name, template in templates.items():
            matches = self.match_template_multiscale(image, template)
            if matches:
                all_matches[name] = [(x, y, conf) for x, y, conf, scale in matches]
        
        return all_matches

# ===================================================================
# NON-MAXIMUM SUPPRESSION
# ===================================================================

def non_max_suppression(detections: List[Tuple], overlap_thresh: int = 45) -> List[Tuple]:
    """
    Elimina detecciones duplicadas muy cercanas
    detections: [(name, card_type, (x, y), confidence), ...]
    """
    if len(detections) == 0:
        return []
    
    keep = []
    for detection in detections:
        name, card_type, (x, y), conf = detection
        
        # Verificar si está muy cerca de alguna detección ya guardada
        too_close = False
        for kept_detection in keep:
            _, _, (kx, ky), _ = kept_detection
            distance = np.sqrt((x - kx)**2 + (y - ky)**2)
            
            if distance < overlap_thresh:
                too_close = True
                break
        
        if not too_close:
            keep.append(detection)
    
    return keep

# ===================================================================
# CAPTURA Y DETECCIÓN
# ===================================================================

def capture_log_area():
    """Captura el área del log"""
    with mss.mss() as sct:
        region = {
            'left': LOG_AREA['left'],
            'top': LOG_AREA['top'],
            'width': LOG_AREA['width'],
            'height': LOG_AREA['height']
        }
        screenshot = np.array(sct.grab(region))
        return cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

def detect_all_cards(log_screenshot: np.ndarray, heroes: Dict, captains: Dict, matcher: SimpleTemplateMatcher):
    """Detecta todas las cards (heroes y capitanes) en el screenshot"""
    all_detections = []
    
    # Detectar heroes
    hero_matches = matcher.find_all_templates(log_screenshot, heroes)
    for name, matches in hero_matches.items():
        for x, y, conf in matches:
            # Convertir a coordenadas absolutas de pantalla
            abs_x = LOG_AREA['left'] + x
            abs_y = LOG_AREA['top'] + y
            all_detections.append((name, 'hero', (abs_x, abs_y), conf))
    
    # Detectar capitanes
    captain_matches = matcher.find_all_templates(log_screenshot, captains)
    for name, matches in captain_matches.items():
        for x, y, conf in matches:
            # Convertir a coordenadas absolutas de pantalla
            abs_x = LOG_AREA['left'] + x
            abs_y = LOG_AREA['top'] + y
            all_detections.append((name, 'captain', (abs_x, abs_y), conf))
    
    # Aplicar NMS
    all_detections = non_max_suppression(all_detections, DETECTION_CONFIG['nms_threshold'])
    
    # Separar por tipo
    heroes_found = [(n, t, p, c) for n, t, p, c in all_detections if t == 'hero']
    captains_found = [(n, t, p, c) for n, t, p, c in all_detections if t == 'captain']
    
    return heroes_found, captains_found

# ===================================================================
# VISUALIZACIÓN DEBUG
# ===================================================================

def draw_debug_overlay(log_screenshot: np.ndarray, heroes_found: List, captains_found: List) -> np.ndarray:
    """Dibuja overlay con todas las detecciones"""
    debug_img = log_screenshot.copy()
    
    # Información general en la parte superior
    cv2.putText(debug_img, f"HEROES: {len(heroes_found)} | CAPTAINS: {len(captains_found)}", 
               (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['text'], 2)
    
    cv2.putText(debug_img, "VERDE=Hero | AZUL=Captain | ESC=Salir", 
               (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['text'], 1)
    
    cv2.putText(debug_img, f"Threshold: {DETECTION_CONFIG['threshold']} | Multi-scale: ON", 
               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    
    # Dibujar HEROES (VERDE)
    for name, card_type, (abs_x, abs_y), conf in heroes_found:
        # Convertir a coordenadas relativas del log
        rel_x = abs_x - LOG_AREA['left']
        rel_y = abs_y - LOG_AREA['top']
        
        # Rectángulo de la card (90x110 px aprox)
        cv2.rectangle(debug_img, (rel_x, rel_y), (rel_x + 90, rel_y + 110), 
                     COLORS['hero'], 3)
        
        # Punto de click en el centro (+25, +25 desde esquina)
        click_x = rel_x + 25
        click_y = rel_y + 25
        cv2.circle(debug_img, (click_x, click_y), 8, COLORS['click_point'], -1)
        cv2.circle(debug_img, (click_x, click_y), 9, COLORS['hero'], 2)
        
        # Etiqueta con nombre
        cv2.putText(debug_img, f"{name}", 
                   (rel_x, rel_y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLORS['hero'], 2)
        
        # Coordenadas de click
        cv2.putText(debug_img, f"Click: ({abs_x + 25}, {abs_y + 25})", 
                   (rel_x, rel_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['text'], 1)
        
        # Confianza
        cv2.putText(debug_img, f"Conf: {conf:.3f}", 
                   (rel_x, rel_y + 128), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS['text'], 1)
    
    # Dibujar CAPITANES (AZUL)
    for name, card_type, (abs_x, abs_y), conf in captains_found:
        # Convertir a coordenadas relativas del log
        rel_x = abs_x - LOG_AREA['left']
        rel_y = abs_y - LOG_AREA['top']
        
        # Rectángulo de la card (70x90 px aprox, más pequeño que heroes)
        cv2.rectangle(debug_img, (rel_x, rel_y), (rel_x + 70, rel_y + 90), 
                     COLORS['captain'], 3)
        
        # Punto de click en el centro (+20, +20 desde esquina)
        click_x = rel_x + 20
        click_y = rel_y + 20
        cv2.circle(debug_img, (click_x, click_y), 6, COLORS['click_point'], -1)
        cv2.circle(debug_img, (click_x, click_y), 7, COLORS['captain'], 2)
        
        # Etiqueta con nombre
        cv2.putText(debug_img, f"{name}", 
                   (rel_x, rel_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['captain'], 2)
        
        # Coordenadas de click
        cv2.putText(debug_img, f"Click: ({abs_x + 20}, {abs_y + 20})", 
                   (rel_x, rel_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, COLORS['text'], 1)
        
        # Confianza
        cv2.putText(debug_img, f"Conf: {conf:.3f}", 
                   (rel_x, rel_y + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['text'], 1)
    
    return debug_img

# ===================================================================
# MAIN
# ===================================================================

def main():
    print("="*70)
    print("🎯 TESTER DEBUG V3.0 - DETECCIÓN EN TIEMPO REAL")
    print("="*70)
    print("\nCONFIGURACIÓN:")
    print(f"  • Threshold: {DETECTION_CONFIG['threshold']}")
    print(f"  • Multi-scale: {'ON' if DETECTION_CONFIG['multi_scale'] else 'OFF'}")
    print(f"  • Scales: {DETECTION_CONFIG['min_scale']} - {DETECTION_CONFIG['max_scale']}")
    print(f"  • NMS Threshold: {DETECTION_CONFIG['nms_threshold']}px")
    print(f"\n  • Área de captura: {LOG_AREA}")
    print(f"\nCOLORES:")
    print(f"  🟢 VERDE = Heroes")
    print(f"  🔵 AZUL = Capitanes")
    print(f"  ⚪ Punto blanco = Coordenada exacta del click")
    print("\n⌨️  Presiona ESC para salir")
    print("="*70)
    
    # Inicializar template matcher
    matcher = SimpleTemplateMatcher()
    
    # Cargar templates
    heroes = matcher.load_templates_from_directory("heroes")
    captains = matcher.load_templates_from_directory("captains")
    
    if not heroes and not captains:
        print("\n❌ ERROR: No se cargaron templates")
        print("   Crea las carpetas:")
        print("   • assets/heroes/    (con archivos .jpg de heroes)")
        print("   • assets/captains/  (con archivos .jpg de capitanes)")
        input("\nPresiona ENTER para salir...")
        return
    
    print(f"\n✅ Templates cargados:")
    print(f"   • {len(heroes)} heroes")
    print(f"   • {len(captains)} capitanes")
    print("\n🎬 Iniciando captura en tiempo real...")
    print("   (Ventana aparecerá en 2 segundos)\n")
    
    time.sleep(2)
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Capturar pantalla
            log_screenshot = capture_log_area()
            
            # Detectar cards
            heroes_found, captains_found = detect_all_cards(
                log_screenshot, heroes, captains, matcher
            )
            
            # Dibujar overlay
            debug_img = draw_debug_overlay(log_screenshot, heroes_found, captains_found)
            
            # Redimensionar para mejor visualización
            display_img = cv2.resize(debug_img, (900, 700))
            
            # Mostrar
            cv2.imshow("🎯 DEBUG LIVE - ESC=Salir", display_img)
            
            # Procesar eventos (ESC para salir)
            key = cv2.waitKey(100)  # 100ms = ~10 FPS
            if key == 27:  # ESC
                print("\n🛑 ESC presionado, saliendo...")
                break
            
            # Log en consola cada 10 frames
            frame_count += 1
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"[Frame {frame_count:04d}] Heroes: {len(heroes_found):2d} | Captains: {len(captains_found):2d} | FPS: {fps:.1f}")
    
    except KeyboardInterrupt:
        print("\n🛑 Ctrl+C presionado, saliendo...")
    
    finally:
        cv2.destroyAllWindows()
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"📊 ESTADÍSTICAS:")
        print(f"  • Frames procesados: {frame_count}")
        print(f"  • Tiempo total: {elapsed:.1f}s")
        print(f"  • FPS promedio: {frame_count/elapsed:.1f}")
        print(f"{'='*70}")
        print("\n✅ Tester finalizado correctamente")

if __name__ == "__main__":
    main()
