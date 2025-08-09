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


class ReportWorkerSignals(QObject):
    """Signals for the report generation worker thread."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)


class ReportWorker:
    """Worker class to run report generation in a separate thread."""
    
    def __init__(self, start_date: str, end_date: str, sucursal: str, device_filter: str):
        self.start_date = start_date
        self.end_date = end_date
        self.sucursal = sucursal
        self.device_filter = device_filter
        self.signals = ReportWorkerSignals()
        
    def run(self):
        """Execute the report generation process."""
        try:
            self.signals.progress.emit("Iniciando generación de reporte...")
            manager = AttendanceReportManager()
            
            result = manager.generate_attendance_report(
                start_date=self.start_date,
                end_date=self.end_date,
                sucursal=self.sucursal,
                device_filter=self.device_filter
            )
            
            self.signals.finished.emit(result)
            
        except Exception as e:
            self.signals.error.emit(str(e))


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
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
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
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{current_time}] {message}"
        self.status_text.append(formatted_message)
        self.status_bar.showMessage(message)
    
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
        self.status_text.clear()
        self.update_status(f"Iniciando reporte para {sucursal} ({start_date} - {end_date})")
        
        # Create and start worker thread
        self.report_worker = ReportWorker(start_date, end_date, sucursal, device_filter)
        self.report_worker.signals.progress.connect(self.update_status)
        self.report_worker.signals.finished.connect(self.on_report_finished)
        self.report_worker.signals.error.connect(self.on_report_error)
        
        # Start the worker in a separate thread
        worker_thread = Thread(target=self.report_worker.run)
        worker_thread.daemon = True
        worker_thread.start()
    
    def on_report_finished(self, result: dict):
        """Handle successful report generation."""
        self.generate_btn.setEnabled(True)
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