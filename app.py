import sys
import pandas as pd
import os, platform, subprocess
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtCore import *
import math

from backend.custom_models import PandasModel, SearchProxyModel, CustomProxyModel
from backend.duplicates_checker import *
from backend.pandas_manager import PandasManager

class WorkerKilledException(Exception):
    pass

class WorkerSignals(QObject):
    finished = Signal(list)
    progress1 = Signal(int, int)
    progress2 = Signal(int, int)
    progress3 = Signal(int, int)

class Worker(QObject):

    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self.signals = WorkerSignals()

    @Slot()
    def process(self):
        files_by_size, progress, total_files = get_files_by_size(self.paths, self.update_progress_1)
        hashes_on_1k, hashes_on_1k_num = get_duplicate_files_hashes_and_count(files_by_size, self.update_progress_2)
        duplicate_files, unique_file_hashes = find_duplicate_files(hashes_on_1k, self.update_progress_3)
    
        self.signals.finished.emit(duplicate_files)
        # self.signals.finished.emit(files_by_size, total_files)

    def update_progress_1(self, progress, total):
        self.signals.progress1.emit(progress, total)

    def update_progress_2(self, progress, total):
        self.signals.progress2.emit(progress, total)

    def update_progress_3(self, progress, total):
        self.signals.progress3.emit(progress, total)

class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_ui()
        self.assignVariables()

        self.worker_thread = QThread()
        self.folderButton.clicked.connect(self.openFolderDialog)
        self.openButton.clicked.connect(self.execute_function)
        self.exportButton.clicked.connect(self.save_to_csv)

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
        self.exportButton = self.window.findChild(QPushButton, 'exportButton')

        # Qlabels
        self.total_size = self.window.findChild(QLabel, 'total_size')
        self.total_duplicate_size = self.window.findChild(QLabel, 'total_duplicate_size')
        self.total_duplicate_files = self.window.findChild(QLabel, 'total_duplicate_files')
        self.total_unique_files = self.window.findChild(QLabel, 'total_unique_files')
        self.total_duplicate_size_single = self.window.findChild(QLabel, 'total_duplicate_size_single')
        self.total_files_single = self.window.findChild(QLabel, 'total_files_single')
        self.total_size_single = self.window.findChild(QLabel, 'total_size_single')
        self.small_hash_count = self.window.findChild(QLabel, 'small_hash_count')

        #LineEdit
        self.folderEdit = self.window.findChild(QLineEdit, 'folderEdit')
        self.comboBox = self.window.findChild(QComboBox, 'comboBox')

        #ProgressBar
        self.progress_bar_1 =  self.window.findChild(QProgressBar, 'progressBar_1')
        self.progress_bar_2 =  self.window.findChild(QProgressBar, 'progressBar_2')
        self.progress_bar_3 =  self.window.findChild(QProgressBar, 'progressBar_3')

    def openFolderDialog(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        folderPath = dialog.getExistingDirectory(self, "Select Folder")
        self.folderEdit.setText(folderPath)

    def execute_function(self):
        folder_path = self.folderEdit.text()
        self.progress_bar_1.setValue(0)
        self.progress_bar_2.setValue(0)
        self.progress_bar_3.setValue(0)

        if not folder_path:
            self.show_error_message("Input is empty!")
        elif not os.path.exists(folder_path) and not os.path.isdir(folder_path):
            self.show_error_message(f"The folder '{folder_path}' does not exist.")
        else:
            if not self.worker_thread.isRunning():
                self.worker = Worker(folder_path)

                self.worker.signals = WorkerSignals()
                self.worker.signals.finished.connect(self.on_worker_finished)

                # Connect the progress signals to the worker's update_progress methods
                self.worker.signals.progress1.connect(self.update_progress_1)
                self.worker.signals.progress2.connect(self.update_progress_2)
                self.worker.signals.progress3.connect(self.update_progress_3)

                self.worker.moveToThread(self.worker_thread)
                self.worker_thread.started.connect(self.worker.process)

                self.worker_thread.start()

    def on_worker_finished(self, result):
        # Process the received data (list of dictionaries) here
        if result:
            self.pandas_data = PandasManager(result)
            self.show_hash_grouped_table(0)
            self.show_specific_data()
            self.show_all_data()
            self.setLabels(0)
        else:
            self.show_message("No Duplicate Files Found.")

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

        self.hash_grouped_view.clicked.connect(self.handle_table_click)

    def show_specific_data(self):
        
        df = self.pandas_data.get_dataframe_copy()

        model = PandasModel(df)

        self.searchModel = QSortFilterProxyModel() #No need for custom filter model
        self.searchModel.setDynamicSortFilter(True)
        self.searchModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.searchModel.setFilterKeyColumn(0) # this will search in specific column
        self.searchModel.setSourceModel(model)

        self.groupby_duplicatesView.setModel(self.searchModel)

        self.groupby_duplicatesView.horizontalHeader().setStretchLastSection(True)
        self.groupby_duplicatesView.setAlternatingRowColors(True)
        self.groupby_duplicatesView.setSelectionBehavior(QTableView.SelectRows)
        self.groupby_duplicatesView.setSortingEnabled(True)
        self.groupby_duplicatesView.sortByColumn(4,Qt.DescendingOrder)

    def show_all_data(self):
        
        df = self.pandas_data.get_dataframe_copy()

        self.duplicatesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.duplicatesView.customContextMenuRequested.connect(lambda pos: self.showContextMenu(pos, self.duplicatesView))

        model = PandasModel(df)

        self.duplicatesView.setModel(model)

        self.duplicatesView.horizontalHeader().setStretchLastSection(True)
        self.duplicatesView.setAlternatingRowColors(True)
        self.duplicatesView.setSelectionBehavior(QTableView.SelectRows)
        self.duplicatesView.setSortingEnabled(True)
        self.duplicatesView.sortByColumn(4,Qt.DescendingOrder)

    def get_multiple_selections(self, tableview):
        indexes = tableview.selectionModel().selectedIndexes()
        values = set()
        for index in indexes:
            value = index.sibling(index.row(), 1).data()
            values.add(value)

        return values

    def handle_multiple_selections(self, items):
        print(items)

    def set_unique_info(self, value, idex):

        total_size_single, total_files_single, total_duplicate_size_single = self.pandas_data.get_group_summary(value, idex)
        self.total_size_single.setText(self.get_readable_size(total_size_single))
        self.total_files_single.setText(str(total_files_single))
        self.total_duplicate_size_single.setText(self.get_readable_size(total_duplicate_size_single))

    def setLabels(self, idx):

        self.total_size.setText(self.get_readable_size(self.pandas_data.get_total_filesize()))
        self.total_duplicate_size.setText(self.get_readable_size(self.pandas_data.get_total_duplicates_size(idx)))
        self.total_duplicate_files.setText(str(self.pandas_data.get_total_files_count()-self.pandas_data.get_unique_file_count(idx)))
        self.total_unique_files.setText(str(self.pandas_data.get_unique_file_count(idx)))

    def handle_table_click(self):
        index = self.hash_grouped_view.selectionModel().currentIndex()
        value = str(index.sibling(index.row(),0).data())
        
        idx = self.comboBox.currentIndex()
        if idx == 0:    
            self.searchModel.setFilterKeyColumn(4)
        elif idx == 1:  
            self.searchModel.setFilterKeyColumn(5)
        self.searchModel.setFilterFixedString(value) 
        self.set_unique_info(value, idx)

    @Slot(int, int)
    def update_progress_1(self, progress, total):
        # Update the progress bar value
        percentage = int((progress / total) * 100)
        self.progress_bar_1.setValue(percentage)

    @Slot(int, int)
    def update_progress_2(self, progress, total):
        # Update the progress bar value
        percentage = int((progress / total) * 100)
        self.progress_bar_2.setValue(percentage)

    @Slot(int, int)
    def update_progress_3(self, progress, total):
        # Update the progress bar value
        percentage = int((progress / total) * 100)
        self.progress_bar_3.setValue(percentage)

    def showContextMenu(self, pos, tableview):
        current_item = tableview.indexAt(pos)
        values = self.get_multiple_selections(tableview)
        if current_item is not None:
            row = current_item.row()
            print(row)
            menu = QMenu(self)

            print_action = QAction("Print Files", self)
            print_action.triggered.connect(lambda: self.handle_multiple_selections(values))
            menu.addAction(print_action)

            # delete_action = QAction("Delete", self)
            # delete_action.triggered.connect(lambda: self.deleteRow(row))
            # menu.addAction(delete_action)

            # perm_delete_action = QAction("Permanent Delete", self)
            # perm_delete_action.triggered.connect(lambda: self.permanentDeleteRow(row))
            # menu.addAction(perm_delete_action)

            menu.exec(tableview.viewport().mapToGlobal(pos))

    def save_to_csv(self):
        
        path = self.folderEdit.text()
        self.pandas_data.save_dataframe_to_csv(path)
    
    def show_error_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.exec()

    def show_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Info")
        msg_box.setText(message)
        msg_box.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    sys.exit(app.exec())