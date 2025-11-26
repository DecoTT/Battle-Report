"""
Config Manager Module
Sistema de gestión de configuración centralizada
con validación y manejo dinámico de assets
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import shutil
from datetime import datetime

@dataclass
class CoordinateConfig:
    """Configuración de coordenadas para elementos UI"""
    x: int
    y: int
    width: int
    height: int
    
    def to_tuple(self) -> tuple:
        """Convierte a tupla (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)
    
    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return asdict(self)

@dataclass
class AssetConfig:
    """Configuración para un asset"""
    name: str
    path: str
    category: str
    threshold: float = 0.8
    enabled: bool = True
    metadata: Dict = None

class ConfigManager:
    """Gestor centralizado de configuración"""
    
    def __init__(self, base_dir: str = "GameDataScraperSuite"):
        """
        Inicializa el gestor de configuración
        
        Args:
            base_dir: Directorio base del proyecto
        """
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        self.assets_dir = self.base_dir / "assets"
        self.data_dir = self.base_dir / "data"
        
        # Crear directorios si no existen
        self._create_directories()
        
        # Cargar configuraciones
        self.app_config = self._load_or_create_config("app_config.json", self._get_default_app_config())
        self.coordinates = self._load_or_create_config("coordinates.json", self._get_default_coordinates())
        self.heroes_config = self._load_or_create_config("heroes_list.json", self._get_default_heroes())
        self.forbidden_caps = self._load_or_create_config("forbidden_caps.json", self._get_default_forbidden_caps())
        
        # Cache de assets
        self.assets_cache: Dict[str, AssetConfig] = {}
        self._load_assets_metadata()
    
    def _create_directories(self):
        """Crea la estructura de directorios necesaria"""
        directories = [
            self.base_dir,
            self.config_dir,
            self.assets_dir,
            self.assets_dir / "heroes",
            self.assets_dir / "captains",
            self.assets_dir / "ui_elements",
            self.assets_dir / "templates",
            self.data_dir,
            self.data_dir / "chat_logs",
            self.data_dir / "battle_reports",
            self.data_dir / "excel_reports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_default_app_config(self) -> Dict:
        """Retorna la configuración por defecto de la aplicación"""
        return {
            "version": "1.0.0",
            "language": "es",
            "debug_mode": False,
            "auto_save": True,
            "save_interval": 300,  # segundos
            "screenshot_quality": 95,
            "ocr_settings": {
                "engine": "tesseract",
                "language": "spa+eng",
                "confidence_threshold": 60
            },
            "template_matching": {
                "method": "CCOEFF_NORMED",
                "default_threshold": 0.8,
                "multiscale": True
            },
            "scroll_settings": {
                "speed": 3,
                "delay": 0.5,
                "smooth": True
            },
            "window_settings": {
                "width": 1920,
                "height": 1080,
                "capture_area": {
                    "x": 0,
                    "y": 100,
                    "width": 1920,
                    "height": 880
                }
            }
        }
    
    def _get_default_coordinates(self) -> Dict:
        """Retorna las coordenadas por defecto para elementos UI"""
        return {
            "chat_area": {
                "x": 100,
                "y": 200,
                "width": 600,
                "height": 700
            },
            "battle_report_area": {
                "x": 50,
                "y": 150,
                "width": 1820,
                "height": 880
            },
            "hero_card": {
                "x": 0,
                "y": 0,
                "width": 150,
                "height": 200
            },
            "captain_card": {
                "x": 0,
                "y": 0,
                "width": 150,
                "height": 200
            },
            "return_button": {
                "x": 50,
                "y": 50,
                "width": 100,
                "height": 50
            },
            "scroll_markers": {
                "troops_header": {
                    "x": 100,
                    "y": 300,
                    "width": 400,
                    "height": 50
                }
            }
        }
    
    def _get_default_heroes(self) -> Dict:
        """Retorna la lista por defecto de héroes"""
        return {
            "heroes": [
                {
                    "name": "Haemon",
                    "enabled": True,
                    "template_path": "assets/heroes/haemon.jpg",
                    "threshold": 0.85
                }
            ],
            "detection_settings": {
                "check_artifacts": True,
                "artifact_threshold": 0.75
            }
        }
    
    def _get_default_forbidden_caps(self) -> Dict:
        """Retorna la lista por defecto de capitanes prohibidos"""
        return {
            "forbidden": [
                {
                    "name": "Amanitore",
                    "template_path": "assets/captains/amanitore.jpg",
                    "threshold": 0.85,
                    "enabled": True
                },
                {
                    "name": "Carter",
                    "template_path": "assets/captains/carter.jpg",
                    "threshold": 0.85,
                    "enabled": True
                }
            ],
            "detection_settings": {
                "strict_mode": True,
                "log_detections": True
            }
        }
    
    def _load_or_create_config(self, filename: str, default: Dict) -> Dict:
        """
        Carga un archivo de configuración o crea uno por defecto
        
        Args:
            filename: Nombre del archivo
            default: Configuración por defecto
            
        Returns:
            Configuración cargada o creada
        """
        config_path = self.config_dir / filename
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error cargando {filename}: {e}")
                print(f"Usando configuración por defecto")
                return default
        else:
            # Crear archivo con configuración por defecto
            self._save_config(filename, default)
            return default
    
    def _save_config(self, filename: str, config: Dict):
        """
        Guarda una configuración en archivo
        
        Args:
            filename: Nombre del archivo
            config: Configuración a guardar
        """
        config_path = self.config_dir / filename
        
        # Hacer backup si existe
        if config_path.exists():
            backup_path = config_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy(config_path, backup_path)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"Configuración guardada: {filename}")
        except Exception as e:
            print(f"Error guardando {filename}: {e}")
    
    def _load_assets_metadata(self):
        """Carga metadata de todos los assets disponibles"""
        self.assets_cache.clear()
        
        # Escanear directorio de assets
        for category_dir in self.assets_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                
                for asset_file in category_dir.glob("*"):
                    if asset_file.suffix.lower() in ['.jpg', '.png', '.jpeg']:
                        asset_name = asset_file.stem
                        
                        # Buscar configuración específica del asset
                        threshold = self._get_asset_threshold(asset_name, category)
                        
                        asset_config = AssetConfig(
                            name=asset_name,
                            path=str(asset_file),
                            category=category,
                            threshold=threshold,
                            enabled=self._is_asset_enabled(asset_name, category)
                        )
                        
                        self.assets_cache[f"{category}/{asset_name}"] = asset_config
    
    def _get_asset_threshold(self, name: str, category: str) -> float:
        """Obtiene el threshold específico para un asset"""
        default_threshold = self.app_config.get('template_matching', {}).get('default_threshold', 0.8)
        
        if category == "heroes":
            for hero in self.heroes_config.get('heroes', []):
                if hero['name'] == name:
                    return hero.get('threshold', default_threshold)
        elif category == "captains":
            for captain in self.forbidden_caps.get('forbidden', []):
                if captain['name'] == name:
                    return captain.get('threshold', default_threshold)
        
        return default_threshold
    
    def _is_asset_enabled(self, name: str, category: str) -> bool:
        """Verifica si un asset está habilitado"""
        if category == "heroes":
            for hero in self.heroes_config.get('heroes', []):
                if hero['name'] == name:
                    return hero.get('enabled', True)
        elif category == "captains":
            for captain in self.forbidden_caps.get('forbidden', []):
                if captain['name'] == name:
                    return captain.get('enabled', True)
        
        return True
    
    def get_coordinate(self, element: str) -> Optional[CoordinateConfig]:
        """
        Obtiene las coordenadas de un elemento
        
        Args:
            element: Nombre del elemento
            
        Returns:
            Configuración de coordenadas o None
        """
        if element in self.coordinates:
            coords = self.coordinates[element]
            return CoordinateConfig(
                x=coords['x'],
                y=coords['y'],
                width=coords['width'],
                height=coords['height']
            )
        return None
    
    def set_coordinate(self, element: str, x: int, y: int, width: int, height: int):
        """
        Establece las coordenadas de un elemento
        
        Args:
            element: Nombre del elemento
            x, y, width, height: Coordenadas
        """
        self.coordinates[element] = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        self._save_config("coordinates.json", self.coordinates)
    
    def add_hero(self, name: str, template_path: str, 
                threshold: float = 0.85, enabled: bool = True):
        """
        Añade un nuevo héroe a la configuración
        
        Args:
            name: Nombre del héroe
            template_path: Ruta al template
            threshold: Umbral de detección
            enabled: Si está habilitado
        """
        hero = {
            "name": name,
            "enabled": enabled,
            "template_path": template_path,
            "threshold": threshold
        }
        
        # Verificar si ya existe
        heroes_list = self.heroes_config.get('heroes', [])
        for i, h in enumerate(heroes_list):
            if h['name'] == name:
                heroes_list[i] = hero
                break
        else:
            heroes_list.append(hero)
        
        self.heroes_config['heroes'] = heroes_list
        self._save_config("heroes_list.json", self.heroes_config)
        self._load_assets_metadata()  # Recargar cache
    
    def add_forbidden_captain(self, name: str, template_path: str,
                            threshold: float = 0.85, enabled: bool = True):
        """
        Añade un capitán prohibido a la configuración
        
        Args:
            name: Nombre del capitán
            template_path: Ruta al template
            threshold: Umbral de detección
            enabled: Si está habilitado
        """
        captain = {
            "name": name,
            "template_path": template_path,
            "threshold": threshold,
            "enabled": enabled
        }
        
        # Verificar si ya existe
        forbidden_list = self.forbidden_caps.get('forbidden', [])
        for i, c in enumerate(forbidden_list):
            if c['name'] == name:
                forbidden_list[i] = captain
                break
        else:
            forbidden_list.append(captain)
        
        self.forbidden_caps['forbidden'] = forbidden_list
        self._save_config("forbidden_caps.json", self.forbidden_caps)
        self._load_assets_metadata()  # Recargar cache
    
    def remove_hero(self, name: str):
        """Elimina un héroe de la configuración"""
        heroes_list = self.heroes_config.get('heroes', [])
        self.heroes_config['heroes'] = [h for h in heroes_list if h['name'] != name]
        self._save_config("heroes_list.json", self.heroes_config)
        self._load_assets_metadata()
    
    def remove_forbidden_captain(self, name: str):
        """Elimina un capitán prohibido de la configuración"""
        forbidden_list = self.forbidden_caps.get('forbidden', [])
        self.forbidden_caps['forbidden'] = [c for c in forbidden_list if c['name'] != name]
        self._save_config("forbidden_caps.json", self.forbidden_caps)
        self._load_assets_metadata()
    
    def get_assets_by_category(self, category: str) -> List[AssetConfig]:
        """
        Obtiene todos los assets de una categoría
        
        Args:
            category: Categoría de assets
            
        Returns:
            Lista de configuraciones de assets
        """
        return [asset for key, asset in self.assets_cache.items() 
                if asset.category == category and asset.enabled]
    
    def get_enabled_heroes(self) -> List[Dict]:
        """Obtiene la lista de héroes habilitados"""
        return [hero for hero in self.heroes_config.get('heroes', []) 
                if hero.get('enabled', True)]
    
    def get_enabled_forbidden_captains(self) -> List[Dict]:
        """Obtiene la lista de capitanes prohibidos habilitados"""
        return [captain for captain in self.forbidden_caps.get('forbidden', [])
                if captain.get('enabled', True)]
    
    def update_app_setting(self, key: str, value: Any):
        """
        Actualiza una configuración de la aplicación
        
        Args:
            key: Clave de configuración (puede ser anidada con '.')
            value: Nuevo valor
        """
        keys = key.split('.')
        config = self.app_config
        
        # Navegar hasta la clave final
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Establecer el valor
        config[keys[-1]] = value
        
        # Guardar configuración
        self._save_config("app_config.json", self.app_config)
    
    def get_app_setting(self, key: str, default: Any = None) -> Any:
        """
        Obtiene una configuración de la aplicación
        
        Args:
            key: Clave de configuración (puede ser anidada con '.')
            default: Valor por defecto si no existe
            
        Returns:
            Valor de la configuración
        """
        keys = key.split('.')
        config = self.app_config
        
        try:
            for k in keys:
                config = config[k]
            return config
        except (KeyError, TypeError):
            return default
    
    def export_config(self, output_path: str):
        """
        Exporta toda la configuración a un archivo
        
        Args:
            output_path: Ruta del archivo de salida
        """
        all_config = {
            "app_config": self.app_config,
            "coordinates": self.coordinates,
            "heroes": self.heroes_config,
            "forbidden_captains": self.forbidden_caps,
            "assets": {key: asdict(asset) for key, asset in self.assets_cache.items()}
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_config, f, indent=4, ensure_ascii=False)
        
        print(f"Configuración exportada a {output_path}")
    
    def import_config(self, input_path: str):
        """
        Importa configuración desde un archivo
        
        Args:
            input_path: Ruta del archivo a importar
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                all_config = json.load(f)
            
            # Actualizar configuraciones
            if 'app_config' in all_config:
                self.app_config = all_config['app_config']
                self._save_config("app_config.json", self.app_config)
            
            if 'coordinates' in all_config:
                self.coordinates = all_config['coordinates']
                self._save_config("coordinates.json", self.coordinates)
            
            if 'heroes' in all_config:
                self.heroes_config = all_config['heroes']
                self._save_config("heroes_list.json", self.heroes_config)
            
            if 'forbidden_captains' in all_config:
                self.forbidden_caps = all_config['forbidden_captains']
                self._save_config("forbidden_caps.json", self.forbidden_caps)
            
            self._load_assets_metadata()
            print(f"Configuración importada desde {input_path}")
            
        except Exception as e:
            print(f"Error importando configuración: {e}")
    
    def reset_to_defaults(self):
        """Resetea toda la configuración a valores por defecto"""
        self.app_config = self._get_default_app_config()
        self.coordinates = self._get_default_coordinates()
        self.heroes_config = self._get_default_heroes()
        self.forbidden_caps = self._get_default_forbidden_caps()
        
        self._save_config("app_config.json", self.app_config)
        self._save_config("coordinates.json", self.coordinates)
        self._save_config("heroes_list.json", self.heroes_config)
        self._save_config("forbidden_caps.json", self.forbidden_caps)
        
        self._load_assets_metadata()
        print("Configuración reseteada a valores por defecto")
