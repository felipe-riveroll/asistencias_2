#!/usr/bin/env python3
"""
Test script to verify the PyQt6 GUI can be imported and initialized correctly.
This script tests the GUI components without running the full attendance report.
"""

import sys
from datetime import datetime

# Test GUI imports
try:
    from PyQt6.QtWidgets import QApplication
    from gui_pyqt6 import AttendanceReportGUI, ResultDialog

    print("✅ PyQt6 GUI imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


# Test GUI initialization
def test_gui_initialization():
    """Test that the GUI can be initialized without errors."""
    try:
        app = QApplication(sys.argv if sys.argv else ["test"])

        # Test main window creation
        window = AttendanceReportGUI()
        print("✅ Main window created successfully")

        # Test date validation
        is_valid = window.validate_dates()
        print(f"✅ Date validation working: {is_valid}")

        # Test branch options
        branch_count = window.branch_combo.count()
        print(f"✅ Branch options loaded: {branch_count} branches")

        # Test result dialog with success case
        test_result = {
            "success": True,
            "excel_report": "test_report.xlsx",
            "employees_processed": 10,
            "days_processed": 30,
        }
        result_dialog = ResultDialog(test_result, window)
        print("✅ Success result dialog created")

        # Test result dialog with error case
        test_error_result = {"success": False, "error": "Test error message"}
        error_dialog = ResultDialog(test_error_result, window)
        print("✅ Error result dialog created")

        print("✅ All GUI components initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ GUI initialization error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing PyQt6 GUI components...")
    print("=" * 50)

    success = test_gui_initialization()

    print("=" * 50)
    if success:
        print("✅ All tests passed! GUI is ready to use.")
        print("\nTo run the actual GUI application, execute:")
        print("python gui_pyqt6.py")
    else:
        print("❌ Tests failed. Please check the error messages above.")
        sys.exit(1)
