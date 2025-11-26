"""
Scroll Controller Module
Sistema de control de scroll para navegación automática
con detección de contenido nuevo y marcadores
"""

import pyautogui
import mss
import cv2
import numpy as np
import time
import hashlib
from typing import Tuple, Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum

class ScrollDirection(Enum):
    """Dirección del scroll"""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

@dataclass
class ScrollState:
    """Estado actual del scroll"""
    position: int
    direction: ScrollDirection
    content_hash: str
    timestamp: float
    screenshot: Optional[np.ndarray] = None

class ScrollController:
    """Controlador de scroll con detección inteligente de contenido"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el controlador de scroll
        
        Args:
            config: Configuración personalizada
        """
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
            
        self.sct = mss.mss()
        self.scroll_history: List[ScrollState] = []
        self.content_hashes: set = set()
        self.markers: Dict[str, np.ndarray] = {}
        
        # Configurar pyautogui
        pyautogui.PAUSE = self.config['pause_between_actions']
        pyautogui.FAILSAFE = self.config['failsafe']
        
    def _get_default_config(self) -> Dict:
        """Retorna la configuración por defecto"""
        return {
            'scroll_speed': 3,              # Líneas por scroll
            'scroll_delay': 0.5,             # Delay entre scrolls (segundos)
            'detection_region': None,       # Región para detectar cambios
            'max_retries': 5,               # Máximo de intentos sin cambio
            'hash_precision': 8,            # Precisión del hash (reducir imagen)
            'pause_between_actions': 0.1,   # Pausa entre acciones de pyautogui
            'failsafe': True,               # Modo seguro de pyautogui
            'smooth_scroll': True,          # Scroll suave
            'capture_area': {               # Área de captura por defecto
                'left': 0,
                'top': 100,
                'width': 1920,
                'height': 880
            }
        }
    
    def set_capture_area(self, left: int, top: int, width: int, height: int):
        """
        Define el área de captura para screenshots
        
        Args:
            left: Coordenada X inicial
            top: Coordenada Y inicial
            width: Ancho del área
            height: Alto del área
        """
        self.config['capture_area'] = {
            'left': left,
            'top': top,
            'width': width,
            'height': height
        }
    
    def capture_screen(self, region: Optional[Dict] = None) -> np.ndarray:
        """
        Captura una screenshot del área especificada
        
        Args:
            region: Región específica o None para usar el área por defecto
            
        Returns:
            Screenshot como numpy array
        """
        if region is None:
            region = self.config['capture_area']
            
        screenshot = np.array(self.sct.grab(region))
        # Convertir de BGRA a BGR
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        return screenshot
    
    def compute_content_hash(self, image: np.ndarray, 
                            region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """
        Calcula un hash del contenido de la imagen
        
        Args:
            image: Imagen para calcular hash
            region: Región específica (x, y, width, height)
            
        Returns:
            Hash del contenido
        """
        # Aplicar región si se especifica
        if region:
            x, y, w, h = region
            image = image[y:y+h, x:x+w]
        
        # Reducir tamaño para hacer el hash más eficiente
        precision = self.config['hash_precision']
        height, width = image.shape[:2]
        new_height = height // precision
        new_width = width // precision
        
        if new_height > 0 and new_width > 0:
            resized = cv2.resize(image, (new_width, new_height))
        else:
            resized = image
        
        # Calcular hash
        img_bytes = resized.tobytes()
        return hashlib.md5(img_bytes).hexdigest()
    
    def scroll(self, direction: ScrollDirection = ScrollDirection.DOWN, 
              amount: Optional[int] = None):
        """
        Realiza un scroll en la dirección especificada
        
        Args:
            direction: Dirección del scroll
            amount: Cantidad de scroll (None usa el valor por defecto)
        """
        if amount is None:
            amount = self.config['scroll_speed']
        
        if self.config['smooth_scroll']:
            # Scroll suave simulando arrastre
            if direction == ScrollDirection.DOWN:
                pyautogui.scroll(-amount)
            elif direction == ScrollDirection.UP:
                pyautogui.scroll(amount)
            elif direction == ScrollDirection.LEFT:
                pyautogui.hscroll(amount)
            elif direction == ScrollDirection.RIGHT:
                pyautogui.hscroll(-amount)
        else:
            # Scroll instantáneo con teclas
            if direction == ScrollDirection.DOWN:
                for _ in range(amount):
                    pyautogui.press('down')
            elif direction == ScrollDirection.UP:
                for _ in range(amount):
                    pyautogui.press('up')
            elif direction == ScrollDirection.LEFT:
                for _ in range(amount):
                    pyautogui.press('left')
            elif direction == ScrollDirection.RIGHT:
                for _ in range(amount):
                    pyautogui.press('right')
        
        # Esperar después del scroll
        time.sleep(self.config['scroll_delay'])
    
    def scroll_to_marker(self, marker_template: np.ndarray, 
                        direction: ScrollDirection = ScrollDirection.DOWN,
                        max_scrolls: int = 50) -> bool:
        """
        Hace scroll hasta encontrar un marcador específico
        
        Args:
            marker_template: Template del marcador a buscar
            direction: Dirección del scroll
            max_scrolls: Máximo número de scrolls
            
        Returns:
            True si encuentra el marcador, False si no
        """
        for i in range(max_scrolls):
            # Capturar pantalla actual
            screenshot = self.capture_screen()
            
            # Buscar marcador
            result = cv2.matchTemplate(screenshot, marker_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.8:  # Threshold para considerar encontrado
                print(f"Marcador encontrado después de {i} scrolls en posición {max_loc}")
                return True
            
            # Hacer scroll
            self.scroll(direction)
        
        print(f"Marcador no encontrado después de {max_scrolls} scrolls")
        return False
    
    def scroll_until_no_change(self, direction: ScrollDirection = ScrollDirection.DOWN,
                              check_region: Optional[Tuple[int, int, int, int]] = None,
                              callback: Optional[Callable] = None) -> List[np.ndarray]:
        """
        Hace scroll hasta que no detecta cambios en el contenido
        
        Args:
            direction: Dirección del scroll
            check_region: Región para verificar cambios
            callback: Función a llamar después de cada scroll
            
        Returns:
            Lista de screenshots capturadas
        """
        screenshots = []
        no_change_count = 0
        max_retries = self.config['max_retries']
        
        # Captura inicial
        current_screen = self.capture_screen()
        current_hash = self.compute_content_hash(current_screen, check_region)
        self.content_hashes.add(current_hash)
        screenshots.append(current_screen)
        
        # Guardar estado inicial
        self.scroll_history.append(ScrollState(
            position=0,
            direction=direction,
            content_hash=current_hash,
            timestamp=time.time(),
            screenshot=current_screen
        ))
        
        position = 1
        
        while no_change_count < max_retries:
            # Hacer scroll
            self.scroll(direction)
            
            # Capturar nueva pantalla
            new_screen = self.capture_screen()
            new_hash = self.compute_content_hash(new_screen, check_region)
            
            # Verificar si hay cambio
            if new_hash in self.content_hashes:
                no_change_count += 1
                print(f"Sin cambios detectados ({no_change_count}/{max_retries})")
            else:
                no_change_count = 0
                self.content_hashes.add(new_hash)
                screenshots.append(new_screen)
                
                # Guardar estado
                self.scroll_history.append(ScrollState(
                    position=position,
                    direction=direction,
                    content_hash=new_hash,
                    timestamp=time.time(),
                    screenshot=new_screen
                ))
                
                print(f"Nuevo contenido detectado en posición {position}")
                
                # Ejecutar callback si existe
                if callback:
                    callback(new_screen, position)
            
            position += 1
        
        print(f"Scroll completado. Total de pantallas únicas: {len(screenshots)}")
        return screenshots
    
    def find_text_marker(self, marker_text: str, 
                        ocr_engine=None,
                        direction: ScrollDirection = ScrollDirection.DOWN) -> bool:
        """
        Busca un marcador de texto usando OCR
        
        Args:
            marker_text: Texto del marcador a buscar
            ocr_engine: Motor OCR a usar (debe tener método extract_text)
            direction: Dirección del scroll
            
        Returns:
            True si encuentra el marcador, False si no
        """
        if ocr_engine is None:
            print("Se requiere un motor OCR para buscar texto")
            return False
        
        max_scrolls = 50
        
        for i in range(max_scrolls):
            # Capturar pantalla
            screenshot = self.capture_screen()
            
            # Extraer texto con OCR
            results = ocr_engine.extract_text(screenshot)
            
            # Buscar marcador en el texto extraído
            full_text = ' '.join([r.text for r in results])
            
            if marker_text in full_text:
                print(f"Marcador de texto '{marker_text}' encontrado después de {i} scrolls")
                
                # Encontrar posición exacta del marcador
                for result in results:
                    if marker_text in result.text:
                        print(f"Posición del marcador: {result.bbox}")
                        break
                
                return True
            
            # Hacer scroll
            self.scroll(direction)
        
        print(f"Marcador de texto '{marker_text}' no encontrado")
        return False
    
    def smart_scroll(self, target_element: np.ndarray, 
                    max_attempts: int = 10) -> Optional[Tuple[int, int]]:
        """
        Scroll inteligente para centrar un elemento en pantalla
        
        Args:
            target_element: Template del elemento objetivo
            max_attempts: Máximo de intentos
            
        Returns:
            Posición del elemento si lo encuentra, None si no
        """
        screen_height = self.config['capture_area']['height']
        screen_center_y = screen_height // 2
        
        for attempt in range(max_attempts):
            # Capturar pantalla
            screenshot = self.capture_screen()
            
            # Buscar elemento
            result = cv2.matchTemplate(screenshot, target_element, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.8:
                element_y = max_loc[1] + target_element.shape[0] // 2
                
                # Si está cerca del centro, terminamos
                if abs(element_y - screen_center_y) < 50:
                    print(f"Elemento centrado en posición {max_loc}")
                    return max_loc
                
                # Calcular dirección y cantidad de scroll
                if element_y < screen_center_y:
                    # Elemento está arriba, scroll up
                    scroll_amount = (screen_center_y - element_y) // 20
                    self.scroll(ScrollDirection.UP, min(scroll_amount, 5))
                else:
                    # Elemento está abajo, scroll down
                    scroll_amount = (element_y - screen_center_y) // 20
                    self.scroll(ScrollDirection.DOWN, min(scroll_amount, 5))
            else:
                # Elemento no visible, hacer scroll exploratorio
                self.scroll(ScrollDirection.DOWN, 3)
        
        return None
    
    def page_down(self, times: int = 1):
        """Simula presionar Page Down"""
        for _ in range(times):
            pyautogui.press('pagedown')
            time.sleep(self.config['scroll_delay'])
    
    def page_up(self, times: int = 1):
        """Simula presionar Page Up"""
        for _ in range(times):
            pyautogui.press('pageup')
            time.sleep(self.config['scroll_delay'])
    
    def scroll_to_top(self):
        """Scroll hasta el inicio de la página"""
        pyautogui.hotkey('ctrl', 'home')
        time.sleep(self.config['scroll_delay'])
    
    def scroll_to_bottom(self):
        """Scroll hasta el final de la página"""
        pyautogui.hotkey('ctrl', 'end')
        time.sleep(self.config['scroll_delay'])
    
    def drag_scroll(self, start_x: int, start_y: int, 
                   end_x: int, end_y: int, duration: float = 0.5):
        """
        Realiza scroll arrastrando el mouse
        
        Args:
            start_x, start_y: Posición inicial
            end_x, end_y: Posición final
            duration: Duración del arrastre
        """
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration, button='left')
        time.sleep(self.config['scroll_delay'])
    
    def reset(self):
        """Resetea el estado del controlador"""
        self.scroll_history.clear()
        self.content_hashes.clear()
        print("Estado del controlador reseteado")
    
    def get_scroll_history(self) -> List[ScrollState]:
        """Retorna el historial de scroll"""
        return self.scroll_history.copy()
    
    def save_screenshots(self, output_dir: str = "screenshots"):
        """
        Guarda todos los screenshots del historial
        
        Args:
            output_dir: Directorio de salida
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for i, state in enumerate(self.scroll_history):
            if state.screenshot is not None:
                filename = f"{output_dir}/scroll_{i:03d}_{state.content_hash[:8]}.png"
                cv2.imwrite(filename, state.screenshot)
        
        print(f"Screenshots guardados en {output_dir}")
