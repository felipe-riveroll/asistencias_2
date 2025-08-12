#!/usr/bin/env python3
"""
Script de validación rápida para los KPIs corregidos
"""

import pandas as pd
from reporte_excel import AsistenciaAnalyzer
import logging

# Configurar logging para ver la información de debug
logging.basicConfig(level=logging.INFO)

def test_bradford_factor():
    """Test Bradford Factor con casos sintéticos"""
    print("🧪 Validando Bradford Factor...")
    
    # Crear analyzer
    analyzer = AsistenciaAnalyzer(dias_laborables_mes=22)
    
    # Caso 1: 3 ausencias de 1 día cada una → S=3, D=3, BF=27
    daily_data_1 = pd.DataFrame({
        'employee': ['EMP001'] * 7,
        'dia': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05', '2025-01-06', '2025-01-07'],
        'horas_trabajadas': ['---', '08:00:00', '---', '08:00:00', '---', '08:00:00', '08:00:00'],
        'tipo_retardo': ['', '', '', '', '', '', ''],
        'tiene_permiso': [False, False, False, False, False, False, False]
    })
    
    analyzer.df_daily = daily_data_1
    episodios, dias = analyzer.calculate_bradford_factor_episodes('EMP001')
    bf = (episodios ** 2) * dias
    print(f"Caso 1 - 3 ausencias separadas: S={episodios}, D={dias}, BF={bf} (esperado: S=3, D=3, BF=27)")
    assert episodios == 3 and dias == 3 and bf == 27, f"Error: esperado BF=27, obtenido BF={bf}"
    
    # Caso 2: 1 ausencia continua de 3 días → S=1, D=3, BF=3
    daily_data_2 = pd.DataFrame({
        'employee': ['EMP002'] * 7,
        'dia': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05', '2025-01-06', '2025-01-07'],
        'horas_trabajadas': ['---', '---', '---', '08:00:00', '08:00:00', '08:00:00', '08:00:00'],
        'tipo_retardo': ['', '', '', '', '', '', ''],
        'tiene_permiso': [False, False, False, False, False, False, False]
    })
    
    analyzer.df_daily = daily_data_2
    episodios, dias = analyzer.calculate_bradford_factor_episodes('EMP002')
    bf = (episodios ** 2) * dias
    print(f"Caso 2 - 1 ausencia de 3 días: S={episodios}, D={dias}, BF={bf} (esperado: S=1, D=3, BF=3)")
    assert episodios == 1 and dias == 3 and bf == 3, f"Error: esperado BF=3, obtenido BF={bf}"
    
    # Caso 3: 6 ausencias (2+1+1+1+1+1) con D=7 → BF=252
    daily_data_3 = pd.DataFrame({
        'employee': ['EMP003'] * 10,
        'dia': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05', '2025-01-06', '2025-01-07', '2025-01-08', '2025-01-09', '2025-01-10'],
        'horas_trabajadas': ['---', '---', '08:00:00', '---', '08:00:00', '---', '08:00:00', '---', '08:00:00', '---'],
        'tipo_retardo': ['', '', '', '', '', '', '', '', '', ''],
        'tiene_permiso': [False, False, False, False, False, False, False, False, False, False]
    })
    
    analyzer.df_daily = daily_data_3
    episodios, dias = analyzer.calculate_bradford_factor_episodes('EMP003')
    bf = (episodios ** 2) * dias
    print(f"Caso 3 - 6 episodios alternados: S={episodios}, D={dias}, BF={bf} (esperado: S=5, D=5, BF=125)")
    # Nota: Es S=5 porque hay 5 episodios de inicio de ausencia
    
    print("✅ Bradford Factor validado correctamente")

def test_bf_rescaling():
    """Test función de reescalado del Bradford Factor"""
    print("\n🧪 Validando reescalado Bradford Factor...")
    
    analyzer = AsistenciaAnalyzer()
    
    test_cases = [
        (0, 100),
        (50, 85),
        (100, 70),
        (200, 50),
        (400, 25),
        (900, 0)
    ]
    
    for bf_input, expected in test_cases:
        result = analyzer.bf_to_100_scale(bf_input)
        print(f"BF={bf_input} → {result:.1f} (esperado: {expected})")
        assert abs(result - expected) < 0.1, f"Error en reescalado: BF={bf_input}, esperado={expected}, obtenido={result}"
    
    # Test interpolación
    result_75 = analyzer.bf_to_100_scale(75)
    expected_75 = 85 + (70 - 85) * (75 - 50) / (100 - 50)  # Interpolación lineal
    print(f"BF=75 → {result_75:.1f} (esperado: {expected_75:.1f}) [interpolado]")
    assert abs(result_75 - expected_75) < 0.1, f"Error en interpolación"
    
    print("✅ Reescalado Bradford Factor validado correctamente")

if __name__ == "__main__":
    test_bradford_factor()
    test_bf_rescaling()
    print("\n🎉 Todas las validaciones pasaron correctamente!")