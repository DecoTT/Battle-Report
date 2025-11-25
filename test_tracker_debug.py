# ================================================
# test_tracker_debug.py
# PRUEBA 100% INDEPENDIENTE - 0 RIESGO
# ================================================
import cv2
import numpy as np
import mss
import pyautogui
import time
from pathlib import Path
from dataclasses import dataclass

# === TU NUEVO TRACKER (COPIA-PEGA) ===
@dataclass
class SeenCard:
    gametag: str | None
    hero_name: str
    last_seen: float
    y_center: int
    processed: bool = False

class PerfectCardTracker:
    def __init__(self):
        self.seen: dict[str, SeenCard] = {}
        self.gametags: set[str] = set()
        self.max_y_processed = 0
        self.min_y_seen = 99999

    def _key(self, hero_name: str) -> str:
        return hero_name.lower().strip()

    def add_detection(self, hero_name: str, y_center: int):
        key = self._key(hero_name)
        now = time.time()
        self.min_y_seen = min(self.min_y_seen, y_center)
        if key not in self.seen:
            self.seen[key] = SeenCard(None, hero_name, now, y_center)
        else:
            self.seen[key].last_seen = now
            self.seen[key].y_center = y_center

    def should_click(self, hero_name: str, y_center: int) -> bool:
        key = self._key(hero_name)
        card = self.seen.get(key)
        if card and card.gametag and card.gametag in self.gametags:
            return False
        if card and card.processed and y_center < self.max_y_processed + 180:
            return False
        return True

    def mark_processed(self, hero_name: str, y_center: int, gametag: str | None):
        key = self._key(hero_name)
        if key not in self.seen:
            self.add_detection(hero_name, y_center)
        self.seen[key].processed = True
        self.seen[key].gametag = gametag
        self.max_y_processed = max(self.max_y_processed, y_center)
        if gametag:
            self.gametags.add(gametag)

    def needs_scroll(self) -> bool:
        return self.max_y_processed > self.min_y_seen + 250
# ================================================

# CONFIGURACIÓN DE TU JUEGO
LOG_AREA = {'left': 490, 'top': 441, 'width': 444, 'height': 380}
HERO_TEMPLATES = {}  # Se cargan automáticamente

# Cargar héroes (solo los .jpg en assets/heroes)
def load_heroes():
    path = Path("assets/heroes")
    if not path.exists():
        print("Crea la carpeta assets/heroes y mete imágenes de héroes")
        return {}
    heroes = {}
    for f in path.glob("*.jpg"):
        img = cv2.imread(str(f))
        if img is not None:
            heroes[f.stem] = img
            print(f"Héroe cargado: {f.stem}")
    return heroes

# Capturar pantalla
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

# Detectar héroes
def detect_heroes(screen, templates):
    found = []
    for name, tmpl in templates.items():
        res = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.8)
        for pt in zip(*loc[::-1]):
            found.append((name, pt))
    # Eliminar duplicados cercanos
    keep = []
    for name, pt in found:
        if not any(np.linalg.norm(np.array(pt) - np.array(k[1])) < 40 for k in keep):
            keep.append((name, pt))
    return keep

# Simular OCR (en prueba real usarás tu capture_gametag)
def fake_ocr():
    names = ["ViadmirPoostain", "xXDragonXx", "Lulu123", "ElTMinettes"]
    return names[int(time.time()) % len(names)]

# === MODO DEBUG VISUAL ===
def draw_debug(screen, detections, tracker):
    debug = screen.copy()
    for name, (x, y) in detections:
        center_y = LOG_AREA['top'] + y + 60
        color = (0, 255, 0) if tracker.should_click(name, center_y) else (0, 0, 255)
        cv2.rectangle(debug, (x, y), (x+100, y+120), color, 3)
        cv2.putText(debug, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(debug, f"Y:{center_y}", (x, y+135), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
    cv2.imshow("DEBUG - VERDE=CLICKEAR ROJO=SKIP", cv2.resize(debug, (800, 600)))
    cv2.waitKey(1)

# === PRUEBA EN VIVO ===
def main():
    print("TEST TRACKER - Presiona ESC en la ventana para salir")
    global HERO_TEMPLATES
    HERO_TEMPLATES = load_heroes()
    if not HERO_TEMPLATES:
        print("SIN HÉROES → Modo simulación")
        HERO_TEMPLATES = {"sim_hero": np.zeros((100,100,3), dtype=np.uint8)}

    tracker = PerfectCardTracker()
    screen_count = 0

    try:
        while True:
            screen = grab_log()
            heroes = detect_heroes(screen, HERO_TEMPLATES)
            print(f"\nPantalla {screen_count} → {len(heroes)} héroes")

            processed = 0
            for name, (x, y) in heroes:
                cy = LOG_AREA['top'] + y + 60
                tracker.add_detection(name, cy)

                if tracker.should_click(name, cy):
                    print(f"CLICKEAR {name} @ Y={cy}")
                    # SIMULACIÓN DE CLIC (descomenta para probar real)
                    # pyautogui.click(LOG_AREA['left'] + x + 55, LOG_AREA['top'] + y + 60)
                    gametag = fake_ocr()
                    tracker.mark_processed(name, cy, gametag)
                    print(f"CAPTURADO: {gametag}")
                    processed += 1
                    time.sleep(2)
                else:
                    print(f"SKIP {name} (ya visto)")

            draw_debug(screen, heroes, tracker)

            # SCROLL INTELIGENTE
            if tracker.needs_scroll() and processed > 0:
                pyautogui.scroll(-6)
                print("SCROLL ↓↓↓ avanzando...")
            else:
                pyautogui.scroll(-2)
                print("scroll suave")
            time.sleep(1.5)
            screen_count += 1

    except KeyboardInterrupt:
        print("\nPRUEBA FINALIZADA - Todo OK!")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()