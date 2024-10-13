import re
import json
import sys
import subprocess
import os
import git
import time
from datetime import datetime
from ctypes import *
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

def ensure_psutil():
    """Ensure psutil is installed."""
    try:
        import psutil
    except ImportError:
        print("psutil is not installed. Installing now...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
            import numpy as np
            print("psutil installed successfully.")
        except Exception as e:
            print(f"Failed to install psutil: {e}")
            sys.exit(1)

def ensure_numpy():
    """Ensure numpy is installed."""
    try:
        import numpy as np
    except ImportError:
        print("Numpy is not installed. Installing now...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
            import numpy as np
            print("Numpy installed successfully.")
        except Exception as e:
            print(f"Failed to install numpy: {e}")
            sys.exit(1)

def ensure_pyqt_installed():
    """Ensure PyQt5 is installed."""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt5'])
        print("PyQt5 has been installed successfully.")
    except Exception as e:
        print(f"Failed to install PyQt5: {e}")
        sys.exit(1)

def install_gitpython():
    """Install GitPython dynamically based on the system type."""
    try:
        print("GitPython not found. Attempting to install GitPython...")
        if sys.platform.startswith("linux"):
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-git"])
        elif sys.platform == "win32":
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gitpython"])
        else:
            print("Unsupported platform for automatic GitPython installation.")
            sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during GitPython installation: {e}")
        sys.exit(1)

def check_gitpython():
    """Check if GitPython is installed."""
    try:
        import git
        return git
    except ModuleNotFoundError:
        install_gitpython()
        return check_gitpython()  # Retry import after installation

def push_to_github(directory, commit_message):
    """Push changes to the specified GitHub repository."""
    try:
        repo = git.Repo(directory)
        repo.git.add('--all')
        repo.index.commit(commit_message)
        origin = repo.remote(name='origin')
        origin.push()
        print("Report pushed to GitHub successfully!")
    except git.exc.GitError as e:
        print(f"Git error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def calculate_average(samples):
    """Calculates and returns the truncated average of the sample readings."""
    average = np.mean(samples)
    return truncate(average, 3)

def truncate(value, decimal_places):
    """Truncates a floating-point number to a specified number of decimal places."""
    factor = 10.0 ** decimal_places
    return int(value * factor) / factor

def scan_barcode():
    """Prompts the user to scan a barcode and returns it."""
    barcode, ok = QtWidgets.QInputDialog.getText(None, "Scan Barcode", "Please scan a barcode:")
    if ok and barcode:
        return barcode
    else:
        QtWidgets.QMessageBox.warning(None, "Warning", "No barcode scanned.")
        return None

class LoadPCBDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load PCB")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel("Please load the PCB onto the fixture and click 'RUN TEST'.")
        layout.addWidget(self.label)

        self.run_test_button = QtWidgets.QPushButton("RUN TEST")
        self.run_test_button.clicked.connect(self.accept)
        layout.addWidget(self.run_test_button)

        self.setLayout(layout)

def determine_pass_fail(average, lower_limit, upper_limit):
    """Determines if the average reading passes or fails based on limits."""
    return "Pass" if lower_limit <= average <= upper_limit else "Fail"

def parse_pcb_barcode(input_string):
    """Parses the PCB barcode into its components."""
    board_name_pattern = r"^(.*?)-"
    board_rev_pattern = r"^[^-]*-(.*?)-"
    board_var_pattern = r"(?:[^-]*-){2}([^-]*)-"
    board_sn_pattern = r"(?:[^-]*-){3}([^-\s]*)"

    board_name = re.match(board_name_pattern, input_string).group(1).lower() if re.match(board_name_pattern, input_string) else "unknown"
    board_rev = re.match(board_rev_pattern, input_string).group(1) if re.match(board_rev_pattern, input_string) else "unknown"
    board_var = re.search(board_var_pattern, input_string).group(1) if re.search(board_var_pattern, input_string) else "unknown"
    board_sn = re.search(board_sn_pattern, input_string).group(1) if re.search(board_sn_pattern, input_string) else "unknown"

    return board_name, board_rev, board_var, board_sn

def report_json_to_html(data):
    """Convert JSON data to a well-formatted HTML representation."""
    html = '<html><head><style>'
    html += 'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }'
    html += 'th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }'
    html += 'tr:nth-child(even) { background-color: #f2f2f2; }'
    html += 'tr:hover { background-color: #d1e7dd; }'
    html += 'h2 { color: #333; }'
    html += 'h3 { color: #555; }'
    html += 'p { font-size: 14px; }'
    html += '.pass { font-weight: bold; color: green; }'
    html += '.fail { font-weight: bold; color: red; }'
    html += '</style></head><body>'

    html += '<h2>Test Reports</h2>'
    
    for report in data.get("test_reports", []):
        html += f'<h3>Report Timestamp: {report["timestamp"]}</h3>'
        html += f'<p>Barcode: <strong>{report["barcode"]}</strong></p>'
        html += f'<p>Overall Status: <strong class="{"pass" if report["overall_status"] == "Pass" else "fail"}">{report["overall_status"]}</strong></p>'

        html += '<h4>Test Results:</h4>'
        html += '<table>'
        html += '<tr><th>Test Number</th><th>Description</th><th>Target Value</th><th>Lower Limit</th><th>Upper Limit</th><th>Measured Value</th><th>Conclusion</th></tr>'

        for result in report.get("test_results", []):
            html += '<tr>'
            html += f'<td>{result["test_number"]}</td>'
            html += f'<td>{result["description"]}</td>'
            html += f'<td>{result["target_value"]}</td>'
            html += f'<td>{result["lower_limit"]}</td>'
            html += f'<td>{result["upper_limit"]}</td>'
            html += f'<td>{result["measured_value"]}</td>'
            html += f'<td class="{"pass" if result["conclusion"] == "Pass" else "fail"}">{result["conclusion"]}</td>'
            html += '</tr>'

        html += '</table>'

    html += '</body></html>'
    return html

def red_tag_messages_json_to_html(data):
    """Convert red tag messages JSON data to HTML format."""
    red_tag_messages = data.get("red_tag_messages", [])
    
    if not red_tag_messages:
        return "<p>No red tag messages available.</p>"

    # Start building the HTML table
    html = """
    <h3>Red Tag Messages</h3>
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr>
            <th style="padding: 10px;">Timestamp</th>
            <th style="padding: 10px;">Message</th>
        </tr>
    """

    for message in red_tag_messages:
        timestamp = message.get("timestamp", "N/A")
        red_tag_message = message.get("red_tag_message", "No message available")

        html += f"""
        <tr>
            <td style="padding: 10px;">{timestamp}</td>
            <td style="padding: 10px;">{red_tag_message}</td>
        </tr>
        """

    html += "</table>"
    return html

def process_flow_json_to_html(process_flow_data):
    """Convert process flow JSON data to HTML format."""
    process_flow_messages = process_flow_data.get("process_flow_messages", [])
    
    if not process_flow_messages:
        return "<p>No process flow information available.</p>"

    # Start building the HTML table
    html = """
    <h3>Process Flow Messages</h3>
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr>
            <th style="padding: 10px;">Timestamp</th>
            <th style="padding: 10px;">Message</th>
        </tr>
    """

    for message in process_flow_messages:
        timestamp = message.get("timestamp", "N/A")
        process_flow_message = message.get("process_flow_message", "No message available")

        html += f"""
        <tr>
            <td style="padding: 10px;">{timestamp}</td>
            <td style="padding: 10px;">{process_flow_message}</td>
        </tr>
        """

    html += "</table>"
    return html

def add_red_tag_message(message, filename):
    """Adds a red tag message to the JSON file specified by the filename."""
    
    # Load existing data
    with open(filename, 'r') as file:
        data = json.load(file)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create new red tag message
    new_message = {
        "timestamp": timestamp,
        "red_tag_message": message
    }

    # Append new message to red tag messages
    data["red_tag_messages"].append(new_message)

    # Save the updated data back to the file
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    
    # Push to github
    push_to_github(REPO_DIR, "Added red tag message")

def load_red_tag_messages(self):
    """Reloads and displays the red tag messages from the last opened file."""
    if hasattr(self, 'last_opened_file'):
        try:
            with open(self.last_opened_file, 'r') as file:
                report_content = json.load(file)
            self.red_tag_display.setHtml(red_tag_messages_json_to_html(report_content))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load red tag messages: {str(e)}")

def save_red_tag_messages(self, messages):
    """Save red tag messages to the JSON file."""
    data = {"red_tag_messages": messages}
    with open('red_tag_messages.json', 'w') as f:
        json.dump(data, f, indent=4)

def update_red_tag_message(file_path, row, new_message):
    """Update the red tag message in the JSON file."""
    # Load the existing JSON data
    with open(file_path, 'r') as file:
        report_content = json.load(file)

    # Update the red tag message at the specified row
    if row < len(report_content["red_tag_messages"]):
        report_content["red_tag_messages"][row]["red_tag_message"] = new_message

    # Save the updated JSON back to the file
    with open(file_path, 'w') as file:
        json.dump(report_content, file, indent=4)

def update_red_tag_message(old_message, new_message, report_file):
    """Update a red tag message in the report JSON file."""
    try:
        with open(report_file, 'r') as file:
            data = json.load(file)

        # Update the red tag messages list
        if "red_tag_messages" in data:
            data["red_tag_messages"] = [new_message if msg == old_message else msg for msg in data["red_tag_messages"]]

        # Save the updated JSON back to the file
        with open(report_file, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Error updating red tag message: {str(e)}")
