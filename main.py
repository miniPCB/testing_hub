import os
import sys
import subprocess
from datetime import datetime
import json
from common import ensure_numpy, ensure_pyqt_installed, install_gitpython, parse_pcb_barcode, report_json_to_html, red_tag_messages_json_to_html, process_flow_json_to_html, load_red_tag_messages, add_red_tag_message, save_red_tag_messages

try:
    import numpy as np
except ImportError:
    print("Numpy is not installed. Installing now...")
    ensure_numpy()

try:
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QListWidget, 
        QPushButton, QMessageBox, QHBoxLayout, QTabWidget, QLineEdit, 
        QListWidgetItem, QDialog, QInputDialog
    )
    from PyQt5.QtCore import QThread, pyqtSignal, Qt
except ImportError:
    print("PyQt5 is not installed. Installing now...")
    ensure_pyqt_installed()

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
        self.setWindowTitle("Testing Hub")
        self.setMinimumSize(1400, 900)
        
        # Create the tab widget
        self.tab_widget = QTabWidget()

        # Create Testing tab
        self.testing_tab = QWidget()
        self.setup_testing_tab()
        self.tab_widget.addTab(self.testing_tab, "Testing")

        # Create Reports tab
        self.reports_tab = QWidget()
        self.setup_reports_tab()
        self.tab_widget.addTab(self.reports_tab, "Reports")

        # Set the main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.show()

    def setup_testing_tab(self):
        """Sets up the Testing tab UI."""
        layout = QHBoxLayout()
        
        # Create the tester pane
        tester_layout = QVBoxLayout()
        self.list_widget = QListWidget()
        tester_layout.addWidget(QPushButton("Update All", clicked=self.git_pull))  # Update button
        tester_layout.addWidget(self.list_widget)

        # Populate the QListWidget with scripts
        test_programs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_programs')
        for script_name in os.listdir(test_programs_dir):
            if script_name.endswith('.py') and script_name not in ['dwfconstants.py', 'Enumerate.py']:
                script_path = os.path.join(test_programs_dir, script_name)
                self.list_widget.addItem(script_name[:-3])  # Display without '.py'
                self.script_mapping[script_name[:-3]] = (script_path, test_programs_dir)

        # Connect double-click event to run_test function
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Clear output button
        clear_button = QPushButton("Clear Output")
        clear_button.clicked.connect(self.clear_output)
        tester_layout.addWidget(clear_button)

        # Set fixed width for tester pane
        tester_widget = QWidget()
        tester_widget.setLayout(tester_layout)
        tester_widget.setFixedWidth(200)

        # Create output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(620)

        # Add widgets to main layout
        layout.addWidget(tester_widget)
        layout.addWidget(self.output_area)
        self.testing_tab.setLayout(layout)

    def setup_reports_tab(self):
        """Sets up the Reports tab UI."""
        layout = QHBoxLayout()

        # Create a vertical layout for the barcode input and available reports
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)

        # Add a label for the barcode input pane
        barcode_label = QLabel("Barcode Input:")
        left_layout.addWidget(barcode_label)

        # Create the barcode input field and load report button
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Enter Barcode...")

        # Connect the textChanged signal to the filter method
        self.barcode_input.textChanged.connect(self.filter_reports)

        load_report_button = QPushButton("Load Report", clicked=self.load_report)

        # Add to left layout
        left_layout.addWidget(self.barcode_input)
        left_layout.addWidget(load_report_button)

        # List to display filenames
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemDoubleClicked.connect(self.open_selected_file)

        # Add a label for the file list pane
        file_list_label = QLabel("Available Reports:")
        left_layout.addWidget(file_list_label)
        left_layout.addWidget(self.file_list_widget)

        # Create a widget for the left layout and set fixed width
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(300)

        # Create the tab widget for sub-tabs
        self.sub_tab_widget = QTabWidget()

        # Create Reports Display tab
        self.reports_display_tab = QWidget()
        self.setup_reports_display_tab()
        self.sub_tab_widget.addTab(self.reports_display_tab, "Reports Display")

        # Create Process Flow tab
        self.process_flow_tab = QWidget()
        self.setup_process_flow_tab()  # Implement this method to set up the process flow
        self.sub_tab_widget.addTab(self.process_flow_tab, "Process Flow")

        # Create Red Tag Messages tab
        self.red_tag_messages_tab = QWidget()
        self.setup_red_tag_messages_tab()  # Implement this method to set up red tag messages
        self.sub_tab_widget.addTab(self.red_tag_messages_tab, "Red Tag Messages")

        # Add the left widget and sub-tabs to the main layout
        layout.addWidget(left_widget)
        layout.addWidget(self.sub_tab_widget)

        self.reports_tab.setLayout(layout)

    def setup_reports_display_tab(self):
        """Sets up the Reports Display tab UI."""
        layout = QVBoxLayout()
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        layout.addWidget(self.report_display)
        self.reports_display_tab.setLayout(layout)

    def setup_process_flow_tab(self):
        """Sets up the Process Flow tab UI."""
        layout = QVBoxLayout()
        
        # Create the process flow display area
        self.process_flow_display = QTextEdit()
        self.process_flow_display.setReadOnly(True)
        
        layout.addWidget(self.process_flow_display)
        self.process_flow_tab.setLayout(layout)

    def setup_red_tag_messages_tab(self):
        """Sets up the Red Tag Messages tab UI."""
        layout = QVBoxLayout()

        # Create the red tag display area
        self.red_tag_display = QTextEdit()
        self.red_tag_display.setReadOnly(True)
        layout.addWidget(self.red_tag_display)

        # Create a horizontal layout for the input field and button
        input_layout = QHBoxLayout()

        # Create input field for the new red tag message
        self.red_tag_input = QLineEdit()
        self.red_tag_input.setPlaceholderText("Enter Red Tag Message...")
        input_layout.addWidget(self.red_tag_input)

        # Create the "Add Message" button
        add_button = QPushButton("Add Message", clicked=self.on_add_red_tag_message)
        add_button.setFixedWidth(250)  # Set button width to 250 pixels
        input_layout.addWidget(add_button)

        # Add the input layout to the main layout
        layout.addLayout(input_layout)

        # Set the layout for the tab
        self.red_tag_messages_tab.setLayout(layout)

    def on_add_red_tag_message(self):
        """Handles the addition of a red tag message."""
        message = self.red_tag_input.text().strip()
        if message:
            if hasattr(self, 'last_opened_file'):
                add_red_tag_message(message, self.last_opened_file)  # Call the function with the last opened file
                self.red_tag_input.clear()  # Clear the input field after adding
                # Optionally, reload/display the updated messages
                load_red_tag_messages(self)  # Ensure this function is implemented to refresh the display
            else:
                QMessageBox.warning(self, "Error", "No report file is currently open.")
        else:
            QMessageBox.warning(self, "Input Error", "Please enter a message.")

    def filter_reports(self):
        """Filter the report list based on the barcode input."""
        barcode = self.barcode_input.text().strip().lower()
        print(f"Filtering reports with barcode: {barcode}")
        self.file_list_widget.clear()

        reports_dir = os.path.join(self.parent_dir, 'testing_hub', 'reports')
        report_files = [f for f in os.listdir(reports_dir) if f.endswith('.json')]

        for report_file in report_files:
            if barcode in report_file.lower():
                item = QListWidgetItem(report_file)
                with open(os.path.join(reports_dir, report_file), 'r') as file:
                    report_content = json.load(file)
                    overall_status = report_content.get("test_reports", [{}])[0].get("overall_status", "Fail")

                if overall_status == "Pass":
                    item.setBackground(Qt.darkGreen)
                    item.setForeground(Qt.white)
                else:
                    item.setBackground(Qt.red)
                    item.setForeground(Qt.white)

                self.file_list_widget.addItem(item)

    def load_report(self):
        """Load the report corresponding to the entered barcode or show all files if blank."""
        barcode = self.barcode_input.text().strip()
        
        if not barcode:
            self.file_list_widget.clear()
            reports_dir = os.path.join(self.parent_dir, 'testing_hub', 'reports')
            
            # Retrieve and sort report files
            report_files = [f for f in os.listdir(reports_dir) if f.endswith('.json')]
            report_files.sort()  # Sort the report files alphabetically

            for report_file in report_files:
                report_file_path = os.path.join(reports_dir, report_file)
                with open(report_file_path, 'r') as file:
                    report_content = json.load(file)
                    overall_status = report_content.get("test_reports", [{}])[0].get("overall_status", "Fail")

                item = QListWidgetItem(report_file)
                if overall_status == "Pass":
                    item.setBackground(Qt.darkGreen)
                    item.setForeground(Qt.white)
                else:
                    item.setBackground(Qt.red)
                    item.setForeground(Qt.white)
                    
                self.file_list_widget.addItem(item)
            
            self.report_display.clear()
            self.red_tag_display.clear()
            self.process_flow_display.clear()
        else:
            board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
            board_id = f"{board_name}-{board_rev}-{board_var}-{board_sn}"
            report_file_name = f"{board_name}-{board_rev}-{board_var}-{board_sn}.json"
            report_file_path = os.path.join(self.parent_dir, 'testing_hub', 'reports', report_file_name)

            print(f"Looking for report file: {report_file_path}")

            if os.path.exists(report_file_path):
                with open(report_file_path, 'r') as file:
                    report_content = json.load(file)
                self.report_display.setHtml(report_json_to_html(report_content))
                self.red_tag_display.setHtml(red_tag_messages_json_to_html(report_content))
                self.process_flow_display.setHtml(process_flow_json_to_html(report_content))
                self.file_list_widget.clear()
            else:
                self.report_display.clear()
                self.red_tag_display.clear()
                self.process_flow_display.clear()
                report_dialog = ReportNotFoundDialog(board_id, report_file_name, report_file_path, self)
                report_dialog.exec_()
    
    def open_selected_file(self, item):
        """Open the selected report file from the list and populate the sub-tabs."""
        filename = item.text()
        reports_dir = os.path.join(self.parent_dir, 'testing_hub', 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        try:
            with open(file_path, 'r') as file:
                report_content = json.load(file)
            
            # Display the report content in the report display area
            self.report_display.setHtml(report_json_to_html(report_content))

            # Display red tag messages
            self.red_tag_display.setHtml(red_tag_messages_json_to_html(report_content))

            # Display process flow content
            self.process_flow_display.setHtml(process_flow_json_to_html(report_content))

            # Save the path of the last opened file for future reference
            self.last_opened_file = file_path

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open report: {str(e)}")

    def git_pull(self):
        """Function to run git fetch and then git pull command."""
        try:
            subprocess.check_call(['git', 'fetch'], cwd=self.parent_dir)
            subprocess.check_call(['git', 'pull'], cwd=self.parent_dir)
            self.append_output("Successfully pulled from the repository.")
        except subprocess.CalledProcessError as e:
            self.append_output(f"Error during git pull: {e}")


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

class ReportNotFoundDialog(QDialog):
    def __init__(self, board_id, report_file_name, report_file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Not Found")
        
        # Set the minimum size of the dialog
        self.resize(400, 150)

        self.board_id = board_id
        self.report_file_name = report_file_name
        self.report_file_path = report_file_path

        layout = QVBoxLayout()
        
        # Add a message label
        message_label = QLabel(f"Create a Red Tag for: {self.board_id}.")
        layout.addWidget(message_label)

        # Create the "Create Report File" button
        create_report_button = QPushButton("Create a Red Tag")
        create_report_button.clicked.connect(lambda: self.create_report_file(self.board_id))
        layout.addWidget(create_report_button)

        self.setLayout(layout)

    def create_report_file(self, board_id):
        """Creates a new report file."""
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_data = {
            "test_reports": [{
                "timestamp": timestamp,
                "barcode": board_id,
                "overall_status": "Fail"
            }],
            "process_flow_messages": [],
            "red_tag_messages": []
        }

        report_file_path = self.report_file_path

        try:
            with open(report_file_path, 'w') as file:
                json.dump(report_data, file, indent=4)

            QMessageBox.information(self, "Success", f"Report file '{os.path.basename(report_file_path)}' created successfully!")
            self.accept()  # Close the dialog after creating the report
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create report file: {str(e)}")

if __name__ == "__main__":
    parent_directory = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    app = QApplication(sys.argv)
    ex = TestLauncher(parent_directory)
    sys.exit(app.exec_())
