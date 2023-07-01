import sys
import pandas as pd
import os, platform, subprocess
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtCore import *
import math

from backend.custom_models import PandasModel
from backend.duplicates_checker import search_duplicate_files
from backend.pandas_manager import PandasManager

class WorkerKilledException(Exception):
    pass

class WorkerSignals(QObject):
    finished = Signal(list)

class Worker(QObject):

    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self.signals = WorkerSignals()

    def process(self):
        result = search_duplicate_files(self.paths)
        self.signals.finished.emit(result)   

class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_ui()
        self.assignVariables()

        self.worker_thread = QThread()
        self.folderButton.clicked.connect(self.openFolderDialog)
        self.openButton.clicked.connect(self.execute_function)

        self.comboBox.activated.connect(self.onSelected)
        
        
    def load_ui(self):
        ui_file_name = "UI/user_interface.ui"
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        if not self.window:
            print(loader.errorString())
            sys.exit(-1)
        ui_file.close()
        self.window.show()

    def assignVariables(self):

        # QTableViews
        self.hash_grouped_view = self.window.findChild(QTableView, 'allFilesView')
        self.duplicatesView = self.window.findChild(QTableView, 'duplicatesView')
        self.groupby_duplicatesView = self.window.findChild(QTableView, 'duplicatesView_3')

        #Buttons
        self.folderButton = self.window.findChild(QToolButton, 'folderButton')
        self.openButton = self.window.findChild(QPushButton, 'openButton')

        # Qlabels
        self.total_size = self.window.findChild(QLabel, 'total_size')
        self.total_duplicate_size = self.window.findChild(QLabel, 'total_duplicate_size')
        self.total_files = self.window.findChild(QLabel, 'total_files')
        self.total_unique_files = self.window.findChild(QLabel, 'total_unique_files')
        self.total_duplicate_size_single = self.window.findChild(QLabel, 'total_duplicate_size_single')
        self.total_files_single = self.window.findChild(QLabel, 'total_files_single')
        self.total_size_single = self.window.findChild(QLabel, 'total_size_single')
        self.small_hash_count = self.window.findChild(QLabel, 'small_hash_count')

        #LineEdit
        self.folderEdit = self.window.findChild(QLineEdit, 'folderEdit')
        self.comboBox = self.window.findChild(QComboBox, 'comboBox')

    def openFolderDialog(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        folderPath = dialog.getExistingDirectory(self, "Select Folder")
        self.folderEdit.setText(folderPath)

    def execute_function(self):
        paths = self.folderEdit.text()
        if not self.worker_thread.isRunning():
            self.worker = Worker(paths)

            self.worker.signals = WorkerSignals()
            self.worker.signals.finished.connect(self.on_worker_finished)

            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(self.worker.process)

            self.worker_thread.start()

    def on_worker_finished(self, result):
        # Process the received data (list of dictionaries) here
        self.pandas_data = PandasManager(result)
        self.show_hash_grouped_table(0)

        self.worker_thread.quit()
        self.worker_thread.wait()
    
    def get_readable_size(self, size_bytes):
        """
        Convert bytes to a human-readable format.
        
        Args:
            size_bytes (int): Size in bytes.

        Returns:
            str: Human-readable size.

        Examples:
            >>> get_readable_size(2048)
            '2 KB'
        """

        # Check if size is zero
        if size_bytes == 0:
            return "0 B"

        # Define size units and their abbreviations
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

        # Calculate the appropriate suffix index based on logarithmic calculation
        exponent = int(math.floor(math.log(size_bytes, 1024)))

        # Calculate the divisor based on the suffix index
        divisor = math.pow(1024, exponent)

        # Calculate the size in the appropriate unit
        size = round(size_bytes / divisor, 2)

        # Format the result as a string with the size and unit
        result = f"{size} {suffixes[exponent]}"

        return result

    def onSelected(self, value):
        
        self.show_hash_grouped_table(value)

    def show_hash_grouped_table(self, data):
        
        # Create a DataFrame from the given data
        df = self.pandas_data.get_modified_group_dataframe(data)
        
        # Create a table model using the DataFrame
        table_model = PandasModel(df)
        
        # Set the table view's model to the created model
        self.hash_grouped_view.setModel(table_model)
    
        self.hash_grouped_view.horizontalHeader().setStretchLastSection(True)
        self.hash_grouped_view.setAlternatingRowColors(True)
        self.hash_grouped_view.setSelectionBehavior(QTableView.SelectRows)
        self.hash_grouped_view.setSortingEnabled(True)
        self.hash_grouped_view.sortByColumn(1,Qt.DescendingOrder)

        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    sys.exit(app.exec())