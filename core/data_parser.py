"""
Data Parser Module
Parser inteligente para extraer información de silver y otros formatos de juego
Maneja múltiples formatos y expresiones matemáticas
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import ast
import operator
from datetime import datetime

@dataclass
class ParseResult:
    """Resultado del parseo de datos"""
    original_text: str
    parsed_value: Optional[float]
    unit: Optional[str]
    parse_method: str
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None

class DataParser:
    """Parser especializado para datos del juego"""
    
    def __init__(self):
        """Inicializa el parser con patrones y configuración"""
        self.silver_patterns = self._init_silver_patterns()
        self.math_operators = self._init_math_operators()
        self.unit_multipliers = {
            'k': 1_000,
            'm': 1_000_000,
            'b': 1_000_000_000,
            't': 1_000_000_000_000,
            'mil': 1_000_000,
            'bill': 1_000_000_000
        }
        
    def _init_silver_patterns(self) -> List[Dict]:
        """Inicializa los patrones de regex para silver"""
        return [
            # Formato simple: "45b silver" o "39.1 plata"
            {
                'pattern': r'(\d+(?:\.\d+)?)\s*([kmbt]?)(?:\s*(?:silver|plata|oro|gold))?',
                'type': 'simple',
                'groups': ['value', 'unit']
            },
            # Formato con suma: "14 + 15 + 16 = 45b"
            {
                'pattern': r'([\d\s\+\-\*\/\(\)\.]+)\s*=\s*(\d+(?:\.\d+)?)\s*([kmbt]?)',
                'type': 'equation_result',
                'groups': ['equation', 'value', 'unit']
            },
            # Formato con CP: "CP 23valor = 39.1 Plata"
            {
                'pattern': r'CP\s*(\d+)\s*(?:valor)?\s*=\s*(\d+(?:\.\d+)?)\s*([kmbt]?)(?:\s*(?:silver|plata))?',
                'type': 'cp_value',
                'groups': ['cp_level', 'value', 'unit']
            },
            # Solo números con unidad: "45b" o "39.1m"
            {
                'pattern': r'^(\d+(?:\.\d+)?)\s*([kmbt])$',
                'type': 'number_unit',
                'groups': ['value', 'unit']
            },
            # Expresión matemática sola: "14 + 15 + 16"
            {
                'pattern': r'^([\d\s\+\-\*\/\(\)\.]+)$',
                'type': 'math_expression',
                'groups': ['expression']
            },
            # Formato con texto adicional: "mi contribución: 45b silver"
            {
                'pattern': r'(?:contribución|contribution|aporte|total|suma)[\s:]*(\d+(?:\.\d+)?)\s*([kmbt]?)',
                'type': 'contribution',
                'groups': ['value', 'unit']
            }
        ]
    
    def _init_math_operators(self) -> Dict:
        """Inicializa operadores matemáticos seguros"""
        return {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg
        }
    
    def parse_silver(self, text: str) -> ParseResult:
        """
        Parsea texto para extraer valores de silver
        
        Args:
            text: Texto a parsear
            
        Returns:
            Resultado del parseo con valor en billions
        """
        if not text:
            return ParseResult(
                original_text=text,
                parsed_value=None,
                unit=None,
                parse_method='empty',
                success=False,
                error_message="Texto vacío"
            )
        
        # Limpiar y normalizar texto
        text = text.strip().lower()
        
        # Intentar con cada patrón
        for pattern_info in self.silver_patterns:
            pattern = pattern_info['pattern']
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                groups = match.groups()
                
                try:
                    if pattern_info['type'] == 'simple':
                        value = float(groups[0])
                        unit = groups[1] if len(groups) > 1 else ''
                        final_value = self._apply_unit_multiplier(value, unit)
                        
                        return ParseResult(
                            original_text=text,
                            parsed_value=final_value,
                            unit=unit if unit else 'b',
                            parse_method=pattern_info['type'],
                            success=True
                        )
                    
                    elif pattern_info['type'] == 'equation_result':
                        # Usar el resultado de la ecuación
                        value = float(groups[1])
                        unit = groups[2] if len(groups) > 2 else ''
                        final_value = self._apply_unit_multiplier(value, unit)
                        
                        # Verificar la ecuación si es posible
                        equation = groups[0]
                        calc_value = self._safe_eval_math(equation)
                        
                        metadata = {
                            'equation': equation,
                            'calculated': calc_value,
                            'stated': final_value
                        }
                        
                        return ParseResult(
                            original_text=text,
                            parsed_value=final_value,
                            unit=unit if unit else 'b',
                            parse_method=pattern_info['type'],
                            success=True,
                            metadata=metadata
                        )
                    
                    elif pattern_info['type'] == 'cp_value':
                        cp_level = int(groups[0])
                        value = float(groups[1])
                        unit = groups[2] if len(groups) > 2 else ''
                        final_value = self._apply_unit_multiplier(value, unit)
                        
                        return ParseResult(
                            original_text=text,
                            parsed_value=final_value,
                            unit=unit if unit else 'b',
                            parse_method=pattern_info['type'],
                            success=True,
                            metadata={'cp_level': cp_level}
                        )
                    
                    elif pattern_info['type'] == 'number_unit':
                        value = float(groups[0])
                        unit = groups[1]
                        final_value = self._apply_unit_multiplier(value, unit)
                        
                        return ParseResult(
                            original_text=text,
                            parsed_value=final_value,
                            unit=unit,
                            parse_method=pattern_info['type'],
                            success=True
                        )
                    
                    elif pattern_info['type'] == 'math_expression':
                        expression = groups[0]
                        calc_value = self._safe_eval_math(expression)
                        
                        if calc_value is not None:
                            # Asumir que el resultado está en billions si no hay unidad
                            return ParseResult(
                                original_text=text,
                                parsed_value=calc_value * 1_000_000_000,
                                unit='b',
                                parse_method=pattern_info['type'],
                                success=True,
                                metadata={'expression': expression}
                            )
                    
                    elif pattern_info['type'] == 'contribution':
                        value = float(groups[0])
                        unit = groups[1] if len(groups) > 1 else ''
                        final_value = self._apply_unit_multiplier(value, unit)
                        
                        return ParseResult(
                            original_text=text,
                            parsed_value=final_value,
                            unit=unit if unit else 'b',
                            parse_method=pattern_info['type'],
                            success=True
                        )
                    
                except (ValueError, IndexError) as e:
                    continue
        
        # Si ningún patrón coincide, intentar extraer cualquier número
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            try:
                # Tomar el número más grande encontrado
                value = max(float(n) for n in numbers)
                
                # Buscar indicios de unidad en el texto
                unit = 'b'  # Por defecto billions
                if any(word in text for word in ['mil', 'million', 'm']):
                    unit = 'm'
                elif any(word in text for word in ['thousand', 'k']):
                    unit = 'k'
                elif any(word in text for word in ['trillion', 't']):
                    unit = 't'
                
                final_value = self._apply_unit_multiplier(value, unit)
                
                return ParseResult(
                    original_text=text,
                    parsed_value=final_value,
                    unit=unit,
                    parse_method='fallback_number',
                    success=True,
                    error_message="Parseo aproximado"
                )
            except:
                pass
        
        # No se pudo parsear
        return ParseResult(
            original_text=text,
            parsed_value=None,
            unit=None,
            parse_method='failed',
            success=False,
            error_message="No se pudo extraer valor de silver"
        )
    
    def _apply_unit_multiplier(self, value: float, unit: str) -> float:
        """
        Aplica el multiplicador de unidad al valor
        
        Args:
            value: Valor base
            unit: Unidad (k, m, b, t)
            
        Returns:
            Valor en unidades base (normalmente convertido a valor real)
        """
        if not unit:
            # Si no hay unidad, asumir que ya está en billions para silver
            return value * 1_000_000_000
        
        unit = unit.lower()
        multiplier = self.unit_multipliers.get(unit, 1)
        return value * multiplier
    
    def _safe_eval_math(self, expression: str) -> Optional[float]:
        """
        Evalúa de forma segura una expresión matemática
        
        Args:
            expression: Expresión matemática como string
            
        Returns:
            Resultado de la evaluación o None si falla
        """
        try:
            # Limpiar la expresión
            expression = expression.replace(' ', '')
            
            # Parser seguro usando AST
            node = ast.parse(expression, mode='eval')
            
            def _eval(node):
                if isinstance(node, ast.Expression):
                    return _eval(node.body)
                elif isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.Num):  # Python < 3.8
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = _eval(node.left)
                    right = _eval(node.right)
                    return self.math_operators[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = _eval(node.operand)
                    return self.math_operators[type(node.op)](operand)
                else:
                    raise ValueError(f"Tipo de nodo no soportado: {type(node)}")
            
            result = _eval(node.body)
            return float(result)
            
        except Exception as e:
            print(f"Error evaluando expresión '{expression}': {e}")
            return None
    
    def parse_player_name(self, text: str) -> Optional[str]:
        """
        Extrae el nombre del jugador del texto
        
        Args:
            text: Texto que contiene el nombre del jugador
            
        Returns:
            Nombre del jugador o None
        """
        # Limpiar texto
        text = text.strip()
        
        # Patrones comunes para nombres de jugador
        patterns = [
            r'(?:Player|Jugador|User|Usuario)[\s:]+([^\n\r]+)',
            r'(?:Name|Nombre)[\s:]+([^\n\r]+)',
            r'^([A-Za-z0-9_\-\s]+?)[\s:]+\d',  # Nombre seguido de números
            r'\[([^\]]+)\]',  # Nombre entre corchetes
            r'^([A-Za-z0-9_\-]+)',  # Nombre simple al inicio
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validar que es un nombre razonable
                if 2 <= len(name) <= 30 and not name.isdigit():
                    return name
        
        # Si no hay patrones, tomar la primera palabra que parece un nombre
        words = text.split()
        for word in words:
            if 2 <= len(word) <= 30 and not word.isdigit():
                return word
        
        return None
    
    def parse_battle_time(self, text: str) -> Optional[datetime]:
        """
        Extrae información de tiempo/fecha de batalla
        
        Args:
            text: Texto con información de tiempo
            
        Returns:
            datetime o None
        """
        # Patrones de fecha/hora comunes
        patterns = [
            r'(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})',  # 2025-10-27 14:30
            r'(\d{2}[-/]\d{2}[-/]\d{4}\s+\d{2}:\d{2})',  # 27/10/2025 14:30
            r'(\d{2}:\d{2}:\d{2})',  # Solo hora
            r'(\d{2}[-/]\d{2})',  # Solo fecha corta
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                time_str = match.group(1)
                
                # Intentar parsear con diferentes formatos
                formats = [
                    '%Y-%m-%d %H:%M',
                    '%d/%m/%Y %H:%M',
                    '%d-%m-%Y %H:%M',
                    '%H:%M:%S',
                    '%d/%m',
                    '%d-%m'
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(time_str, fmt)
                    except ValueError:
                        continue
        
        return None
    
    def parse_multiline_chat(self, lines: List[str]) -> List[ParseResult]:
        """
        Parsea múltiples líneas de chat
        
        Args:
            lines: Lista de líneas de texto
            
        Returns:
            Lista de resultados de parseo
        """
        results = []
        combined_text = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detectar si es continuación o nueva entrada
            if re.match(r'^[A-Za-z0-9_\-\[\]]+[\s:]+', line):
                # Nueva entrada - procesar la anterior si existe
                if combined_text:
                    result = self.parse_silver(combined_text)
                    results.append(result)
                combined_text = line
            else:
                # Continuación de la entrada anterior
                combined_text += " " + line
        
        # Procesar la última entrada
        if combined_text:
            result = self.parse_silver(combined_text)
            results.append(result)
        
        return results
    
    def extract_numbers(self, text: str) -> List[float]:
        """
        Extrae todos los números de un texto
        
        Args:
            text: Texto a procesar
            
        Returns:
            Lista de números encontrados
        """
        # Encontrar todos los números (enteros y decimales)
        pattern = r'-?\d+(?:\.\d+)?'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                numbers.append(float(match))
            except ValueError:
                continue
        
        return numbers
    
    def format_silver_value(self, value: float, precision: int = 1) -> str:
        """
        Formatea un valor de silver para mostrar
        
        Args:
            value: Valor en unidades base
            precision: Decimales a mostrar
            
        Returns:
            String formateado (ej: "45.5b")
        """
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.{precision}f}t"
        elif value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.{precision}f}b"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.{precision}f}m"
        elif value >= 1_000:
            return f"{value / 1_000:.{precision}f}k"
        else:
            return f"{value:.{precision}f}"
    
    def validate_silver_range(self, value: float, 
                            min_expected: float = 1_000_000,
                            max_expected: float = 1_000_000_000_000) -> bool:
        """
        Valida si un valor de silver está en un rango esperado
        
        Args:
            value: Valor a validar
            min_expected: Valor mínimo esperado
            max_expected: Valor máximo esperado
            
        Returns:
            True si está en rango, False si no
        """
        return min_expected <= value <= max_expected
    
    def parse_artifact_info(self, text: str) -> Dict[str, Any]:
        """
        Parsea información de artefactos
        
        Args:
            text: Texto con información de artefactos
            
        Returns:
            Diccionario con información parseada
        """
        info = {
            'has_artifacts': False,
            'artifact_count': 0,
            'artifact_names': []
        }
        
        # Buscar indicadores de artefactos
        artifact_indicators = [
            'artifact', 'artefacto', 'equip', 'gear',
            'item', 'objeto', 'equipamiento'
        ]
        
        text_lower = text.lower()
        
        for indicator in artifact_indicators:
            if indicator in text_lower:
                info['has_artifacts'] = True
                break
        
        # Buscar números asociados con artefactos
        if info['has_artifacts']:
            numbers = self.extract_numbers(text)
            if numbers:
                info['artifact_count'] = int(numbers[0]) if numbers[0] < 10 else 0
        
        # Buscar nombres específicos de artefactos (personalizable)
        artifact_patterns = [
            r'(?:artifact|artefacto)[\s:]+([^\n\r,]+)',
        ]
        
        for pattern in artifact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            info['artifact_names'].extend(matches)
        
        return info
