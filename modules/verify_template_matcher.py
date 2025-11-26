"""
Script de Verificación Rápida - TemplateMatcher
Verifica que la configuración de TemplateMatcher esté correcta
"""

import sys
from pathlib import Path

# Añadir directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core import TemplateMatcher
    print("✅ Módulo TemplateMatcher importado correctamente")
except ImportError as e:
    print(f"❌ Error importando TemplateMatcher: {e}")
    sys.exit(1)

def verify_template_matcher_config():
    """Verifica que TemplateMatcher esté configurado correctamente"""
    print("\n" + "="*60)
    print("🔍 VERIFICANDO CONFIGURACIÓN DE TEMPLATE MATCHER")
    print("="*60 + "\n")
    
    # Crear instancia
    tm = TemplateMatcher()
    
    # Configurar como en battle_report_scraper.py
    tm.config['default_threshold'] = 0.78
    tm.config['multi_scale']['enabled'] = True
    tm.config['multi_scale']['min_scale'] = 0.9
    tm.config['multi_scale']['max_scale'] = 1.1
    tm.config['multi_scale']['scale_step'] = 0.05
    
    # Verificar configuración
    checks = [
        ("Threshold", tm.config['default_threshold'], 0.78),
        ("Multi-scale enabled", tm.config['multi_scale']['enabled'], True),
        ("Min scale", tm.config['multi_scale']['min_scale'], 0.9),
        ("Max scale", tm.config['multi_scale']['max_scale'], 1.1),
        ("Scale step", tm.config['multi_scale']['scale_step'], 0.05)
    ]
    
    all_ok = True
    for name, actual, expected in checks:
        status = "✅" if actual == expected else "❌"
        print(f"{status} {name}: {actual} {'(OK)' if actual == expected else f'(Esperado: {expected})'}")
        if actual != expected:
            all_ok = False
    
    print("\n" + "="*60)
    
    # Cargar héroes
    print("\n📁 VERIFICANDO CARGA DE HÉROES...")
    heroes_dir = Path("assets/heroes")
    
    if not heroes_dir.exists():
        print(f"❌ Directorio no existe: {heroes_dir}")
        print("   Crea el directorio y añade los templates de héroes (.jpg)")
        all_ok = False
    else:
        heroes = tm.load_templates_from_directory("heroes")
        print(f"✅ Directorio encontrado: {heroes_dir}")
        print(f"✅ Cargados {len(heroes)} héroes:")
        for hero_name in sorted(heroes.keys()):
            print(f"   - {hero_name}")
        
        if len(heroes) == 0:
            print("\n⚠️  No se encontraron héroes en assets/heroes/")
            print("   Asegúrate de tener archivos .jpg en ese directorio")
            all_ok = False
    
    print("\n" + "="*60)
    
    # Resultado final
    if all_ok:
        print("\n🎉 ¡TODO CORRECTO! TemplateMatcher está configurado perfectamente")
        print("   Deberías detectar TODOS los héroes al ejecutar el scraper")
    else:
        print("\n⚠️  HAY PROBLEMAS - Revisa los errores arriba")
        print("   Soluciona los problemas antes de ejecutar el scraper")
    
    print("\n" + "="*60 + "\n")
    
    return all_ok

if __name__ == "__main__":
    try:
        success = verify_template_matcher_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
