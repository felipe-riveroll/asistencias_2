"""
Main orchestration script for the attendance reporting system.
This script coordinates all modules to generate comprehensive attendance reports.
"""

from datetime import datetime
import sys
import logging

# Import our modular components
from config import validate_api_credentials, setup_logging
from utils import obtener_codigos_empleados_api, determine_period_type
from api_client import APIClient, procesar_permisos_empleados
from data_processor import AttendanceProcessor
from report_generator import ReportGenerator
from db_postgres_connection import (
    connect_db,
    obtener_horarios_multi_quincena,
    mapear_horarios_por_empleado_multi,
)

# Setup logging
logger = setup_logging()


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
        logger.info(f"Iniciando reporte para {sucursal}...")
        
        try:
            # Validate API credentials
            validate_api_credentials()
            
            # Step 1: Fetch check-ins
            logger.info("Paso 1: Obteniendo registros de entrada/salida...")
            checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
            if not checkin_records:
                logger.error(f"No se obtuvieron registros de entrada/salida para el dispositivo '{device_filter}' en el período {start_date} al {end_date}.")
                logger.error("Posibles causas:")
                logger.error("  1. No hay registros de entrada/salida para este dispositivo en el período especificado")
                logger.error("  2. El filtro de dispositivo no coincide con ningún dispositivo en el sistema")
                logger.error("  3. Los dispositivos de esta sucursal tienen nombres diferentes")
                logger.error("Sugerencia: Verifica el filtro de dispositivo o intenta con un período diferente.")
                return {"success": False, "error": f"No se encontraron registros de entrada/salida para el dispositivo '{device_filter}' en el período {start_date} al {end_date}"}

            codigos_empleados_api = obtener_codigos_empleados_api(checkin_records)

            # Step 2: Fetch leave applications
            logger.info("Paso 2: Obteniendo solicitudes de permisos...")
            leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
            permisos_dict = procesar_permisos_empleados(leave_records)

            # Step 2a: Fetch all employee joining dates
            logger.info("Paso 2a: Obteniendo todas las fechas de contratación...")
            all_joining_dates = self.api_client.fetch_employee_joining_dates()
            joining_dates_dict = {
                str(rec["employee"]): datetime.strptime(
                    rec["date_of_joining"], "%Y-%m-%d"
                ).date()
                for rec in all_joining_dates
            }
            logger.debug(f"Se encontraron {len(joining_dates_dict)} fechas de contratación en total.")

            # Step 3: Fetch schedules
            logger.info("Paso 3: Obteniendo horarios...")
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
                logger.error(f"No se encontraron horarios para la sucursal '{sucursal}'.")
                logger.error("Posibles causas:")
                logger.error("  1. No hay empleados asignados a esta sucursal en la base de datos")
                logger.error("  2. Los empleados no tienen horarios configurados")
                logger.error("  3. No hay empleados que coincidan con los códigos de la API")
                logger.error("Sugerencia: Verifica que haya empleados con horarios asignados en la base de datos.")
                conn_pg.close()
                return {"success": False, "error": f"No hay horarios para la sucursal '{sucursal}'. Verifica que los empleados tengan horarios asignados en la base de datos."}

            cache_horarios = mapear_horarios_por_empleado_multi(horarios_por_quincena)
            conn_pg.close()

            # Step 4: Process data
            logger.info("Paso 4: Procesando datos...")
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
            df_detalle = self.processor.aplicar_regla_perdon_retardos(df_detalle)
            df_detalle = self.processor.clasificar_faltas_con_permisos(df_detalle)
            # Apply joining date logic as the final processing step
            df_detalle = self.processor.marcar_dias_no_contratado(df_detalle, joining_dates_dict)

            # Step 5: Generate reports
            logger.info("Paso 5: Generando reportes...")
            
            # Generate detailed CSV report
            detailed_filename = self.report_generator.save_detailed_report(df_detalle)
            
            # Generate summary CSV report
            df_resumen = self.report_generator.generar_resumen_periodo(df_detalle)
            
            # Generate HTML dashboard
            html_filename = ""
            if not df_resumen.empty:
                logger.info("Paso 6: Generando dashboard HTML...")
                html_filename = self.report_generator.generar_reporte_html(
                    df_detalle, df_resumen, start_date, end_date, sucursal
                )
            else:
                logger.warning("Resumen no generado, omitiendo creación del dashboard HTML.")

            # Generate Excel report
            excel_filename = ""
            if not df_resumen.empty:
                logger.info("Paso 7: Generando reporte Excel...")
                excel_filename = self.report_generator.generar_reporte_excel(
                    df_detalle, df_resumen, sucursal, start_date, end_date
                )
            else:
                logger.warning("Resumen no generado, omitiendo creación del reporte Excel.")

            logger.info("¡Proceso completado!")
            
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
            logger.error(f"Error durante la generación del reporte: {str(e)}")
            return {"success": False, "error": str(e)}


def main():
    """
    Main function that runs the attendance report with configurable parameters.
    Can be run with command line arguments or by modifying the default values.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar reporte de asistencia')
    parser.add_argument('--start', type=str, default="2025-07-01",
                       help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default="2025-07-31",
                       help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--sucursal', type=str, default="Rio Blanco",
                       help='Nombre de la sucursal')
    parser.add_argument('--device', type=str, default="%Rio%",
                       help='Filtro de dispositivo (ej: %Rio%, %RB%, %Blanco%)')
    
    args = parser.parse_args()
    
    # Usar valores de línea de comandos o valores por defecto
    start_date = args.start
    end_date = args.end
    sucursal = args.sucursal
    device_filter = args.device
    
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
        logger.info("="*60)
        logger.info("GENERACIÓN DE REPORTE COMPLETADA EXITOSAMENTE")
        logger.info("="*60)
        logger.info(f"Período: {start_date} al {end_date}")
        logger.info(f"Sucursal: {sucursal}")
        logger.info(f"Filtro de dispositivo: {device_filter}")
        logger.info(f"Empleados procesados: {result.get('employees_processed', 'N/A')}")
        logger.info(f"Días procesados: {result.get('days_processed', 'N/A')}")
        logger.info("Archivos generados:")
        if result.get("detailed_report"):
            logger.info(f"   • Reporte detallado: {result['detailed_report']}")
        if result.get("summary_report"):
            logger.info(f"   • Reporte resumen: {result['summary_report']}")
        if result.get("html_dashboard"):
            logger.info(f"   • Dashboard HTML: {result['html_dashboard']}")
        if result.get("excel_report"):
            logger.info(f"   • Reporte Excel: {result['excel_report']}")
        logger.info("¡Todos los reportes han sido generados exitosamente!")
    else:
        logger.error("="*60)
        logger.error("FALLÓ LA GENERACIÓN DEL REPORTE")
        logger.error("="*60)
        logger.error(f"Error: {result.get('error', 'Error desconocido')}")
        logger.error(f"Sucursal: {sucursal}")
        logger.error(f"Filtro de dispositivo: {device_filter}")
        logger.error(f"Período: {start_date} al {end_date}")
        logger.error("Por favor verifica tu configuración e intenta de nuevo.")
        logger.error("💡 Sugerencia: Ejecuta 'python rio_blanco_setup.py' para obtener ayuda.")
        sys.exit(1)


if __name__ == "__main__":
    main()