"""
Template Matcher Module
Sistema avanzado de template matching con cache y multi-escala
Optimizado para detección de elementos UI en juegos
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
import json
import os
from pathlib import Path
import hashlib

@dataclass
class MatchResult:
    """Clase para almacenar resultados de template matching"""
    template_name: str
    position: Tuple[int, int]  # x, y
    size: Tuple[int, int]      # width, height
    confidence: float
    scale: float
    method: str

class TemplateMatcher:
    """Sistema de template matching con características avanzadas"""
    
    def __init__(self, templates_dir: str = "assets", config_path: Optional[str] = None):
        """
        Inicializa el matcher de templates
        
        Args:
            templates_dir: Directorio base para los templates
            config_path: Ruta al archivo de configuración
        """
        self.templates_dir = Path(templates_dir)
        self.config = self._load_config(config_path)
        self.template_cache = {}
        self.methods = {
            'CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Carga la configuración desde archivo JSON"""
        default_config = {
            'default_threshold': 0.8,
            'multi_scale': {
                'enabled': True,
                'min_scale': 0.8,
                'max_scale': 1.2,
                'scale_step': 0.05
            },
            'matching_method': 'CCOEFF_NORMED',
            'use_cache': True,
            'debug_mode': False,
            'custom_thresholds': {}  # Template específicos con umbrales personalizados
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Error cargando configuración: {e}")
                
        return default_config
    
    def _get_template_hash(self, template_path: str) -> str:
        """Genera un hash único para un template"""
        with open(template_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def load_template(self, template_path: Union[str, Path], 
                     force_reload: bool = False) -> Optional[np.ndarray]:
        """
        Carga un template desde archivo con soporte de cache
        
        Args:
            template_path: Ruta al archivo de template
            force_reload: Forzar recarga ignorando cache
            
        Returns:
            Template como numpy array o None si falla
        """
        template_path = str(template_path)
        
        # Verificar cache
        if self.config['use_cache'] and not force_reload:
            if template_path in self.template_cache:
                return self.template_cache[template_path]
        
        # Cargar template
        if not os.path.exists(template_path):
            print(f"Template no encontrado: {template_path}")
            return None
            
        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"Error cargando template: {template_path}")
                return None
                
            # Guardar en cache
            if self.config['use_cache']:
                self.template_cache[template_path] = template
                
            return template
            
        except Exception as e:
            print(f"Error cargando template {template_path}: {e}")
            return None
    
    def load_templates_from_directory(self, sub_dir: str = "") -> Dict[str, np.ndarray]:
        """
        Carga todos los templates de un directorio
        
        Args:
            sub_dir: Subdirectorio dentro del directorio de templates
            
        Returns:
            Diccionario {nombre: template}
        """
        templates = {}
        directory = self.templates_dir / sub_dir
        
        if not directory.exists():
            print(f"Directorio no existe: {directory}")
            return templates
        
        for file_path in directory.glob("*.jpg"):
            name = file_path.stem
            template = self.load_template(str(file_path))
            if template is not None:
                templates[name] = template
                
        for file_path in directory.glob("*.png"):
            name = file_path.stem
            template = self.load_template(str(file_path))
            if template is not None:
                templates[name] = template
                
        return templates
    
    def match_template(self, image: np.ndarray, template: np.ndarray,
                      threshold: Optional[float] = None,
                      method: Optional[str] = None) -> List[MatchResult]:
        """
        Busca un template en la imagen
        
        Args:
            image: Imagen donde buscar
            template: Template a buscar
            threshold: Umbral de confianza (usa default si no se especifica)
            method: Método de matching
            
        Returns:
            Lista de matches encontrados
        """
        if threshold is None:
            threshold = self.config['default_threshold']
            
        if method is None:
            method = self.config['matching_method']
            
        matching_method = self.methods.get(method, cv2.TM_CCOEFF_NORMED)
        
        # Convertir a escala de grises si es necesario
        if len(image.shape) == 3:
            img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = image
            
        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template
        
        # Realizar matching
        result = cv2.matchTemplate(img_gray, template_gray, matching_method)
        
        # Encontrar todas las ubicaciones que superan el threshold
        matches = []
        
        if method == 'SQDIFF_NORMED':
            # Para SQDIFF, valores más bajos son mejores
            locations = np.where(result <= (1 - threshold))
        else:
            # Para otros métodos, valores más altos son mejores
            locations = np.where(result >= threshold)
        
        # Convertir locations a lista de matches
        for pt in zip(*locations[::-1]):
            confidence = result[pt[1], pt[0]]
            if method == 'SQDIFF_NORMED':
                confidence = 1 - confidence
                
            matches.append(MatchResult(
                template_name="",
                position=(pt[0], pt[1]),
                size=(template.shape[1], template.shape[0]),
                confidence=float(confidence),
                scale=1.0,
                method=method
            ))
        
        # Eliminar detecciones duplicadas cercanas
        matches = self._non_max_suppression(matches)
        
        return matches
    
    def match_template_multiscale(self, image: np.ndarray, template: np.ndarray,
                                 template_name: str = "",
                                 threshold: Optional[float] = None) -> List[MatchResult]:
        """
        Busca un template en múltiples escalas
        
        Args:
            image: Imagen donde buscar
            template: Template a buscar
            template_name: Nombre del template
            threshold: Umbral de confianza
            
        Returns:
            Lista de matches encontrados en todas las escalas
        """
        if not self.config['multi_scale']['enabled']:
            matches = self.match_template(image, template, threshold)
            for match in matches:
                match.template_name = template_name
            return matches
        
        all_matches = []
        
        # Obtener configuración de escala
        min_scale = self.config['multi_scale']['min_scale']
        max_scale = self.config['multi_scale']['max_scale']
        scale_step = self.config['multi_scale']['scale_step']
        
        # Iterar sobre diferentes escalas
        for scale in np.arange(min_scale, max_scale + scale_step, scale_step):
            # Redimensionar template
            width = int(template.shape[1] * scale)
            height = int(template.shape[0] * scale)
            
            if width < 10 or height < 10:  # Evitar templates muy pequeños
                continue
                
            resized_template = cv2.resize(template, (width, height))
            
            # Buscar matches en esta escala
            matches = self.match_template(image, resized_template, threshold)
            
            # Actualizar información de matches
            for match in matches:
                match.template_name = template_name
                match.scale = scale
                
            all_matches.extend(matches)
        
        # Eliminar duplicados considerando todas las escalas
        all_matches = self._non_max_suppression(all_matches, scale_aware=True)
        
        return all_matches
    
    def _non_max_suppression(self, matches: List[MatchResult], 
                            overlap_threshold: float = 0.5,
                            scale_aware: bool = False) -> List[MatchResult]:
        """
        Elimina detecciones duplicadas usando Non-Maximum Suppression
        
        Args:
            matches: Lista de matches
            overlap_threshold: Umbral de overlap para considerar duplicados
            scale_aware: Considerar escala en la supresión
            
        Returns:
            Lista filtrada de matches
        """
        if len(matches) == 0:
            return []
        
        # Convertir a numpy arrays para procesamiento eficiente
        boxes = []
        confidences = []
        
        for match in matches:
            x, y = match.position
            w, h = match.size
            boxes.append([x, y, x + w, y + h])
            confidences.append(match.confidence)
        
        boxes = np.array(boxes)
        confidences = np.array(confidences)
        
        # Ordenar por confianza
        indices = np.argsort(confidences)[::-1]
        
        keep = []
        while len(indices) > 0:
            # Tomar el de mayor confianza
            current = indices[0]
            keep.append(current)
            
            if len(indices) == 1:
                break
            
            # Calcular IoU con los demás
            current_box = boxes[current]
            other_boxes = boxes[indices[1:]]
            
            # Calcular intersección
            x1 = np.maximum(current_box[0], other_boxes[:, 0])
            y1 = np.maximum(current_box[1], other_boxes[:, 1])
            x2 = np.minimum(current_box[2], other_boxes[:, 2])
            y2 = np.minimum(current_box[3], other_boxes[:, 3])
            
            intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
            
            # Calcular áreas
            current_area = (current_box[2] - current_box[0]) * (current_box[3] - current_box[1])
            other_areas = (other_boxes[:, 2] - other_boxes[:, 0]) * (other_boxes[:, 3] - other_boxes[:, 1])
            
            # Calcular IoU
            union = current_area + other_areas - intersection
            iou = intersection / (union + 1e-6)
            
            # Mantener solo los que no se solapan demasiado
            indices = indices[1:][iou < overlap_threshold]
        
        return [matches[i] for i in keep]
    
    def find_all_templates(self, image: np.ndarray, templates: Dict[str, np.ndarray],
                          use_multiscale: bool = True) -> Dict[str, List[MatchResult]]:
        """
        Busca múltiples templates en una imagen
        
        Args:
            image: Imagen donde buscar
            templates: Diccionario de templates {nombre: template}
            use_multiscale: Usar búsqueda multi-escala
            
        Returns:
            Diccionario {nombre_template: lista de matches}
        """
        results = {}
        
        for name, template in templates.items():
            # Obtener threshold personalizado si existe
            threshold = self.config['custom_thresholds'].get(name, 
                                                             self.config['default_threshold'])
            
            if use_multiscale:
                matches = self.match_template_multiscale(image, template, name, threshold)
            else:
                matches = self.match_template(image, template, threshold)
                for match in matches:
                    match.template_name = name
            
            if matches:
                results[name] = matches
                
        return results
    
    def find_best_match(self, image: np.ndarray, template: np.ndarray,
                       use_multiscale: bool = False) -> Optional[MatchResult]:
        """
        Encuentra el mejor match de un template
        
        Args:
            image: Imagen donde buscar
            template: Template a buscar
            use_multiscale: Usar búsqueda multi-escala
            
        Returns:
            Mejor match o None si no encuentra
        """
        if use_multiscale:
            matches = self.match_template_multiscale(image, template)
        else:
            matches = self.match_template(image, template)
        
        if not matches:
            return None
        
        # Retornar el de mayor confianza
        return max(matches, key=lambda m: m.confidence)
    
    def visualize_matches(self, image: np.ndarray, 
                         matches: Union[List[MatchResult], Dict[str, List[MatchResult]]]) -> np.ndarray:
        """
        Visualiza los matches en la imagen
        
        Args:
            image: Imagen original
            matches: Lista de matches o diccionario de matches por template
            
        Returns:
            Imagen con los matches dibujados
        """
        vis_image = image.copy()
        
        # Convertir a lista si es diccionario
        if isinstance(matches, dict):
            all_matches = []
            for template_matches in matches.values():
                all_matches.extend(template_matches)
            matches = all_matches
        
        # Colores para diferentes templates
        colors = [
            (0, 255, 0),    # Verde
            (255, 0, 0),    # Azul
            (0, 0, 255),    # Rojo
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Amarillo
        ]
        
        template_colors = {}
        
        for match in matches:
            # Asignar color por template
            if match.template_name not in template_colors:
                template_colors[match.template_name] = colors[len(template_colors) % len(colors)]
            
            color = template_colors[match.template_name]
            
            x, y = match.position
            w, h = match.size
            
            # Dibujar rectángulo
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
            
            # Añadir etiqueta
            label = f"{match.template_name} {match.confidence:.2f}"
            if match.scale != 1.0:
                label += f" @{match.scale:.2f}x"
                
            cv2.putText(vis_image, label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return vis_image
    
    def save_config(self, config_path: str):
        """Guarda la configuración actual"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def clear_cache(self):
        """Limpia el cache de templates"""
        self.template_cache.clear()
        print("Cache de templates limpiado")
