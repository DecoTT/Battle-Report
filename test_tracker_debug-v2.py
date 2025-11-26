# ================================================
# test_tracker_debug.py - V2.0 FIJADO
# ================================================
import cv2
import numpy as np
import mss
import pyautogui
import time
from pathlib import Path
from dataclasses import dataclass
import keyboard  # pip install keyboard

@dataclass
class SeenCard:
    gametag: str | None
    hero_name: str
    last_seen: float
    y_center: int
    processed: bool = False


class PerfectCardTracker:
    """Persiste por combinación héroe+gametag para evitar falsos 'procesado'."""

    UNKNOWN = None

    def __init__(self):
        # Llave: (hero_key, gametag_key)
        self.seen: dict[tuple[str, str | None], SeenCard] = {}
        self.gametags: set[str] = set()
        self.max_y_processed = 0
        self.min_y_seen = 99999

    def _hero_key(self, hero_name: str) -> str:
        return hero_name.lower().strip()

    def _key(self, hero_name: str, gametag: str | None) -> tuple[str, str | None]:
        return (self._hero_key(hero_name), gametag.lower().strip() if gametag else self.UNKNOWN)

    def should_click(self, hero_name: str, y_center: int) -> bool:
        hero_key = self._hero_key(hero_name)
        for (stored_hero, _), card in self.seen.items():
            if stored_hero != hero_key:
                continue
            if card.gametag and card.gametag.lower() in self.gametags:
                return False
            if card.processed and y_center < self.max_y_processed + 180:
                return False
        return True

    def add_detection(self, hero_name: str, y_center: int):  # ← MOVIDO AQUÍ
        key = self._key(hero_name, None)
        now = time.time()
        self.min_y_seen = min(self.min_y_seen, y_center)
        card = self.seen.get(key)
        if not card:
            self.seen[key] = SeenCard(None, hero_name, now, y_center)
        else:
            card.last_seen = now
            card.y_center = y_center

    def mark_processed(self, hero_name: str, y_center: int, gametag: str | None):
        # Registrar detección desconocida y luego consolidar con gametag real
        self.add_detection(hero_name, y_center)  # ← SIEMPRE registrar
        hero_key = self._hero_key(hero_name)
        normalized_tag = gametag.strip() if gametag else None

        # Fusionar la entrada UNKNOWN con la real
        unknown_key = (hero_key, self.UNKNOWN)
        unknown_card = self.seen.pop(unknown_key, None)

        key = self._key(hero_name, normalized_tag)
        card = self.seen.get(key)
        if not card:
            base = unknown_card or SeenCard(None, hero_name, time.time(), y_center)
            card = SeenCard(normalized_tag, base.hero_name, time.time(), y_center, True)
            self.seen[key] = card
        else:
            card.gametag = normalized_tag
            card.last_seen = time.time()
            card.y_center = y_center
            card.processed = True

        self.max_y_processed = max(self.max_y_processed, y_center)
        if normalized_tag:
            self.gametags.add(normalized_tag.lower())

    def needs_scroll(self) -> bool:
        return self.max_y_processed > self.min_y_seen + 250

# CONFIGURACIÓN FIJADA
LOG_AREA = {'left': 490, 'top': 441, 'width': 444, 'height': 380}
HERO_TEMPLATES = {}

def load_heroes():
    path = Path("assets/heroes")
    if not path.exists():
        print("❌ Crea assets/heroes/ con .jpg de héroes")
        return {}
    heroes = {}
    for f in path.glob("*.jpg"):
        img = cv2.imread(str(f))
        if img is not None:
            heroes[f.stem] = img
            print(f"✅ {f.stem}")
    return heroes

def grab_log():
    with mss.mss() as sct:
        region = {
            'left': LOG_AREA['left'],
            'top': LOG_AREA['top'],
            'width': LOG_AREA['width'],
            'height': LOG_AREA['height']
        }
        img = np.array(sct.grab(region))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def detect_heroes(screen, templates):
    found = []
    for name, tmpl in templates.items():
        res = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.78)  # ← BAJADO threshold
        for pt in zip(*loc[::-1]):
            found.append((name, pt))
    
    # NMS mejorado
    keep = []
    for name, pt in found:
        too_close = False
        for k_name, k_pt in keep:
            dist = np.linalg.norm(np.array(pt) - np.array(k_pt))
            if dist < 45:
                too_close = True
                break
        if not too_close:
            keep.append((name, pt))
    return keep

def fake_ocr():
    names = ["ViadmirPoostain", "xXDragonXx", "Lulu123", "ElTMinettes", "ProGamerMX"]
    return names[int(time.time() * 10) % len(names)]

# === DEBUG VISUAL MEJORADO ===
def draw_debug(screen, detections, tracker):
    debug = screen.copy()
    for i, (name, (x, y)) in enumerate(detections):
        screen_x = LOG_AREA['left'] + x + 25  # ← FIX: +25px para centro
        screen_y = LOG_AREA['top'] + y + 25   # ← FIX: +25px para centro
        cy = screen_y
        
        if tracker.should_click(name, cy):
            color = (0, 255, 0)  # VERDE = CLICKEAR
            status = "🟢 CLICK"
        else:
            color = (0, 0, 255)  # ROJO = SKIP
            status = "🔴 SKIP"
        
        # Rectángulo FIJADO al centro de la card
        cv2.rectangle(debug, (x, y), (x+90, y+110), color, 3)
        cv2.circle(debug, (x+25, y+25), 8, (255,255,255), -1)  # ← PUNTO CLICK
        
        cv2.putText(debug, f"{name} {status}", (x, y-5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        cv2.putText(debug, f"Y:{cy} CLICK:({screen_x},{screen_y})", 
                   (x, y+125), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1)
    
    cv2.imshow("🎯 DEBUG - VERDE=CLICK ROJO=SKIP | ESC=salir", cv2.resize(debug, (900, 700)))
    return cv2.waitKey(1) != 27  # ESC = 27

# === MAIN MEJORADO ===
def main():
    print("🔥 TEST TRACKER V2.0 - FIJADO!")
    print("🟢 VERDE = CLICK | 🔴 ROJO = SKIP | ESC = SALIR")
    
    global HERO_TEMPLATES
    HERO_TEMPLATES = load_heroes()
    if not HERO_TEMPLATES:
        print("⚠️ SIN HÉROES - Modo demo")
        time.sleep(3)
    
    tracker = PerfectCardTracker()
    screen_count = 0
    esc_pressed = False

    # Listener ESC
    def on_esc():
        nonlocal esc_pressed
        esc_pressed = True
        print("\n🛑 ESC detectado!")
    
    keyboard.on_press_key('esc', lambda _: on_esc())

    try:
        while not esc_pressed:
            screen = grab_log()
            heroes = detect_heroes(screen, HERO_TEMPLATES)
            
            print(f"\n{'='*50}")
            print(f"📺 Pantalla {screen_count} → {len(heroes)} héroes")
            
            processed = 0
            for name, (x, y) in heroes:
                screen_x = LOG_AREA['left'] + x + 25  # ← FIX CENTRO
                screen_y = LOG_AREA['top'] + y + 25   # ← FIX CENTRO
                cy = screen_y
                
                # === CAMBIO CLAVE: should_click ANTES de add_detection ===
                if tracker.should_click(name, cy):
                    print(f"🟢 CLICKEAR {name} @ ({screen_x},{screen_y})")
                    
                    # REAL CLICK (descomenta para probar)
                    # pyautogui.click(screen_x, screen_y, duration=0.1)
                    
                    gametag = fake_ocr()
                    tracker.mark_processed(name, cy, gametag)
                    print(f"   ✅ CAPTURADO: {gametag}")
                    processed += 1
                    time.sleep(1.5)  # Simular tiempo real
                else:
                    print(f"🔴 SKIP {name} @ Y={cy}")
                
                tracker.add_detection(name, cy)  # ← AHORA registrar

            # === DEBUG VISUAL ===
            if not draw_debug(screen, heroes, tracker):
                esc_pressed = True

            # === SCROLL AGRESIVO ===
            if tracker.needs_scroll() or processed > 0:
                pyautogui.scroll(-15)  # ← FIX: -15 AGRESIVO
                scroll_type = "↓↓↓ AGRESIVO"
            else:
                pyautogui.scroll(-8)   # ← FIX: -8 mínimo
                scroll_type = "↓ suave"
            print(f"🖱️ {scroll_type}")
            
            time.sleep(0.8)  # ← Más rápido
            screen_count += 1
            
            if screen_count > 200:
                print("🔄 Límite alcanzado")
                break

    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n🎉 PRUEBA FINALIZADA!")
        print(f"📊 {len(tracker.gametags)} únicos | {screen_count} pantallas")
        cv2.destroyAllWindows()
        keyboard.unhook_all()

if __name__ == "__main__":
    main()