"""
Main orchestration script for the attendance reporting system.
This script coordinates all modules to generate comprehensive attendance reports.
"""

from datetime import datetime
import sys

# Import our modular components
from config import validate_api_credentials
from utils import obtener_codigos_empleados_api, determine_period_type
from api_client import APIClient, procesar_permisos_empleados
from data_processor import AttendanceProcessor
from report_generator import ReportGenerator
from db_postgres_connection import (
    connect_db,
    obtener_horarios_multi_quincena,
    mapear_horarios_por_empleado_multi,
)


class AttendanceReportManager:
    """Main class that orchestrates the entire attendance reporting process."""
    
    def __init__(self):
        """Initialize the report manager with all required components."""
        self.api_client = APIClient()
        self.processor = AttendanceProcessor()
        self.report_generator = ReportGenerator()
    
    def generate_attendance_report(
        self, 
        start_date: str, 
        end_date: str, 
        sucursal: str, 
        device_filter: str
    ) -> dict:
        """
        Main method to generate a complete attendance report.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            sucursal: Branch name
            device_filter: Device filter pattern (e.g., "%villas%")
            
        Returns:
            Dictionary with report status and generated filenames
        """
        print(f"\n🚀 Iniciando reporte para {sucursal}...")
        
        try:
            # Validate API credentials
            validate_api_credentials()
            
            # Step 1: Fetch check-ins
            print("\n📡 Paso 1: Obteniendo registros de entrada/salida...")
            checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
            if not checkin_records:
                print("❌ No se obtuvieron registros de entrada/salida. Saliendo.")
                return {"success": False, "error": "No se encontraron registros de entrada/salida"}

            codigos_empleados_api = obtener_codigos_empleados_api(checkin_records)

            # Step 2: Fetch leave applications
            print("\n📄 Paso 2: Obteniendo solicitudes de permisos...")
            leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
            permisos_dict = procesar_permisos_empleados(leave_records)

            # Step 2a: Fetch employee joining dates
            print("\n📅 Paso 2a: Obteniendo fechas de contratación...")
            joining_dates_records = self.api_client.fetch_employee_joining_dates()
            joining_dates_dict = {
                str(rec["employee"]): datetime.strptime(
                    rec["date_of_joining"], "%Y-%m-%d"
                ).date()
                for rec in joining_dates_records
            }
            print(f"DEBUG: Se encontraron {len(joining_dates_dict)} fechas de contratación.")
            if not joining_dates_dict:
                print("ADVERTENCIA: No se pudieron obtener las fechas de contratación. La lógica para empleados nuevos no se aplicará.")


            # Step 3: Fetch schedules
            print("\n📋 Paso 3: Obteniendo horarios...")
            conn_pg = connect_db()
            if conn_pg is None:
                return {"success": False, "error": "Falló la conexión a la base de datos"}

            incluye_primera, incluye_segunda = determine_period_type(start_date, end_date)
            
            cache_horarios = {}
            horarios_por_quincena = obtener_horarios_multi_quincena(
                sucursal,
                conn_pg,
                codigos_empleados_api,
                incluye_primera=incluye_primera,
                incluye_segunda=incluye_segunda,
            )
            
            if not any(horarios_por_quincena.values()):
                print(f"❌ No se encontraron horarios para la sucursal {sucursal}.")
                conn_pg.close()
                return {"success": False, "error": f"No hay horarios para la sucursal {sucursal}"}

            cache_horarios = mapear_horarios_por_empleado_multi(horarios_por_quincena)
            conn_pg.close()

            # Step 4: Process data
            print("\n📊 Paso 4: Procesando datos...")
            df_detalle = self.processor.process_checkins_to_dataframe(
                checkin_records, start_date, end_date
            )
            df_detalle = self.processor.procesar_horarios_con_medianoche(
                df_detalle, cache_horarios
            )
            df_detalle = self.processor.analizar_asistencia_con_horarios_cache(
                df_detalle, cache_horarios
            )
            df_detalle = self.processor.aplicar_calculo_horas_descanso(df_detalle)
            df_detalle = self.processor.ajustar_horas_esperadas_con_permisos(
                df_detalle, permisos_dict, cache_horarios
            )
            df_detalle = self.processor.marcar_dias_no_contratado(df_detalle, joining_dates_dict)
            df_detalle = self.processor.aplicar_regla_perdon_retardos(df_detalle)
            df_detalle = self.processor.clasificar_faltas_con_permisos(df_detalle)

            # Step 5: Generate reports
            print("\n💾 Paso 5: Generando reportes...")
            
            # Generate detailed CSV report
            detailed_filename = self.report_generator.save_detailed_report(df_detalle)
            
            # Generate summary CSV report
            df_resumen = self.report_generator.generar_resumen_periodo(df_detalle)
            
            # Generate HTML dashboard
            html_filename = ""
            if not df_resumen.empty:
                print("\n🌐 Paso 6: Generando dashboard HTML...")
                html_filename = self.report_generator.generar_reporte_html(
                    df_detalle, df_resumen, start_date, end_date, sucursal
                )
            else:
                print("⚠️ Resumen no generado, omitiendo creación del dashboard HTML.")

            # Generate Excel report
            excel_filename = ""
            if not df_resumen.empty:
                print("\n📊 Paso 7: Generando reporte Excel...")
                excel_filename = self.report_generator.generar_reporte_excel(
                    df_detalle, df_resumen, sucursal, start_date, end_date
                )
            else:
                print("⚠️ Resumen no generado, omitiendo creación del reporte Excel.")

            print("\n🎉 ¡Proceso completado!")
            
            return {
                "success": True,
                "detailed_report": detailed_filename,
                "summary_report": "resumen_periodo.csv",
                "html_dashboard": html_filename,
                "excel_report": excel_filename,
                "employees_processed": len(codigos_empleados_api),
                "days_processed": len(df_detalle["dia"].unique()) if not df_detalle.empty else 0
            }
            
        except Exception as e:
            print(f"❌ Error durante la generación del reporte: {str(e)}")
            return {"success": False, "error": str(e)}


def main():
    """
    Main function that runs the attendance report with configurable parameters.
    Modify these parameters as needed for your specific requirements.
    """
    # ==========================================================================
    # CONFIGURATION SECTION - MODIFY THESE PARAMETERS AS NEEDED
    # ==========================================================================
    
    # Date range for the report
    start_date = "2025-07-01"
    end_date = "2025-07-31"
    
    # Branch and device filter
    sucursal = "31pte"
    device_filter = "%31%"
    
    # ==========================================================================
    # END CONFIGURATION SECTION
    # ==========================================================================
    
    # Create and run the report manager
    manager = AttendanceReportManager()
    result = manager.generate_attendance_report(
        start_date=start_date,
        end_date=end_date,
        sucursal=sucursal,
        device_filter=device_filter
    )
    
    # Print final results
    if result["success"]:
        print("\n" + "="*60)
        print("📊 GENERACIÓN DE REPORTE COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"📅 Período: {start_date} al {end_date}")
        print(f"🏢 Sucursal: {sucursal}")
        print(f"👥 Empleados procesados: {result.get('employees_processed', 'N/A')}")
        print(f"📆 Días procesados: {result.get('days_processed', 'N/A')}")
        print("\n📁 Archivos generados:")
        if result.get("detailed_report"):
            print(f"   • Reporte detallado: {result['detailed_report']}")
        if result.get("summary_report"):
            print(f"   • Reporte resumen: {result['summary_report']}")
        if result.get("html_dashboard"):
            print(f"   • Dashboard HTML: {result['html_dashboard']}")
        if result.get("excel_report"):
            print(f"   • Reporte Excel: {result['excel_report']}")
        print("\n✅ ¡Todos los reportes han sido generados exitosamente!")
    else:
        print("\n" + "="*60)
        print("❌ FALLÓ LA GENERACIÓN DEL REPORTE")
        print("="*60)
        print(f"Error: {result.get('error', 'Error desconocido')}")
        print("\nPor favor verifica tu configuración e intenta de nuevo.")
        sys.exit(1)


if __name__ == "__main__":
    main()