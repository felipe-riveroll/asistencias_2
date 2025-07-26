#!/usr/bin/env python3
"""
Script para ejecutar las pruebas unitarias desde la raíz del proyecto.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado."""
    print(f"🧪 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando: {e}")
        print(f"Salida de error: {e.stderr}")
        return False

def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print("🚀 Ejecutor de Pruebas - Sistema de Reportes de Asistencia")
        print("=" * 60)
        print("📋 COMANDOS DISPONIBLES:")
        print("  - python run_tests.py basic     # Pruebas básicas")
        print("  - python run_tests.py edge      # Casos edge")
        print("  - python run_tests.py all       # Todas las pruebas")
        print("  - python run_tests.py coverage  # Con cobertura")
        print("  - python run_tests.py fast      # Pruebas rápidas")
        print("  - python run_tests.py summary   # Este resumen")
        return 0
    
    command = sys.argv[1].lower()
    
    if command == "basic":
        success = run_command(
            "uv run python -m pytest tests/test_generar_reporte_optimizado.py -v",
            "Ejecutando pruebas unitarias básicas..."
        )
        print(f"\n🎯 Resultado pruebas básicas: {'✅ PASARON' if success else '❌ FALLARON'}")
        return 0 if success else 1
        
    elif command == "edge":
        success = run_command(
            "uv run python -m pytest tests/test_casos_edge.py -v",
            "Ejecutando pruebas de casos edge..."
        )
        print(f"\n🎯 Resultado casos edge: {'✅ PASARON' if success else '❌ FALLARON'}")
        return 0 if success else 1
        
    elif command == "all":
        success = run_command(
            "uv run python -m pytest tests/ -v",
            "Ejecutando todas las pruebas..."
        )
        print(f"\n🎯 Resultado todas las pruebas: {'✅ PASARON' if success else '❌ FALLARON'}")
        return 0 if success else 1
        
    elif command == "coverage":
        success = run_command(
            "uv run python -m pytest tests/ --cov=generar_reporte_optimizado --cov-report=term-missing --cov-report=html -v",
            "Ejecutando pruebas con cobertura de código..."
        )
        print(f"\n🎯 Resultado con cobertura: {'✅ PASARON' if success else '❌ FALLARON'}")
        return 0 if success else 1
        
    elif command == "fast":
        success = run_command(
            "uv run python -m pytest tests/ -m 'not slow' -v",
            "Ejecutando pruebas rápidas..."
        )
        print(f"\n🎯 Resultado pruebas rápidas: {'✅ PASARON' if success else '❌ FALLARON'}")
        return 0 if success else 1
        
    elif command == "summary":
        print("📋 RESUMEN DE PRUEBAS DISPONIBLES")
        print("=" * 60)
        
        test_files = [
            "tests/test_generar_reporte_optimizado.py",
            "tests/test_casos_edge.py"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"✅ {test_file}")
            else:
                print(f"❌ {test_file} (no encontrado)")
        
        print("\n🎯 COMANDOS DISPONIBLES:")
        print("  - python run_tests.py basic     # Pruebas básicas")
        print("  - python run_tests.py edge      # Casos edge")
        print("  - python run_tests.py all       # Todas las pruebas")
        print("  - python run_tests.py coverage  # Con cobertura")
        print("  - python run_tests.py fast      # Pruebas rápidas")
        print("  - python run_tests.py summary   # Este resumen")
        return 0
        
    else:
        print(f"❌ Comando desconocido: {command}")
        print("Usa 'python run_tests.py summary' para ver los comandos disponibles")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 