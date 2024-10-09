import os
import sys
import json
import re
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QListWidget, QPushButton, QMessageBox, QTabWidget, QLineEdit
)
from PyQt5.QtCore import QThread, pyqtSignal

def parse_pcb_barcode(input_string):
    """Parses the PCB barcode into components: board name, revision, variant, serial number."""
    board_name_pattern = r"^(.*?)-"
    board_rev_pattern = r"^[^-]*-(.*?)-"
    board_var_pattern = r"(?:[^-]*-){2}([^-]*)-"
    board_sn_pattern = r"(?:[^-]*-){3}([^-\s]*)"

    board_name = re.match(board_name_pattern, input_string).group(1).lower() if re.match(board_name_pattern, input_string) else "unknown"
    board_rev = re.match(board_rev_pattern, input_string).group(1) if re.match(board_rev_pattern, input_string) else "unknown"
    board_var = re.search(board_var_pattern, input_string).group(1) if re.search(board_var_pattern, input_string) else "unknown"
    board_sn = re.search(board_sn_pattern, input_string).group(1) if re.search(board_sn_pattern, input_string) else "unknown"

    return board_name, board_rev, board_var, board_sn

class TestRunner(QThread):
    output_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, script, directory):
        super().__init__()
        self.script = script
        self.directory = directory
        self.process = None

    def run(self):
        os.chdir(self.directory)
        command = f'python -u "{self.script}"' if sys.platform.startswith('win') else f'python3 -u "{self.script}"'

        self.process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )

        # Read output
        for stdout_line in iter(self.process.stdout.readline, ""):
            if stdout_line:
                self.output_signal.emit(stdout_line.strip())
        self.process.stdout.close()

        # Read errors
        for stderr_line in iter(self.process.stderr.readline, ""):
            if stderr_line:
                self.error_signal.emit(stderr_line.strip())
        self.process.stderr.close()

        self.process.wait()

class TestLauncher(QWidget):
    def __init__(self, parent_dir):
        super().__init__()
        self.parent_dir = parent_dir
        self.runner = None
        self.script_mapping = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Test Program Launcher with Tabs")
        self.setMinimumSize(1280, 800)

        # Create the tab widget
        self.tabs = QTabWidget()
        
        # Create the Testing tab (with the current layout)
        testing_tab = QWidget()
        testing_tab_layout = self.create_testing_tab_layout()
        testing_tab.setLayout(testing_tab_layout)
        
        # Add the Testing tab to the tab widget
        self.tabs.addTab(testing_tab, "Testing")
        
        # Create the Reports tab (with barcode ID input and report display)
        reports_tab = QWidget()
        reports_tab_layout = self.create_reports_tab_layout()
        reports_tab.setLayout(reports_tab_layout)

        # Add the Reports tab to the tab widget
        self.tabs.addTab(reports_tab, "Reports")
        
        # Set the main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.show()

    def create_testing_tab_layout(self):
        """Creates the layout for the Testing tab."""
        main_layout = QHBoxLayout()

        # Create left layout for the testers pane
        left_layout = QVBoxLayout()

        # Path to the test programs directory
        test_programs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_programs')

        # Create a QListWidget to display script names
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(200)  # Set the fixed width for the testers pane
        left_layout.addWidget(self.list_widget)

        # Populate the QListWidget with scripts in the test_programs directory
        for script_name in os.listdir(test_programs_dir):
            if script_name.endswith('.py') and script_name not in ['dwfconstants.py', 'Enumerate.py']:
                script_path = os.path.join(test_programs_dir, script_name)
                self.list_widget.addItem(script_name[:-3])  # Display without '.py'
                self.script_mapping[script_name[:-3]] = (script_path, test_programs_dir)

        # Connect double-click event to run_test function
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Add the left layout to the main layout
        main_layout.addLayout(left_layout)

        # Create right layout for the output pane
        right_layout = QVBoxLayout()

        # Clear output button
        clear_button = QPushButton("Clear Output")
        clear_button.clicked.connect(self.clear_output)
        right_layout.addWidget(clear_button)

        # Output area to display terminal output
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(750)
        right_layout.addWidget(self.output_area)

        # Add the right layout to the main layout
        main_layout.addLayout(right_layout)
        
        # Add the stretch at the end to adjust the space
        right_layout.addStretch()

        return main_layout

    def create_reports_tab_layout(self):
        """Creates the layout for the Reports tab."""
        main_layout = QVBoxLayout()

        # Text box for entering barcode ID
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Enter the barcode ID...")
        main_layout.addWidget(self.barcode_input)

        # Button to load the report
        load_report_button = QPushButton("Load Report")
        load_report_button.clicked.connect(self.load_report)
        main_layout.addWidget(load_report_button)

        # Report display area
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        main_layout.addWidget(self.report_display)

        return main_layout

    def load_report(self):
        """Loads and displays the report based on the entered barcode ID."""
        barcode = self.barcode_input.text()

        # Parse the barcode
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)

        # Validate parsed barcode
        if board_name == "unknown" or board_rev == "unknown" or board_sn == "unknown":
            QMessageBox.warning(self, "Error", "Invalid barcode format.")
            return

        # Search for the report based on the barcode (assuming the JSON files follow the parsed barcode format)
        report_file = f"{board_name}-{board_rev}-{board_var}-{board_sn}.json"

        try:
            # Assume the reports are in the current working directory or a specific folder
            with open(report_file, 'r') as file:
                report_data = json.load(file)

            # Display the report in the text area
            self.report_display.clear()
            for report in report_data['test_reports']:
                self.report_display.append(f"Timestamp: {report['timestamp']}")
                self.report_display.append(f"Overall Status: {report['overall_status']}")
                self.report_display.append("Test Results:")
                for result in report['test_results']:
                    self.report_display.append(f"  Test {result['test_number']}: {result['description']}")
                    self.report_display.append(f"    Target: {result['target_value']}, Measured: {result['measured_value']}")
                    self.report_display.append(f"    Limits: ({result['lower_limit']}, {result['upper_limit']}) - Conclusion: {result['conclusion']}")
                self.report_display.append("\n" + "-"*50 + "\n")
        except FileNotFoundError:
            QMessageBox.warning(self, "Error", f"Report file for {board_name}-{board_rev}-{board_var}-{board_sn} not found.")
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Error", f"Failed to decode report file for barcode {barcode}.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred: {e}")

    def run_test(self, script, directory):
        if self.runner and self.runner.isRunning():
            QMessageBox.warning(self, "Warning", "A test is already running.")
            return

        self.runner = TestRunner(script, directory)
        self.runner.output_signal.connect(self.append_output)
        self.runner.error_signal.connect(self.append_output)
        self.runner.start()

    def append_output(self, text):
        self.output_area.append(text)
        self.output_area.moveCursor(self.output_area.textCursor().End)

    def clear_output(self):
        """Clears the contents of the output area."""
        self.output_area.clear()

    def on_item_double_clicked(self, item):
        """Runs the test corresponding to the double-clicked item."""
        script, directory = self.script_mapping[item.text()]
        self.run_test(script, directory)


if __name__ == "__main__":
    parent_directory = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    app = QApplication(sys.argv)
    ex = TestLauncher(parent_directory)
    sys.exit(app.exec_())
