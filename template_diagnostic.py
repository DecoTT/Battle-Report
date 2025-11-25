"""
🔍 TEMPLATE DIAGNOSTIC TOOL
===========================
Herramienta auxiliar para diagnosticar templates individuales

USO:
    python template_diagnostic.py [hero|captain] [nombre]
    
EJEMPLOS:
    python template_diagnostic.py hero gandalf
    python template_diagnostic.py captain aurora
    python template_diagnostic.py          # ← Analiza TODOS
"""

import cv2
import numpy as np
import mss
import sys
from pathlib import Path
from typing import Dict, Tuple

# Configuración
LOG_AREA = {
    'left': 490,
    'top': 441,
    'width': 444,
    'height': 380
}

THRESHOLDS_TO_TEST = [0.70, 0.75, 0.78, 0.80, 0.85, 0.90]

# ===================================================================
# FUNCIONES AUXILIARES
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

def load_template(category: str, name: str) -> Tuple[np.ndarray, Path]:
    """Carga un template específico"""
    template_path = Path("assets") / category / f"{name}.jpg"
    
    if not template_path.exists():
        return None, template_path
    
    template = cv2.imread(str(template_path))
    return template, template_path

def test_template_at_thresholds(screenshot: np.ndarray, template: np.ndarray, name: str):
    """Prueba un template con diferentes thresholds"""
    print(f"\n{'='*70}")
    print(f"🔍 Analizando: {name}")
    print(f"   Template size: {template.shape[1]}x{template.shape[0]}")
    print(f"{'='*70}")
    
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    max_conf = np.max(result)
    max_loc = np.unravel_index(np.argmax(result), result.shape)
    
    print(f"\n📊 MÁXIMA CONFIANZA: {max_conf:.4f}")
    print(f"   Posición: ({max_loc[1]}, {max_loc[0]})")
    
    print(f"\n📈 DETECCIONES POR THRESHOLD:")
    print(f"{'Threshold':<12} {'Matches':<10} {'Recomendación'}")
    print(f"{'-'*50}")
    
    for threshold in THRESHOLDS_TO_TEST:
        locations = np.where(result >= threshold)
        num_matches = len(locations[0])
        
        # Recomendación
        if num_matches == 0:
            rec = "❌ No detecta"
        elif num_matches == 1:
            rec = "✅ PERFECTO"
        elif num_matches <= 3:
            rec = "⚠️ Aceptable"
        else:
            rec = f"❌ Demasiados ({num_matches})"
        
        # Marcar el threshold actual de battle_report
        marker = " ← ACTUAL" if threshold == 0.78 else ""
        
        print(f"{threshold:<12.2f} {num_matches:<10} {rec}{marker}")
    
    # Recomendación final
    print(f"\n💡 RECOMENDACIÓN:")
    if max_conf >= 0.85:
        print(f"   ✅ Template EXCELENTE (conf={max_conf:.3f})")
    elif max_conf >= 0.78:
        print(f"   ✅ Template BUENO (conf={max_conf:.3f})")
    elif max_conf >= 0.70:
        print(f"   ⚠️ Template MARGINAL (conf={max_conf:.3f})")
        print(f"   → Considera recapturar con mejor calidad")
    else:
        print(f"   ❌ Template MALO (conf={max_conf:.3f})")
        print(f"   → DEBE recapturarse")
    
    return max_conf, max_loc, result

def visualize_best_match(screenshot: np.ndarray, template: np.ndarray, name: str, 
                         max_conf: float, max_loc: Tuple):
    """Muestra visualmente el mejor match"""
    vis = screenshot.copy()
    h, w = template.shape[:2]
    top_left = (max_loc[1], max_loc[0])
    bottom_right = (top_left[0] + w, top_left[1] + h)
    
    # Dibujar rectángulo
    color = (0, 255, 0) if max_conf >= 0.78 else (0, 165, 255)
    cv2.rectangle(vis, top_left, bottom_right, color, 3)
    
    # Punto central
    center = (top_left[0] + w//2, top_left[1] + h//2)
    cv2.circle(vis, center, 8, (255, 255, 255), -1)
    
    # Etiqueta
    label = f"{name} - {max_conf:.3f}"
    cv2.putText(vis, label, (top_left[0], top_left[1] - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Info general
    cv2.putText(vis, "ESC=Siguiente | Q=Quit", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Resize para visualización
    vis_resized = cv2.resize(vis, (900, 700))
    cv2.imshow(f"🔍 Template: {name}", vis_resized)
    
    key = cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    return key == ord('q')  # Return True si quiere salir

def analyze_all_templates(category: str = None):
    """Analiza todos los templates de una categoría"""
    categories = [category] if category else ['heroes', 'captains']
    
    print("="*70)
    print("🔍 ANALIZANDO TODOS LOS TEMPLATES")
    print("="*70)
    
    # Capturar pantalla UNA vez
    print("\n📸 Capturando pantalla...")
    screenshot = capture_log_area()
    print(f"   ✅ Capturado: {screenshot.shape}")
    
    all_results = []
    
    for cat in categories:
        templates_dir = Path("assets") / cat
        if not templates_dir.exists():
            print(f"\n⚠️ No existe: {templates_dir}")
            continue
        
        print(f"\n{'='*70}")
        print(f"📁 Categoría: {cat.upper()}")
        print(f"{'='*70}")
        
        for template_file in sorted(templates_dir.glob("*.jpg")):
            name = template_file.stem
            template = cv2.imread(str(template_file))
            
            if template is None:
                print(f"   ❌ Error leyendo: {name}")
                continue
            
            max_conf, max_loc, result = test_template_at_thresholds(
                screenshot, template, name
            )
            
            all_results.append({
                'name': name,
                'category': cat,
                'max_conf': max_conf,
                'status': '✅' if max_conf >= 0.78 else '⚠️' if max_conf >= 0.70 else '❌'
            })
            
            # Visualizar
            should_quit = visualize_best_match(
                screenshot, template, name, max_conf, max_loc
            )
            
            if should_quit:
                print("\n🛑 Análisis interrumpido por usuario")
                break
        
        if should_quit:
            break
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"{'Nombre':<20} {'Categoría':<12} {'Max Conf':<12} {'Estado'}")
    print(f"{'-'*70}")
    
    for res in sorted(all_results, key=lambda x: x['max_conf'], reverse=True):
        print(f"{res['name']:<20} {res['category']:<12} "
              f"{res['max_conf']:<12.3f} {res['status']}")
    
    # Estadísticas
    excellent = sum(1 for r in all_results if r['max_conf'] >= 0.85)
    good = sum(1 for r in all_results if 0.78 <= r['max_conf'] < 0.85)
    marginal = sum(1 for r in all_results if 0.70 <= r['max_conf'] < 0.78)
    bad = sum(1 for r in all_results if r['max_conf'] < 0.70)
    
    print(f"\n{'='*70}")
    print(f"✅ Excelentes (≥0.85): {excellent}")
    print(f"✅ Buenos (0.78-0.84): {good}")
    print(f"⚠️ Marginales (0.70-0.77): {marginal}")
    print(f"❌ Malos (<0.70): {bad}")
    print(f"{'='*70}")

def analyze_single_template(category: str, name: str):
    """Analiza un template específico"""
    print("="*70)
    print(f"🔍 ANÁLISIS DE TEMPLATE INDIVIDUAL")
    print("="*70)
    
    # Cargar template
    template, path = load_template(category, name)
    
    if template is None:
        print(f"\n❌ ERROR: No se encontró {path}")
        print(f"\nVerifica que exista:")
        print(f"   {path}")
        return
    
    print(f"\n✅ Template cargado: {name}")
    print(f"   Ruta: {path}")
    print(f"   Tamaño: {template.shape[1]}x{template.shape[0]}")
    
    # Capturar pantalla
    print(f"\n📸 Capturando pantalla...")
    screenshot = capture_log_area()
    print(f"   ✅ Capturado: {screenshot.shape}")
    
    # Analizar
    max_conf, max_loc, result = test_template_at_thresholds(
        screenshot, template, name
    )
    
    # Visualizar
    print(f"\n📺 Mostrando visualización...")
    print(f"   ESC = Continuar")
    visualize_best_match(screenshot, template, name, max_conf, max_loc)
    
    print(f"\n✅ Análisis completado")

# ===================================================================
# MAIN
# ===================================================================

def main():
    print("\n" + "="*70)
    print("🔍 TEMPLATE DIAGNOSTIC TOOL")
    print("="*70)
    
    if len(sys.argv) == 1:
        # Sin argumentos = analizar todos
        analyze_all_templates()
    
    elif len(sys.argv) == 2:
        # Solo categoría = analizar toda esa categoría
        category = sys.argv[1]
        if category not in ['hero', 'heroes', 'captain', 'captains']:
            print(f"\n❌ Categoría inválida: {category}")
            print(f"   Usa: hero/heroes o captain/captains")
            return
        
        # Normalizar nombre de categoría
        category = 'heroes' if category in ['hero', 'heroes'] else 'captains'
        analyze_all_templates(category)
    
    elif len(sys.argv) == 3:
        # Categoría + nombre = analizar uno específico
        category = sys.argv[1]
        name = sys.argv[2]
        
        if category not in ['hero', 'heroes', 'captain', 'captains']:
            print(f"\n❌ Categoría inválida: {category}")
            print(f"   Usa: hero/heroes o captain/captains")
            return
        
        # Normalizar nombre de categoría
        category = 'heroes' if category in ['hero', 'heroes'] else 'captains'
        analyze_single_template(category, name)
    
    else:
        print("\n❌ Demasiados argumentos")
        print("\nUSO:")
        print("   python template_diagnostic.py")
        print("   python template_diagnostic.py [hero|captain]")
        print("   python template_diagnostic.py [hero|captain] [nombre]")

if __name__ == "__main__":
    main()
