"""
Script de demostración de la nueva lógica de puntualidad y retardos
Este script muestra ejemplos de cómo funciona la clasificación implementada.
"""

import pandas as pd
from datetime import datetime

def demo_nueva_logica_retardos():
    """
    Demuestra la nueva lógica de puntualidad y retardos implementada
    """
    print("🎯 DEMOSTRACIÓN DE NUEVA LÓGICA DE PUNTUALIDAD Y RETARDOS")
    print("=" * 60)
    
    # Casos de ejemplo
    casos_ejemplo = [
        {"hora_entrada": "08:00", "checada": "07:55", "descripcion": "Llegada temprana"},
        {"hora_entrada": "08:00", "checada": "08:00", "descripcion": "Llegada exacta"},
        {"hora_entrada": "08:00", "checada": "08:10", "descripcion": "10 min tarde (puntual)"},
        {"hora_entrada": "08:00", "checada": "08:15", "descripcion": "15 min tarde (límite puntual)"},
        {"hora_entrada": "08:00", "checada": "08:16", "descripcion": "16 min tarde (retardo)"},
        {"hora_entrada": "08:00", "checada": "08:25", "descripcion": "25 min tarde (retardo)"},
        {"hora_entrada": "08:00", "checada": "08:30", "descripcion": "30 min tarde (límite retardo)"},
        {"hora_entrada": "08:00", "checada": "08:31", "descripcion": "31 min tarde (falta injustificada)"},
        {"hora_entrada": "08:00", "checada": "09:00", "descripcion": "60 min tarde (falta injustificada)"},
    ]
    
    def clasificar_retardo(hora_entrada_str, checada_str):
        """Aplica la misma lógica implementada en el código principal"""
        try:
            hora_prog = datetime.strptime(hora_entrada_str + ":00", '%H:%M:%S')
            hora_checada = datetime.strptime(checada_str + ":00", '%H:%M:%S')
            
            # Calcular diferencia en minutos
            diferencia = (hora_checada - hora_prog).total_seconds() / 60
            
            # Aplicar la nueva lógica
            if diferencia <= 15:
                return "A Tiempo", int(diferencia)
            elif diferencia <= 30:
                return "Retardo", int(diferencia)
            else:
                return "Falta Injustificada", int(diferencia)
                
        except (ValueError, TypeError):
            return "Error", 0
    
    print(f"{'Hora Entrada':<12} {'Checada':<8} {'Diferencia':<10} {'Clasificación':<18} {'Descripción'}")
    print("-" * 80)
    
    for caso in casos_ejemplo:
        clasificacion, minutos = clasificar_retardo(caso["hora_entrada"], caso["checada"])
        print(f"{caso['hora_entrada']:<12} {caso['checada']:<8} {minutos:>3} min{'':>4} {clasificacion:<18} {caso['descripcion']}")
    
    print("\n📋 RESUMEN DE LA LÓGICA IMPLEMENTADA:")
    print("   ✅ Puntual: Check-in hasta 15 minutos después de la hora acordada")
    print("   ⚠️  Retardo: Check-in entre 16 y 30 minutos después")
    print("   ❌ Falta Injustificada: Check-in después de 30 minutos (automático)")
    print("\n💡 BENEFICIOS:")
    print("   • Diferenciación clara entre retardos leves y graves")
    print("   • Marcado automático de faltas por retardos extremos")
    print("   • Contador de retardos solo para retardos reales (16-30 min)")
    print("   • Faltas injustificadas se cuentan separadamente")

if __name__ == "__main__":
    demo_nueva_logica_retardos()
