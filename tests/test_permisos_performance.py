"""
Pruebas de rendimiento y casos extremos para la integración de permisos.
"""

import pytest
import pandas as pd
from datetime import date, timedelta
import time
import sys
import os

# Importar las funciones a probar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generar_reporte_optimizado import (
    procesar_permisos_empleados,
    ajustar_horas_esperadas_con_permisos,
    clasificar_faltas_con_permisos,
)


class TestRendimientoPermisos:
    """Pruebas de rendimiento para la funcionalidad de permisos"""

    def test_procesar_gran_volumen_permisos(self):
        """Prueba con gran volumen de permisos (1000+ registros)"""
        # Generar 1000 permisos para 100 empleados durante 365 días
        large_leave_data = []
        start_date = date(2025, 1, 1)

        for emp_id in range(1, 101):  # 100 empleados
            for day_offset in range(0, 365, 30):  # Un permiso cada 30 días
                current_date = start_date + timedelta(days=day_offset)
                large_leave_data.append(
                    {
                        "employee": str(emp_id),
                        "employee_name": f"Employee {emp_id}",
                        "leave_type": "Vacaciones",
                        "from_date": current_date.strftime("%Y-%m-%d"),
                        "to_date": (current_date + timedelta(days=2)).strftime(
                            "%Y-%m-%d"
                        ),
                        "status": "Approved",
                    }
                )

        # Medir tiempo de procesamiento
        start_time = time.time()
        result = procesar_permisos_empleados(large_leave_data)
        processing_time = time.time() - start_time

        # Verificar que se procesó correctamente
        assert len(result) == 100  # 100 empleados
        assert processing_time < 5.0  # Debería completarse en menos de 5 segundos

        # Verificar algunos datos específicos
        assert "1" in result
        assert "100" in result

        # Cada empleado debería tener múltiples días con permiso
        for emp_id in ["1", "50", "100"]:
            assert len(result[emp_id]) > 10  # Al menos 10 días con permiso

    def test_ajustar_dataframe_grande(self):
        """Prueba con DataFrame grande (10,000+ filas)"""
        # Generar DataFrame grande
        employees = [str(i) for i in range(1, 101)]  # 100 empleados
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(100)]  # 100 días

        large_df_data = []
        for emp in employees:
            for d in dates:
                large_df_data.append(
                    {
                        "employee": emp,
                        "dia": d,
                        "horas_esperadas": "8:00:00",
                        "tipo_retardo": "A Tiempo",
                    }
                )

        large_df = pd.DataFrame(large_df_data)  # 10,000 filas

        # Permisos para algunos empleados
        permisos_dict = {
            "1": {
                dates[0]: {"leave_type": "Vacaciones", "employee_name": "Employee 1"}
            },
            "50": {
                dates[50]: {"leave_type": "Incapacidad", "employee_name": "Employee 50"}
            },
            "100": {
                dates[99]: {"leave_type": "Permiso", "employee_name": "Employee 100"}
            },
        }

        cache_horarios = {
            str(i): {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}
            for i in range(1, 101)
        }

        # Medir tiempo
        start_time = time.time()
        result = ajustar_horas_esperadas_con_permisos(
            large_df, permisos_dict, cache_horarios
        )
        processing_time = time.time() - start_time

        # Verificar rendimiento y correctitud
        assert len(result) == 10000
        assert processing_time < 10.0  # Máximo 10 segundos
        assert "tiene_permiso" in result.columns
        assert result["tiene_permiso"].sum() == 3  # Solo 3 días con permiso


class TestCasosExtremos:
    """Pruebas para casos extremos y edge cases"""

    def test_permiso_fecha_invalida(self):
        """Prueba con fechas inválidas en permisos"""
        invalid_leave_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-13-01",  # Mes inválido
                "to_date": "2025-12-01",
                "status": "Approved",
            }
        ]

        # Debería manejar la excepción graciosamente
        with pytest.raises(ValueError):
            procesar_permisos_empleados(invalid_leave_data)

    def test_permiso_rango_fechas_invertido(self):
        """Prueba con rango de fechas invertido (to_date < from_date)"""
        inverted_leave_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-20",
                "to_date": "2025-07-15",  # Fecha final anterior a inicial
                "status": "Approved",
            }
        ]

        result = procesar_permisos_empleados(inverted_leave_data)

        # El resultado debe estar vacío o manejar el caso correctamente
        assert "1" not in result or len(result["1"]) == 0

    def test_empleado_codigo_muy_largo(self):
        """Prueba con código de empleado extremadamente largo"""
        long_code_data = [
            {
                "employee": "A" * 1000,  # Código de 1000 caracteres
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
            }
        ]

        result = procesar_permisos_empleados(long_code_data)

        # Debería procesar correctamente
        long_key = "A" * 1000
        assert long_key in result
        assert date(2025, 7, 16) in result[long_key]

    def test_permiso_año_muy_futuro(self):
        """Prueba con permisos en año muy futuro"""
        future_leave_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "3025-07-16",  # Año 3025
                "to_date": "3025-07-16",
                "status": "Approved",
            }
        ]

        result = procesar_permisos_empleados(future_leave_data)

        # Debería procesar sin errores
        assert "1" in result
        assert date(3025, 7, 16) in result["1"]

    def test_dataframe_solo_una_fila(self):
        """Prueba con DataFrame de una sola fila"""
        single_row_df = pd.DataFrame(
            {
                "employee": ["1"],
                "dia": [date(2025, 7, 16)],
                "horas_esperadas": ["8:00:00"],
                "tipo_retardo": ["Falta"],
                "es_falta": [1],
            }
        )

        permisos_dict = {
            "1": {
                date(2025, 7, 16): {
                    "leave_type": "Vacaciones",
                    "employee_name": "Test Employee",
                }
            }
        }

        cache_horarios = {
            "1": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}
        }

        # Ajustar horas
        result_ajuste = ajustar_horas_esperadas_con_permisos(
            single_row_df.copy(), permisos_dict, cache_horarios
        )

        # Clasificar faltas
        result_final = clasificar_faltas_con_permisos(result_ajuste)

        # Verificar resultado
        assert len(result_final) == 1
        assert result_final.iloc[0]["tiene_permiso"] == True
        assert result_final.iloc[0]["falta_justificada"] == True

    def test_permiso_mismo_dia_multiples_tipos(self):
        """Prueba con múltiples permisos el mismo día (caso raro pero posible)"""
        duplicate_day_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Incapacidad",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
            },
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Permiso Personal",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
            },
        ]

        result = procesar_permisos_empleados(duplicate_day_data)

        # Solo debe mantener el último permiso procesado
        assert "1" in result
        assert date(2025, 7, 16) in result["1"]
        # El tipo de permiso será el del último procesado
        assert result["1"][date(2025, 7, 16)]["leave_type"] == "Permiso Personal"


class TestIntegracionRobustez:
    """Pruebas de robustez e integración completa"""

    def test_flujo_completo_con_datos_faltantes(self):
        """Prueba flujo completo con algunos datos faltantes"""
        # Datos con algunos campos faltantes o None
        leave_data_incomplete = [
            {
                "employee": "1",
                "employee_name": None,  # Nombre faltante
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-16",
                "status": "Approved",
            },
            {
                "employee": "2",
                "employee_name": "Employee 2",
                "leave_type": None,  # Tipo faltante
                "from_date": "2025-07-17",
                "to_date": "2025-07-17",
                "status": "Approved",
            },
        ]

        df_test = pd.DataFrame(
            {
                "employee": ["1", "1", "2", "2"],
                "dia": [
                    date(2025, 7, 16),
                    date(2025, 7, 17),
                    date(2025, 7, 16),
                    date(2025, 7, 17),
                ],
                "horas_esperadas": ["8:00:00", "8:00:00", "8:00:00", "8:00:00"],
                "tipo_retardo": ["Falta", "A Tiempo", "A Tiempo", "Falta"],
                "es_falta": [1, 0, 0, 1],
            }
        )

        cache_horarios = {
            "1": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
            "2": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None},
        }

        # Procesar permisos
        permisos_dict = procesar_permisos_empleados(leave_data_incomplete)

        # Ajustar horas
        df_ajustado = ajustar_horas_esperadas_con_permisos(
            df_test.copy(), permisos_dict, cache_horarios
        )

        # Clasificar faltas
        df_final = clasificar_faltas_con_permisos(df_ajustado)

        # Verificar que el proceso completó sin errores
        assert len(df_final) == 4
        assert "tiene_permiso" in df_final.columns
        assert "falta_justificada" in df_final.columns

        # Verificar que los permisos se aplicaron correctamente
        emp1_dia16 = df_final[
            (df_final["employee"] == "1") & (df_final["dia"] == date(2025, 7, 16))
        ]
        emp2_dia17 = df_final[
            (df_final["employee"] == "2") & (df_final["dia"] == date(2025, 7, 17))
        ]

        assert len(emp1_dia16) == 1
        assert len(emp2_dia17) == 1
        assert emp1_dia16.iloc[0]["tiene_permiso"] == True
        assert emp2_dia17.iloc[0]["tiene_permiso"] == True

    def test_consistencia_multiples_ejecuciones(self):
        """Verificar que múltiples ejecuciones producen resultados consistentes"""
        leave_data = [
            {
                "employee": "1",
                "employee_name": "Test Employee",
                "leave_type": "Vacaciones",
                "from_date": "2025-07-16",
                "to_date": "2025-07-17",
                "status": "Approved",
            }
        ]

        df_test = pd.DataFrame(
            {
                "employee": ["1", "1"],
                "dia": [date(2025, 7, 16), date(2025, 7, 17)],
                "horas_esperadas": ["8:00:00", "8:00:00"],
                "tipo_retardo": ["Falta", "Falta"],
                "es_falta": [1, 1],
            }
        )

        cache_horarios = {
            "1": {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None}
        }

        # Ejecutar el proceso múltiples veces
        results = []
        for i in range(5):
            permisos_dict = procesar_permisos_empleados(leave_data)
            df_ajustado = ajustar_horas_esperadas_con_permisos(
                df_test.copy(), permisos_dict, cache_horarios
            )
            df_final = clasificar_faltas_con_permisos(df_ajustado)
            results.append(df_final.copy())

        # Verificar que todos los resultados son idénticos
        for i in range(1, 5):
            pd.testing.assert_frame_equal(
                results[0].sort_values(["employee", "dia"]).reset_index(drop=True),
                results[i].sort_values(["employee", "dia"]).reset_index(drop=True),
                check_dtype=False,
            )


class TestMemoriaYRecursos:
    """Pruebas de uso de memoria y recursos"""

    def test_uso_memoria_con_datos_grandes(self):
        """Verificar que el procesamiento sea eficiente con datos grandes"""
        # Crear datos grandes
        large_leave_data = []
        for i in range(5000):  # 5000 permisos
            large_leave_data.append(
                {
                    "employee": str(i % 100),  # 100 empleados únicos
                    "employee_name": f"Employee {i % 100}",
                    "leave_type": "Vacaciones",
                    "from_date": "2025-07-16",
                    "to_date": "2025-07-18",
                    "status": "Approved",
                }
            )

        # Procesar datos y medir tiempo
        start_time = time.time()
        result = procesar_permisos_empleados(large_leave_data)
        processing_time = time.time() - start_time

        # Verificar eficiencia
        assert len(result) <= 100  # No más de 100 empleados únicos
        assert processing_time < 30.0  # Máximo 30 segundos para 5000 registros

        # Verificar que el resultado tiene sentido
        assert len(result) > 0
        for emp_id, permisos in result.items():
            assert len(permisos) > 0  # Cada empleado debe tener al menos un permiso


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
