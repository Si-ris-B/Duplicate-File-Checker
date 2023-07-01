import sys
import pandas as pd
import os, platform, subprocess
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import *
from PySide6.QtCore import *

from backend.custom_models import PandasModel


class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_ui()
        self.assignVariables()

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
        self.allFilesView = self.window.findChild(QTableView, 'allFilesView')
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyMainWindow()
    sys.exit(app.exec())