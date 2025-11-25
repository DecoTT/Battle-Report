# Game Data Scraper Suite

Sistema integral de captura y análisis de datos para juegos, especializado en extracción de información de chats y reportes de batalla.

## 🚀 Características Principales

### Módulos Core
- **OCR Engine**: Motor unificado para OCR con soporte para Tesseract y EasyOCR
- **Template Matcher**: Sistema avanzado de template matching con cache y multi-escala
- **Scroll Controller**: Control inteligente de scroll con detección de contenido nuevo
- **Config Manager**: Gestión centralizada de configuración y assets
- **Data Parser**: Parser especializado para extracción de valores de silver

### Módulos Principales

#### 1. Dommy Chat Scraper
- Captura automática de mensajes del chat
- Detección de marcadores de inicio/fin (*****) 
- Parseo inteligente de valores de silver (45b, 39.1, etc.)
- Soporte para formatos multilinea y expresiones matemáticas
- Exportación con nomenclatura DC_YYYYMMDD

#### 2. Battle Report Scraper
- Análisis automatizado de reportes de batalla
- Detección de participantes mediante template matching
- Identificación de héroes y verificación de artefactos
- Detección de capitanes prohibidos
- Navegación inteligente entre ventanas emergentes
- Exportación con nomenclatura BR_YYYYMMDD

#### 3. Categorizer Report
- Combinación de datos de chat y batalla
- Generación de reportes en Excel/CSV/JSON
- Cálculo automático de estadísticas
- Validación de participación
- Parser matemático para silver

### Herramientas de Desarrollo

#### Asset Extractor
- Captura de pantalla con selección de región
- Recorte y etiquetado de assets
- Guardado automático con categorización
- Integración con configuración

#### Coordinate Finder
- Detección de coordenadas en tiempo real
- Captura de puntos y regiones
- Preview con crosshair
- Exportación a JSON

#### Asset Manager
- Gestión CRUD de héroes y capitanes
- Control de listas permitidas/prohibidas
- Sistema de backups
- Importación/exportación masiva

## 📋 Requisitos

### Software
- Python 3.8 o superior
- Tesseract OCR instalado
- Windows 10/11 (para algunas funciones de automatización)

### Librerías Python
```bash
pip install -r requirements.txt
```

## 🛠️ Instalación

1. **Clonar el repositorio o descomprimir el archivo**
```bash
cd GameDataScraperSuite
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Instalar Tesseract OCR**
   - Windows: Descargar desde [GitHub Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - Añadir al PATH o configurar la ruta en el código

4. **Inicializar la estructura del proyecto**
```bash
python setup.py
```

## 🎮 Uso Rápido

### Aplicación Principal
```bash
python main.py
```

### Herramientas Individuales

**Asset Extractor:**
```bash
python tools/asset_extractor.py
```

**Coordinate Finder:**
```bash
python tools/coord_finder.py
```

**Asset Manager:**
```bash
python tools/asset_manager.py
```

## 📁 Estructura del Proyecto

```
GameDataScraperSuite/
│
├── 📁 modules/              # Módulos principales
│   ├── dommy_chat_scraper.py
│   ├── battle_report_scraper.py
│   └── categorizer_report.py
│
├── 📁 core/                 # Módulos core reutilizables
│   ├── ocr_engine.py
│   ├── template_matcher.py
│   ├── scroll_controller.py
│   ├── config_manager.py
│   └── data_parser.py
│
├── 📁 assets/               # Assets del juego
│   ├── 📁 heroes/
│   ├── 📁 captains/
│   ├── 📁 ui_elements/
│   └── 📁 templates/
│
├── 📁 config/               # Archivos de configuración
│   ├── app_config.json
│   ├── coordinates.json
│   ├── heroes_list.json
│   └── forbidden_caps.json
│
├── 📁 data/                 # Datos procesados
│   ├── 📁 chat_logs/
│   ├── 📁 battle_reports/
│   └── 📁 excel_reports/
│
├── 📁 tools/                # Herramientas de desarrollo
│   ├── asset_extractor.py
│   ├── coord_finder.py
│   └── asset_manager.py
│
├── main.py                  # Aplicación principal
├── requirements.txt
└── README.md
```

## 🔧 Configuración

### Configuración de OCR
Editar `config/app_config.json`:
```json
{
  "ocr_settings": {
    "engine": "tesseract",
    "language": "spa+eng",
    "confidence_threshold": 60
  }
}
```

### Configuración de Template Matching
```json
{
  "template_matching": {
    "method": "CCOEFF_NORMED",
    "default_threshold": 0.8,
    "multiscale": true
  }
}
```

### Añadir un Nuevo Héroe

1. **Usando Asset Manager:**
   - Abrir `tools/asset_manager.py`
   - Click en "Nuevo" en la pestaña de Héroes
   - Seleccionar imagen y configurar threshold

2. **Manualmente:**
   - Copiar imagen a `assets/heroes/nombre.jpg`
   - Editar `config/heroes_list.json`

### Definir Capitanes Prohibidos

1. **Usando Asset Manager:**
   - Abrir `tools/asset_manager.py`
   - Pestaña "Capitanes Prohibidos"
   - Click en "Nuevo" y configurar

2. **Manualmente:**
   - Copiar imagen a `assets/captains/nombre.jpg`
   - Editar `config/forbidden_caps.json`

## 📊 Formatos de Datos

### Chat Log (DC_YYYYMMDD.json)
```json
{
  "date": "2025-10-27",
  "chat_name": "Dommy Monday",
  "participants": [
    {
      "name": "Player1",
      "raw_message": "14 + 15 + 16 = 45b silver",
      "parsed_silver": 45000000000,
      "parse_success": true
    }
  ]
}
```

### Battle Report (BR_YYYYMMDD.json)
```json
{
  "date": "2025-10-27",
  "participants": [
    {
      "name": "Player1",
      "artifacts_used": false,
      "forbidden_captains": [],
      "participated": true
    }
  ]
}
```

## 🎯 Casos de Uso

### Capturar Chat Diario

1. Abrir la aplicación principal
2. Ir a la pestaña "Dommy Chat"
3. Configurar nombre del chat y fecha
4. Click en "Iniciar Captura"
5. El programa buscará el marcador y capturará todo el texto

### Analizar Reporte de Batalla

1. Abrir reporte de batalla en el juego
2. Ir a la pestaña "Battle Report"
3. Click en "Iniciar Análisis"
4. El programa navegará automáticamente detectando participantes

### Generar Reporte Combinado

1. Ir a la pestaña "Categorizer"
2. Seleccionar archivo de chat (DC_*.json)
3. Seleccionar archivo de batalla (BR_*.json)
4. Configurar formato de salida
5. Click en "Generar Reporte"

## 🐛 Solución de Problemas

### Error: "Tesseract no encontrado"
- Instalar Tesseract OCR
- Añadir al PATH del sistema
- O configurar ruta en `pytesseract.pytesseract.tesseract_cmd`

### Templates no detectados
- Verificar calidad de imagen del template
- Ajustar threshold en Asset Manager
- Probar con diferentes métodos de matching

### Error de parseo de silver
- Verificar formato del texto
- Revisar patrones en `core/data_parser.py`
- Añadir nuevo patrón si es necesario

## 📈 Optimización y Performance

### Caché de Templates
- Los templates se cachean automáticamente
- Limpiar caché si hay problemas: `template_matcher.clear_cache()`

### Procesamiento por Lotes
- Usar `batch_extract()` para múltiples imágenes
- Configurar `multi_scale` según necesidad

### Configuración de Debug
```python
config_manager.update_app_setting('debug_mode', True)
```

## 🤝 Contribución

### Añadir Nuevo Parser
1. Editar `core/data_parser.py`
2. Añadir patrón a `silver_patterns`
3. Implementar lógica de parseo
4. Añadir tests

### Crear Nuevo Módulo
1. Heredar de clases base en `core/`
2. Implementar interfaz requerida
3. Añadir a `main.py`
4. Documentar uso

## 📝 Notas de Desarrollo

- El sistema usa coordenadas absolutas de pantalla
- Los templates deben ser de buena calidad (preferiblemente PNG)
- El OCR funciona mejor con texto negro sobre fondo blanco
- Para mejor detección, capturar templates en la misma resolución de uso

## ⚠️ Limitaciones Conocidas

- Requiere resolución consistente para template matching
- OCR puede fallar con fuentes muy estilizadas
- El scroll automático requiere que la ventana esté visible
- Algunos elementos del juego pueden cambiar entre versiones

## 📜 Licencia

© 2025 Decoding - Total Alliance
Todos los derechos reservados.

## 🆘 Soporte

Para soporte o reportar bugs, contactar al equipo de desarrollo.

---

**Versión:** 1.0.0  
**Última actualización:** Octubre 2025
