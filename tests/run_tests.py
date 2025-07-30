#!/usr/bin/env python3
"""
Script para ejecutar las pruebas unitarias con pytest del sistema de reportes de asistencia.
"""

import pytest
import sys
import os

# Agregar el directorio padre al path para importar los módulos principales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_basic_tests():
    """Ejecuta las pruebas básicas con pytest."""
    print("🧪 Ejecutando pruebas unitarias básicas con pytest...")
    print("=" * 60)

    # Ejecutar pruebas básicas
    exit_code = pytest.main(
        [
            "test_generar_reporte_optimizado.py",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    return exit_code == 0


def run_edge_case_tests():
    """Ejecuta las pruebas de casos edge con pytest."""
    print("\n🧪 Ejecutando pruebas de casos edge con pytest...")
    print("=" * 60)

    # Ejecutar pruebas de casos edge
    exit_code = pytest.main(
        [
            "test_casos_edge.py",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    return exit_code == 0


def run_all_tests():
    """Ejecuta todas las pruebas con pytest."""
    print("🧪 Ejecutando todas las pruebas con pytest...")
    print("=" * 60)

    # Ejecutar todas las pruebas
    exit_code = pytest.main(
        [
            "test_generar_reporte_optimizado.py",
            "test_casos_edge.py",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    return exit_code == 0


def run_specific_test(test_path):
    """Ejecuta una prueba específica."""
    print(f"🧪 Ejecutando prueba específica: {test_path}")
    print("=" * 60)

    exit_code = pytest.main(
        [test_path, "-v", "--tb=short", "--strict-markers", "--disable-warnings"]
    )

    return exit_code == 0


def run_tests_with_coverage():
    """Ejecuta las pruebas con cobertura de código."""
    print("🧪 Ejecutando pruebas con cobertura de código...")
    print("=" * 60)

    # Verificar si pytest-cov está instalado
    try:
        import pytest_cov
    except ImportError:
        print("❌ pytest-cov no está instalado. Instalando...")
        os.system("uv add pytest-cov")

    # Ejecutar pruebas con cobertura
    exit_code = pytest.main(
        [
            "test_generar_reporte_optimizado.py",
            "test_casos_edge.py",
            "--cov=generar_reporte_optimizado",
            "--cov-report=term-missing",
            "--cov-report=html",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    return exit_code == 0


def run_fast_tests():
    """Ejecuta solo las pruebas rápidas (sin mocks complejos)."""
    print("🧪 Ejecutando pruebas rápidas...")
    print("=" * 60)

    # Ejecutar pruebas marcadas como rápidas
    exit_code = pytest.main(
        [
            "test_generar_reporte_optimizado.py",
            "test_casos_edge.py",
            "-m",
            "not slow",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings",
        ]
    )

    return exit_code == 0


def show_test_summary():
    """Muestra un resumen de las pruebas disponibles."""
    print("📋 RESUMEN DE PRUEBAS DISPONIBLES")
    print("=" * 60)

    test_files = ["test_generar_reporte_optimizado.py", "test_casos_edge.py"]

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


def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print("🚀 Ejecutor de Pruebas Pytest - Sistema de Reportes de Asistencia")
        print("=" * 60)
        show_test_summary()
        return 0

    command = sys.argv[1].lower()

    if command == "basic":
        success = run_basic_tests()
        print(
            f"\n🎯 Resultado pruebas básicas: {'✅ PASARON' if success else '❌ FALLARON'}"
        )
        return 0 if success else 1

    elif command == "edge":
        success = run_edge_case_tests()
        print(
            f"\n🎯 Resultado casos edge: {'✅ PASARON' if success else '❌ FALLARON'}"
        )
        return 0 if success else 1

    elif command == "all":
        success = run_all_tests()
        print(
            f"\n🎯 Resultado todas las pruebas: {'✅ PASARON' if success else '❌ FALLARON'}"
        )
        return 0 if success else 1

    elif command == "coverage":
        success = run_tests_with_coverage()
        print(
            f"\n🎯 Resultado con cobertura: {'✅ PASARON' if success else '❌ FALLARON'}"
        )
        return 0 if success else 1

    elif command == "fast":
        success = run_fast_tests()
        print(
            f"\n🎯 Resultado pruebas rápidas: {'✅ PASARON' if success else '❌ FALLARON'}"
        )
        return 0 if success else 1

    elif command == "summary":
        show_test_summary()
        return 0

    elif command.startswith("test_"):
        # Ejecutar una prueba específica
        success = run_specific_test(command)
        print(
            f"\n🎯 Resultado prueba específica: {'✅ PASÓ' if success else '❌ FALLÓ'}"
        )
        return 0 if success else 1

    else:
        print(f"❌ Comando desconocido: {command}")
        show_test_summary()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
