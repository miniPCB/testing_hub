import os
import sys
import subprocess
from datetime import datetime
import json
from common import ensure_numpy, ensure_pyqt_installed, parse_pcb_barcode, report_json_to_html, red_tag_messages_json_to_html, process_flow_json_to_html, load_red_tag_messages, add_red_tag_message, save_red_tag_messages

try:
    import numpy as np
except ImportError:
    print("Numpy is not installed. Installing now...")
    ensure_numpy()

try:
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QListWidget, 
        QPushButton, QMessageBox, QHBoxLayout, QTabWidget, QLineEdit, 
        QListWidgetItem, QDialog, QInputDialog, QAction, QMainWindow, 
        QCheckBox, QTreeWidget, QTreeWidgetItem,
        QRadioButton, QButtonGroup, QDialogButtonBox
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

class TestLauncher(QMainWindow):
    def __init__(self, parent_dir):
        super().__init__()
        self.parent_dir = parent_dir
        self.script_mapping = {}
        self.messages = {}  # Initialize messages as empty
        self.load_messages()  # Load messages during initialization
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Testing Hub")
        self.setMinimumSize(1400, 900)

        # Create the menu bar
        self.create_menu_bar()

        # Create the tab widget
        self.tab_widget = QTabWidget()

        # Add tabs here...
        self.setup_testing_tab()
        self.setup_reports_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        # Create a central widget and set the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Set the central widget in the QMainWindow
        self.setCentralWidget(central_widget)

        self.show()

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        # messages action
        messages_action = QAction("Manage Messages", self)
        messages_action.triggered.connect(self.open_messages_dialog)
        file_menu.addAction(messages_action)

        # Manage Configurations action (moved from Configuration menu to File menu)
        manage_config_action = QAction("Manage Configurations", self)
        manage_config_action.triggered.connect(self.open_config_manager)
        file_menu.addAction(manage_config_action)  # Add to File menu

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Actions menu
        actions_menu = menu_bar.addMenu("Actions")

        # Apply Process Message action
        apply_process_message_action = QAction("Apply Process Message", self)
        apply_process_message_action.triggered.connect(self.apply_process_message)
        actions_menu.addAction(apply_process_message_action)

        # Apply Red Tag Message action
        apply_red_tag_message_action = QAction("Apply Red Tag Message", self)
        apply_red_tag_message_action.triggered.connect(self.apply_red_tag_message)
        actions_menu.addAction(apply_red_tag_message_action)

        # Build Assembly action
        build_assembly_action = QAction("Build Assembly", self)
        #build_assembly_action.triggered.connect(self.build_assembly)
        actions_menu.addAction(build_assembly_action)

    def open_config_manager(self):
        """Opens the configuration management dialog."""
        config_dialog = ConfigManagerDialog(self.parent_dir)
        config_dialog.exec_()  # Open the dialog modally


    def apply_process_message(self):
        # Ensure messages are loaded
        if not hasattr(self, 'messages') or not self.messages:
            self.load_messages()  # Load messages if they haven't been loaded yet

        # Retrieve process messages from the messages
        messages = self.messages.get("process_messages", [])
        
        if not messages:
            QMessageBox.warning(self, "No Messages", "No process messages are available to apply.")
            return
        
        # Open the ApplyMessageDialog to select a message (with radio buttons)
        dialog = ApplyMessageDialog(messages, "Process")

        if dialog.exec_() == QDialog.Accepted:
            # Correctly pass the selected message to BarcodeProcessingDialog
            barcode_dialog = BarcodeProcessingDialog(dialog.selected_message, "Process")
            barcode_dialog.exec_()

    def apply_red_tag_message(self):
        # Ensure messages are loaded
        if not hasattr(self, 'messages') or not self.messages:
            self.load_messages()  # Load messages if they haven't been loaded yet

        # Retrieve red tag messages from the messages
        messages = self.messages.get("red_tag_messages", [])
        
        if not messages:
            QMessageBox.warning(self, "No Messages", "No red tag messages are available to apply.")
            return
        
        # Open the ApplyMessageDialog to select a red tag message (with radio buttons)
        dialog = ApplyMessageDialog(messages, "Red Tag")

        if dialog.exec_() == QDialog.Accepted:
            # Correctly pass the selected message to BarcodeProcessingDialog
            barcode_dialog = BarcodeProcessingDialog(dialog.selected_message, "Red Tag")
            barcode_dialog.exec_()

    def load_messages(self):
        """Loads messages from the JSON file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        messages_file = os.path.join(current_dir, 'config', 'messages.json')
        try:
            with open(messages_file, 'r') as file:
                self.messages = json.load(file)
                print("messages loaded successfully:", self.messages)
        except (FileNotFoundError, json.JSONDecodeError):
            self.messages = {}
            print(f"Failed to load messages or {messages_file} not found.")

    def stop_barcode_processing(self):
        QMessageBox.information(self, "Process Stopped", "Stopped applying messages to scanned barcodes.")

    def open_messages_dialog(self):
        """Opens the messages dialog."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        messages_file = os.path.join(current_dir, 'config', 'messages.json')
        dialog = messagesDialog(messages_file)
        dialog.exec_()  # Open the dialog modally

    def setup_testing_tab(self):
        """Sets up the Testing tab UI."""
        self.testing_tab = QWidget()
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
        self.tab_widget.addTab(self.testing_tab, "Testing")

    def setup_reports_tab(self):
        """Sets up the Reports tab UI."""
        self.reports_tab = QWidget()
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
        self.barcode_input.textChanged.connect(self.filter_reports)

        load_report_button = QPushButton("Load Report", clicked=self.load_report)
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
        self.setup_process_flow_tab()
        self.sub_tab_widget.addTab(self.process_flow_tab, "Process Flow")

        # Create Red Tag Messages tab
        self.red_tag_messages_tab = QWidget()
        self.setup_red_tag_messages_tab()
        self.sub_tab_widget.addTab(self.red_tag_messages_tab, "Red Tag Messages")

        # Add the left widget and sub-tabs to the main layout
        layout.addWidget(left_widget)
        layout.addWidget(self.sub_tab_widget)

        self.reports_tab.setLayout(layout)
        self.tab_widget.addTab(self.reports_tab, "Reports")

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
        self.process_flow_display = QTextEdit()
        self.process_flow_display.setReadOnly(True)
        layout.addWidget(self.process_flow_display)
        self.process_flow_tab.setLayout(layout)

    def setup_red_tag_messages_tab(self):
        """Sets up the Red Tag Messages tab UI."""
        layout = QVBoxLayout()
        self.red_tag_display = QTextEdit()
        self.red_tag_display.setReadOnly(True)
        layout.addWidget(self.red_tag_display)

        input_layout = QHBoxLayout()
        self.red_tag_input = QLineEdit()
        self.red_tag_input.setPlaceholderText("Enter Red Tag Message...")
        input_layout.addWidget(self.red_tag_input)

        add_button = QPushButton("Add Message", clicked=self.on_add_red_tag_message)
        add_button.setFixedWidth(250)
        input_layout.addWidget(add_button)
        layout.addLayout(input_layout)

        self.red_tag_messages_tab.setLayout(layout)

    def on_add_red_tag_message(self):
        """Handles the addition of a red tag message."""
        message = self.red_tag_input.text().strip()
        if message:
            if hasattr(self, 'last_opened_file'):
                add_red_tag_message(message, self.last_opened_file)
                self.red_tag_input.clear()
                load_red_tag_messages(self)
            else:
                QMessageBox.warning(self, "Error", "No report file is currently open.")
        else:
            QMessageBox.warning(self, "Input Error", "Please enter a message.")

    def filter_reports(self):
        """Filter the report list based on the barcode input."""
        barcode = self.barcode_input.text().strip().lower()
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
            report_files = [f for f in os.listdir(reports_dir) if f.endswith('.json')]

            for report_file in report_files:
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
            self.report_display.clear()
            self.red_tag_display.clear()
            self.process_flow_display.clear()
        else:
            board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
            report_file_name = f"{board_name}-{board_rev}-{board_var}-{board_sn}.json"
            report_file_path = os.path.join(self.parent_dir, 'testing_hub', 'reports', report_file_name)

            if os.path.exists(report_file_path):
                with open(report_file_path, 'r') as file:
                    report_content = json.load(file)
                self.report_display.setHtml(report_json_to_html(report_content))
                self.red_tag_display.setHtml(red_tag_messages_json_to_html(report_content))
                self.process_flow_display.setHtml(process_flow_json_to_html(report_content))
                self.file_list_widget.clear()
            else:
                QMessageBox.warning(self, "Error", "Report not found.")

    def open_selected_file(self, item):
        """Open the selected report file from the list and populate the sub-tabs."""
        filename = item.text()
        reports_dir = os.path.join(self.parent_dir, 'testing_hub', 'reports')
        file_path = os.path.join(reports_dir, filename)

        try:
            with open(file_path, 'r') as file:
                report_content = json.load(file)
            self.report_display.setHtml(report_json_to_html(report_content))
            self.red_tag_display.setHtml(red_tag_messages_json_to_html(report_content))
            self.process_flow_display.setHtml(process_flow_json_to_html(report_content))
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

    def run_test(self, script, directory):
        if hasattr(self, 'runner') and self.runner.isRunning():
            QMessageBox.warning(self, "Warning", "A test is already running.")
            return

        self.runner = TestRunner(script, directory)
        self.runner.output_signal.connect(self.append_output)
        self.runner.error_signal.connect(self.append_output)
        self.runner.start()

class messagesDialog(QDialog):
    def __init__(self, messages_file):
        super().__init__()
        self.messages_file = messages_file
        self.setWindowTitle("messages")
        self.setMinimumSize(800, 600)  # Set minimum size to 800x600

        # Create the tab widget
        self.tab_widget = QTabWidget()

        # Load the messages from the JSON file
        self.messages = self.load_messages()

        # Process Messages tab
        self.process_messages_tab = QWidget()
        self.setup_process_messages_tab()

        # Red Tag Messages tab
        self.red_tag_messages_tab = QWidget()
        self.setup_red_tag_messages_tab()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.process_messages_tab, "Process Messages")
        self.tab_widget.addTab(self.red_tag_messages_tab, "Red Tag Messages")

        # Create the main layout and add the tab widget
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        # Add save button
        save_button = QPushButton("Save", self)
        save_button.clicked.connect(self.save_messages)
        layout.addWidget(save_button)

        # Set layout
        self.setLayout(layout)

    def load_messages(self):
        """Loads messages from the JSON file."""
        try:
            with open(self.messages_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def save_messages(self):
        """Saves the messages to the JSON file."""
        try:
            with open(self.messages_file, 'w') as file:
                json.dump(self.messages, file, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save messages: {str(e)}")

    def setup_process_messages_tab(self):
        """Sets up the Process Messages tab."""
        layout = QVBoxLayout()

        # Input field for adding process messages
        self.process_message_input = QLineEdit()
        self.process_message_input.setPlaceholderText("Enter Process Message")
        layout.addWidget(self.process_message_input)

        # Button to add process message
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_process_message)
        layout.addWidget(add_button)

        # Create a QTreeWidget to display process messages
        self.process_message_tree = QTreeWidget()
        self.process_message_tree.setHeaderLabels(["", "Process Message"])
        for message in self.messages.get("process_messages", []):
            item = QTreeWidgetItem(self.process_message_tree)
            item.setText(1, message)
            item.setCheckState(0, Qt.Unchecked)
        layout.addWidget(self.process_message_tree)

        # Button to remove selected process messages
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_process_message)
        layout.addWidget(remove_button)

        self.process_messages_tab.setLayout(layout)

    def setup_red_tag_messages_tab(self):
        """Sets up the Red Tag Messages tab."""
        layout = QVBoxLayout()

        # Input field for adding red tag messages
        self.red_tag_message_input = QLineEdit()
        self.red_tag_message_input.setPlaceholderText("Enter Red Tag Message")
        layout.addWidget(self.red_tag_message_input)

        # Button to add red tag message
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_red_tag_message)
        layout.addWidget(add_button)

        # Create a QTreeWidget to display red tag messages
        self.red_tag_message_tree = QTreeWidget()
        self.red_tag_message_tree.setHeaderLabels(["", "Red Tag Message"])
        for message in self.messages.get("red_tag_messages", []):
            item = QTreeWidgetItem(self.red_tag_message_tree)
            item.setText(1, message)
            item.setCheckState(0, Qt.Unchecked)
        layout.addWidget(self.red_tag_message_tree)

        # Button to remove selected red tag messages
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_red_tag_message)
        layout.addWidget(remove_button)

        self.red_tag_messages_tab.setLayout(layout)

    def add_process_message(self):
        """Adds a new process message."""
        message = self.process_message_input.text().strip()
        if message:
            item = QTreeWidgetItem(self.process_message_tree)
            item.setText(1, message)
            item.setCheckState(0, Qt.Unchecked)
            self.messages.setdefault("process_messages", []).append(message)
            self.process_message_input.clear()

    def remove_process_message(self):
        """Removes the selected process messages."""
        # Reverse loop to avoid skipping items when removing
        for index in range(self.process_message_tree.topLevelItemCount() - 1, -1, -1):
            item = self.process_message_tree.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                # Remove from the tree widget
                self.process_message_tree.takeTopLevelItem(index)
                # Remove from the messages
                self.messages["process_messages"].remove(item.text(1))

    def add_red_tag_message(self):
        """Adds a new red tag message."""
        message = self.red_tag_message_input.text().strip()
        if message:
            item = QTreeWidgetItem(self.red_tag_message_tree)
            item.setText(1, message)
            item.setCheckState(0, Qt.Unchecked)
            self.messages.setdefault("red_tag_messages", []).append(message)
            self.red_tag_message_input.clear()

    def remove_red_tag_message(self):
        """Removes the selected red tag messages."""
        # Reverse loop to avoid skipping items when removing
        for index in range(self.red_tag_message_tree.topLevelItemCount() - 1, -1, -1):
            item = self.red_tag_message_tree.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                # Remove from the tree widget
                self.red_tag_message_tree.takeTopLevelItem(index)
                # Remove from the messages
                self.messages["red_tag_messages"].remove(item.text(1))

class ApplyMessageDialog(QDialog):
    def __init__(self, messages, message_type):
        super().__init__()
        self.setWindowTitle(f"Apply {message_type} Message")
        self.selected_message = None
        self.message_type = message_type

        # Layout for radio buttons
        layout = QVBoxLayout()

        # Add a title for the dialog
        label = QLabel(f"Restart application for latest messages:")
        layout.addWidget(label)

        # Create a group of radio buttons for the messages
        self.button_group = QButtonGroup(self)
        for i, message in enumerate(messages):
            radio_button = QRadioButton(message)
            self.button_group.addButton(radio_button, i)
            layout.addWidget(radio_button)

        # Create an Apply button
        apply_button = QPushButton("Apply Message")
        apply_button.clicked.connect(self.apply_message)
        layout.addWidget(apply_button)

        self.setLayout(layout)

    def apply_message(self):
        # Get the selected message
        selected_button = self.button_group.checkedButton()
        if selected_button:
            self.selected_message = selected_button.text()
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", f"No {self.message_type} message selected.")

class BarcodeProcessingDialog(QDialog):
    stop_signal = pyqtSignal()

    def __init__(self, message, message_type):
        super().__init__()
        self.setWindowTitle(f"Applying {message_type} Message")
        
        layout = QVBoxLayout()
        
        # Display the selected message
        layout.addWidget(QLabel(f"Applying '{message}' to scanned barcodes..."))

        # Stop button
        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_processing)
        layout.addWidget(stop_button)

        self.setLayout(layout)

    def stop_processing(self):
        self.stop_signal.emit()  # Emit the stop signal
        self.accept()  # Close the dialog

class ConfigManagerDialog(QDialog):
    def __init__(self, parent_dir):
        super().__init__()
        self.parent_dir = parent_dir
        self.setWindowTitle("Configuration Manager")
        self.setMinimumSize(800, 600)

        # Load items and assemblies
        self.config_items = self.load_json_file('config_items.json', 'items')
        self.config_assemblies = self.load_json_file('config_assemblies.json', 'assemblies')

        # Create a tab widget
        self.tab_widget = QTabWidget()

        # Create Items tab
        self.items_tab = QWidget()
        self.setup_items_tab()

        # Create assemblies tab
        self.assemblies_tab = QWidget()
        self.setup_assemblies_tab()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.items_tab, "Items")
        self.tab_widget.addTab(self.assemblies_tab, "assemblies")

        # Create the main layout and add the tab widget
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        # Add Save and Close buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_configurations)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_json_file(self, filename, key):
        """Helper function to load items or assemblies from a JSON file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'config', filename)
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            return data.get(key, [])
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    def setup_items_tab(self):
        """Sets up the UI for managing config items."""
        layout = QVBoxLayout()

        # List to display items
        self.items_list = QListWidget()
        for item in self.config_items:
            self.items_list.addItem(f"{item['id']} - {item['name']} ({item['type']})")
        layout.addWidget(self.items_list)

        # Add, Edit, and Remove buttons for items
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Item")
        add_button.clicked.connect(self.add_item)

        edit_button = QPushButton("Edit Item")  # Create the edit button
        edit_button.clicked.connect(self.edit_item)  # Connect to edit_item method

        remove_button = QPushButton("Remove Item")
        remove_button.clicked.connect(self.remove_item)

        # Add the buttons to the layout
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(remove_button)
        layout.addLayout(button_layout)

        self.items_tab.setLayout(layout)

    def setup_assemblies_tab(self):
        """Sets up the UI for managing config assemblies."""
        layout = QVBoxLayout()

        # List to display assemblies
        self.assemblies_list = QListWidget()
        for profile in self.config_assemblies:
            self.assemblies_list.addItem(f"{profile['id']} - {profile['name']}")
        layout.addWidget(self.assemblies_list)

        # Add, Edit, and Remove buttons for assemblies
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Profile")
        add_button.clicked.connect(self.add_profile)

        edit_button = QPushButton("Edit Profile")  # Create the edit button
        edit_button.clicked.connect(self.edit_profile)  # Connect to edit_profile method

        remove_button = QPushButton("Remove Profile")
        remove_button.clicked.connect(self.remove_profile)

        # Add the buttons to the layout
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(remove_button)
        layout.addLayout(button_layout)

        self.assemblies_tab.setLayout(layout)

    # Methods to add and edit items and assemblies
    def add_item(self):
        """Opens a dialog to add a new config item."""
        item_dialog = ItemDialog(self.config_items)
        if item_dialog.exec_() == QDialog.Accepted:
            new_item = item_dialog.get_item()
            self.config_items.append(new_item)
            self.items_list.addItem(f"{new_item['id']} - {new_item['name']} ({new_item['type']})")

    def edit_item(self):
        """Opens a dialog to edit the selected config item."""
        selected_item_index = self.items_list.currentRow()
        if selected_item_index >= 0:
            selected_item = self.config_items[selected_item_index]
            item_dialog = ItemDialog(self.config_items, item=selected_item)
            if item_dialog.exec_() == QDialog.Accepted:
                updated_item = item_dialog.get_item()
                self.config_items[selected_item_index] = updated_item
                self.items_list.item(selected_item_index).setText(f"{updated_item['id']} - {updated_item['name']} ({updated_item['type']})")

    def remove_item(self):
        """Removes the selected item from the list."""
        selected_item = self.items_list.currentRow()
        if selected_item >= 0:
            self.config_items.pop(selected_item)
            self.items_list.takeItem(selected_item)

    def add_profile(self):
        """Opens a dialog to add a new profile."""
        profile_dialog = ProfileDialog(self.config_assemblies, self.config_items)
        if profile_dialog.exec_() == QDialog.Accepted:
            new_profile = profile_dialog.get_profile()
            self.config_assemblies.append(new_profile)
            self.assemblies_list.addItem(f"{new_profile['id']} - {new_profile['name']}")

    def edit_profile(self):
        """Opens a dialog to edit the selected profile."""
        selected_profile_index = self.assemblies_list.currentRow()
        if selected_profile_index >= 0:
            selected_profile = self.config_assemblies[selected_profile_index]
            profile_dialog = ProfileDialog(self.config_assemblies, self.config_items, profile=selected_profile)
            if profile_dialog.exec_() == QDialog.Accepted:
                updated_profile = profile_dialog.get_profile()
                self.config_assemblies[selected_profile_index] = updated_profile
                self.assemblies_list.item(selected_profile_index).setText(f"{updated_profile['id']} - {updated_profile['name']}")

    def remove_profile(self):
        """Removes the selected profile from the list."""
        selected_profile = self.assemblies_list.currentRow()
        if selected_profile >= 0:
            self.config_assemblies.pop(selected_profile)
            self.assemblies_list.takeItem(selected_profile)

    def save_configurations(self):
        """Saves the items and assemblies to their respective JSON files."""
        self.save_json_file('config_items.json', 'items', self.config_items)
        self.save_json_file('config_assemblies.json', 'assemblies', self.config_assemblies)
        QMessageBox.information(self, "Saved", "Configuration items and assemblies saved successfully.")

    def save_json_file(self, filename, key, data):
        """Helper function to save items or assemblies to a JSON file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'config', filename)
        with open(file_path, 'w') as file:
            json.dump({key: data}, file, indent=4)


class ItemDialog(QDialog):
    def __init__(self, items, item=None):  # Optional item argument for editing
        super().__init__()
        self.setWindowTitle("Add or Edit Item")
        self.items = items
        self.item_data = {}

        layout = QVBoxLayout()

        # Input fields for item details
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Item ID")
        layout.addWidget(self.id_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Item Name")
        layout.addWidget(self.name_input)

        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText("Item Type")
        layout.addWidget(self.type_input)

        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Item Version")
        layout.addWidget(self.version_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Item Description")
        layout.addWidget(self.desc_input)

        # Pre-fill the fields if editing
        if item:
            self.id_input.setText(item['id'])
            self.name_input.setText(item['name'])
            self.type_input.setText(item['type'])
            self.version_input.setText(item['version'])
            self.desc_input.setText(item['description'])

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        """Override accept to capture item data."""
        self.item_data = {
            'id': self.id_input.text(),
            'name': self.name_input.text(),
            'type': self.type_input.text(),
            'version': self.version_input.text(),
            'description': self.desc_input.toPlainText()
        }
        super().accept()

    def get_item(self):
        """Returns the item data."""
        return self.item_data

class ProfileDialog(QDialog):
    def __init__(self, assemblies, items, profile=None):  # Optional profile argument for editing
        super().__init__()
        self.setWindowTitle("Add or Edit Profile")
        self.assemblies = assemblies
        self.items = items
        self.profile_data = {}

        layout = QVBoxLayout()

        # Input fields for profile details
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Profile ID")
        layout.addWidget(self.id_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile Name")
        layout.addWidget(self.name_input)

        # Dropdown or list for selecting items to include in the profile
        self.items_list = QListWidget()
        self.items_list.setSelectionMode(QListWidget.MultiSelection)
        for item in self.items:
            self.items_list.addItem(f"{item['id']} - {item['name']} ({item['type']})")
        layout.addWidget(self.items_list)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Profile Description")
        layout.addWidget(self.desc_input)

        # Pre-fill the fields if editing
        if profile:
            self.id_input.setText(profile['id'])
            self.name_input.setText(profile['name'])
            # Mark selected items
            for i in range(self.items_list.count()):
                item_widget = self.items_list.item(i)
                if any(selected_item == item_widget.text() for selected_item in profile['items']):
                    item_widget.setSelected(True)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        """Override accept to capture profile data."""
        selected_items = [item.text() for item in self.items_list.selectedItems()]
        self.profile_data = {
            'id': self.id_input.text(),
            'name': self.name_input.text(),
            'items': selected_items,
            'description': self.desc_input.toPlainText()
        }
        super().accept()

    def get_profile(self):
        """Returns the profile data."""
        return self.profile_data

if __name__ == "__main__":
    parent_directory = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    app = QApplication(sys.argv)
    ex = TestLauncher(parent_directory)
    sys.exit(app.exec_())
