import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTextEdit, QTabWidget, QSizePolicy, QLabel, QTableWidget, QTableWidgetItem
)
from PyQt5.QtGui import QFont

class TestHub(QWidget):
    def __init__(self):
        super().__init__()

        # Set window title
        self.setWindowTitle("Testing Hub")

        # Resize the window to 1280x850
        self.resize(1280, 850)

        # Create tab widget
        self.tabs = QTabWidget()

        # Tab 1: Testers and printout pane
        self.tab1 = QWidget()
        self.init_tab1()

        # Tab 2: Test Results view
        self.tab2 = QWidget()
        self.init_tab2()

        # Tab 3: Testing Statistics
        self.tab3 = QWidget()
        self.init_tab3()

        # Add tabs to tab widget
        self.tabs.addTab(self.tab1, "Testing")
        self.tabs.addTab(self.tab2, "Build Yields")
        self.tabs.addTab(self.tab3, "Board Data")

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def init_tab1(self):
        """Initialize the first tab (Testers and their printouts)."""
        main_layout = QHBoxLayout()

        # Left layout for tester list and "Update All" button
        left_layout = QVBoxLayout()
        self.update_button = QPushButton("Update All")
        self.tester_list = QListWidget()
        self.tester_list.addItems(["Tester 1", "Tester 2", "Tester 3", "Tester 4", "Tester 5"])
        self.tester_list.setFixedWidth(200)  # Make the tester pane narrower

        left_layout.addWidget(self.update_button)
        left_layout.addWidget(self.tester_list)

        # Right layout for tester printouts and "Clear Display" button
        right_layout = QVBoxLayout()
        self.clear_button = QPushButton("Clear Display")
        self.tester_display = QTextEdit()
        self.tester_display.setReadOnly(True)

        right_layout.addWidget(self.clear_button)
        right_layout.addWidget(self.tester_display)

        # Add left and right layouts to the main layout
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.tab1.setLayout(main_layout)

    def init_tab2(self):
        """Initialize the second tab (Test Results view with yield and failure mode counters)."""
        layout = QVBoxLayout()

        # Top section with selectable panes (rows)
        top_layout = QHBoxLayout()

        # Board Name pane
        self.board_name_list = QListWidget()
        self.board_name_list.addItems(["Board A", "Board B", "Board C", "Board D"])
        self.board_name_list.setFixedHeight(100)
        self.board_name_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.board_name_list.itemSelectionChanged.connect(self.filter_board_revision)

        # Board Revision pane
        self.board_revision_list = QListWidget()
        self.board_revision_list.setFixedHeight(100)
        self.board_revision_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Board Variant pane
        self.board_variant_list = QListWidget()
        self.board_variant_list.setFixedHeight(100)
        self.board_variant_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # SN Range pane
        self.sn_range_list = QListWidget()
        self.sn_range_list.setFixedHeight(100)
        self.sn_range_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Add the panes to the top layout and make them stretch
        top_layout.addWidget(self.board_name_list)
        top_layout.addWidget(self.board_revision_list)
        top_layout.addWidget(self.board_variant_list)
        top_layout.addWidget(self.sn_range_list)

        # Middle section: Yield Information, Failure Mode Occurrences, and Test Results (side by side)
        middle_layout = QHBoxLayout()

        # Yield Information pane
        self.yield_info = QListWidget()
        self.yield_info.setFixedHeight(200)
        self.yield_info.itemSelectionChanged.connect(self.update_failure_modes_and_test_results)
        middle_layout.addWidget(self.yield_info)

        # Failure Mode Occurrence pane
        self.failure_mode_occurrences = QListWidget()
        self.failure_mode_occurrences.setFixedHeight(200)
        middle_layout.addWidget(self.failure_mode_occurrences)

        # Test Results pane (moved to the end)
        self.test_results_list = QListWidget()
        self.test_results_list.setFixedHeight(200)
        self.test_results_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.test_results_list.itemSelectionChanged.connect(self.display_test_report)
        middle_layout.addWidget(self.test_results_list)

        # Align the panes to the top by using QVBoxLayout and adding the middle section
        top_container_layout = QVBoxLayout()
        top_container_layout.addLayout(top_layout)  # Panes at the top
        top_container_layout.addLayout(middle_layout)  # Middle section

        # Printout pane for displaying the selected test report
        self.test_report_display = QTextEdit()
        self.test_report_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set a larger font for the test report pane
        report_font = QFont()
        report_font.setPointSize(14)  # Set the desired font size (14 in this case)
        self.test_report_display.setFont(report_font)

        # Stretching the height of the test report pane by slightly more than 2x
        layout.addLayout(top_container_layout)
        layout.addWidget(self.test_report_display, stretch=2)

        self.tab2.setLayout(layout)

    def filter_board_revision(self):
        """Filter the Board Revision list based on the selected Board Name."""
        selected_board = self.board_name_list.currentItem().text()

        # Clear the revision, variant, and SN Range panes when a new Board is selected
        self.board_revision_list.clear()
        self.board_variant_list.clear()
        self.sn_range_list.clear()
        self.test_results_list.clear()
        self.yield_info.clear()
        self.failure_mode_occurrences.clear()
        self.test_report_display.clear()

        # Add filtered revisions based on the selected board
        if selected_board == "Board A":
            self.board_revision_list.addItems(["Rev 1", "Rev 2", "Rev 3"])
        elif selected_board == "Board B":
            self.board_revision_list.addItems(["Rev A", "Rev B"])
        elif selected_board == "Board C":
            self.board_revision_list.addItems(["Rev X", "Rev Y"])
        else:
            self.board_revision_list.addItems(["Rev 10", "Rev 20", "Rev 30"])

        # Connect subsequent filtering for the next panes
        self.board_revision_list.itemSelectionChanged.connect(self.filter_board_variant)

    def filter_board_variant(self):
        """Filter the Board Variant list based on the selected Board Revision."""
        selected_revision = self.board_revision_list.currentItem().text()

        # Clear variant and SN Range panes when a new revision is selected
        self.board_variant_list.clear()
        self.sn_range_list.clear()
        self.test_results_list.clear()
        self.yield_info.clear()
        self.failure_mode_occurrences.clear()
        self.test_report_display.clear()

        # Add filtered variants based on the selected revision
        if selected_revision in ["Rev 1", "Rev A", "Rev X"]:
            self.board_variant_list.addItems(["Variant 1", "Variant 2"])
        else:
            self.board_variant_list.addItems(["Variant A", "Variant B"])

        # Connect subsequent filtering for SN Range
        self.board_variant_list.itemSelectionChanged.connect(self.filter_sn_range)

    def filter_sn_range(self):
        """Filter the SN Range list based on the selected Board Variant."""
        selected_variant = self.board_variant_list.currentItem().text()

        # Clear SN Range and test result panes when a new variant is selected
        self.sn_range_list.clear()
        self.test_results_list.clear()
        self.yield_info.clear()
        self.failure_mode_occurrences.clear()
        self.test_report_display.clear()

        # Add filtered SN ranges based on the selected variant
        if selected_variant == "Variant 1":
            self.sn_range_list.addItems(["100-200", "201-300"])
        else:
            self.sn_range_list.addItems(["400-500", "501-600"])

        # Connect final filtering to show test results
        self.sn_range_list.itemSelectionChanged.connect(self.filter_test_results)

    def filter_test_results(self):
        """Display the test results based on the selected SN Range."""
        selected_sn_range = self.sn_range_list.currentItem().text()

        # Clear the test results pane
        self.test_results_list.clear()
        self.test_report_display.clear()
        self.yield_info.clear()
        self.failure_mode_occurrences.clear()

        # Display simulated test result files based on the SN range
        if selected_sn_range == "100-200":
            self.test_results_list.addItems(["TestResult_001.txt", "TestResult_002.txt"])
        else:
            self.test_results_list.addItems(["TestResult_101.txt", "TestResult_102.txt"])

        # Update yield information and failure mode occurrences dynamically
        self.update_yield_and_failure_modes(selected_sn_range)

    def update_yield_and_failure_modes(self, sn_range):
        """Update the yield and failure mode occurrence information based on the SN range."""
        # Simulated dynamic update logic based on SN range
        self.yield_info.clear()
        self.yield_info.addItems([
            f"Total Units Tested for SN Range {sn_range}: 1000",
            "Total Passed: 950",
            "Total Failed: 50",
            "Yield: 95%"
        ])

        self.failure_mode_occurrences.clear()
        self.failure_mode_occurrences.addItems([
            "Open Circuit: 20",
            "Short Circuit: 15",
            "Solder Issue: 8",
            "Component Failure: 5",
            "Other: 2"
        ])

    def update_failure_modes_and_test_results(self):
        """Update the Failure Mode Occurrences and Test Results based on the selected yield information."""
        selected_yield = self.yield_info.currentItem().text()

        # Example filtering logic based on the selected yield info
        if "SN Range 100-200" in selected_yield:
            self.failure_mode_occurrences.clear()
            self.failure_mode_occurrences.addItems([
                "Open Circuit: 10",
                "Short Circuit: 5",
                "Solder Issue: 3",
                "Component Failure: 2",
                "Other: 1"
            ])

            self.test_results_list.clear()
            self.test_results_list.addItems(["TestResult_001.txt", "TestResult_002.txt"])
        else:
            self.failure_mode_occurrences.clear()
            self.failure_mode_occurrences.addItems([
                "Open Circuit: 20",
                "Short Circuit: 15",
                "Solder Issue: 8",
                "Component Failure: 5",
                "Other: 2"
            ])

            self.test_results_list.clear()
            self.test_results_list.addItems(["TestResult_101.txt", "TestResult_102.txt"])

    def init_tab3(self):
        """Initialize the third tab (Testing Statistics for yield and Pareto analysis)."""
        layout = QVBoxLayout()

        # Yield Information
        self.yield_info_statistics = QTextEdit()
        self.yield_info_statistics.setReadOnly(True)
        self.yield_info_statistics.setFont(QFont('Arial', 12))
        self.yield_info_statistics.setText("Yield Information:\n\nTotal Units Tested: 1000\nTotal Passed: 950\nTotal Failed: 50\nYield: 95%")

        # Pareto Analysis Table (using QTableWidget)
        self.pareto_table = QTableWidget()
        self.pareto_table.setRowCount(5)  # Example failure modes
        self.pareto_table.setColumnCount(2)
        self.pareto_table.setHorizontalHeaderLabels(['Failure Mode', 'Occurrences'])

        # Populate the Pareto table with example data
        failure_modes = [('Open Circuit', 20), ('Short Circuit', 15), ('Solder Issue', 8), ('Component Failure', 5), ('Other', 2)]
        for i, (failure, occurrences) in enumerate(failure_modes):
            self.pareto_table.setItem(i, 0, QTableWidgetItem(failure))
            self.pareto_table.setItem(i, 1, QTableWidgetItem(str(occurrences)))

        # Add components to the layout
        layout.addWidget(QLabel("Yield Information"))
        layout.addWidget(self.yield_info_statistics)
        layout.addWidget(QLabel("Pareto Analysis of Failure Modes"))
        layout.addWidget(self.pareto_table)

        self.tab3.setLayout(layout)

    def display_test_report(self):
        """Display the contents of the selected test result file."""
        selected_file = self.test_results_list.currentItem().text()

        # Clear the report display
        self.test_report_display.clear()

        # Simulate loading and displaying the content of the test report
        # In a real application, you would read the file content here
        report_content = f"Contents of {selected_file}:\nThis is a simulated test report."
        self.test_report_display.setText(report_content)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestHub()
    window.show()
    sys.exit(app.exec_())
