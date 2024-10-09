import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, StringVar, Radiobutton, PhotoImage
import re
import os
import json
import datetime
import getpass
import socket
import subprocess

# Constants
GITREPO = "https://github.com/Mesa-NManteufel/redTAG.git"
SAVE_DIRECTORY = "/home/pi/redTAG/redtags"
LABELS_FILE = "/home/pi/redTAG/redLabels.json"
RED_TAG_FILE = "/home/pi/redTAG/redTagMessages.json"
VERSION = "v010"

# Global lists to store labels and red tag messages
labels_list = []
red_tag_messages_list = []

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

def read_existing_issues(file_name):
    issues = []
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            for line in file:
                if line.startswith("Message:"):
                    issues.append(line.strip())
    return issues

def push_to_github(file_name, suppress_message=False):
    try:
        subprocess.run(['git', 'add', file_name], check=True)
        commit_message = f"Update {file_name} with new message"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        subprocess.run(['git', 'push'], check=True)
        if not suppress_message:
            messagebox.showinfo("Success", f"File '{file_name}' successfully pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred while pushing to GitHub: {e}")

def pull_from_github():
    try:
        subprocess.run(['git', 'reset', '--hard', 'HEAD'], check=True)
        subprocess.run(['git', 'fetch', 'origin'], check=True)
        subprocess.run(['git', 'merge', 'origin/main', '--allow-unrelated-histories'], check=True)
        subprocess.run(['git', 'pull', '--allow-unrelated-histories'], check=True)
        messagebox.showinfo("Update", "Successfully pulled the latest files from GitHub.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"An error occurred while pulling from GitHub: {e}")

def display_message_content(board_name, board_rev, board_var, board_sn):
    global current_board_name, current_board_rev, current_board_var, current_board_sn
    current_board_name, current_board_rev, current_board_var, current_board_sn = board_name, board_rev, board_var, board_sn
    file_name = os.path.join(SAVE_DIRECTORY, f"{board_name}-{board_rev}-{board_var}-{board_sn}.txt")
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            content = file.read()
        message_text.delete(1.0, tk.END)  # Clear the existing content
        message_text.insert(tk.END, content)  # Insert the new content
    else:
        messagebox.showwarning("Warning", f"File '{file_name}' not found.")
        message_text.delete(1.0, tk.END)

    # Update the board info section
    board_name_label.config(text=f"Board Name: {board_name}")
    board_var_label.config(text=f"Board Variant: {board_var}")
    board_rev_label.config(text=f"Board Revision: {board_rev}")
    board_sn_label.config(text=f"Board SN: {board_sn}")

def scan_barcode():
    barcode = simpledialog.askstring("Scan Barcode", "Please scan a barcode:")
    if barcode:
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
        display_message_content(board_name, board_rev, board_var, board_sn)
        # Enable the Board Information and Trends tabs
        tab_control.tab(board_info_tab, state='normal')
        tab_control.tab(trends_tab, state='normal')
        # Switch to the Board Information > Messages tab
        tab_control.select(board_info_tab)
        boards_subtab_control.select(messages_subtab)
    else:
        messagebox.showwarning("Warning", "No barcode scanned.")

def add_new_message():
    new_message = new_message_entry.get().strip()
    if new_message and current_board_name:
        file_name = os.path.join(SAVE_DIRECTORY, f"{current_board_name}-{current_board_rev}-{current_board_var}-{current_board_sn}.txt")
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = getpass.getuser()
        computer_name = socket.gethostname()
        full_message = f"Message: {current_datetime} - {user_name}@{computer_name} - {new_message}"

        try:
            with open(file_name, 'a+') as file:
                file.write(f"{full_message}\n")
            #push_to_github(file_name, suppress_message=True)  # Suppress the success message here
            display_message_content(current_board_name, current_board_rev, current_board_var, current_board_sn)
            new_message_entry.delete(0, tk.END)
            messagebox.showinfo("Success", "Message added successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while writing to the file '{file_name}': {e}")
    else:
        messagebox.showwarning("Warning", "No message entered or no barcode scanned.")

def add_new_label():
    new_label = new_label_entry.get().strip()
    if new_label:
        labels_list.append(new_label)
        save_labels_to_file()
        update_label_list()
        new_label_entry.delete(0, tk.END)
    else:
        messagebox.showwarning("Warning", "No Process Message entered.")

def add_new_red_tag_message():
    new_message = new_red_tag_message_entry.get().strip()
    if new_message:
        red_tag_messages_list.append(new_message)
        save_red_tag_messages_to_file()
        update_red_tag_messages_list()
        new_red_tag_message_entry.delete(0, tk.END)
    else:
        messagebox.showwarning("Warning", "No Red Tag message entered.")

def remove_label():
    selected_label = selected_label_var.get()
    if selected_label:
        labels_list.remove(selected_label)
        save_labels_to_file()
        update_label_list()
        messagebox.showinfo("Success", f"Process Message '{selected_label}' removed successfully.")
    else:
        messagebox.showwarning("Warning", "No Process Message selected.")

def remove_red_tag_message():
    selected_message = selected_red_tag_message_var.get()
    if selected_message:
        red_tag_messages_list.remove(selected_message)
        save_red_tag_messages_to_file()
        update_red_tag_messages_list()
        messagebox.showinfo("Success", f"Red Tag message '{selected_message}' removed successfully.")
    else:
        messagebox.showwarning("Warning", "No Red Tag message selected.")

def save_labels_to_file():
    try:
        with open(LABELS_FILE, 'w') as file:
            json.dump(labels_list, file)
    except Exception as e:
        messagebox.showerror("Error", f"Could not save labels to file: {e}")

def save_red_tag_messages_to_file():
    try:
        with open(RED_TAG_FILE, 'w') as file:
            json.dump(red_tag_messages_list, file)
    except Exception as e:
        messagebox.showerror("Error", f"Could not save Red Tag messages to file: {e}")

def load_labels_from_file():
    global labels_list
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE, 'r') as file:
                labels_list = json.load(file)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load labels from file: {e}")

def load_red_tag_messages_from_file():
    global red_tag_messages_list
    if os.path.exists(RED_TAG_FILE):
        try:
            with open(RED_TAG_FILE, 'r') as file:
                red_tag_messages_list = json.load(file)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load Red Tag messages from file: {e}")

def apply_selected_label():
    selected_label = selected_label_var.get()
    if selected_label:
        apply_label(selected_label)
    else:
        messagebox.showwarning("Warning", "No Process Message selected.")

def apply_selected_red_tag_message():
    selected_message = selected_red_tag_message_var.get()
    if selected_message:
        apply_red_tag_message(selected_message)
    else:
        messagebox.showwarning("Warning", "No Red Tag message selected.")

def apply_label(label_message):
    while True:
        barcode = simpledialog.askstring("Apply Process Message", f"Apply Process Message: '{label_message}'. Scan a barcode (or type 'x' to finish):")
        
        if barcode is None or barcode.lower() == 'x':
            break
        
        if not barcode:
            messagebox.showwarning("Warning", "No barcode scanned. Please scan a valid barcode.")
            continue
        
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
        file_name = os.path.join(SAVE_DIRECTORY, f"{board_name}-{board_rev}-{board_var}-{board_sn}.txt")
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = getpass.getuser()
        computer_name = socket.gethostname()
        issue_message = f"Message: {current_datetime} - {user_name}@{computer_name} - {label_message}"
        
        try:
            with open(file_name, 'a+') as file:
                if os.path.getsize(file_name) == 0:
                    file.write(f"Board Name: {board_name}\n")
                    file.write(f"Board Revision: {board_rev}\n")
                    file.write(f"Board Variant: {board_var}\n")
                    file.write(f"Board Serial Number: {board_sn}\n")
                file.write(f"{issue_message}\n")
            #push_to_github(file_name, suppress_message=True)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while writing to the file '{file_name}': {e}")

def apply_red_tag_message(red_tag_message):
    while True:
        barcode = simpledialog.askstring("Apply Red Tag Message", f"Apply Red Tag message: '{red_tag_message}'. Scan a barcode (or type 'x' to finish):")
        
        if barcode is None or barcode.lower() == 'x':
            break
        
        if not barcode:
            messagebox.showwarning("Warning", "No barcode scanned. Please scan a valid barcode.")
            continue
        
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
        file_name = os.path.join(SAVE_DIRECTORY, f"{board_name}-{board_rev}-{board_var}-{board_sn}.txt")
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_name = getpass.getuser()
        computer_name = socket.gethostname()
        issue_message = f"Message: {current_datetime} - {user_name}@{computer_name} - {red_tag_message}"
        
        try:
            with open(file_name, 'a+') as file:
                if os.path.getsize(file_name) == 0:
                    file.write(f"Board Name: {board_name}\n")
                    file.write(f"Board Revision: {board_rev}\n")
                    file.write(f"Board Variant: {board_var}\n")
                    file.write(f"Board Serial Number: {board_sn}\n")
                file.write(f"{issue_message}\n")
            #push_to_github(file_name, suppress_message=True)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while writing to the file '{file_name}': {e}")

def update_label_list():
    for widget in label_list_frame.winfo_children():
        widget.destroy()
    for label in labels_list:
        Radiobutton(label_list_frame, text=label, variable=selected_label_var, value=label).pack(anchor=tk.W)

def update_red_tag_messages_list():
    for widget in red_tag_message_list_frame.winfo_children():
        widget.destroy()
    for message in red_tag_messages_list:
        Radiobutton(red_tag_message_list_frame, text=message, variable=selected_red_tag_message_var, value=message).pack(anchor=tk.W)

def delete_file():
    barcode = simpledialog.askstring("Delete File", "Scan a barcode to delete the associated file:")
    if barcode:
        board_name, board_rev, board_var, board_sn = parse_pcb_barcode(barcode)
        file_name = os.path.join(SAVE_DIRECTORY, f"{board_name}-{board_rev}-{board_var}-{board_sn}.txt")
        if os.path.exists(file_name):
            os.remove(file_name)
            messagebox.showinfo("Success", f"File '{file_name}' deleted.")
            try:
                subprocess.run(['git', 'rm', file_name], check=True)
                subprocess.run(['git', 'commit', '-m', f"Delete {file_name}"], check=True)
                subprocess.run(['git', 'push'], check=True)
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"An error occurred while pushing deletion to GitHub: {e}")
        else:
            messagebox.showwarning("Warning", f"File '{file_name}' not found.")
    else:
        messagebox.showwarning("Warning", "No barcode provided.")

def setup_tabs():
    global tab_control, board_info_tab, boards_subtab_control, messages_subtab, trends_tab
    global board_name_label, board_var_label, board_rev_label, board_sn_label
    global new_label_entry, label_list_frame, selected_label_var
    global new_red_tag_message_entry, red_tag_message_list_frame, selected_red_tag_message_var

    tab_control = ttk.Notebook(root)
    
    # Controls Tab
    controls_tab = ttk.Frame(tab_control)
    tab_control.add(controls_tab, text='Controls')

    # Add the "Scan a Barcode", "Delete a File", and "Update" buttons side-by-side
    controls_button_frame = ttk.Frame(controls_tab)
    controls_button_frame.pack(pady=10, padx=10, anchor=tk.W)

    scan_button = tk.Button(controls_button_frame, text="Scan a Barcode", command=scan_barcode)
    scan_button.pack(side=tk.LEFT, padx=5)

    delete_button = tk.Button(controls_button_frame, text="Delete a File", command=delete_file)
    delete_button.pack(side=tk.LEFT, padx=5)

    update_button = tk.Button(controls_button_frame, text="Update", command=pull_from_github)
    update_button.pack(side=tk.LEFT, padx=5)

    # Sub-tabs within Controls Tab
    controls_subtab_control = ttk.Notebook(controls_tab)
    controls_subtab_control.pack(expand=1, fill="both")

    # Process Messages Subtab within Controls
    process_messages_subtab = ttk.Frame(controls_subtab_control)
    controls_subtab_control.add(process_messages_subtab, text='Process Messages')
    
    # Add New Process Message field and button
    new_label_frame = ttk.Frame(process_messages_subtab)
    new_label_frame.pack(pady=10, padx=10, fill=tk.X)

    new_label_entry = tk.Entry(new_label_frame, width=30)
    new_label_entry.pack(side=tk.LEFT, padx=5)

    add_label_button = tk.Button(new_label_frame, text="Add New Process Message", command=add_new_label)
    add_label_button.pack(side=tk.LEFT, padx=5)

    # List of labels with radio buttons
    label_list_frame = ttk.Frame(process_messages_subtab)
    label_list_frame.pack(pady=10, padx=10, fill=tk.X)

    selected_label_var = StringVar()
    
    # Apply and Remove Label buttons
    label_button_frame = ttk.Frame(process_messages_subtab)
    label_button_frame.pack(pady=10)

    apply_label_button = tk.Button(label_button_frame, text="Apply Process Message", command=apply_selected_label)
    apply_label_button.pack(side=tk.LEFT, padx=5)

    remove_label_button = tk.Button(label_button_frame, text="Remove", command=remove_label)
    remove_label_button.pack(side=tk.LEFT, padx=5)

    # Red Tag Messages Subtab within Controls
    red_tag_messages_subtab = ttk.Frame(controls_subtab_control)
    controls_subtab_control.add(red_tag_messages_subtab, text='Red Tag Messages')
    
    # Add New Red Tag Message field and button
    new_red_tag_message_frame = ttk.Frame(red_tag_messages_subtab)
    new_red_tag_message_frame.pack(pady=10, padx=10, fill=tk.X)

    new_red_tag_message_entry = tk.Entry(new_red_tag_message_frame, width=30)
    new_red_tag_message_entry.pack(side=tk.LEFT, padx=5)

    add_red_tag_message_button = tk.Button(new_red_tag_message_frame, text="Add New Red Tag Message", command=add_new_red_tag_message)
    add_red_tag_message_button.pack(side=tk.LEFT, padx=5)

    # List of Red Tag messages with radio buttons
    red_tag_message_list_frame = ttk.Frame(red_tag_messages_subtab)
    red_tag_message_list_frame.pack(pady=10, padx=10, fill=tk.X)

    selected_red_tag_message_var = StringVar()
    
    # Apply and Remove Red Tag Message buttons
    red_tag_button_frame = ttk.Frame(red_tag_messages_subtab)
    red_tag_button_frame.pack(pady=10)

    apply_red_tag_message_button = tk.Button(red_tag_button_frame, text="Apply Red Tag Message", command=apply_selected_red_tag_message)
    apply_red_tag_message_button.pack(side=tk.LEFT, padx=5)

    remove_red_tag_message_button = tk.Button(red_tag_button_frame, text="Remove", command=remove_red_tag_message)
    remove_red_tag_message_button.pack(side=tk.LEFT, padx=5)

    # Trends Tab (Placeholder)
    trends_tab = ttk.Frame(tab_control)
    tab_control.add(trends_tab, text='Trends')
    tk.Label(trends_tab, text="Trends functionality coming soon...", font=("Arial", 14)).pack(pady=20)
    tab_control.tab(trends_tab, state='disabled')  # Disable the Trends tab until a barcode is scanned
    
    # Board Information Tab with Subtabs
    board_info_tab = ttk.Frame(tab_control)
    tab_control.add(board_info_tab, text='Board Information')

    # Board Info Section at the Top
    board_info_frame = ttk.Frame(board_info_tab)
    board_info_frame.pack(fill=tk.X, padx=10, pady=10)

    board_name_label = ttk.Label(board_info_frame, text="Board Name: N/A", font=("Arial", 12))
    board_name_label.grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)

    board_var_label = ttk.Label(board_info_frame, text="Board Variant: N/A", font=("Arial", 12))
    board_var_label.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)

    board_rev_label = ttk.Label(board_info_frame, text="Board Revision: N/A", font=("Arial", 12))
    board_rev_label.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)

    board_sn_label = ttk.Label(board_info_frame, text="Board SN: N/A", font=("Arial", 12))
    board_sn_label.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)

    # Subtabs within Board Information
    boards_subtab_control = ttk.Notebook(board_info_tab)
    boards_subtab_control.pack(expand=1, fill="both")

    # Process History Subtab (renamed from Labels)
    process_history_subtab = ttk.Frame(boards_subtab_control)
    boards_subtab_control.add(process_history_subtab, text='Process History')
    tk.Label(process_history_subtab, text="Process history management will go here.").pack(pady=20)

    # Messages Subtab
    messages_subtab = ttk.Frame(boards_subtab_control)
    boards_subtab_control.add(messages_subtab, text='Messages')
    
    global message_text, new_message_entry
    message_text = tk.Text(messages_subtab, wrap=tk.WORD)
    message_text.pack(expand=True, fill='both')

    new_message_entry = tk.Entry(messages_subtab, width=50)
    new_message_entry.pack(side=tk.LEFT, padx=10, pady=10)
    
    add_message_button = tk.Button(messages_subtab, text="Add Custom Message", command=add_new_message)
    add_message_button.pack(side=tk.LEFT, padx=10, pady=10)

    # Set the default window size to 1280x720 pixels
    root.geometry("1280x720")

    # Disable the Board Information tab until a barcode is scanned
    tab_control.tab(board_info_tab, state='disabled')

    # Testing Subtab
    testing_subtab = ttk.Frame(boards_subtab_control)
    boards_subtab_control.add(testing_subtab, text='Testing')
    tk.Label(testing_subtab, text="Testing management will go here.").pack(pady=20)
    
    # About Tab
    about_tab = ttk.Frame(tab_control)
    tab_control.add(about_tab, text='About')
    tk.Label(about_tab, text="By Nolan Manteufel", font=("Arial", 12)).pack(pady=5)
    tk.Label(about_tab, text="Mesa Technologies", font=("Arial", 12)).pack(pady=5)
    tk.Label(about_tab, text="(c) 2024", font=("Arial", 12)).pack(pady=5)
    tk.Label(about_tab, text="Version 2.0", font=("Arial", 12)).pack(pady=5)

    tab_control.pack(expand=1, fill="both")

if __name__ == "__main__":
    current_board_name = current_board_rev = current_board_var = current_board_sn = None
    root = tk.Tk()
    root.title("redTAG")
    #root.iconbitmap('icon.ico')
    icon = PhotoImage(file='icon.png')
    root.iconphoto(True, icon)  # Set the window icon to the PNG image
    load_labels_from_file()  # Load labels from JSON file on startup
    load_red_tag_messages_from_file()  # Load Red Tag messages from JSON file on startup
    setup_tabs()
    update_label_list()  # Populate the label list with the loaded labels
    update_red_tag_messages_list()  # Populate the Red Tag message list with the loaded messages
    root.mainloop()
