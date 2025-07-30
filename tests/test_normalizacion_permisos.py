"""
Tests para la normalización de tipos de permisos.

Este módulo contiene tests que verifican:
1. Normalización de variantes de permisos sin goce
2. Manejo de acentos y espacios
3. Casos edge y valores nulos
"""

import pytest
from generar_reporte_optimizado import normalize_leave_type, POLITICA_PERMISOS


class TestNormalizacionPermisos:
    """Tests para la normalización de tipos de permisos."""

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            # Variantes básicas de permisos sin goce
            ("permiso sin goce", "permiso sin goce de sueldo"),
            ("sin goce de sueldo", "permiso sin goce de sueldo"),
            ("sin goce", "permiso sin goce de sueldo"),
            ("permiso sgs", "permiso sin goce de sueldo"),
            
            # Con acentos
            ("permiso sin goce de sueldo", "permiso sin goce de sueldo"),
            ("Permiso Sin Goce De Sueldo", "permiso sin goce de sueldo"),
            ("PERMISO SIN GOCE DE SUELDO", "permiso sin goce de sueldo"),
            
            # Con espacios extra
            ("  permiso sin goce  ", "permiso sin goce de sueldo"),
            ("  sin goce de sueldo  ", "permiso sin goce de sueldo"),
            ("\tpermiso sin goce\n", "permiso sin goce de sueldo"),
            
            # Otros tipos de permisos (no se normalizan)
            ("permiso médico", "permiso medico"),
            ("vacaciones", "vacaciones"),
            ("incapacidad", "incapacidad"),
            ("permiso con goce", "permiso con goce"),
        ]
    )
    def test_normalize_leave_type_variantes(self, input_type, expected):
        """Prueba la normalización de variantes de permisos."""
        result = normalize_leave_type(input_type)
        assert result == expected

    def test_normalize_leave_type_valores_nulos(self):
        """Prueba el manejo de valores nulos y vacíos."""
        assert normalize_leave_type("") == ""
        assert normalize_leave_type(None) == ""
        assert normalize_leave_type("   ") == ""

    def test_normalize_leave_type_caracteres_especiales(self):
        """Prueba el manejo de caracteres especiales."""
        # Con acentos
        assert normalize_leave_type("permiso médico") == "permiso medico"
        assert normalize_leave_type("incapacidad por enfermedad") == "incapacidad por enfermedad"
        
        # Con números
        assert normalize_leave_type("permiso día 1") == "permiso dia 1"
        
        # Con símbolos
        assert normalize_leave_type("permiso (especial)") == "permiso (especial)"

    def test_politica_permisos_consistencia(self):
        """Verifica que la política de permisos sea consistente con la normalización."""
        # Todos los tipos sin goce deben tener la política "no_ajustar"
        tipos_sin_goce = [
            "permiso sin goce de sueldo",
            "permiso sin goce",
            "sin goce de sueldo",
            "sin goce",
        ]
        
        for tipo in tipos_sin_goce:
            tipo_normalizado = normalize_leave_type(tipo)
            assert tipo_normalizado in POLITICA_PERMISOS
            assert POLITICA_PERMISOS[tipo_normalizado] == "no_ajustar"

    def test_normalize_leave_type_case_insensitive(self):
        """Prueba que la normalización sea insensible a mayúsculas/minúsculas."""
        variants = [
            "PERMISO SIN GOCE",
            "Permiso Sin Goce",
            "permiso sin goce",
            "PERMISO sin GOCE",
        ]
        
        for variant in variants:
            result = normalize_leave_type(variant)
            assert result == "permiso sin goce de sueldo"

    def test_normalize_leave_type_multiple_spaces(self):
        """Prueba el manejo de múltiples espacios."""
        variants = [
            "permiso   sin   goce",
            "  permiso  sin  goce  ",
            "\tpermiso\tsin\tgoce\t",
            "permiso\nsin\ngoce",
        ]
        
        for variant in variants:
            result = normalize_leave_type(variant)
            assert result == "permiso sin goce de sueldo"

    def test_normalize_leave_type_preserves_other_types(self):
        """Prueba que otros tipos de permisos no se normalicen incorrectamente."""
        other_types = [
            "vacaciones",
            "permiso con goce",
            "incapacidad por enfermedad",
            "permiso personal",
            "día festivo",
        ]
        
        for permiso_type in other_types:
            result = normalize_leave_type(permiso_type)
            # No debe convertirse en "permiso sin goce de sueldo"
            assert result != "permiso sin goce de sueldo"
            # Debe mantener su identidad (sin acentos)
            assert "sin goce" not in result.lower() 