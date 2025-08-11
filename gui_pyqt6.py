#!/usr/bin/env python3
"""
PyQt6 Desktop GUI for Attendance Report Generator
This application provides a user-friendly interface to generate attendance reports
with date selection, branch selection, and automatic Excel file opening capabilities.
"""

import sys
import os
import subprocess
import platform
import time
from datetime import datetime, date
from pathlib import Path
from threading import Thread

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QDateEdit, QPushButton, QComboBox, QTextEdit, QMessageBox, 
    QDialog, QDialogButtonBox, QGroupBox, QProgressBar, QStatusBar
)
from PyQt6.QtCore import QDate, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon

from main import AttendanceReportManager
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


class CustomAttendanceReportManager(AttendanceReportManager):
    """Extended AttendanceReportManager with progress callbacks for GUI."""
    
    def __init__(self):
        super().__init__()
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """Set the progress callback function."""
        self.progress_callback = callback
    
    def emit_progress(self, step: int, message: str, records: int = 0):
        """Emit progress update if callback is set."""
        if self.progress_callback:
            self.progress_callback(step, message, records)
    
    def generate_attendance_report(
        self, 
        start_date: str, 
        end_date: str, 
        sucursal: str, 
        device_filter: str
    ) -> dict:
        """Generate attendance report with progress updates."""
        try:
            # Validate API credentials
            validate_api_credentials()
            
            # Step 1: Fetch check-ins
            start_time = time.time()
            self.emit_progress(1, "📡 Obteniendo registros de entrada/salida...")
            
            checkin_records = self.api_client.fetch_checkins(start_date, end_date, device_filter)
            if not checkin_records:
                return {"success": False, "error": "No se encontraron registros de entrada/salida"}

            codigos_empleados_api = obtener_codigos_empleados_api(checkin_records)
            step1_time = time.time() - start_time
            
            self.emit_progress(
                1, 
                f"📡 Paso 1/7: Check-ins obtenidos ({len(checkin_records)} registros en {step1_time:.1f}s)", 
                len(checkin_records)
            )

            # Step 2: Fetch leave applications
            step_start = time.time()
            self.emit_progress(2, "📄 Obteniendo solicitudes de permisos...")
            
            leave_records = self.api_client.fetch_leave_applications(start_date, end_date)
            permisos_dict = procesar_permisos_empleados(leave_records)
            step2_time = time.time() - step_start
            
            self.emit_progress(
                2, 
                f"📄 Paso 2/7: Permisos obtenidos ({len(leave_records)} registros en {step2_time:.1f}s)", 
                len(leave_records)
            )

            # Step 3: Fetch schedules
            step_start = time.time()
            self.emit_progress(3, "📋 Obteniendo horarios...")
            
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
                conn_pg.close()
                return {"success": False, "error": f"No hay horarios para la sucursal {sucursal}"}

            cache_horarios = mapear_horarios_por_empleado_multi(horarios_por_quincena)
            conn_pg.close()
            step3_time = time.time() - step_start
            
            self.emit_progress(
                3, 
                f"📋 Paso 3/7: Horarios obtenidos ({len(cache_horarios)} empleados en {step3_time:.1f}s)", 
                len(cache_horarios)
            )

            # Step 4: Process data
            step_start = time.time()
            self.emit_progress(4, "📊 Procesando datos...")
            
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
            step4_time = time.time() - step_start
            
            processed_records = len(df_detalle) if not df_detalle.empty else 0
            self.emit_progress(
                4, 
                f"📊 Paso 4/7: Datos procesados ({processed_records} registros en {step4_time:.1f}s)", 
                processed_records
            )

            # Step 5: Generate reports
            step_start = time.time()
            self.emit_progress(5, "💾 Generando reportes CSV...")
            
            detailed_filename = self.report_generator.save_detailed_report(df_detalle)
            df_resumen = self.report_generator.generar_resumen_periodo(df_detalle)
            step5_time = time.time() - step_start
            
            self.emit_progress(
                5, 
                f"💾 Paso 5/7: Reportes CSV generados en {step5_time:.1f}s"
            )

            # Step 6: Generate HTML dashboard
            step_start = time.time()
            html_filename = ""
            if not df_resumen.empty:
                self.emit_progress(6, "🌐 Generando dashboard HTML...")
                html_filename = self.report_generator.generar_reporte_html(
                    df_detalle, df_resumen, start_date, end_date, sucursal
                )
                step6_time = time.time() - step_start
                self.emit_progress(
                    6, 
                    f"🌐 Paso 6/7: Dashboard HTML generado en {step6_time:.1f}s"
                )
            else:
                self.emit_progress(6, "⚠️ Paso 6/7: Dashboard HTML omitido (sin datos)")

            # Step 7: Generate Excel report
            step_start = time.time()
            excel_filename = ""
            if not df_resumen.empty:
                self.emit_progress(7, "📊 Generando reporte Excel...")
                excel_filename = self.report_generator.generar_reporte_excel(
                    df_detalle, df_resumen, sucursal, start_date, end_date
                )
                step7_time = time.time() - step_start
                self.emit_progress(
                    7, 
                    f"📊 Paso 7/7: Reporte Excel generado en {step7_time:.1f}s"
                )
            else:
                self.emit_progress(7, "⚠️ Paso 7/7: Reporte Excel omitido (sin datos)")
            
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
            return {"success": False, "error": str(e)}


class ReportWorkerSignals(QObject):
    """Signals for the report generation worker thread."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    status_update = pyqtSignal(str, int, int, float, int)  # message, current_step, total_steps, elapsed_time, records_processed
    error = pyqtSignal(str)


class ReportWorker:
    """Worker class to run report generation in a separate thread."""
    
    def __init__(self, start_date: str, end_date: str, sucursal: str, device_filter: str):
        self.start_date = start_date
        self.end_date = end_date
        self.sucursal = sucursal
        self.device_filter = device_filter
        self.signals = ReportWorkerSignals()
        self.start_time = None
        self.current_step = 0
        self.total_steps = 7
        self.records_processed = 0
        
    def run(self):
        """Execute the report generation process."""
        try:
            self.start_time = time.time()
            self.signals.progress.emit("Iniciando generación de reporte...")
            
            # Create custom manager with progress callbacks
            manager = CustomAttendanceReportManager()
            manager.set_progress_callback(self.on_progress_update)
            
            result = manager.generate_attendance_report(
                start_date=self.start_date,
                end_date=self.end_date,
                sucursal=self.sucursal,
                device_filter=self.device_filter
            )
            
            self.signals.finished.emit(result)
            
        except Exception as e:
            self.signals.error.emit(str(e))
    
    def on_progress_update(self, step: int, message: str, records: int = 0):
        """Handle progress updates from the report manager."""
        self.current_step = step
        if records > 0:
            self.records_processed += records
        
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        self.signals.progress.emit(message)
        self.signals.status_update.emit(
            message, self.current_step, self.total_steps, elapsed_time, self.records_processed
        )


class ResultDialog(QDialog):
    """Dialog to show report generation results and provide Excel file access."""
    
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.result = result
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the result dialog UI."""
        self.setWindowTitle("Reporte Generado")
        self.setFixedSize(500, 300)
        
        layout = QVBoxLayout()
        
        # Success message
        if self.result.get("success"):
            success_label = QLabel("✅ ¡Reporte generado exitosamente!")
            success_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            layout.addWidget(success_label)
            
            # Report details
            details_group = QGroupBox("Detalles del Reporte")
            details_layout = QVBoxLayout()
            
            employees_processed = self.result.get('employees_processed', 'N/A')
            days_processed = self.result.get('days_processed', 'N/A')
            
            details_layout.addWidget(QLabel(f"👥 Empleados procesados: {employees_processed}"))
            details_layout.addWidget(QLabel(f"📆 Días procesados: {days_processed}"))
            
            if self.result.get("excel_report"):
                excel_path = self.result["excel_report"]
                details_layout.addWidget(QLabel(f"📊 Archivo Excel: {excel_path}"))
            
            details_group.setLayout(details_layout)
            layout.addWidget(details_group)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            if self.result.get("excel_report"):
                open_excel_btn = QPushButton("📊 Abrir Excel")
                open_excel_btn.clicked.connect(self.open_excel_file)
                button_layout.addWidget(open_excel_btn)
            
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(self.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
        else:
            # Error message
            error_label = QLabel("❌ Error al generar el reporte")
            error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            layout.addWidget(error_label)
            
            error_text = QTextEdit()
            error_text.setPlainText(self.result.get("error", "Error desconocido"))
            error_text.setMaximumHeight(150)
            error_text.setReadOnly(True)
            layout.addWidget(error_text)
            
            # Close button
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def open_excel_file(self):
        """Open the generated Excel file with the default application."""
        excel_path = self.result.get("excel_report")
        if not excel_path or not os.path.exists(excel_path):
            QMessageBox.warning(self, "Archivo no encontrado", 
                              f"No se pudo encontrar el archivo Excel: {excel_path}")
            return
        
        try:
            if platform.system() == "Windows":
                os.startfile(excel_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", excel_path])
            else:  # Linux
                subprocess.run(["xdg-open", excel_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"No se pudo abrir el archivo Excel:\n{str(e)}")


class AttendanceReportGUI(QMainWindow):
    """Main GUI window for the attendance report generator."""
    
    # Branch configurations: (display_name, sucursal, device_filter)
    BRANCH_OPTIONS = [
        ("31 PTE", "31pte", "%31%"),
        ("VILLAS", "Villas", "%villas%"),
        ("NAVE", "Nave", "%nave%"),
    ]
    
    def __init__(self):
        super().__init__()
        self.report_worker = None
        self.last_gui_line = ""  # Para evitar mensajes duplicados en GUI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("Generador de Reportes de Asistencia")
        self.setFixedSize(600, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title_label = QLabel("🏢 Generador de Reportes de Asistencia")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        main_layout.addWidget(title_label)
        
        # Date selection group
        date_group = QGroupBox("📅 Selección de Fechas")
        date_layout = QVBoxLayout()
        
        # Start date
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Fecha de inicio:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.dateChanged.connect(self.validate_dates)
        start_date_layout.addWidget(self.start_date_edit)
        date_layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("Fecha final:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.dateChanged.connect(self.validate_dates)
        end_date_layout.addWidget(self.end_date_edit)
        date_layout.addLayout(end_date_layout)
        
        # Date validation message
        self.date_validation_label = QLabel("")
        self.date_validation_label.setStyleSheet("color: red; font-size: 10px;")
        date_layout.addWidget(self.date_validation_label)
        
        date_group.setLayout(date_layout)
        main_layout.addWidget(date_group)
        
        # Branch selection group
        branch_group = QGroupBox("🏢 Selección de Sucursal")
        branch_layout = QVBoxLayout()
        
        branch_selection_layout = QHBoxLayout()
        branch_selection_layout.addWidget(QLabel("Sucursal:"))
        self.branch_combo = QComboBox()
        for display_name, _, _ in self.BRANCH_OPTIONS:
            self.branch_combo.addItem(display_name)
        branch_selection_layout.addWidget(self.branch_combo)
        branch_layout.addLayout(branch_selection_layout)
        
        branch_group.setLayout(branch_layout)
        main_layout.addWidget(branch_group)
        
        # Generate button
        self.generate_btn = QPushButton("🚀 Generar Reporte")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        main_layout.addWidget(self.generate_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Status display
        status_group = QGroupBox("📊 Estado del Sistema")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        self.status_text.setPlainText("Listo para generar reportes...")
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Initial validation
        self.validate_dates()
        
    def validate_dates(self):
        """Validate that end date is after start date."""
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        
        if end_date <= start_date:
            self.date_validation_label.setText("⚠️ La fecha final debe ser posterior a la fecha de inicio")
            self.generate_btn.setEnabled(False)
            return False
        else:
            self.date_validation_label.setText("")
            self.generate_btn.setEnabled(True)
            return True
    
    def update_status(self, message: str):
        """Update the status display and status bar."""
        # Verificar duplicados (ignorar espacios y saltos de línea)
        clean_message = message.strip()
        if clean_message == self.last_gui_line.strip():
            return  # No mostrar mensaje duplicado en GUI
        
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{current_time}] {message}"
        self.status_text.append(formatted_message)
        self.status_bar.showMessage(message)
        
        # Actualizar última línea enviada al GUI
        self.last_gui_line = message
    
    def update_progress_status(self, message: str, current_step: int, total_steps: int, elapsed_time: float, records_processed: int):
        """Update status with detailed progress information."""
        # Verificar duplicados para el mensaje principal
        clean_message = message.strip()
        if clean_message != self.last_gui_line.strip():
            current_time = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{current_time}] {message}"
            self.status_text.append(formatted_message)
            
            # Actualizar última línea enviada al GUI
            self.last_gui_line = message
        
        # Siempre mostrar la línea de progreso general (esta no debe duplicarse porque incluye tiempo dinámico)
        current_time = datetime.now().strftime("%H:%M:%S")
        progress_line = f"Progreso: {current_step}/{total_steps} pasos completados • Tiempo total: {elapsed_time:.1f}s • Registros procesados: {records_processed}"
        progress_formatted = f"[{current_time}] ℹ️ {progress_line}"
        self.status_text.append(progress_formatted)
        
        # Actualizar barra de progreso
        percent = int((current_step / total_steps) * 100) if total_steps else 0
        if percent < 0:
            percent = 0
        elif percent > 100:
            percent = 100
        self.progress_bar.setValue(percent)
        
        self.status_bar.showMessage(f"{message} | {progress_line}")
    
    def generate_report(self):
        """Start the report generation process."""
        if not self.validate_dates():
            return
        
        # Get selected values
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        selected_index = self.branch_combo.currentIndex()
        _, sucursal, device_filter = self.BRANCH_OPTIONS[selected_index]
        
        # Update UI for processing state
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        self.last_gui_line = ""  # Reiniciar control de duplicados
        self.update_status(f"Iniciando reporte para {sucursal} ({start_date} - {end_date})")
        
        # Create and start worker thread
        self.report_worker = ReportWorker(start_date, end_date, sucursal, device_filter)
        self.report_worker.signals.progress.connect(self.update_status)
        self.report_worker.signals.status_update.connect(self.update_progress_status)
        self.report_worker.signals.finished.connect(self.on_report_finished)
        self.report_worker.signals.error.connect(self.on_report_error)
        
        # Start the worker in a separate thread
        worker_thread = Thread(target=self.report_worker.run)
        worker_thread.daemon = True
        worker_thread.start()
    
    def on_report_finished(self, result: dict):
        """Handle successful report generation."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(100 if result.get("success") else self.progress_bar.value())
        self.progress_bar.setVisible(False)
        
        if result.get("success"):
            self.update_status("✅ Reporte generado exitosamente")
        else:
            self.update_status(f"❌ Error: {result.get('error', 'Error desconocido')}")
        
        # Show result dialog
        dialog = ResultDialog(result, self)
        dialog.exec()
    
    def on_report_error(self, error_message: str):
        """Handle report generation error."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.value())
        self.progress_bar.setVisible(False)
        self.update_status(f"❌ Error: {error_message}")
        
        # Show error dialog
        result = {"success": False, "error": error_message}
        dialog = ResultDialog(result, self)
        dialog.exec()


def main():
    """Main function to start the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Generador de Reportes de Asistencia")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Empresa")
    
    # Create and show main window
    window = AttendanceReportGUI()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()