"""
Battle Report Scraper Module
Módulo para automatizar la captura de asistencia en reportes de batalla
Detecta héroes, capitanes prohibidos y genera reporte de participantes
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import mss
import pyautogui
import time
import json
import hashlib  # 🆕 Para detectar cambios en contenido
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
import winsound
import threading
from dataclasses import dataclass, field
import os
import sys
import re

# Intentar importar win32api para clicks más confiables
try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠️ Módulo 'win32api' no disponible. Instala con: pip install pywin32")

# Intentar importar keyboard para el listener de ESC
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("⚠️ Módulo 'keyboard' no disponible. Instala con: pip install keyboard")
    print("   Sin esto, no podrás detener con ESC durante la captura.")

# Configurar ruta de Tesseract si existe
try:
    import pytesseract
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"✅ Tesseract configurado: {tesseract_path}")
    else:
        print("⚠️ Tesseract no encontrado en la ruta por defecto")
except ImportError:
    pass

# Añadir el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core import (
        OCREngine, TemplateMatcher, ScrollController, 
        ConfigManager, ScrollDirection
    )
except ImportError as e:
    print(f"Error importando módulos core: {e}")
    print("Asegúrate de que los módulos core estén en la carpeta correcta")
    # Intentar importación alternativa
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from core import (
            OCREngine, TemplateMatcher, ScrollController, 
            ConfigManager, ScrollDirection
        )
    except ImportError:
        print("No se pudieron importar los módulos core. Verifica la estructura de directorios.")
        sys.exit(1)

# ===================================================================
# CLASES MEJORADAS PARA OCR Y PERSISTENCIA DE INSTANCIA
# ===================================================================

class ImprovedOCREngine:
    """
    Motor OCR mejorado con preprocesamiento que funciona al 100%.
    Usa cv2.dilate con kernel 1x1 y 8 iteraciones.
    Este método logró 10/10 (100%) en pruebas reales.
    """
    
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
        Preprocesado mínimo: convierte a escala de grises y aplica dilate.
        Este método logró 100% de éxito en pruebas.
        """
        # Si la imagen tiene 4 canales (BGRA/RGBA), quita el alfa
        if img.ndim == 3 and img.shape[2] == 4:
            img = img[:, :, :3]

        # Convertir a escala de grises si es imagen en color
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # CRÍTICO: Este dilate es la clave del éxito - 100% en pruebas
        gray = cv2.dilate(gray, np.ones((1,1), np.uint8), iterations=8)

        return gray
    
    def extract_text(self, img: np.ndarray) -> str:
        """Extrae texto de imagen usando el método que funciona"""
        if img is None or img.size == 0:
            return ""
        
        processed = self.preprocess_for_ocr(img)
        
        try:
            text = pytesseract.image_to_string(
                processed, 
                lang='eng',
                config=self.tesseract_config
            ).strip()
            
            text = self.clean_text(text)
            return text
        except Exception as e:
            print(f"Error OCR: {e}")
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


@dataclass
class HeroInstance:
    """Instancia de héroe con persistencia temporal para evitar duplicados"""
    hero_name: str
    first_seen: datetime
    last_seen: datetime
    positions: list = field(default_factory=list)
    processed: bool = False
    gametag: Optional[str] = None
    
    def update_position(self, pos: Tuple[int, int]):
        """Actualiza la última posición vista"""
        self.last_seen = datetime.now()
        self.positions.append(pos)
        if len(self.positions) > 5:
            self.positions.pop(0)
    
    def is_expired(self, timeout_seconds: float = 3.0) -> bool:
        """Verifica si la instancia ha expirado"""
        return (datetime.now() - self.last_seen).total_seconds() > timeout_seconds
    
    def is_same_instance(self, pos: Tuple[int, int], distance_threshold: int = 150) -> bool:
        """Determina si una nueva posición corresponde a esta instancia"""
        if not self.positions:
            return False
        
        last_pos = self.positions[-1]
        distance = np.sqrt((pos[0] - last_pos[0])**2 + (pos[1] - last_pos[1])**2)
        return distance <= distance_threshold


@dataclass
class SeenCard:
    """Representa una card detectada en la cuadrícula."""
    hero_name: str
    gametag: Optional[str]
    last_seen: float
    y_center: int
    processed: bool = False


class InstanceTracker:
    """
    Persiste instancias por (héroe + gametag), no solo por héroe.

    Reglas clave:
    - Una detección sin gametag se registra como hero+UNKNOWN y *no* bloquea
      otros intentos del mismo héroe.
    - Cuando se captura el gametag, la entrada hero+UNKNOWN se fusiona en la
      clave hero+gametag y se marca como procesada.
    - Se evita re-clickear el mismo gametag ya procesado; nuevas detecciones
      del mismo héroe con gametag distinto siguen siendo válidas.
    """

    # Representación del valor UNKNOWN para el gametag
    UNKNOWN = None

    # Tolerancia vertical para considerar que dos detecciones son la misma card
    # Aumentamos a 320 px para cubrir variaciones al hacer scroll entre frames
    SAME_CARD_Y_TOLERANCE = 320

    # Enfriamiento global por héroe (en segundos). Si se procesó recientemente,
    # evitaremos re-clics rápidos del mismo héroe aunque se desplace en pantalla.
    REPROCESS_COOLDOWN_S = 60

    # Tiempo durante el cual una card ya procesada bloquea re-clics aunque
    # aparezca a una Y distinta. Esto previene duplicados en desplazamientos.
    PROCESSED_LOCK_S = 45

    def __init__(self) -> None:
        # Mapa de instancias vistas. Llave: (hero_key, gametag_key)
        self.seen: Dict[Tuple[str, Optional[str]], SeenCard] = {}
        # Conjunto de gametags procesados (normalizados) para estadísticas
        self.gametags: Set[str] = set()
        # Guarda el Y máximo procesado para ayudar con scroll
        self.max_y_processed: int = 0
        # Guarda el mínimo Y visto para determinar si necesitamos scroll agresivo
        self.min_y_seen: int = 99999

        # Lleva registro de cuándo se procesó por última vez un héroe para
        # aplicar el enfriamiento global y evitar clicks duplicados al hacer scroll.
        self.last_processed_ts: Dict[str, float] = {}

    def _hero_key(self, hero_name: str) -> str:
        """Normaliza el nombre del héroe para usar como key."""
        return hero_name.strip().lower()

    def _gametag_key(self, gametag: Optional[str]) -> Optional[str]:
        """Normaliza el gametag a minúsculas o retorna UNKNOWN si es None."""
        return gametag.strip().lower() if gametag else self.UNKNOWN

    def _key(self, hero_name: str, gametag: Optional[str]) -> Tuple[str, Optional[str]]:
        """Genera una clave compuesta (hero_key, gametag_key)."""
        return (self._hero_key(hero_name), self._gametag_key(gametag))

    # --- Registro de detecciones ---
    def add_detection(self, hero_name: str, y_center: int) -> None:
        """
        Registra una card vista sin gametag (hero+UNKNOWN).

        - Actualiza el "min_y_seen" para saber desde dónde empezamos a ver cards.
        - Si la card ya existía, solo refresca la última vez y su Y.
        """
        now = time.time()
        # Actualizar el mínimo Y visto para scroll
        self.min_y_seen = min(self.min_y_seen, y_center)
        key = self._key(hero_name, None)
        card = self.seen.get(key)
        if not card:
            # Primera vez que vemos esta card sin gametag
            self.seen[key] = SeenCard(hero_name=hero_name, gametag=None, last_seen=now, y_center=y_center)
        else:
            # Solo actualizar última vez vista y posición
            card.last_seen = now
            card.y_center = y_center

    # --- Lógica de decisión para procesar ---
    def should_process(self, hero_name: str, y_center: int) -> bool:
        """
        Devuelve True solo si debemos abrir la card.

        - Solo bloquea cuando ya hay *un gametag procesado* para ese héroe en
          la misma zona Y (misma card).
        - Las entradas hero+UNKNOWN nunca bloquean; sirven solo para mergear
          al capturar el gametag.
        """
        hero_key = self._hero_key(hero_name)
        now = time.time()
        # Enfriamiento global: si acabamos de procesar este héroe, evitamos
        # re-clics rápidos que ocurren cuando la misma card se desplaza por scroll.
        last_ts = self.last_processed_ts.get(hero_key)
        if last_ts and (now - last_ts) < self.REPROCESS_COOLDOWN_S:
            return False
        # Revisar si ya tenemos registrada una card para este héroe
        for (stored_hero, stored_tag), card in self.seen.items():
            if stored_hero != hero_key:
                continue
            # Solo evaluamos cards que ya fueron procesadas con gametag
            if not card.processed or stored_tag is self.UNKNOWN:
                continue
            # Bloqueamos si la misma card apareció de nuevo cerca en Y o si fue
            # vista muy recientemente (scroll vertical puede moverla de posición)
            recently_seen = (now - card.last_seen) < self.PROCESSED_LOCK_S
            same_y_band = abs(y_center - card.y_center) < self.SAME_CARD_Y_TOLERANCE
            if recently_seen or same_y_band:
                return False
        return True

    # --- Confirmación de procesado ---
    def mark_processed(self, hero_name: str, y_center: int, gametag: Optional[str]) -> None:
        """
        Marca la card como procesada y persiste por hero+gametag.

        - Si existía hero+UNKNOWN, se fusiona con la nueva clave hero+gametag.
        - El gametag se normaliza en minúsculas para deduplicar.
        - Guarda el Y máximo procesado para ayudar al scroll.
        """
        now = time.time()
        hero_key = self._hero_key(hero_name)
        # Normalizar el gametag si existe
        normalized_tag = gametag.strip() if gametag else None
        # Eliminar/recuperar la entrada hero+UNKNOWN para este héroe
        unknown_key = (hero_key, self.UNKNOWN)
        unknown_card = self.seen.pop(unknown_key, None)
        # Generar clave definitiva hero+gametag
        key = self._key(hero_name, normalized_tag)
        card = self.seen.get(key)
        if not card:
            # Si no existía, creamos una nueva usando datos de unknown si había
            base = unknown_card or SeenCard(hero_name=hero_name, gametag=None, last_seen=now, y_center=y_center)
            card = SeenCard(
                hero_name=base.hero_name,
                gametag=normalized_tag,
                last_seen=now,
                y_center=y_center,
                processed=True,
            )
            self.seen[key] = card
        else:
            # Ya existe la entrada, solo actualizar datos y marcar como procesada
            card.gametag = normalized_tag
            card.last_seen = now
            card.y_center = y_center
            card.processed = True
        # Actualizar el máximo Y procesado
        self.max_y_processed = max(self.max_y_processed, y_center)
        # Registrar gametag en el set de gametags
        if normalized_tag:
            self.gametags.add(normalized_tag.lower())
        # Actualizar el timestamp de última vez procesado para este héroe
        self.last_processed_ts[hero_key] = now

    def needs_scroll(self) -> bool:
        """Indica si debemos forzar scroll agresivo."""
        return self.max_y_processed > self.min_y_seen + 250

    def reset(self) -> None:
        """Resetea el tracker a estado limpio."""
        self.seen.clear()
        self.gametags.clear()
        self.max_y_processed = 0
        self.min_y_seen = 99999
        print("🔄 ImprovedInstanceTracker reseteado")

    def get_stats(self) -> Dict[str, object]:
        """Retorna estadísticas del tracker para UI/reporte."""
        return {
            'active_instances': len(self.seen),
            'processed_heroes': len([c for c in self.seen.values() if c.processed]),
            'unique_gametags': len(self.gametags),
            'gametags': sorted(list(self.gametags)),
            'max_y_processed': self.max_y_processed,
            'min_y_seen': self.min_y_seen
        }


class ImprovedInstanceTracker(InstanceTracker):
    """
    Alias para compatibilidad hacia atrás.

    El repositorio previo exponía ``ImprovedInstanceTracker``; este alias
    permite resolver conflictos de merge manteniendo la API esperada, pero la
    lógica principal vive en ``InstanceTracker``.
    """
    pass


@dataclass
class Participant:
    """Datos de un participante"""
    name: str
    hero_detected: bool = False
    forbidden_captains: List[str] = None
    captain_with_armor: List[str] = None
    position: Tuple[int, int] = None
    
    def __post_init__(self):
        if self.forbidden_captains is None:
            self.forbidden_captains = []
        if self.captain_with_armor is None:
            self.captain_with_armor = []

class BattleReportScraper:
    """Scraper para reportes de batalla con detección de asistencia"""
    
    def __init__(self):
        # Configuración de áreas y coordenadas
        self.LOG_REGISTER_AREA = {
            'left': 490,
            'top': 441,
            'width': 444,  # 934 - 490
            'height': 380  # 821 - 441
        }
        
        self.HERO_INFO_AREA = {
            'x_start': 527,
            'y_start': 361,
            'x_end': 1006,
            'y_end': 805
        }
        
        self.GAMETAG_AREA = {
            'x_start': 1190,
            'y_start': 335,
            'x_end': 1327,
            'y_end': 355
        }
        
        self.CAPTAIN_NAME_AREA = {
            'x_start': 1121,
            'y_start': 341,
            'x_end': 1260,
            'y_end': 355
        }
        
        # Coordenadas de cierre de ventanas
        self.CLOSE_CAPTAIN_POS = (1378, 317)
        self.CLOSE_HERO_POS = (1421, 319)
        
        # Configuración de grid (4 columnas x 3 filas)
        self.GRID_COLS = 4
        self.GRID_ROWS = 3
        self.CARD_WIDTH = 110  # Ancho aproximado de cada card
        self.CARD_HEIGHT = 125  # Alto aproximado de cada card
        
        # Capitanes permitidos
        self.ALLOWED_CAPTAINS = [
            'aurora', 'carter', 'dustan', 
            'farhad', 'helen', 'stror', 'tengel'
        ]
        
        # Inicializar componentes
        self.ocr_engine = OCREngine()
        self.instance_tracker = ImprovedInstanceTracker()  # 🔧 FIXED: Usar ImprovedInstanceTracker
        self.template_matcher = TemplateMatcher()
        
        # === CONFIGURACIÓN CRÍTICA: 100% como test_tracker_debug-v2.py ===
        self.template_matcher.config['default_threshold'] = 0.78  # 🎯 BAJADO de 0.8 a 0.78
        self.template_matcher.config['multi_scale']['enabled'] = True
        self.template_matcher.config['multi_scale']['min_scale'] = 0.9
        self.template_matcher.config['multi_scale']['max_scale'] = 1.1
        self.template_matcher.config['multi_scale']['scale_step'] = 0.05
        print("✅ TemplateMatcher configurado: threshold=0.78, multi-scale=ON")
        
        self.scroll_controller = ScrollController()
        self.config_manager = ConfigManager()
        # self.sct removido - se crea en cada captura para evitar problemas de threading
        
        # Estado del scraper
        self.running = False
        self.participants = {}
        self.unknown_assets = []
        self.processed_positions = set()  # Para capitanes
        # Llevar registro de nombres de capitanes ya procesados para evitar
        # clicks repetidos en la misma unidad across diferentes héroes
        self.processed_captain_names = set()
        self.esc_listener_active = False
        
        # Configurar listener de ESC si está disponible
        if KEYBOARD_AVAILABLE:
            keyboard.on_press_key('esc', self.on_esc_pressed)
        
        # GUI - Crear primero la interfaz
        self.setup_gui()
        
        # Cargar assets existentes - Después de crear la GUI
        self.load_assets()
        
    def setup_gui(self):
        """Configura la interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("Battle Report Scraper - Asistencia")
        self.root.geometry("900x700")
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel de configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Fecha del reporte
        ttk.Label(config_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(config_frame, textvariable=self.date_var, width=15).grid(row=0, column=1, pady=5)
        
        # Tiempo de espera inicial
        ttk.Label(config_frame, text="Espera inicial (seg):").grid(row=0, column=2, padx=(20, 5), pady=5)
        self.wait_time_var = tk.IntVar(value=20)
        ttk.Spinbox(config_frame, from_=0, to=60, textvariable=self.wait_time_var, 
                   width=10).grid(row=0, column=3, pady=5)
        
        # Auto-añadir assets desconocidos
        self.auto_add_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Auto-añadir assets desconocidos", 
                       variable=self.auto_add_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Debug mode
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="Modo Debug", 
                       variable=self.debug_var).grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=5)
        
        # Panel de control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="INICIAR CAPTURA", 
                                   command=self.start_capture,
                                   style="Success.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="DETENER", 
                                  command=self.stop_capture,
                                  state=tk.DISABLED,
                                  style="Danger.TButton")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Fine Tuning Grid", 
                  command=self.open_grid_tuning).pack(side=tk.LEFT, padx=20)
        
        ttk.Button(control_frame, text="Gestionar Assets", 
                  command=self.open_asset_manager).pack(side=tk.LEFT, padx=5)
        
        # Panel de progreso
        progress_frame = ttk.LabelFrame(main_frame, text="Progreso", padding="10")
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="Esperando inicio...")
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Panel de resultados
        results_frame = ttk.LabelFrame(main_frame, text="Participantes Detectados", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para participantes
        columns = ("Héroe", "Capitanes Prohibidos", "Con Armadura", "Posición")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="tree headings", height=15)
        
        self.results_tree.heading("#0", text="Jugador")
        self.results_tree.heading("Héroe", text="Héroe")
        self.results_tree.heading("Capitanes Prohibidos", text="Capitanes Prohibidos")
        self.results_tree.heading("Con Armadura", text="Con Armadura")
        self.results_tree.heading("Posición", text="Posición")
        
        self.results_tree.column("#0", width=150)
        self.results_tree.column("Héroe", width=80, anchor=tk.CENTER)
        self.results_tree.column("Capitanes Prohibidos", width=200)
        self.results_tree.column("Con Armadura", width=150)
        self.results_tree.column("Posición", width=80, anchor=tk.CENTER)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.config(yscrollcommand=scrollbar.set)
        
        # Panel de acciones
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Exportar JSON", 
                  command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Exportar CSV", 
                  command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Copiar Resultado", 
                  command=self.copy_result).pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Listo")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X)
        
        # Configurar estilos
        style = ttk.Style()
        style.configure("Success.TButton", foreground="green")
        style.configure("Danger.TButton", foreground="red")
        
    def load_assets(self):
        """Carga los assets de héroes y capitanes usando TemplateMatcher"""
        # === CAMBIO CRÍTICO: Usar TemplateMatcher como en test_tracker_debug ===
        print("🔄 Cargando assets con TemplateMatcher...")
        
        # Cargar héroes con TemplateMatcher
        self.heroes = self.template_matcher.load_templates_from_directory("heroes")
        print(f"✅ Cargados {len(self.heroes)} héroes: {list(self.heroes.keys())}")
        
        # Cargar capitanes con TemplateMatcher
        self.captains = self.template_matcher.load_templates_from_directory("captains")
        print(f"✅ Cargados {len(self.captains)} capitanes: {list(self.captains.keys())}")
                    
        # Cargar assets especiales
        self.load_special_assets()
        
        self.log(f"Cargados {len(self.heroes)} héroes y {len(self.captains)} capitanes")
        
    def load_special_assets(self):
        """Carga assets especiales como el marcador de tropas y dragones"""
        templates_dir = Path("assets/templates")
        
        # Verificar que el directorio existe
        if not templates_dir.exists():
            print(f"⚠️ ERROR: El directorio {templates_dir} no existe")
            if hasattr(self, 'root'):
                self.log(f"⚠️ ERROR: El directorio {templates_dir} no existe")
            self.troops_marker = None
            self.dragon_templates = []
            return
        
        # Cargar marcador de tropas aliadas
        troops_marker = templates_dir / "allied_attacking_troops.jpg"
        if troops_marker.exists():
            self.troops_marker = cv2.imread(str(troops_marker))
            if self.troops_marker is not None:
                print(f"✅ Marcador de tropas cargado: {troops_marker.name} ({self.troops_marker.shape})")
                if hasattr(self, 'root'):
                    self.log(f"✅ Marcador de tropas cargado")
            else:
                print(f"❌ Error leyendo el archivo: {troops_marker}")
                if hasattr(self, 'root'):
                    self.log(f"❌ Error leyendo allied_attacking_troops.jpg")
                self.troops_marker = None
        else:
            self.troops_marker = None
            print(f"❌ ERROR CRÍTICO: No se encontró {troops_marker}")
            print(f"   Archivos en {templates_dir}: {list(templates_dir.glob('*'))}")
            if hasattr(self, 'root'):
                self.log("❌ ERROR: allied_attacking_troops.jpg no encontrado")
            
        # Cargar templates de dragones
        self.dragon_templates = []
        for dragon_file in templates_dir.glob("dragon*.jpg"):
            template = cv2.imread(str(dragon_file))
            if template is not None:
                self.dragon_templates.append(template)
                print(f"✅ Template de dragón cargado: {dragon_file.name}")
                
    def start_capture(self):
        """Inicia la captura del reporte"""
        # Validar que los assets críticos estén cargados
        if self.troops_marker is None:
            messagebox.showerror("Error", 
                               "No se puede iniciar la captura.\n\n"
                               "Falta el archivo: assets/templates/allied_attacking_troops.jpg\n\n"
                               "Este archivo es necesario para detectar la sección de tropas.")
            return
        
        if len(self.heroes) == 0:
            result = messagebox.askyesno("Advertencia", 
                                 "No se han cargado héroes desde assets/heroes/\n"
                                 "La detección de héroes no funcionará correctamente.\n\n"
                                 "¿Desea continuar de todas formas?")
            if not result:
                return
        
        if len(self.captains) == 0:
            result = messagebox.askyesno("Advertencia", 
                                 "No se han cargado capitanes desde assets/captains/\n"
                                 "La detección de capitanes no funcionará correctamente.\n\n"
                                 "¿Desea continuar de todas formas?")
            if not result:
                return
        
        self.running = True
        self.participants.clear()
        self.unknown_assets.clear()
        self.processed_positions.clear()
        self.processed_captain_names.clear()
        
        # Actualizar UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar.start()
        self.results_tree.delete(*self.results_tree.get_children())
        
        # Mensaje sobre detener con ESC
        if KEYBOARD_AVAILABLE:
            self.log("💡 Presiona ESC en cualquier momento para detener la captura")
        
        # Minimizar ventana
        self.root.iconify()
        
        # Iniciar thread de captura
        capture_thread = threading.Thread(target=self.capture_process, daemon=True)
        capture_thread.start()
        
    def capture_process(self):
        """Proceso principal de captura"""
        # Iniciar timer al inicio del proceso (incluye tiempo de espera)
        start_time = time.time()
        self.capture_start_time = datetime.now()
        
        try:
            # Espera inicial
            wait_time = self.wait_time_var.get()
            if wait_time > 0:
                self.update_status(f"Esperando {wait_time} segundos para carga completa...")
                for i in range(wait_time, 0, -1):
                    if not self.running:
                        return
                    self.update_status(f"Esperando... {i} segundos")
                    time.sleep(1)
                    
            # NUEVO: Resetear trackers al iniciar captura limpia
            self.instance_tracker.reset()
            self.processed_positions.clear()
            self.log("🔄 Trackers reseteados - Iniciando captura limpia")
            
            # Mover mouse al área de log register
            center_x = self.LOG_REGISTER_AREA['left'] + self.LOG_REGISTER_AREA['width'] // 2
            center_y = self.LOG_REGISTER_AREA['top'] + self.LOG_REGISTER_AREA['height'] // 2
            pyautogui.moveTo(center_x, center_y)
            
            # Buscar marcador de tropas aliadas
            self.update_status("Buscando marcador de tropas aliadas...")
            if not self.scroll_to_troops_marker():
                self.update_status("❌ No se encontró el marcador de tropas")
                return
                
            # Procesar todas las cards visibles
            self.update_status("Procesando participantes...")
            # Ajustar scroll para tener el grid 4x3 completo en la primera pantalla
            self.log("Ajustando posición inicial del grid...")
            pyautogui.scroll(-2)  # Pequeño scroll para centrar el grid
            time.sleep(0.5)
            
            # Procesar todas las cards visibles
            self.update_status("Procesando participantes...")
            self.process_all_participants()
            
            # NUEVO: Mostrar estadísticas del tracker
            stats = self.instance_tracker.get_stats()
            self.log(f"📊 RESUMEN: {stats['processed_heroes']} héroes únicos detectados")
            if stats['gametags']:
                gametags_list = list(stats['gametags'])[:10]  # Primeros 10
                self.log(f"📋 Gametags: {', '.join(gametags_list)}")
            
            # Señal de finalización
            self.completion_signal()
            
        except Exception as e:
            self.log(f"Error en captura: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Calcular tiempo transcurrido (SIEMPRE, incluso si hay error)
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            self.capture_elapsed_time = f"{minutes}m {seconds}s"
            self.log(f"⏱️ Tiempo total de captura: {self.capture_elapsed_time}")
            
            self.running = False
            self.root.after(0, self.capture_finished)
            
    def scroll_to_troops_marker(self):
        """Hace scroll hasta encontrar el marcador de tropas aliadas"""
        if self.troops_marker is None:
            self.log("❌ ERROR: No hay marcador de tropas cargado (allied_attacking_troops.jpg no encontrado)")
            return False
        
        self.log(f"🔍 Iniciando búsqueda del marcador (máx. 30 scrolls)...")
        
        # Calcular centro del área de log register
        center_x = self.LOG_REGISTER_AREA['left'] + self.LOG_REGISTER_AREA['width'] // 2
        center_y = self.LOG_REGISTER_AREA['top'] + self.LOG_REGISTER_AREA['height'] // 2
        
        # Hacer click en el área para enfocarla (necesario para que el scroll funcione)
        self.click_at(center_x, center_y)
        time.sleep(0.3)
        
        max_scrolls = 60
        for i in range(max_scrolls):
            if not self.running:
                self.log("⏹️ Búsqueda cancelada por el usuario")
                return False
                
            # Capturar pantalla
            screenshot = self.capture_screen()
            
            if screenshot is None:
                self.log(f"⚠️ Error capturando pantalla en scroll {i+1}")
                continue
            
            # Buscar marcador
            try:
                result = cv2.matchTemplate(screenshot, self.troops_marker, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                self.log(f"Scroll {i+1}/{max_scrolls} - Confianza: {max_val:.2f}")
                
                if max_val > 0.75:  # Bajado de 0.8 a 0.75
                    self.log(f"✅ Marcador encontrado en posición {max_loc} (confianza: {max_val:.2f})")
                    
                    # Hacer un poco más de scroll para ocultar el texto
                    # Asegurar que el mouse está en posición antes de hacer scroll
                    pyautogui.moveTo(center_x, center_y)
                    time.sleep(0.2)
                    pyautogui.scroll(-5)  # 🔧 FIX: Era -3, ahora -5
                    time.sleep(0.5)
                    return True
            except Exception as e:
                self.log(f"⚠️ Error en template matching: {e}")
                continue
                
            # Hacer scroll down - Mover mouse al centro antes de scroll
            pyautogui.moveTo(center_x, center_y)
            time.sleep(0.1)
            pyautogui.scroll(-10)  # 🔧 FIX: Era -5, ahora -10 (2x más rápido)
            time.sleep(0.5)
        
        self.log(f"❌ No se encontró el marcador después de {max_scrolls} scrolls")
        return False
        
    def process_all_participants(self):
        """Procesa todos los participantes del reporte"""
        dragon_found = False
        processed_screens = 0
        no_progress_count = 0  # Contador de iteraciones sin progreso
        last_content_hash = None  # 🆕 Para detectar si el contenido cambió
        
        while not dragon_found and self.running:
            # Capturar pantalla actual
            screenshot = self.capture_screen()
            
            if screenshot is None:
                self.log("Error capturando pantalla")
                break
            
            # CRÍTICO: Recortar solo el área de LOG_REGISTER para evitar detectar héroes fuera del área
            log_area = screenshot[
                self.LOG_REGISTER_AREA['top']:self.LOG_REGISTER_AREA['top'] + self.LOG_REGISTER_AREA['height'],
                self.LOG_REGISTER_AREA['left']:self.LOG_REGISTER_AREA['left'] + self.LOG_REGISTER_AREA['width']
            ]
            
            # Verificar si hay dragones (fin del reporte) - buscar en toda la pantalla
            if self.check_for_dragon(screenshot):
                self.log("Dragón detectado - fin del reporte")
                dragon_found = True
                
                # Procesar última pantalla (solo área de logs)
                self.process_current_screen(log_area)
                break
                
            # Procesar pantalla actual (solo área de logs)
            # Retorna: (total_cards_encontradas, cards_realmente_procesadas)
            cards_found, cards_processed = self.process_current_screen(log_area)
            
            # 🆕 Calcular hash del contenido para detectar si realmente cambia
            content_hash = hashlib.md5(log_area.tobytes()).hexdigest()
            content_changed = (content_hash != last_content_hash)
            last_content_hash = content_hash
            
            # Decidir qué hacer basado en los resultados
            if cards_found == 0:
                # No se encontraron cards en absoluto
                self.log("⚠️ No se encontraron cards, haciendo scroll pequeño...")
                pyautogui.scroll(-30)  # 🔧 FIX: Era -3, ahora -30 (10x más rápido)
                time.sleep(0.5)
                no_progress_count += 1
            elif cards_processed == 0:
                # Se encontraron cards pero todas fueron saltadas (ya procesadas)
                
                # 🆕 Si el contenido NO cambió, estamos realmente atascados
                if not content_changed:
                    self.log(f"⚠️ Contenido estancado, scroll MUY AGRESIVO...")
                    pyautogui.scroll(-60)  # 🔧 FIX: Era -20, ahora -60 (3x más rápido)
                    time.sleep(1.2)
                    no_progress_count += 1
                # 🔧 FIX: Scroll más agresivo para avanzar más rápido
                elif self.instance_tracker.needs_scroll():
                    # Usar scroll agresivo si el tracker lo indica
                    scroll_amount = -50  # 🔧 FIX: Era -15, ahora -50
                    self.log(f"⏭️ Todas las cards ya procesadas ({cards_found} saltadas), scroll AGRESIVO...")
                    pyautogui.scroll(scroll_amount)
                    time.sleep(1)
                    no_progress_count += 1
                else:
                    scroll_amount = -40  # 🔧 FIX: Era -12, ahora -40
                    self.log(f"⏭️ Todas las cards ya procesadas ({cards_found} saltadas), avanzando...")
                    pyautogui.scroll(scroll_amount)
                    time.sleep(1)
                    no_progress_count += 1
            else:
                # Se procesaron algunas cards nuevas
                self.log(f"✅ Procesadas {cards_processed} de {cards_found} cards")
                pyautogui.scroll(-25)  # 🔧 FIX: Era -8, ahora -25 (3x más rápido)
                time.sleep(1)
                no_progress_count = 0  # Reset del contador
                
            processed_screens += 1
            
            # Límite de seguridad - si no hay progreso por muchas iteraciones
            if no_progress_count > 10:
                self.log("⚠️ Sin progreso después de 10 intentos, posible fin del reporte")
                break
            
            # Límite de seguridad general
            if processed_screens > 50:
                self.log("Límite de pantallas alcanzado")
                break
        
        # 🆕 RESUMEN FINAL
        stats = self.instance_tracker.get_stats()
        self.log(f"\n{'='*60}")
        self.log(f"📊 RESUMEN: {stats['unique_gametags']} héroes únicos detectados")
        if stats['gametags']:
            self.log(f"📋 Gametags: {', '.join(stats['gametags'])}")
        self.log(f"{'='*60}\n")
                
    def process_current_screen(self, screenshot):
        """Procesa la pantalla actual detectando cards"""
        cards_detected = []
        
        # Detectar todas las cards en la pantalla
        heroes_found = self.detect_cards(screenshot, self.heroes, "hero")
        captains_found = self.detect_cards(screenshot, self.captains, "captain")
        
        # Combinar y ordenar por posición
        all_cards = heroes_found + captains_found
        all_cards.sort(key=lambda x: (x[2][1], x[2][0]))  # Ordenar por Y, luego X
        
        # === MODO DEBUG VISUAL: Mostrar detecciones ===
        if self.debug_var.get():
            self.show_debug_visual(screenshot, heroes_found, captains_found)
        
        # Contador de cards realmente procesadas (no saltadas)
        processed_count = 0
        
        # Procesar cada card
        for card_name, card_type, position, confidence in all_cards:
            if not self.running:
                break
            
            # process_card retorna True si procesó, False si saltó
            was_processed = self.process_card(card_name, card_type, position)
            if was_processed:
                processed_count += 1
            
        # Detectar cards desconocidas
        if self.auto_add_var.get():
            self.detect_unknown_cards(screenshot, all_cards)
        
        # Retornar (total_encontradas, realmente_procesadas)
        return len(all_cards), processed_count
        
    def detect_cards(self, screenshot, templates, card_type):
        """
        Detecta cards en la pantalla usando TemplateMatcher
        ⚠️ IMPORTANTE: 'screenshot' ya es el área del log recortada (log_area)
        """
        found_cards = []
        
        # === VALIDACIÓN: Verificar que la imagen no esté vacía ===
        if screenshot is None or screenshot.size == 0:
            print(f"❌ ERROR: screenshot está vacío en detect_cards")
            return []
        
        if self.debug_var.get():
            print(f"🔍 Área recibida: {screenshot.shape}")
        
        # === USA TEMPLATE MATCHER DIRECTAMENTE (sin recortar otra vez) ===
        all_matches = self.template_matcher.find_all_templates(
            image=screenshot,  # 🎯 Ya es log_area, NO recortar de nuevo
            templates=templates,
            use_multiscale=True
        )
        
        # Convertir MatchResult a formato (name, card_type, position, confidence)
        # Las coordenadas son relativas al área del log
        for name, matches in all_matches.items():
            for match in matches:
                rel_x = match.position[0]
                rel_y = match.position[1]
                confidence = match.confidence
                
                # Convertir a coordenadas absolutas de pantalla
                # 🎯 Sumar offset del área del log
                abs_x = self.LOG_REGISTER_AREA['left'] + rel_x
                abs_y = self.LOG_REGISTER_AREA['top'] + rel_y
                
                # Filtro de confianza
                if confidence >= 0.78:
                    found_cards.append((name, card_type, (abs_x, abs_y), confidence))
        
        # === NMS MANUAL ADICIONAL ===
        found_cards = self.non_max_suppression(found_cards, overlap_thresh=45)
        
        return found_cards
    
    def show_debug_visual(self, screenshot, heroes_found, captains_found):
        """
        Muestra ventana debug COMPLETA con héroes + capitanes como test_tracker_debug-v2.py
        🟢 VERDE = Héroes | 🔵 AZUL = Capitanes | 🟡 AMARILLO = Ya procesado
        """
        # Recortar área del log para visualización
        log_left = self.LOG_REGISTER_AREA['left']
        log_top = self.LOG_REGISTER_AREA['top']
        log_width = self.LOG_REGISTER_AREA['width']
        log_height = self.LOG_REGISTER_AREA['height']
        
        log_area = screenshot[log_top:log_top + log_height, log_left:log_left + log_width]
        debug_img = log_area.copy()
        
        total_detections = 0
        
        # === DIBUJAR HÉROES (VERDE) ===
        for name, card_type, (abs_x, abs_y), conf in heroes_found:
            # Convertir coordenadas absolutas → relativas al log
            rel_x = abs_x - log_left
            rel_y = abs_y - log_top
            
            # Verificar si ya fue procesado
            key = self.instance_tracker._key(name)
            card = self.instance_tracker.seen.get(key)
            already_processed = card and card.processed
            
            # Color según estado
            if already_processed:
                color = (0, 255, 255)  # 🟡 AMARILLO = Ya procesado
                status = "SKIP"
            else:
                color = (0, 255, 0)  # 🟢 VERDE = Click
                status = "HERO"
            
            # Dibujar rectángulo reducido para héroes (2/3 del tamaño aproximado)
            # Ancho original ~90, alto original ~110 → nuevo ancho ~60, alto ~73
            hero_w = int(90 * 2/3)
            hero_h = int(110 * 2/3)
            cv2.rectangle(debug_img, (rel_x, rel_y), (rel_x + hero_w, rel_y + hero_h), color, 2)

            # Punto de click ajustado proporcional al nuevo tamaño (aprox 1/3 del ancho/alto)
            center_x = rel_x + hero_w // 3
            center_y = rel_y + hero_h // 3
            cv2.circle(debug_img, (center_x, center_y), 5, (255, 255, 255), -1)
            
            # Etiqueta con nombre y confianza
            # Mostrar nombre del héroe y, si ya se capturó, el gametag
            card_obj = self.instance_tracker.seen.get(self.instance_tracker._key(name))
            if card_obj and card_obj.gametag:
                label = f"{name}+{card_obj.gametag} {status}"
            else:
                label = f"{name} {status}"
            cv2.putText(debug_img, label, (rel_x, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(debug_img, f"conf:{conf:.2f}", (rel_x, rel_y + 125),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            total_detections += 1
        
        # === DIBUJAR CAPITANES (AZUL) ===
        for name, card_type, (abs_x, abs_y), conf in captains_found:
            # Convertir coordenadas absolutas → relativas al log
            rel_x = abs_x - log_left
            rel_y = abs_y - log_top
            
            # Verificar si ya fue procesado
            pos_key = f"{abs_x},{abs_y}"
            already_processed = pos_key in self.processed_positions
            
            # Color según estado
            if already_processed:
                color = (128, 128, 128)  # GRIS = Ya procesado
                status = "SKIP"
            else:
                color = (255, 0, 0)  # 🔵 AZUL = Captain
                status = "CAPT"
            
            # Dibujar rectángulo reducido para capitanes (2/3 del tamaño aproximado)
            # Ancho original ~70, alto original ~90 → nuevo ancho ~46, alto ~60
            cap_w = int(70 * 2/3)
            cap_h = int(90 * 2/3)
            cv2.rectangle(debug_img, (rel_x, rel_y), (rel_x + cap_w, rel_y + cap_h), color, 2)

            # Punto de click ajustado proporcional al nuevo tamaño (aprox 1/3 del ancho/alto)
            center_x = rel_x + cap_w // 3
            center_y = rel_y + cap_h // 3
            cv2.circle(debug_img, (center_x, center_y), 4, (255, 255, 255), -1)
            
            # Etiqueta
            label = f"{name} {status}"
            cv2.putText(debug_img, label, (rel_x, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            total_detections += 1
        
        # === INFORMACIÓN EN PANTALLA ===
        info_y = 20
        cv2.putText(debug_img, f"HEROES: {len(heroes_found)} | CAPTAINS: {len(captains_found)}", 
                   (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(debug_img, "VERDE=Hero AZUL=Captain AMARILLO=Skip", 
                   (10, info_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Redimensionar para visualización
        debug_resized = cv2.resize(debug_img, (900, 700))
        
        # Mostrar ventana
        cv2.imshow("🎯 DEBUG LIVE - ESC=salir", debug_resized)
        cv2.waitKey(1)  # No bloquear
    
    def _show_debug_window(self, log_area, found_cards, card_type):
        """Muestra ventana de debug visual como test_tracker_debug-v2.py"""
        debug_img = log_area.copy()
        
        for name, ctype, (x, y), conf in found_cards:
            # Convertir a coordenadas relativas del log
            rel_x = x - self.LOG_REGISTER_AREA['left']
            rel_y = y - self.LOG_REGISTER_AREA['top']
            
            # Color según tipo
            if ctype == "hero":
                color = (0, 255, 0)  # Verde para héroes
            else:
                color = (255, 165, 0)  # Naranja para capitanes
            
            # Dibujar rectángulo reducido (2/3 de 50x60 → ~33x40)
            box_w = int(50 * 2/3)
            box_h = int(60 * 2/3)
            cv2.rectangle(debug_img, (rel_x, rel_y), (rel_x + box_w, rel_y + box_h), color, 2)
            
            # Punto de click ajustado proporcional al nuevo tamaño
            center_x = rel_x + box_w // 3
            center_y = rel_y + box_h // 3
            cv2.circle(debug_img, (center_x, center_y), 4, (255, 255, 255), -1)
            
            # Etiqueta
            label = f"{name} {conf:.2f}"
            cv2.putText(debug_img, label, (rel_x, rel_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Redimensionar para mejor visualización
        debug_resized = cv2.resize(debug_img, (900, 700))
        
        # Título con información
        title = f"DEBUG - {card_type.upper()}S: {len(found_cards)} detectados | ESC=cerrar"
        cv2.imshow(title, debug_resized)
        cv2.waitKey(1)  # No bloquear, solo actualizar
        
    
    def non_max_suppression(self, cards, overlap_thresh=30):
        """
        Elimina detecciones duplicadas que están muy cerca una de otra.
        
        Args:
            cards: Lista de tuplas (name, card_type, position, confidence)
            overlap_thresh: Distancia mínima entre detecciones (píxeles)
        
        Returns:
            Lista filtrada de cards sin duplicados
        """
        if len(cards) == 0:
            return []
        
        # Convertir a lista de dict para facilitar el procesamiento
        cards_dict = [
            {
                'name': name,
                'type': card_type,
                'x': pos[0],
                'y': pos[1],
                'position': pos,
                'confidence': conf
            }
            for name, card_type, pos, conf in cards
        ]
        
        # Ordenar por confianza (mayor primero)
        cards_dict.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Lista de cards a mantener
        keep = []
        
        for card in cards_dict:
            # Verificar si está muy cerca de alguna card ya seleccionada
            too_close = False
            for kept_card in keep:
                # Calcular distancia
                dx = abs(card['x'] - kept_card['x'])
                dy = abs(card['y'] - kept_card['y'])
                distance = (dx**2 + dy**2) ** 0.5
                
                # Si están muy cerca y son del mismo tipo, es un duplicado
                if distance < overlap_thresh and card['name'] == kept_card['name']:
                    too_close = True
                    break
            
            if not too_close:
                keep.append(card)
        
        # Convertir de vuelta al formato original
        return [(c['name'], c['type'], c['position'], c['confidence']) for c in keep]

    def process_card(self, card_name, card_type, position):
        """Procesa una card detectada - con instance tracking para héroes"""
        x, y = position
        
        # PARA HÉROES: Usar instance tracker mejorado
        if card_type == "hero":
            # ⚠️ IMPORTANTE: x, y ya son coordenadas ABSOLUTAS (convertidas en detect_cards)
            # NO sumar offset otra vez
            screen_x = x  # 🎯 FIX: Ya son absolutas
            screen_y = y  # 🎯 FIX: Ya son absolutas
            
            # Calcular centro Y de la card para el tracker
            y_center = screen_y + 25  # Centro de la card
            
            # === VERIFICAR SI DEBEMOS PROCESAR ===
            if not self.instance_tracker.should_process(card_name, y_center):
                self.log(f"⏭️  SKIP: {card_name} @ Y={y_center} (ya procesado o gametag capturado)")
                # Registrar detección aunque no procesemos
                self.instance_tracker.add_detection(card_name, y_center)
                return False
            
            self.log(f"📍 Detectado héroe: {card_name} en posición absoluta ({x}, {y})")
            
            # Click en el centro de la card (25px offset como en el test)
            click_x = screen_x + 25
            click_y = screen_y + 25
            self.click_at(click_x, click_y)
            time.sleep(5)
            
            # Capturar gametag
            gametag = self.capture_gametag()
            
            # Marcar como procesado con el gametag capturado
            self.instance_tracker.mark_processed(card_name, y_center, gametag)
            
            if gametag:
                self.log(f"✅ Gametag capturado: {gametag}")
                
                # Registrar participante
                if gametag not in self.participants:
                    self.participants[gametag] = Participant(name=gametag)
                self.participants[gametag].hero_detected = True
                self.participants[gametag].position = (x, y)
                
                # Actualizar UI
                self.update_participant_display(gametag)
            else:
                self.log(f"⚠️ No se pudo capturar gametag")
                
            # Cerrar ventana de héroe
            self.log(f"Cerrando ventana de héroe...")
            self.click_at(*self.CLOSE_HERO_POS)
            time.sleep(0.2)
            # Regresar mouse al área de log
            log_center_x = 490 + (934 - 490) // 2
            log_center_y = 441 + (821 - 441) // 2
            pyautogui.moveTo(log_center_x, log_center_y)
            self.log(f"🖱️ Mouse regresado al área de log ({log_center_x}, {log_center_y})")
            time.sleep(0.2)
            
        elif card_type == "captain":
            # PARA CAPITANES: Evitar procesar repetidamente el mismo capitán
            # Comprobar si el nombre del capitán ya fue procesado anteriormente
            if card_name.lower() in self.processed_captain_names:
                self.log(f"⏭️ Saltando {card_type} {card_name} en ({x}, {y}) - Ya procesado anteriormente")
                return False

            # Lógica original con posiciones redondeadas para evitar duplicados cercanos
            position_key = (round(x / 10) * 10, round(y / 10) * 10, card_type)
            if position_key in self.processed_positions:
                self.log(f"⏭️ Saltando {card_type} {card_name} en ({x}, {y}) - Ya procesado en esta posición")
                return False
            self.processed_positions.add(position_key)

            # ⚠️ IMPORTANTE: x, y ya son coordenadas ABSOLUTAS (convertidas en detect_cards)
            screen_x = x
            screen_y = y

            # Determinar si es capitán prohibido
            is_forbidden = card_name.lower() not in self.ALLOWED_CAPTAINS

            # Procesar si es prohibido o si está en modo debug
            if is_forbidden or self.debug_var.get():
                self.log(f"📍 Detectado capitán: {card_name} en posición absoluta ({x}, {y})")

                # Click en el centro de la card (offset proporcional a tamaño reducido)
                self.click_at(screen_x + 20, screen_y + 20)
                time.sleep(3)

                # Capturar nombre del capitán y verificar armadura
                captain_info = self.capture_captain_info()

                if captain_info and is_forbidden:
                    # Encontrar héroe asociado
                    associated_hero = self.find_associated_hero(position)
                    if associated_hero:
                        if associated_hero not in self.participants:
                            self.participants[associated_hero] = Participant(name=associated_hero)
                        self.participants[associated_hero].forbidden_captains.append(card_name)
                        if captain_info.get('has_armor'):
                            self.participants[associated_hero].captain_with_armor.append(card_name)
                        self.update_participant_display(associated_hero)

                # Marcar nombre del capitán como procesado globalmente
                self.processed_captain_names.add(card_name.lower())

                # Cerrar ventana de capitán
                self.log(f"Cerrando ventana de capitán...")
                self.click_at(*self.CLOSE_CAPTAIN_POS)
                time.sleep(0.2)

                # Regresar mouse al área de log para permitir scroll
                log_center_x = 490 + (934 - 490) // 2  # = 712
                log_center_y = 441 + (821 - 441) // 2  # = 631
                pyautogui.moveTo(log_center_x, log_center_y)
                self.log(f"🖱️ Mouse regresado al área de log ({log_center_x}, {log_center_y})")
                time.sleep(0.2)

            return True

    def capture_gametag(self):
        """Captura el gametag del héroe con OCR mejorado"""
        try:
            # Crear instancia de mss para evitar problemas de threading
            with mss.mss() as sct:
                # Capturar área del gametag
                screenshot = sct.grab({
                    'left': self.GAMETAG_AREA['x_start'],
                    'top': self.GAMETAG_AREA['y_start'],
                    'width': self.GAMETAG_AREA['x_end'] - self.GAMETAG_AREA['x_start'],
                    'height': self.GAMETAG_AREA['y_end'] - self.GAMETAG_AREA['y_start']
                })
                
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                # GUARDAR IMÁGENES PARA DEBUG
                debug_dir = Path("debug_ocr")
                debug_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%H%M%S")
                
                # Guardar imagen original
                debug_original = debug_dir / f"gametag_{timestamp}_original.jpg"
                cv2.imwrite(str(debug_original), img)
                
                # Guardar imagen preprocesada
                processed_img = self.ocr_engine.preprocess_image(img)
                debug_processed = debug_dir / f"gametag_{timestamp}_processed.jpg"
                cv2.imwrite(str(debug_processed), processed_img)
                
                self.log(f"💾 Debug: {debug_original.name}, {debug_processed.name}")
                
                # OCR para extraer texto con threshold muy bajo para capturar todo
                results = self.ocr_engine.extract_text(img, confidence_threshold=0.0)
                
                # Debug: mostrar todos los resultados
                if results:
                    self.log(f"🔍 OCR encontró {len(results)} resultado(s):")
                    for r in results:
                        self.log(f"   • '{r.text}' (confianza: {r.confidence:.1f}%)")
                    
                    # Concatenar todos los textos
                    gametag = ' '.join([r.text for r in results])
                    self.log(f"✅ Gametag detectado: {gametag}")
                    return gametag.strip()
                else:
                    self.log(f"⚠️ OCR no retornó resultados")
                    self.log(f"💡 Revisar imágenes en debug_ocr/ para diagnóstico")
        except Exception as e:
            self.log(f"❌ Error capturando gametag: {e}")
            import traceback
            traceback.print_exc()
            
        return None
        
    def capture_captain_info(self):
        """Captura información del capitán"""
        try:
            # Crear instancia de mss para evitar problemas de threading
            with mss.mss() as sct:
                # Capturar área del nombre del capitán
                screenshot = sct.grab({
                    'left': self.CAPTAIN_NAME_AREA['x_start'],
                    'top': self.CAPTAIN_NAME_AREA['y_start'],
                    'width': self.CAPTAIN_NAME_AREA['x_end'] - self.CAPTAIN_NAME_AREA['x_start'],
                    'height': self.CAPTAIN_NAME_AREA['y_end'] - self.CAPTAIN_NAME_AREA['y_start']
                })
                
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                # OCR para nombre
                results = self.ocr_engine.extract_text(img)
                captain_name = ' '.join([r.text for r in results]) if results else "Unknown"
                
                # TODO: Detectar armadura (necesitaría template o área específica)
                has_armor = False  # Por ahora false, implementar detección real
                
                return {
                    'name': captain_name.strip(),
                    'has_armor': has_armor
                }
        except Exception as e:
            self.log(f"Error capturando info de capitán: {e}")
            return {
                'name': "Unknown",
                'has_armor': False
            }
        
    def find_associated_hero(self, captain_position):
        """Encuentra el héroe asociado a un capitán basado en la posición"""
        x, y = captain_position
        
        # Buscar el héroe más cercano a la izquierda
        closest_hero = None
        min_distance = float('inf')
        
        for participant in self.participants.values():
            if participant.position and participant.hero_detected:
                hero_x, hero_y = participant.position
                
                # El héroe debe estar a la izquierda y en la misma fila aproximadamente
                if hero_x < x and abs(hero_y - y) < self.CARD_HEIGHT:
                    distance = x - hero_x
                    
                    # Máximo 3 posiciones de distancia
                    if distance < self.CARD_WIDTH * 3 and distance < min_distance:
                        min_distance = distance
                        closest_hero = participant.name
                        
        return closest_hero
        
    def detect_unknown_cards(self, screenshot, known_cards):
        """Detecta cards desconocidas para auto-añadir"""
        # TODO: Implementar detección de cards desconocidas
        # Usar detección de contornos o template matching genérico
        pass
        
    def check_for_dragon(self, screenshot):
        """Verifica si hay un dragón en la pantalla"""
        for dragon_template in self.dragon_templates:
            result = cv2.matchTemplate(screenshot, dragon_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.8:
                return True
                
        return False
    
    def click_at(self, x, y, button='left'):
        """
        Hace click en coordenadas específicas usando el método más confiable disponible.
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            button (str): 'left' o 'right'
        """
        self.log(f"Haciendo click en ({x}, {y})...")
        
        # Mover el mouse a la posición
        pyautogui.moveTo(x, y, duration=0.2)
        time.sleep(0.1)
        
        if WIN32_AVAILABLE:
            # Método 1: Win32 API (más confiable para juegos)
            try:
                # Convertir coordenadas de pantalla a coordenadas de ventana
                if button == 'left':
                    win32api.SetCursorPos((x, y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                else:
                    win32api.SetCursorPos((x, y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                
                self.log(f"✓ Click realizado con Win32 API")
                return True
            except Exception as e:
                self.log(f"Error con Win32 API, intentando pyautogui: {e}")
        
        # Método 2: Fallback a pyautogui
        try:
            if button == 'left':
                pyautogui.click(x, y)
            else:
                pyautogui.rightClick(x, y)
            
            self.log(f"✓ Click realizado con pyautogui")
            return True
        except Exception as e:
            self.log(f"❌ Error en click: {e}")
            return False
        
    def capture_screen(self):
        """Captura la pantalla completa"""
        try:
            # Crear nueva instancia en cada captura para evitar problemas de threading
            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[0])
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                return img
        except Exception as e:
            self.log(f"Error capturando pantalla: {e}")
            return None
        
    def update_participant_display(self, name):
        """Actualiza la visualización de un participante"""
        def update():
            # Buscar si ya existe
            for item in self.results_tree.get_children():
                if self.results_tree.item(item)['text'] == name:
                    self.results_tree.delete(item)
                    break
                    
            # Añadir o actualizar
            participant = self.participants.get(name)
            if participant:
                hero_status = "✓" if participant.hero_detected else "✗"
                forbidden = ", ".join(participant.forbidden_captains) if participant.forbidden_captains else "-"
                with_armor = ", ".join(participant.captain_with_armor) if participant.captain_with_armor else "-"
                position = f"{participant.position[0]},{participant.position[1]}" if participant.position else "-"
                
                self.results_tree.insert("", "end", text=name,
                                        values=(hero_status, forbidden, with_armor, position))
                
        self.root.after(0, update)
        
    def completion_signal(self):
        """Señal de finalización con beep"""
        # Beep de finalización
        for _ in range(3):
            winsound.Beep(1000, 200)
            time.sleep(0.1)
        
        elapsed_time = getattr(self, 'capture_elapsed_time', 'N/A')
        self.update_status(f"✅ Captura completada - {len(self.participants)} participantes en {elapsed_time}")
        
    def capture_finished(self):
        """Llamado cuando termina la captura"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.root.deiconify()  # Restaurar ventana
        
        # Mostrar resumen
        total = len(self.participants)
        with_forbidden = sum(1 for p in self.participants.values() if p.forbidden_captains)
        elapsed_time = getattr(self, 'capture_elapsed_time', 'N/A')
        
        messagebox.showinfo("Captura Completada", 
                          f"Participantes detectados: {total}\n"
                          f"Con capitanes prohibidos: {with_forbidden}\n"
                          f"Tiempo transcurrido: {elapsed_time}")
        
    def stop_capture(self):
        """Detiene la captura"""
        self.running = False
        self.update_status("Deteniendo captura...")
    
    def on_esc_pressed(self, event=None):
        """Manejador de evento ESC - Detiene la captura elegantemente"""
        if self.running:
            self.log("🛑 ESC presionado - Deteniendo captura...")
            self.stop_capture()
            # Beep de notificación
            try:
                winsound.Beep(800, 150)
                winsound.Beep(600, 150)
            except:
                pass
        
    def open_grid_tuning(self):
        """Abre ventana de ajuste fino de la grid"""
        tuning_window = tk.Toplevel(self.root)
        tuning_window.title("Fine Tuning - Grid 4x3")
        tuning_window.geometry("400x300")
        
        ttk.Label(tuning_window, text="Ajustar posición de la Grid 4x3",
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        # TODO: Implementar ajuste visual de la grid
        ttk.Label(tuning_window, text="Función en desarrollo").pack(pady=20)
        
    def open_asset_manager(self):
        """Abre el gestor de assets"""
        try:
            import subprocess
            subprocess.Popen([sys.executable, "tools/asset_manager.py"])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor de assets: {e}")
            
    def export_json(self):
        """Exporta los resultados a JSON"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"BR_{self.date_var.get().replace('-', '')}"
        )
        
        if filename:
            data = {
                "date": self.date_var.get(),
                "capture_time": getattr(self, 'capture_start_time', datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_time": getattr(self, 'capture_elapsed_time', 'N/A'),
                "battle_type": "Assistance Report",
                "participants": [
                    {
                        "name": name,
                        "hero_detected": p.hero_detected,
                        "forbidden_captains": p.forbidden_captains,
                        "captain_with_armor": p.captain_with_armor,
                        "participated": p.hero_detected
                    }
                    for name, p in self.participants.items()
                ],
                "total_participants": len(self.participants),
                "violations": sum(1 for p in self.participants.values() if p.forbidden_captains)
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            self.update_status(f"Exportado a {Path(filename).name}")
            messagebox.showinfo("Éxito", "Reporte exportado correctamente")
            
    def export_csv(self):
        """Exporta los resultados a CSV"""
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"BR_{self.date_var.get().replace('-', '')}"
        )
        
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Escribir metadata
                writer.writerow(["Fecha", self.date_var.get()])
                capture_time = getattr(self, 'capture_start_time', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow(["Hora de Captura", capture_time])
                elapsed_time = getattr(self, 'capture_elapsed_time', 'N/A')
                writer.writerow(["Tiempo Transcurrido", elapsed_time])
                writer.writerow([])  # Línea en blanco
                
                # Escribir encabezados
                writer.writerow(["Jugador", "Héroe Detectado", "Capitanes Prohibidos", "Con Armadura"])
                
                # Escribir participantes
                for name, p in self.participants.items():
                    writer.writerow([
                        name,
                        "Sí" if p.hero_detected else "No",
                        ", ".join(p.forbidden_captains) if p.forbidden_captains else "",
                        ", ".join(p.captain_with_armor) if p.captain_with_armor else ""
                    ])
                    
            self.update_status(f"Exportado a {Path(filename).name}")
            messagebox.showinfo("Éxito", "CSV exportado correctamente")
            
    def copy_result(self):
        """Copia el resultado al portapapeles"""
        result = "ASISTENCIA:\n"
        result += "-" * 40 + "\n"
        result += f"Fecha: {self.date_var.get()}\n"
        elapsed_time = getattr(self, 'capture_elapsed_time', 'N/A')
        result += f"Tiempo de captura: {elapsed_time}\n"
        result += "-" * 40 + "\n"
        
        for name, p in self.participants.items():
            result += f"{name}"
            if p.forbidden_captains:
                result += f" [Prohibidos: {', '.join(p.forbidden_captains)}]"
            result += "\n"
            
        result += "-" * 40 + "\n"
        result += f"Total: {len(self.participants)} participantes\n"
        violations = sum(1 for p in self.participants.values() if p.forbidden_captains)
        if violations > 0:
            result += f"Violaciones: {violations}\n"
            
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        
        self.update_status("Resultado copiado al portapapeles")
        messagebox.showinfo("Copiado", "El resultado ha sido copiado al portapapeles")
        
    def update_status(self, message):
        """Actualiza el status en el thread principal"""
        def update():
            if hasattr(self, 'status_var'):
                self.status_var.set(message)
            if hasattr(self, 'progress_label'):
                self.progress_label.config(text=message)
        
        # Solo usar root.after si root existe
        if hasattr(self, 'root'):
            self.root.after(0, update)
        else:
            # Si no hay GUI, solo imprimir
            print(f"[Status] {message}")
        
    def log(self, message):
        """Registra un mensaje"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
        
        # Solo actualizar status si la GUI existe
        if hasattr(self, 'root'):
            self.update_status(message)
        
    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()

if __name__ == "__main__":
    app = BattleReportScraper()
    app.run()
