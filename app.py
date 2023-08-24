import sys
import pandas as pd
import os, platform, subprocess
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtCore import *
import math
import shutil
import logging
from backend.custom_models import PandasModel, SearchProxyModel, CustomProxyModel
from backend.duplicates_checker import *
from backend.pandas_manager import PandasManager
import pyperclip


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

class ConfirmationDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Confirmation")
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))

        layout = QVBoxLayout(self)

        message_label = QLabel("Delete (no way to undelete!)")
        layout.addWidget(message_label)

        button_layout = QHBoxLayout()

        yes_button = QPushButton("Yes")
        yes_button.clicked.connect(self.accept)
        button_layout.addWidget(yes_button)

        no_button = QPushButton("No")
        no_button.clicked.connect(self.reject)
        button_layout.addWidget(no_button)

        layout.addLayout(button_layout)

        
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
        self.comboBox2.activated.connect(self.change_duplicate_view)

        self.moveButton.clicked.connect(self.move_files)
        
        
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
        self.df = None

        #Buttons
        self.folderButton = self.window.findChild(QToolButton, 'folderButton')
        self.openButton = self.window.findChild(QPushButton, 'openButton')
        self.exportButton = self.window.findChild(QPushButton, 'exportButton')
        self.moveButton = self.window.findChild(QPushButton, 'cleanFilesButton')

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
        self.comboBox2 = self.window.findChild(QComboBox, 'comboBox_2')

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
        self.folder_path = self.folderEdit.text()
        self.progress_bar_1.setValue(0)
        self.progress_bar_2.setValue(0)
        self.progress_bar_3.setValue(0)

        if not self.folder_path:
            self.show_error_message("Input is empty!")
        elif not os.path.exists(self.folder_path) and not os.path.isdir(self.folder_path):
            self.show_error_message(f"The folder '{self.folder_path}' does not exist.")
        else:
            if not self.worker_thread.isRunning():
                self.worker = Worker(self.folder_path)

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

        self.groupby_duplicatesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groupby_duplicatesView.customContextMenuRequested.connect(lambda pos: self.showContextMenu(pos, self.groupby_duplicatesView))

        self.groupby_duplicatesView.horizontalHeader().setStretchLastSection(True)
        self.groupby_duplicatesView.setAlternatingRowColors(True)
        self.groupby_duplicatesView.setSelectionBehavior(QTableView.SelectRows)
        self.groupby_duplicatesView.setSortingEnabled(True)
        self.groupby_duplicatesView.sortByColumn(4,Qt.DescendingOrder)

    def change_duplicate_view(self):
        
        idx = self.comboBox2.currentIndex()
        if idx == 0:    
            self.df = self.pandas_data.get_dataframe_copy()
        elif idx == 1:  
            self.df = self.pandas_data.get_excess_duplicates(True)
        elif idx == 2:
            self.df = self.pandas_data.get_excess_duplicates(False)
        self.show_all_data()

    def show_all_data(self):
        
        if not isinstance(self.df, pd.DataFrame):
            self.df = self.pandas_data.get_dataframe_copy()

        model = PandasModel(self.df)

        self.duplicatesView.setModel(model)

        self.duplicatesView.horizontalHeader().setStretchLastSection(True)
        self.duplicatesView.setAlternatingRowColors(True)
        self.duplicatesView.setSelectionBehavior(QTableView.SelectRows)
        self.duplicatesView.setSortingEnabled(True)
        self.duplicatesView.sortByColumn(4,Qt.DescendingOrder)

        self.duplicatesView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.duplicatesView.customContextMenuRequested.connect(lambda pos: self.showContextMenu(pos, self.duplicatesView))

    def get_multiple_selections(self, tableview):
        indexes = tableview.selectionModel().selectedIndexes()
        values = set()
        for index in indexes:
            value = index.sibling(index.row(), 1).data()
            values.add(value)
        return values

    def delete_multiple_selections(self, tableview):
        values = self.get_multiple_selections(tableview)
        for myfile in values:
            # If file exists, delete it.
            if os.path.isfile(myfile):
                os.remove(myfile)
                self.show_message(f"The file '{myfile}' has been permanently deleted.")
            else:
                # If it fails, inform the user.
                self.show_error_message(f"The file '{myfile}' does not exist.")

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
        
        if current_item is not None:
            row = current_item.row()
            print(row)
            menu = QMenu(self)

            # print_action = QAction("Print Files", self)
            # print_action.triggered.connect(lambda: self.handle_multiple_selections(tableview))
            # menu.addAction(print_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.show_confirmation_dialog(tableview))
            menu.addAction(delete_action)

            open_action = QAction("Open file manager here", self)
            open_action.triggered.connect(lambda: self.open_file_location(tableview))
            menu.addAction(open_action)

            copy_name_action = QAction("Copy full path", self)
            copy_name_action.triggered.connect(lambda: self.copy_file_location(tableview))
            menu.addAction(copy_name_action)

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

    def show_confirmation_dialog(self, tableview):
        dialog = ConfirmationDialog()
        if dialog.exec() == QDialog.Accepted:
            self.delete_multiple_selections(tableview)

    def move_files(self):
        
        idx = self.comboBox2.currentIndex()
        if idx == 0:    
            files_list = []
        elif idx == 1:  
            df = self.pandas_data.get_excess_duplicates(True)
            files_list = df['FilePath'].tolist()
        elif idx == 2:
            df = self.pandas_data.get_excess_duplicates(False)
            files_list = df['FilePath'].tolist()

        # Create the destination subdirectory
        dest_dir_path = os.path.join(self.folder_path, "duplicates_bin")
        if not os.path.exists(dest_dir_path):
            os.makedirs(dest_dir_path)

        # Create a logger and set the log level to INFO
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Create a file handler to write the log messages to a log file
        log_file_path = os.path.join(dest_dir_path, f'dup_move_files.log')
        file_handler = logging.FileHandler(log_file_path)

        # Create a formatter for the log messages
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        logger.addHandler(file_handler)

        # Move each matching file to the destination subdirectory
        for filepath in files_list:
            try:
                # Check if the file name already exists in the destination directory
                file_name = os.path.basename(filepath)
                dest_file_path = os.path.join(dest_dir_path, file_name)
                file_name_without_ext = os.path.splitext(file_name)[0]
                ext = os.path.splitext(file_name)[1]
                suffix = 1

                while os.path.exists(dest_file_path):
                    # Rename the file with a suffix if it already exists in the destination directory
                    new_file_name = f"{file_name_without_ext}_{suffix}{ext}"
                    dest_file_path = os.path.join(dest_dir_path, new_file_name)
                    suffix += 1

                # Move the file to the destination subdirectory
                shutil.move(filepath, dest_file_path)

                # Log that the file has been moved successfully
                logger.info(f"Moved '{filepath}' to '{dest_file_path}'")

            except Exception as e:
                # Log any errors that occur while moving the file
                logger.error(f"Error moving '{filepath}' to '{dest_dir_path}': {e}")
        self.show_message(f"All Duplicate Files moved to {dest_dir_path}")

    def open_file_location(self, tableview):
        values = self.get_multiple_selections(tableview)
        for file_path in values:
            file_directory = os.path.dirname(file_path)            
            if os.path.exists(file_directory):
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', '/select,', file_path], shell=True)
                elif os.name == 'posix':  # Linux or Mac
                    subprocess.run(['xdg-open', file_directory])
            else:
                print("File location does not exist.")

    def copy_file_location(self, tableview):
        values = self.get_multiple_selections(tableview)
        pyperclip.copy(values.pop())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    sys.exit(app.exec())