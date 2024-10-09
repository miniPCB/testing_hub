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
        try:
            if not os.path.exists(self.directory):
                self.error_signal.emit(f"Directory does not exist: {self.directory}")
                return
            
            os.chdir(self.directory)
            command = f'python -u "{self.script}"' if sys.platform.startswith('win') else f'python3 -u "{self.script}"'
            
            if not os.path.isfile(self.script):
                self.error_signal.emit(f"Script does not exist: {self.script}")
                return

            self.process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )

            for stdout_line in iter(self.process.stdout.readline, ""):
                if stdout_line:
                    self.output_signal.emit(stdout_line.strip())
            self.process.stdout.close()

            for stderr_line in iter(self.process.stderr.readline, ""):
                if stderr_line:
                    self.error_signal.emit(stderr_line.strip())
            self.process.stderr.close()

            self.process.wait()

        except Exception as e:
            self.error_signal.emit(f"An error occurred: {str(e)}")

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

        self.tabs = QTabWidget()

        testing_tab = QWidget()
        testing_tab_layout = self.create_testing_tab_layout()
        testing_tab.setLayout(testing_tab_layout)
        self.tabs.addTab(testing_tab, "Testing")
        
        reports_tab = QWidget()
        reports_tab_layout = self.create_reports_tab_layout()
        reports_tab.setLayout(reports_tab_layout)
        self.tabs.addTab(reports_tab, "Reports")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.show()

    def create_testing_tab_layout(self):
        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        test_programs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_programs')

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(200)
        left_layout.addWidget(self.list_widget)

        for script_name in os.listdir(test_programs_dir):
            if script_name.endswith('.py') and script_name not in ['dwfconstants.py', 'Enumerate.py']:
                script_path = os.path.join(test_programs_dir, script_name)
                self.list_widget.addItem(script_name[:-3])
                self.script_mapping[script_name[:-3]] = (script_path, test_programs_dir)

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        main_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()
        clear_button = QPushButton("Clear Output")
        clear_button.clicked.connect(self.clear_output)
        right_layout.addWidget(clear_button)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(750)
        right_layout.addWidget(self.output_area)
        right_layout.addStretch()

        main_layout.addLayout(right_layout)

        return main_layout

    def create_reports_tab_layout(self):
        main_layout = QVBoxLayout()

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Enter the barcode ID...")
        main_layout.addWidget(self.barcode_input)

        load_report_button = QPushButton("Load Report")
        load_report_button.clicked.connect(self.load_report)
        main_layout.addWidget(load_report_button)

        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        main_layout.addWidget(self.report_display)

        return main_layout

    def load_report(self):
        """Loads and displays the report based on the entered barcode ID."""
        barcode = self.barcode_input.text()
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)

        if board_name == "unknown" or board_rev == "unknown" or board_sn == "unknown":
            QMessageBox.warning(self, "Error", "Invalid barcode format.")
            return

        report_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        report_file = os.path.join(report_folder, f"{board_name}-{board_rev}-{board_var}-{board_sn}.json")

        try:
            with open(report_file, 'r') as file:
                report_data = json.load(file)

            # Start building the HTML content
            html_content = f"<h2>Report for Barcode: {barcode}</h2>"

            for report in report_data['test_reports']:
                html_content += f"<h3>Timestamp: {report['timestamp']}</h3>"
                overall_status_color = "green" if report['overall_status'] == "Pass" else "red"
                html_content += f"<p><strong>Overall Status:</strong> <span style='color:{overall_status_color};'>{report['overall_status']}</span></p>"

                # Build a table for test results
                html_content += """
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
                    <thead>
                        <tr>
                            <th>Test #</th>
                            <th>Description</th>
                            <th>Target</th>
                            <th>Measured</th>
                            <th>Limits</th>
                            <th>Conclusion</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for result in report['test_results']:
                    conclusion_color = "green" if result['conclusion'] == "Pass" else "red"
                    html_content += f"""
                    <tr>
                        <td>{result['test_number']}</td>
                        <td>{result['description']}</td>
                        <td>{result['target_value']}</td>
                        <td>{result['measured_value']}</td>
                        <td>({result['lower_limit']}, {result['upper_limit']})</td>
                        <td style="color:{conclusion_color};"><strong>{result['conclusion']}</strong></td>
                    </tr>
                    """
                html_content += "</tbody></table><br>"

            # Set the HTML content to the QTextEdit widget
            self.report_display.setHtml(html_content)

        except FileNotFoundError:
            QMessageBox.warning(self, "Error", f"Report file for barcode {barcode} not found in the 'reports' folder.")
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
        self.runner.error_signal.connect(self.handle_error)
        self.runner.start()

    def append_output(self, text):
        self.output_area.append(text)
        self.output_area.moveCursor(self.output_area.textCursor().End)

    def handle_error(self, error_text):
        QMessageBox.critical(self, "Error", error_text)

    def clear_output(self):
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
