import re
import json
import sys
import subprocess
import requests
import os
import time
from datetime import datetime
from ctypes import *
import git
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

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

def check_for_updates(directory):
    """Checks for updates in the specified Git repository directory and pulls if updates are available."""
    try:
        # Change to the script directory
        os.chdir(directory)

        # Run git fetch to check for updates
        fetch_result = subprocess.run(['git', 'fetch'], capture_output=True, text=True)

        if fetch_result.returncode != 0:
            print("Error fetching updates:", fetch_result.stderr)
            return

        # Check the status to see if we are behind
        status_result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)

        if 'Your branch is behind' in status_result.stdout:
            print("Updates available. Pulling the latest changes...")
            pull_result = subprocess.run(['git', 'pull'], capture_output=True, text=True)

            if pull_result.returncode == 0:
                print("Successfully pulled updates:", pull_result.stdout)
            else:
                print("Error pulling updates:", pull_result.stderr)
        else:
            print("No updates available.")

    except Exception as e:
        print(f"An error occurred: {e}")

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

def report_json_to_md(data):
    """Convert JSON data to a well-formatted Markdown representation."""
    md = "# Test Reports\n"
    
    for report in data.get("test_reports", []):
        md += f"## Report Timestamp: {report['timestamp']}\n"
        md += f"**Barcode**: `{report['barcode']}`\n"
        md += f"**Overall Status**: {'*Pass*' if report['overall_status'] == 'Pass' else '*Fail*'}\n"

        md += "\n### Test Results:\n"
        md += "| Test Number | Description | Target Value | Lower Limit | Upper Limit | Measured Value | Conclusion |\n"
        md += "|-------------|-------------|--------------|-------------|-------------|----------------|------------|\n"

        for result in report.get("test_results", []):
            md += f"| {result['test_number']} | {result['description']} | {result['target_value']} | {result['lower_limit']} | {result['upper_limit']} | {result['measured_value']} | {'Pass' if result['conclusion'] == 'Pass' else 'Fail'} |\n"

        md += "\n"

    return md

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
            <th style="padding: 10px;">Source</th>
            <th style="padding: 10px;">Message</th>
        </tr>
    """

    for message in red_tag_messages:
        timestamp = message.get("timestamp", "N/A")
        source = message.get("source", "Unknown")  # Default to "Unknown" if no source is provided
        red_tag_message = message.get("red_tag_message", "No message available")

        html += f"""
        <tr>
            <td style="padding: 10px;">{timestamp}</td>
            <td style="padding: 10px;">{source}</td>
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
        process_flow_message = message.get("message", "No message available")

        html += f"""
        <tr>
            <td style="padding: 10px;">{timestamp}</td>
            <td style="padding: 10px;">{process_flow_message}</td>
        </tr>
        """

    html += "</table>"
    return html

def messages_to_html(messages):
    """Convert messages to HTML format."""
    if not messages:
        return "<p>No messages available.</p>"

    # Start building the HTML table
    html = """
    <h3>Messages</h3>
    <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr>
            <th style="padding: 10px;">Timestamp</th>
            <th style="padding: 10px;">Source</th>
            <th style="padding: 10px;">Message</th>
        </tr>
    """

    for message in messages:
        timestamp = message.get("timestamp", "N/A")
        source = message.get("source", "Unknown")
        red_tag_message = message.get("red_tag_message", "No message available")

        html += f"""
        <tr>
            <td style="padding: 10px;">{timestamp}</td>
            <td style="padding: 10px;">{source}</td>
            <td style="padding: 10px;">{red_tag_message}</td>
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

    # Create new red tag message with source
    new_message = {
        "timestamp": timestamp,
        "source": message.get("source"),  # Add source from the message dictionary
        "red_tag_message": message.get("red_tag_message")  # Add message from the dictionary
    }

    # Append new message to red tag messages
    data["red_tag_messages"].append(new_message)

    # Save the updated data back to the file
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
    
    # Push to GitHub
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

def send_report_via_slack(report_md, slack_webhook_url):
    """Send the formatted report to Slack using mrkdwn."""
    # Create the payload with mrkdwn enabled
    slack_data = {
        "text": report_md,
        "mrkdwn": True  # Explicitly tell Slack to use mrkdwn formatting
    }

    # Send the request to Slack
    response = requests.post(slack_webhook_url, json=slack_data)

    # Check the response
    if response.status_code != 200:
        raise Exception(f"Failed to send message to Slack: {response.status_code}, {response.text}")
    else:
        print("Report successfully sent to Slack!")
