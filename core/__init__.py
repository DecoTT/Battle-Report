"""
Core Package
Módulos principales para el sistema de scraping de datos del juego
"""

from .ocr_engine import OCREngine, OCRResult
from .template_matcher import TemplateMatcher, MatchResult
from .scroll_controller import ScrollController, ScrollDirection, ScrollState
from .config_manager import ConfigManager, CoordinateConfig, AssetConfig
from .data_parser import DataParser, ParseResult

__all__ = [
    'OCREngine',
    'OCRResult',
    'TemplateMatcher',
    'MatchResult',
    'ScrollController',
    'ScrollDirection',
    'ScrollState',
    'ConfigManager',
    'CoordinateConfig',
    'AssetConfig',
    'DataParser',
    'ParseResult'
]

__version__ = '1.0.0'
