import pandas as pd
from PySide6.QtWidgets import *
from PySide6.QtCore import *

class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    sortingAboutToStart = Signal()
    sortingFinished = Signal()

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.index)
        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return str(self._dataframe.iloc[index.row(), index.column()])
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section]+1)

        return None

    def sort(self, columnId, order=Qt.AscendingOrder):
        """sort the model column
        After sorting the data in ascending or descending order, a signal
        `layoutChanged` is emitted.
        Args:
            columnId (int): columnIndex
            order (Qt::SortOrder, optional): descending(1) or ascending(0). defaults to Qt.AscendingOrder
        """
        self.layoutAboutToBeChanged.emit()
        self.sortingAboutToStart.emit()
        column = self._dataframe.columns[columnId]
        self._dataframe.sort_values(by=column, ascending=not bool(order), inplace=True)
        self.layoutChanged.emit()
        self.sortingFinished.emit()

    def flags(self, index):
        return Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsEditable

class SearchProxyModel(QSortFilterProxyModel):

    """proxy model to search for the files in one column"""

    def setFilterRegExp(self, pattern):
        if isinstance(pattern, str):
            pattern = QtCore.QRegExp(
                pattern, Qt.CaseInsensitive,
                QtCore.QRegExp.FixedString)
        super(SearchProxyModel, self).setFilterRegExp(pattern)

    def _accept_index(self, idx):
        if idx.isValid():
            text = idx.data(Qt.DisplayRole)
            if self.filterRegExp().indexIn(text) >= 0:
                return True
            for row in range(idx.model().rowCount(idx)):
                if self._accept_index(idx.model().index(row, 0, idx)):
                    return True
        return False

    def filterAcceptsRow(self, sourceRow, sourceParent):
        idx = self.sourceModel().index(sourceRow, 0, sourceParent)
        return self._accept_index(idx)