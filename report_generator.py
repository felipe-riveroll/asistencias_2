"""
Report generation module for the attendance reporting system.
Handles CSV and HTML report creation with summary statistics.
"""

import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

from config import OUTPUT_DETAILED_REPORT, OUTPUT_SUMMARY_REPORT, OUTPUT_HTML_DASHBOARD
from utils import format_timedelta_with_sign, format_positive_timedelta, time_to_decimal, calculate_working_days
from reporte_excel import generar_reporte_excel


class ReportGenerator:
    """Class for generating attendance reports in various formats."""
    
    def __init__(self):
        """Initialize the report generator."""
        pass
    
    def _time_to_decimal(self, time_str):
        """Wrapper for utils.time_to_decimal"""
        return time_to_decimal(time_str)
    
    def _format_timedelta_with_sign(self, td):
        """Wrapper for utils.format_timedelta_with_sign"""
        return format_timedelta_with_sign(td)
    
    def _format_positive_timedelta(self, td):
        """Wrapper for utils.format_positive_timedelta"""  
        return format_positive_timedelta(td)
    
    def generar_resumen_periodo(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crea un DataFrame de resumen con totales por empleado.
        """
        print("\n📊 Generando resumen del período...")
        if df.empty:
            print("   - No hay datos para generar el resumen.")
            return pd.DataFrame()

        # Always recalculate from the adjusted text column (more robust Plan B)
        df["horas_trabajadas_td"] = pd.to_timedelta(
            df["horas_trabajadas"].fillna("00:00:00")
        )

        if "horas_esperadas_originales" in df.columns:
            df["horas_esperadas_originales_td"] = pd.to_timedelta(
                df["horas_esperadas_originales"].fillna("00:00:00")
            )
        else:
            df["horas_esperadas_originales_td"] = pd.to_timedelta(
                df["horas_esperadas"].fillna("00:00:00")
            )

        if "horas_descontadas_permiso" in df.columns:
            df["horas_descontadas_permiso_td"] = pd.to_timedelta(
                df["horas_descontadas_permiso"].fillna("00:00:00")
            )
        else:
            df["horas_descontadas_permiso_td"] = pd.to_timedelta("00:00:00")

        if "horas_descanso" in df.columns:
            df["horas_descanso_td"] = pd.to_timedelta(
                df["horas_descanso"].fillna("00:00:00")
            )
        else:
            df["horas_descanso_td"] = pd.to_timedelta("00:00:00")

        total_faltas_col = (
            "es_falta_ajustada" if "es_falta_ajustada" in df.columns 
            else "es_falta" if "es_falta" in df.columns
            else None
        )
        
        retardos_col = (
            "es_retardo_acumulable" if "es_retardo_acumulable" in df.columns
            else None
        )
        
        salidas_anticipadas_col = (
            "salida_anticipada" if "salida_anticipada" in df.columns
            else None
        )

        # Build aggregation dict dynamically
        agg_dict = {
            'total_horas_trabajadas': ("horas_trabajadas_td", "sum"),
            'total_horas_esperadas': ("horas_esperadas_originales_td", "sum"),
            'total_horas_descontadas_permiso': ("horas_descontadas_permiso_td", "sum"),
            'total_horas_descanso': ("horas_descanso_td", "sum"),
        }
        
        if retardos_col:
            agg_dict['total_retardos'] = (retardos_col, "sum")
        else:
            # Create a default column with zeros
            df['_temp_retardos'] = 0
            agg_dict['total_retardos'] = ("_temp_retardos", "sum")
            
        if total_faltas_col:
            agg_dict['faltas_del_periodo'] = (total_faltas_col, "sum")
        else:
            # Create a default column with zeros
            df['_temp_faltas'] = 0
            agg_dict['faltas_del_periodo'] = ("_temp_faltas", "sum")
            
        if "falta_justificada" in df.columns:
            agg_dict['faltas_justificadas'] = ("falta_justificada", "sum")
        else:
            df['_temp_faltas_just'] = 0
            agg_dict['faltas_justificadas'] = ("_temp_faltas_just", "sum")
            
        if salidas_anticipadas_col:
            agg_dict['total_salidas_anticipadas'] = (salidas_anticipadas_col, "sum")
        else:
            df['_temp_salidas'] = 0
            agg_dict['total_salidas_anticipadas'] = ("_temp_salidas", "sum")

        resumen_final = (
            df.groupby(["employee", "Nombre"])
            .agg(**agg_dict)
            .reset_index()
        )

        resumen_final["total_horas"] = (
            resumen_final["total_horas_esperadas"]
            - resumen_final["total_horas_descontadas_permiso"]
        )
        resumen_final["total_faltas"] = resumen_final["faltas_del_periodo"]
        diferencia_td = (
            resumen_final["total_horas_trabajadas"] - resumen_final["total_horas"]
        )

        resumen_final["diferencia_HHMMSS"] = diferencia_td.apply(format_timedelta_with_sign)
        resumen_final["total_horas_trabajadas"] = resumen_final[
            "total_horas_trabajadas"
        ].apply(format_positive_timedelta)
        resumen_final["total_horas_esperadas"] = resumen_final[
            "total_horas_esperadas"
        ].apply(format_positive_timedelta)
        resumen_final["total_horas_descontadas_permiso"] = resumen_final[
            "total_horas_descontadas_permiso"
        ].apply(format_positive_timedelta)
        resumen_final["total_horas_descanso"] = resumen_final["total_horas_descanso"].apply(
            format_positive_timedelta
        )
        resumen_final["total_horas"] = resumen_final["total_horas"].apply(
            format_positive_timedelta
        )

        base_columns = [
            "employee",
            "Nombre",
            "total_horas_trabajadas",
            "total_horas_esperadas",
            "total_horas_descontadas_permiso",
            "total_horas_descanso",
            "total_horas",
            "total_retardos",
            "faltas_del_periodo",
            "faltas_justificadas",
            "total_faltas",
            "total_salidas_anticipadas",
            "diferencia_HHMMSS",
        ]
        resumen_final = resumen_final[base_columns]

        # Save summary to CSV
        self._save_csv_with_fallback(resumen_final, OUTPUT_SUMMARY_REPORT, "period summary")

        print("\n**Visualización del Resumen del Período:**\n")
        print(resumen_final.to_string())
        return resumen_final

    def save_detailed_report(self, df: pd.DataFrame) -> str:
        """
        Guarda el reporte detallado de asistencia en CSV.
        
        Args:
            df: DataFrame detallado con todos los datos de asistencia
            
        Returns:
            Nombre del archivo del reporte guardado
        """
        if df.empty:
            print("⚠️ No hay datos para guardar el reporte detallado.")
            return ""

        # Define column order for the detailed report
        checado_cols = sorted([c for c in df.columns if "checado_" in c and c != "checado_1"])
        column_order = [
            "employee", "Nombre", "dia", "dia_semana", "hora_entrada_programada",
            "checado_1", "minutos_tarde", "tipo_retardo", "retardo_perdonado",
            "tipo_retardo_original", "minutos_tarde_original", "tipo_falta_ajustada",
            "tiene_permiso", "tipo_permiso", "es_permiso_medio_dia", "falta_justificada",
            "hora_salida_programada", "salida_anticipada", "horas_esperadas",
            "duration", "horas_trabajadas", "horas_descanso",
        ] + checado_cols

        final_columns = [col for col in column_order if col in df.columns]
        df_final_detallado = df[final_columns].fillna("---")

        filename = self._save_csv_with_fallback(
            df_final_detallado, 
            OUTPUT_DETAILED_REPORT, 
            "detailed report"
        )
        return filename

    def save_summary_report(self, df: pd.DataFrame) -> str:
        """
        Guarda el reporte resumen de período en CSV.
        
        Args:
            df: DataFrame resumen con totales por empleado
            
        Returns:
            Nombre del archivo del reporte guardado
        """
        if df.empty:
            print("⚠️ No hay datos para guardar el reporte resumen.")
            return ""

        filename = self._save_csv_with_fallback(
            df, 
            OUTPUT_SUMMARY_REPORT, 
            "summary report"
        )
        return filename

    def generar_reporte_html(
        self,
        df_detallado: pd.DataFrame,
        df_resumen: pd.DataFrame,
        periodo_inicio: str,
        periodo_fin: str,
        sucursal: str,
    ) -> str:
        """
        Genera un reporte HTML interactivo del período analizado con lógica de JS corregida.
        """
        print("\n📊 Generando reporte HTML interactivo...")

        if df_resumen.empty:
            html_content = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Sin Datos</title></head>
<body><h1>Sin datos disponibles</h1><p>No se encontraron datos para el período.</p></body></html>"""
            with open(OUTPUT_HTML_DASHBOARD, "w", encoding="utf-8") as f:
                f.write(html_content)
            return OUTPUT_HTML_DASHBOARD

        # Prepare employee data for JavaScript
        employee_data_js = []
        for _, row in df_resumen.iterrows():
            employee_data_js.append({
                "employee": str(row["employee"]),
                "name": str(row["Nombre"]),
                "workedHours": str(row["total_horas_trabajadas"]),
                "expectedHours": str(row["total_horas_esperadas"]),
                "permitHours": str(row.get("total_horas_descontadas_permiso", "00:00:00")),
                "netHours": str(row["total_horas"]),
                "delays": int(row.get("total_retardos", 0)),
                "absences": int(row.get("faltas_del_periodo", 0)),
                "justifiedAbsences": int(row.get("faltas_justificadas", 0)),
                "totalAbsences": int(row.get("total_faltas", 0)),
                "difference": str(row.get("diferencia_HHMMSS", "00:00:00")),
                "workedDecimal": time_to_decimal(row["total_horas_trabajadas"]),
                "expectedDecimal": time_to_decimal(row["total_horas_esperadas"]),
                "expectedDecimalAdjusted": time_to_decimal(row["total_horas"]),
                "permitDecimal": time_to_decimal(row.get("total_horas_descontadas_permiso", "00:00:00")),
            })

        # Prepare daily data for charts
        daily_data_js = []
        if not df_detallado.empty and "dia" in df_detallado.columns:
            # Check if hora_entrada_programada exists, if not, use all rows
            if "hora_entrada_programada" in df_detallado.columns:
                df_laborables = df_detallado[df_detallado["hora_entrada_programada"].notna()].copy()
            else:
                df_laborables = df_detallado.copy()
            if not df_laborables.empty:
                # Build aggregation safely checking for column existence
                agg_dict = {
                    'total_empleados': ("employee", "nunique")
                }
                
                if "tipo_falta_ajustada" in df_laborables.columns:
                    agg_dict['faltas_injustificadas'] = (
                        "tipo_falta_ajustada",
                        lambda x: x.isin(["Falta", "Falta Injustificada"]).sum(),
                    )
                elif "es_falta" in df_laborables.columns:
                    agg_dict['faltas_injustificadas'] = ("es_falta", "sum")
                else:
                    # Create temp column for missing data
                    df_laborables['_temp_faltas'] = 0
                    agg_dict['faltas_injustificadas'] = ("_temp_faltas", "sum")
                
                if "falta_justificada" in df_laborables.columns:
                    agg_dict['permisos'] = ("falta_justificada", lambda x: x.sum())
                else:
                    df_laborables['_temp_permisos'] = 0
                    agg_dict['permisos'] = ("_temp_permisos", "sum")
                
                daily_summary = (
                    df_laborables.groupby(["dia", "dia_semana"])
                    .agg(**agg_dict)
                    .reset_index()
                )
                for _, row in daily_summary.iterrows():
                    asistencias = (
                        row["total_empleados"] - row["faltas_injustificadas"] - row["permisos"]
                    )
                    daily_data_js.append({
                        "date": row["dia"].strftime("%d %b"),
                        "day": str(row["dia_semana"]),
                        "attendance": max(0, asistencias),
                        "absences": int(row["faltas_injustificadas"]),
                        "permits": int(row["permisos"]),
                        "total": int(row["total_empleados"]),
                    })

        # Calculate KPIs
        dias_laborales = calculate_working_days(periodo_inicio, periodo_fin)
        total_employees = len(employee_data_js)
        total_absences = sum(e.get("totalAbsences", 0) for e in employee_data_js)
        total_possible_days = total_employees * dias_laborales
        lost_days_percent = (
            (total_absences / total_possible_days * 100) if total_possible_days > 0 else 0
        )

        # KPIs calculated in Python to ensure consistency
        total_worked_py = sum(e["workedDecimal"] for e in employee_data_js)
        total_expected_py = sum(e["expectedDecimal"] for e in employee_data_js)
        attendance_rate = (
            (total_worked_py / total_expected_py * 100) if total_expected_py > 0 else 0
        )

        punctual_employees = sum(
            1 for e in employee_data_js if e["delays"] == 0 and e["workedDecimal"] > 0
        )
        active_employees = sum(1 for e in employee_data_js if e["workedDecimal"] > 0)
        punctuality_rate = (
            (punctual_employees / active_employees * 100) if active_employees > 0 else 0
        )

        lost_days = sum(e.get("totalAbsences", 0) for e in employee_data_js)

        employee_json = json.dumps(employee_data_js, ensure_ascii=False)
        daily_json = json.dumps(daily_data_js, ensure_ascii=False)

        # Generate complete HTML content
        html_content = self._generate_html_template(
            sucursal, periodo_inicio, periodo_fin, attendance_rate, punctuality_rate,
            lost_days, lost_days_percent, employee_json, daily_json
        )

        filename = self._save_html_with_fallback(html_content, OUTPUT_HTML_DASHBOARD)
        return filename

    def generar_reporte_excel(
        self,
        df_detallado: pd.DataFrame,
        df_resumen: pd.DataFrame,
        sucursal: str,
        periodo_inicio: str,
        periodo_fin: str,
    ) -> str:
        """
        Genera un reporte Excel usando el módulo de reporte_excel.
        
        Args:
            df_detallado: DataFrame con datos detallados de asistencia
            df_resumen: DataFrame con resumen del período
            sucursal: Nombre de la sucursal
            periodo_inicio: Fecha de inicio del período
            periodo_fin: Fecha de fin del período
            
        Returns:
            Nombre del archivo Excel generado
        """
        try:
            archivo_excel = generar_reporte_excel(
                df_detallado, df_resumen, sucursal, periodo_inicio, periodo_fin
            )
            return archivo_excel
        except Exception as e:
            print(f"⚠️ Error al generar reporte Excel: {e}")
            return ""

    def _save_csv_with_fallback(self, df: pd.DataFrame, filename: str, description: str) -> str:
        """
        Guarda un DataFrame a CSV con nombre de archivo alternativo si el original está en uso.
        """
        try:
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"✅ {description.title()} guardado en '{filename}'")
            return filename
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback_name = f"{filename.rsplit('.', 1)[0]}_{timestamp}.csv"
            df.to_csv(fallback_name, index=False, encoding="utf-8-sig")
            print(f"⚠️ El archivo original estaba en uso. {description.title()} guardado en '{fallback_name}'")
            return fallback_name

    def _save_html_with_fallback(self, content: str, filename: str) -> str:
        """
        Guarda contenido HTML con nombre de archivo alternativo si el original está en uso.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ Dashboard HTML generado exitosamente: '{filename}'")
            return filename
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fallback_name = f"{filename.rsplit('.', 1)[0]}_{timestamp}.html"
            with open(fallback_name, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"⚠️ El archivo original estaba en uso. Dashboard guardado en '{fallback_name}'")
            return fallback_name

    def _generate_html_template(
        self, sucursal: str, periodo_inicio: str, periodo_fin: str,
        attendance_rate: float, punctuality_rate: float, lost_days: int,
        lost_days_percent: float, employee_json: str, daily_json: str
    ) -> str:
        """
        Generates the complete HTML template for the dashboard.
        """
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Ejecutivo de Asistencia - {sucursal}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/2.3.2/css/dataTables.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f8f9fa; color: #212529; }}
        .header {{ background: white; padding: 2rem; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 3px solid #0066cc; }}
        .header h1 {{ color: #0066cc; font-size: 2.2rem; margin-bottom: 0.5rem; }}
        .header p {{ color: #6c757d; font-size: 1.1rem; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 0 1rem; }}
        .tabs {{ display: flex; justify-content: center; margin-bottom: 2rem; gap: 1rem; }}
        .tab-button {{ padding: 1rem 2rem; font-size: 1rem; font-weight: 600; cursor: pointer; border: 2px solid #0066cc; background: white; color: #0066cc; border-radius: 8px; transition: all 0.2s ease; }}
        .tab-button.active {{ background: #0066cc; color: white; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 3rem; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 2rem; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-left: 4px solid; }}
        .metric-card h3 {{ color: #495057; font-size: 0.9rem; margin-bottom: 1rem; text-transform: uppercase; }}
        .metric-value {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .metric-subtitle {{ font-size: 0.8rem; color: #6c757d; }}
        .metric-card.attendance {{ border-left-color: #28a745; }} .metric-card.attendance .metric-value {{ color: #28a745; }}
        .metric-card.deviation {{ border-left-color: #ff6b35; }} .metric-card.deviation .metric-value {{ color: #ff6b35; }}
        .metric-card.punctuality {{ border-left-color: #ffc107; }} .metric-card.punctuality .metric-value {{ color: #ffc107; }}
        .metric-card.absences {{ border-left-color: #dc3545; }} .metric-card.absences .metric-value {{ color: #dc3545; }}
        .chart-container {{ background: white; border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .chart-title {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; }}
        .chart svg {{ width: 100%; height: auto; }}
        .axis path, .axis .domain {{ stroke: #dee2e6; }}
        .axis .tick text {{ fill: #6c757d; }}
        .grid line {{ stroke: #f1f3f4; stroke-dasharray: 2,2; }}
        .tooltip {{ position: absolute; padding: 12px; background: rgba(33,37,41,0.95); color: white; border-radius: 6px; pointer-events: none; opacity: 0; transition: opacity 0.2s; z-index: 1000; }}
        .table-section {{ background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .controls {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
        .search-box input, .filter-select {{ width: 100%; padding: 12px 16px; border: 2px solid #e9ecef; border-radius: 8px; }}
        .employee-table {{ width: 100%; border-collapse: collapse; }}
        .employee-table th {{ background: #f8f9fa; padding: 1rem; text-align: left; }}
        .employee-table td {{ padding: 1rem; border-bottom: 1px solid #e9ecef; }}
        .positive {{ color: #28a745; }} .negative {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Ejecutivo de Asistencia</h1>
        <p>Sucursal: {sucursal.upper()} | Período: {periodo_inicio} - {periodo_fin}</p>
    </div>
    <div class="container">
        <div class="tabs">
            <button class="tab-button active" onclick="openTab(event, 'dashboard')">Resumen Ejecutivo</button>
            <button class="tab-button" onclick="openTab(event, 'employee-table')">Detalle por Empleado</button>
        </div>
        <div id="dashboard" class="tab-content active">
            <div class="metrics-grid">
                <div class="metric-card attendance">
                    <h3>Tasa de Asistencia</h3>
                    <div class="metric-value" id="attendanceRate">{attendance_rate:.1f}%</div>
                    <div class="metric-subtitle">Horas trabajadas vs planificadas</div>
                </div>
                <div class="metric-card deviation">
                    <h3>Desviación Media Horaria</h3>
                    <div class="metric-value" id="avgDeviationHours">±0.0 h</div>
                    <div class="metric-subtitle">Promedio de dif. de horas</div>
                </div>
                <div class="metric-card punctuality">
                    <h3>Índice de Puntualidad</h3>
                    <div class="metric-value" id="punctualityRate">{punctuality_rate:.0f}%</div>
                    <div class="metric-subtitle">Empleados puntuales</div>
                </div>
                <div class="metric-card absences">
                    <h3>Días Perdidos</h3>
                    <div class="metric-value" id="totalLostDays">{lost_days}</div>
                    <div class="metric-subtitle">{lost_days_percent:.1f}% de capacidad perdida</div>
                </div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Tendencia de Asistencia del Período</div>
                <div id="dailyTrendChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Eficiencia de Recursos Humanos</div>
                <div id="efficiencyChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Análisis de Impacto por Ausencias</div>
                <div id="absenceImpactChart" class="chart"></div>
            </div>
        </div>
        <div id="employee-table" class="tab-content">
            <div class="table-section">
                <div class="chart-title">Análisis Individual</div>
                <table id="tablaDetalleEmpleado" class="employee-table" style="width:100%">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Empleado</th>
                            <th>Hrs. Trabajadas</th>
                            <th>Hrs. Planificadas</th>
                            <th>Variación</th>
                            <th>Retardos</th>
                            <th>Ausencias</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="tooltip"></div>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/2.3.2/js/dataTables.min.js"></script>

    <script>
        const employeeData = {employee_json};
        const dailyData = {daily_json};
        const tooltip = d3.select(".tooltip");

        // --- UTILIDADES ---
        function hhmmssToDecimal(hhmmss) {{
            if (!hhmmss || typeof hhmmss !== 'string') return 0;
            const [h, m, s] = hhmmss.split(':').map(Number);
            return (h || 0) + (m || 0) / 60 + (s || 0) / 3600;
        }}
        function safeDiv(numerator, denominator) {{
            return denominator > 0 ? numerator / denominator : 0;
        }}
        function truncateName(name, max = 20) {{
            return name.length > max ? name.slice(0, max) + "…" : name;
        }}

        // --- PESTAÑAS ---
        function openTab(evt, tabName) {{
            document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
            document.querySelectorAll('.tab-button').forEach(tb => tb.classList.remove('active'));
            document.getElementById(tabName).style.display = 'block';
            evt.currentTarget.classList.add('active');
        }}

        // --- CÁLCULO DE KPIs ---
        function calculateAndDisplayKPIs() {{
            if (!employeeData || employeeData.length === 0) return;

            // Desviación Media Horaria
            const employeesWithPlannedHours = employeeData.filter(e => e.expectedDecimalAdjusted > 0);
            let avgDeviation = 0;
            if (employeesWithPlannedHours.length > 0) {{
                const totalDeviation = employeesWithPlannedHours.reduce((sum, e) => {{
                    return sum + Math.abs(e.workedDecimal - e.expectedDecimalAdjusted);
                }}, 0);
                avgDeviation = safeDiv(totalDeviation, employeesWithPlannedHours.length);
            }}
            document.getElementById('avgDeviationHours').textContent = `±${{avgDeviation.toFixed(1)}} h`;
        }}

        // --- GRÁFICAS ---
        function createDailyTrendChart() {{
            const container = d3.select("#dailyTrendChart");
            if (dailyData.length === 0) {{ container.text("No hay datos de tendencia diaria."); return; }}
            container.html("");
            const margin = {{ top: 20, right: 100, bottom: 50, left: 40 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
            
            const series = [
                {{ key: "attendance", label: "Asistencias", color: "#28a745" }},
                {{ key: "absences", label: "Faltas", color: "#dc3545" }},
                {{ key: "permits", label: "Permisos", color: "#ffc107" }}
            ];
            const x = d3.scaleBand().domain(dailyData.map(d => d.date)).range([0, width]).padding(0.1);
            const y = d3.scaleLinear().domain([0, d3.max(dailyData, d => d.total) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x)).selectAll("text").attr("transform", "rotate(-45)").style("text-anchor", "end");
            svg.append("g").call(d3.axisLeft(y));
            svg.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-width).tickFormat("")).selectAll("line").attr("stroke", "#f1f3f4");

            const lineGen = key => d3.line().x(d => x(d.date) + x.bandwidth() / 2).y(d => y(d[key])).curve(d3.curveMonotoneX);

            series.forEach(s => {{
                svg.append("path").datum(dailyData).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 2.5).attr("d", lineGen(s.key));
                svg.selectAll(`.dot-${{s.key}}`).data(dailyData).enter().append("circle")
                    .attr("cx", d => x(d.date) + x.bandwidth() / 2).attr("cy", d => y(d[s.key])).attr("r", 4).attr("fill", s.color)
                    .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.date}}</strong><br>${{s.label}}: ${{d[s.key]}}`))
                    .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                    .on("mouseout", () => tooltip.style("opacity", 0));
            }});
        }}

        function createEfficiencyChart() {{
            const container = d3.select("#efficiencyChart");
            container.html("");
            
            const data = employeeData
                .map(d => ({{
                    name: truncateName(d.name),
                    fullName: d.name,
                    efficiency: safeDiv(d.workedDecimal, d.expectedDecimalAdjusted) * 100,
                    worked: d.workedDecimal,
                    planned: d.expectedDecimalAdjusted
                }}))
                .filter(d => d.planned > 0)
                .sort((a, b) => b.efficiency - a.efficiency)
                .slice(0, 15);

            if (data.length === 0) {{ container.text("No hay datos de eficiencia para mostrar (sin horas planificadas)."); return; }}

            const margin = {{ top: 20, right: 30, bottom: 40, left: 150 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = data.length * 28;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            const x = d3.scaleLinear().domain([0, Math.max(100, d3.max(data, d => d.efficiency) || 0)]).nice().range([0, width]);
            const y = d3.scaleBand().domain(data.map(d => d.name)).range([0, height]).padding(0.1);

            svg.append("g").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x).ticks(5).tickFormat(d => d + "%"));
            
            svg.append("line").attr("x1", x(100)).attr("x2", x(100)).attr("y1", 0).attr("y2", height).attr("stroke", "#dc3545").attr("stroke-dasharray", "4,4");

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("y", d => y(d.name)).attr("width", d => x(d.efficiency)).attr("height", y.bandwidth())
                .attr("fill", d => d.efficiency >= 98 ? "#28a745" : d.efficiency >= 85 ? "#ffc107" : "#dc3545")
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.fullName}}</strong><br>Eficiencia: ${{d.efficiency.toFixed(1)}}%<br>Trabajadas: ${{d.worked.toFixed(1)}}h<br>Planificadas: ${{d.planned.toFixed(1)}}h`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }}
        
        function createAbsenceImpactChart() {{
            const container = d3.select("#absenceImpactChart");
            container.html("");
            
            const unjustified = d3.sum(employeeData, d => d.absences);
            const justified = d3.sum(employeeData, d => d.justifiedAbsences);
            const delays = d3.sum(employeeData, d => d.delays);
            
            const data = [
                {{ type: "Faltas Injustificadas", count: unjustified, color: "#dc3545" }},
                {{ type: "Faltas Justificadas", count: justified, color: "#ffc107" }},
                {{ type: "Retardos", count: delays, color: "#17a2b8" }}
            ].filter(d => d.count > 0);

            if (data.length === 0) {{ container.text("¡Sin ausencias ni retardos en el período!"); return; }}

            const margin = {{ top: 20, right: 20, bottom: 30, left: 40 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            const x = d3.scaleBand().domain(data.map(d => d.type)).range([0, width]).padding(0.4);
            const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x));
            svg.append("g").call(d3.axisLeft(y));

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("x", d => x(d.type)).attr("y", d => y(d.count))
                .attr("width", x.bandwidth()).attr("height", d => height - y(d.count))
                .attr("fill", d => d.color)
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.type}}</strong><br>Total: ${{d.count}}`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }}

        // --- INICIALIZACIÓN ---
        document.addEventListener('DOMContentLoaded', () => {{
            calculateAndDisplayKPIs();
            createDailyTrendChart();
            createEfficiencyChart();
            createAbsenceImpactChart();
            
            // Inicializar DataTables para la tabla de empleados
            $('#tablaDetalleEmpleado').DataTable({{
                data: employeeData,
                columns: [
                    {{ data: 'employee' }},
                    {{ data: 'name' }},
                    {{ data: 'workedHours' }},
                    {{ data: 'netHours' }},
                    {{
                        data: 'difference',
                        createdCell: function (td, cellData, rowData, row, col) {{
                            if (cellData.startsWith('+')) {{
                                $(td).addClass('positive');
                            }} else if (cellData.startsWith('-')) {{
                                $(td).addClass('negative');
                            }}
                        }}
                    }},
                    {{ data: 'delays' }},
                    {{ data: 'totalAbsences' }}
                ],
                language: {{
                    url: 'https://cdn.datatables.net/plug-ins/2.0.3/i18n/es-MX.json',
                }},
                pageLength: 10,
                responsive: true
            }});
            
            window.addEventListener('resize', () => {{
                createDailyTrendChart();
                createEfficiencyChart();
                createAbsenceImpactChart();
            }});
        }});
    </script>
</body>
</html>"""