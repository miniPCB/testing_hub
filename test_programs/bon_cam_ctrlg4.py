import sys
import subprocess
import os
import time
import json
from datetime import datetime
from ctypes import *
from dwfconstants import *
import re
from PyQt5 import QtWidgets, QtCore

SCRIPT_AUTHOR = "Nolan Manteufel"
SCRIPT_REVISION_DATE = "2024-10-03"
TARGET_BOARD = "cam_ctrlg4"
TARGET_REVISIONS = "0002"

def ensure_numpy():
    """Ensure numpy is installed."""
    try:
        import numpy as np
        #print("Numpy is already installed.")
    except ImportError:
        print("Numpy is not installed. Installing now...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
            import numpy as np  # Try importing again
            print("Numpy installed successfully.")
        except Exception as e:
            print(f"Failed to install numpy: {e}")
            sys.exit(1)

# Ensure numpy is installed
ensure_numpy()

# Function to install GitPython dynamically based on the system type
def install_gitpython():
    try:
        print("GitPython not found. Attempting to install GitPython...")
        if sys.platform.startswith("linux"):  # Check if the system is Linux-based
            try:
                subprocess.check_call(["sudo", "apt-get", "update"])
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-git"])
            except subprocess.CalledProcessError as e:
                print(f"Failed to install GitPython using apt: {e}")
                sys.exit(1)
        elif sys.platform == "win32":  # Windows-based system
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "gitpython"])
            except subprocess.CalledProcessError as e:
                print(f"Failed to install GitPython using pip: {e}")
                sys.exit(1)
        else:
            print("Unsupported platform for automatic GitPython installation.")
            sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during GitPython installation: {e}")
        sys.exit(1)

# Check if gitpython is installed, and install it if not
try:
    import git
except ModuleNotFoundError:
    install_gitpython()
    import git  # Retry import after installation

# Load the appropriate DWF library based on the platform
if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

# Set paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
REPORTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'reports'))

# Declare ctypes variables
hdwf = c_int()
sts = c_byte()
rgdSamples1 = (c_double * 4000)()
rgdSamples2 = (c_double * 4000)()

# GPIO labels dictionary with extended details
gpio_details = {
    0: {"label": "SCL", "lower_limit": 0.25, "upper_limit": 0.4, "target_value": 0.35, "test_number": 1},
    1: {"label": "CSI_5V", "lower_limit": 0.4, "upper_limit": 0.6, "target_value": 0.5, "test_number": 2},
    2: {"label": "CSI_3V3", "lower_limit": 0.3, "upper_limit": 0.5, "target_value": 0.4, "test_number": 3},
    5: {"label": "SDA", "lower_limit": 0.5, "upper_limit": 0.7, "target_value": 0.6, "test_number": 4}
}

def setup_device():
    """Opens the device and configures it."""
    dwf.FDwfParamSet(DwfParamOnClose, c_int(0))  # 0 = run, 1 = stop, 2 = shutdown
    print("Connecting to Analog Discovery 3.")
    dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

    if hdwf.value == hdwfNone.value:
        szerr = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szerr)
        print("Failed to open device: " + str(szerr.value))
        print("Connect and power on Analog Discovery 3.")
        sys.exit(1)

    # Proceed with device configuration if opened successfully
    configure_device()

def configure_device():
    """Configures the device settings."""
    # Set up power supplies
    dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(0), c_int(0), c_double(1))  # Enable positive supply
    dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(0), c_int(1), c_double(5.0))  # Set voltage to 5 V
    dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(0), c_double(1))  # Enable negative supply
    dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(1), c_double(0.0))  # Set voltage to 0 V
    dwf.FDwfAnalogIOEnableSet(hdwf, c_int(1))  # Master enable
    dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))  # Device auto-configure

def set_gpio(pin, value):
    """Sets the specified GPIO pin to the given value."""
    if value:
        dwf.FDwfDigitalIOOutputSet(hdwf, c_int(1 << pin))
    else:
        dwf.FDwfDigitalIOOutputSet(hdwf, c_int(0))
    dwf.FDwfDigitalIOConfigure(hdwf)

def read_scope(scope_channel, samples, buffer_size):
    """Reads data from the specified scope channel with a timeout."""
    dwf.FDwfAnalogInReset(hdwf)
    dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(scope_channel - 1), c_int(1))
    dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(scope_channel - 1), c_double(5.0))
    dwf.FDwfAnalogInChannelOffsetSet(hdwf, c_int(scope_channel - 1), c_double(0.0))
    dwf.FDwfAnalogInFrequencySet(hdwf, c_double(1e5))
    dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(buffer_size))

    dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))

    timeout = 10  # Timeout in seconds
    start_time = time.time()
    while True:
        dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
        if sts.value == DwfStateDone.value:
            break
        if time.time() - start_time > timeout:
            print("Timeout waiting for acquisition to complete")
            return None
        time.sleep(0.1)

    if scope_channel == 1:
        dwf.FDwfAnalogInStatusData(hdwf, 0, samples, buffer_size)
    elif scope_channel == 2:
        dwf.FDwfAnalogInStatusData(hdwf, 1, samples, buffer_size)

    print("Acquisition done")
    return samples

def truncate(value, decimal_places):
    """Truncates a floating-point number to a specified number of decimal places."""
    factor = 10.0 ** decimal_places
    return int(value * factor) / factor

def calculate_average(samples):
    """Calculates and returns the truncated average of the sample readings."""
    average = sum(samples) / len(samples)
    return truncate(average, 3)

def determine_pass_fail(average, lower_limit, upper_limit):
    """Determines if the average reading passes or fails based on limits."""
    return "Pass" if lower_limit <= average <= upper_limit else "Fail"

def set_led(state):
    """Sets the LED states based on the current state."""
    # GPIO assignments:
    # 7: PUSHBUTTON
    # 15: READY
    # 6: IN PROGRESS
    # 3: FAIL
    # 4: PASS

    # Clear all LEDs first
    set_gpio(15, 0)  # READY
    set_gpio(6, 0)  # IN PROGRESS
    set_gpio(3, 0)  # FAIL
    set_gpio(4, 0)  # PASS

    if state == "READY":
        set_gpio(15, 1)
    elif state == "IN PROGRESS":
        set_gpio(6, 1)
    elif state == "PASS":
        set_gpio(4, 1)
    elif state == "FAIL":
        set_gpio(3, 1)

def push_to_github(directory, commit_message):
    """Push changes to the specified GitHub repository."""
    try:
        repo = git.Repo(directory)
        repo.git.add('--all')
        repo.index.commit(commit_message)
        origin = repo.remote(name='origin')
        origin.push()
        print("Changes pushed to GitHub successfully!")
    except git.exc.GitError as e:
        print(f"Git error occurred: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def parse_pcb_barcode(input_string):
    board_name_pattern = r"^(.*?)-"
    board_rev_pattern = r"^[^-]*-(.*?)-"
    board_var_pattern = r"(?:[^-]*-){2}([^-]*)-"
    board_sn_pattern = r"(?:[^-]*-){3}([^-\s]*)"

    board_name = re.match(board_name_pattern, input_string).group(1).lower() if re.match(board_name_pattern, input_string) else "unknown"
    board_rev = re.match(board_rev_pattern, input_string).group(1) if re.match(board_rev_pattern, input_string) else "unknown"
    board_var = re.search(board_var_pattern, input_string).group(1) if re.search(board_var_pattern, input_string) else "unknown"
    board_sn = re.search(board_sn_pattern, input_string).group(1) if re.search(board_sn_pattern, input_string) else "unknown"

    return board_name, board_rev, board_var, board_sn

def scan_barcode():
    #app = QtWidgets.QApplication(sys.argv)  # Create a QApplication if not already created
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

class MessageDialog(QtWidgets.QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Message")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel(message)
        layout.addWidget(self.label)

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

def main():

    app = QtWidgets.QApplication(sys.argv)

    print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("MESA Technologies")
    print(f"Test Program: {TARGET_BOARD}")
    print(f"Revision: {SCRIPT_REVISION_DATE}")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    barcode = scan_barcode()

    if barcode is None:
        print("No barcode scanned. Exiting.")
        return  # Exit the main function if no barcode is scanned

    board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
    print(f"BOARD: {board_name}\nREV: {board_rev}\nVARIANT: {board_var}\nSN: {board_sn}")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    
    # Check if the board name matches the target board
    if board_name != TARGET_BOARD:
        print(f"Board name '{board_name}' does not match the target '{TARGET_BOARD}'. Exiting.")
        return  # Exit if the board does not match

    # Show dialog to load PCB
    dialog = LoadPCBDialog()
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        print("User cancelled the test. Exiting.")
        return

    # Proceed with a brief delay after confirmation
    print("Starting tests in 2 seconds...")  # You can change this delay as needed
    QtCore.QThread.sleep(2)

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    setup_device()

    # List of GPIO pins to test
    gpio_pins = [0, 1, 2, 5]

    # List to store the results for each test
    test_results = []

    # Global status tracker
    overall_status = "Pass"

    # Wait for RUN button press
    set_led("READY")
    while True:
        # Simulate reading the pushbutton (GPIO 0)
        # Replace this with actual GPIO read logic
        pushbutton_pressed = input("Press ENTER to start testing...") == ""  # Simulated button press
        if pushbutton_pressed:
            break

    set_led("IN PROGRESS")

    # Iterate through each GPIO pin
    for pin in gpio_pins:
        details = gpio_details.get(pin, {})
        label = details.get("label", "Unknown")
        lower_limit = details.get("lower_limit", 0)
        upper_limit = details.get("upper_limit", 1)
        target_value = details.get("target_value", 0.5)
        test_number = details.get("test_number", 0)

        set_gpio(pin, 1)

        # Wait for 1 second to allow the signal to stabilize
        time.sleep(1)

        if pin in []:
            read_scope(1, rgdSamples1, 4000)
            avg_scope = calculate_average(rgdSamples1)
        else:
            read_scope(2, rgdSamples2, 4000)
            avg_scope = calculate_average(rgdSamples2)

        status = determine_pass_fail(avg_scope, lower_limit, upper_limit)
        print(f"Test# {test_number}:\t{label}: \t{avg_scope:.3f} V \t{status}")

        # Append the result to the test results list
        test_results.append({
            "test_number": test_number,
            "description": label,
            "target_value": target_value,
            "lower_limit": lower_limit,
            "upper_limit": upper_limit,
            "measured_value": avg_scope,
            "conclusion": status
        })
            
        if status == "Fail":
            overall_status = "Fail"  # Set overall status to Fail if any test fails

        set_gpio(pin, 0)

    # Determine final status
    if all(result['conclusion'] == "Pass" for result in test_results):
        set_led("PASS")
    else:
        set_led("FAIL")

           # Create a timestamp for the test report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Prepare the new report entry with the timestamp and overall status
        new_report_entry = {
            "timestamp": timestamp,
            "barcode": barcode,
            "overall_status": overall_status,  # Add overall status here
            "test_results": test_results
        }
        
        # Save all test results to a JSON file
        filename = os.path.join(REPORTS_DIR, f"{board_name}-{board_rev}-{board_var}-{board_sn}.json")

        # Check if the file exists
        if os.path.exists(filename):
            # Load existing data
            with open(filename, "r") as f:
                existing_data = json.load(f)
        else:
            # Initialize existing data if the file does not exist
            existing_data = {"test_reports": []}

        # Append new test results
        existing_data["test_reports"].append(new_report_entry)

        # Save updated results back to the file
        with open(filename, "w") as f:
            json.dump(existing_data, f, indent=4)

        # Push report to GitHub
        commit_message = f"{board_name}-{board_rev}-{board_var}-{board_sn}--{overall_status}"
        push_to_github(REPO_DIR, commit_message)

        dwf.FDwfDeviceCloseAll()
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(f"END OF TEST: {overall_status}")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    
    print("Test script exited.")

if __name__ == "__main__":
    main()
