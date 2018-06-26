import logging

from pathlib import Path
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore

from modules.app_globals import UI_POS_WIN, UI_POS_FILE
from modules.gui_set_path import SetDirectoryPath
from modules.pos_schnuffi_compare import GuiCompare
from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)


def sort_widget(widget, maximum_width: int=800):
    header = widget.header()
    header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)

    widget_width = max(100, widget.width())
    oversize_width = 0

    # First pass calculate complete oversized width if every item text would be visible
    for column in range(1, header.count() - 1):
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        column_width = header.sectionSize(column) + 40
        oversize_width += column_width

    # Add last and first column width
    oversize_width += header.sectionSize(header.count()) + header.sectionSize(0)

    # Calculate scale factor needed to fit columns inside visible area
    column_scale_factor = max(1, widget_width) / max(1, oversize_width)

    for column in range(1, header.count() - 1):
        width = min((header.sectionSize(column) * column_scale_factor), maximum_width)
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
        header.resizeSection(column, width)

    # Set sorting order to ascending by column 0: order
    widget.sortByColumn(0, QtCore.Qt.AscendingOrder)


class FileWindow(QtWidgets.QWidget):
    compare = QtCore.pyqtSignal()

    def __init__(self, app_class, ui):
        super(FileWindow, self).__init__()
        self.app, self.ui = app_class, ui

        LOGGER.setLevel(logging.ERROR)
        loadUi(UI_POS_FILE, self)
        LOGGER.setLevel(logging.DEBUG)

        self.old_file_dlg = SetDirectoryPath(app_class, ui,
                                             mode='file',
                                             line_edit=self.OldLineEdit,
                                             tool_button=self.OldToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )

        self.new_file_dlg = SetDirectoryPath(app_class, ui,
                                             mode='file',
                                             line_edit=self.NewLineEdit,
                                             tool_button=self.NewToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )

        self.okBtn.pressed.connect(self.validate_and_close)
        self.cancelBtn.pressed.connect(self.close)
        self.swapBtn.pressed.connect(self.swap_paths)

        self.show()

    def swap_paths(self):
        old_path = self.old_file_dlg.path
        new_path = self.new_file_dlg.path

        self.old_file_dlg.set_path(new_path)
        self.new_file_dlg.set_path(old_path)

    def validate_and_close(self):
        if not self.validate_paths():
            self.okLabel.setText('Gültigen Pfad für alte und neue POS Datei angeben.')
            return
        else:
            self.okLabel.setText('')
            self.compare.emit()
            self.close()

    def validate_paths(self):
        if not self.verify_pos_path(self.old_file_dlg.path) or not self.verify_pos_path(self.new_file_dlg.path):
            return False

        return True

    @staticmethod
    def verify_pos_path(pos_path: Path):
        if not pos_path:
            return False

        if pos_path.suffix.casefold() not in ['.pos', '.xml']:
            return False

        if not pos_path.exists():
            return False

        return True


class SchnuffiWindow(QtWidgets.QMainWindow):
    def __init__(self, app_class):
        super(SchnuffiWindow, self).__init__()
        self.app = app_class

        LOGGER.setLevel(logging.ERROR)
        loadUi(UI_POS_WIN, self)
        LOGGER.setLevel(logging.DEBUG)

        self.actionBeenden.triggered.connect(self.close)


class SchnuffiApp(QtCore.QObject):
    # File dialog window
    file_win = None

    # Comparision thread
    cmp_thread = None

    def __init__(self, app):
        super(SchnuffiApp, self).__init__()
        self.app = app
        self.ui = SchnuffiWindow(app)

        self.ui.actionOpen.triggered.connect(self.open_file_window)
        self.widget_list = [self.ui.AddedWidget, self.ui.ModifiedWidget, self.ui.RemovedWidget]

        for widget in self.widget_list:
            widget.clear()

        self.ui.show()

    def open_file_window(self):
        self.file_win = FileWindow(self.app, self.ui)
        self.file_win.compare.connect(self.compare)

    def compare(self):
        for widget in self.widget_list:
            widget.clear()

        self.cmp_thread = GuiCompare(self.file_win.old_file_dlg.path,
                                     self.file_win.new_file_dlg.path,
                                     self.widget_list)

        self.cmp_thread.add_item.connect(self.add_widget_item)
        self.cmp_thread.finished.connect(self.finished_compare)

        self.cmp_thread.start()
        self.ui.statusBar().showMessage('POS Daten werden geladen und verglichen...', 8000)

    @staticmethod
    def add_widget_item(item: QtWidgets.QTreeWidgetItem, target: QtWidgets.QTreeWidget):
        target.addTopLevelItem(item)

    def finished_compare(self):
        for widget in self.widget_list:
            sort_widget(widget)

        self.ui.statusBar().showMessage('POS Daten laden und vergleichen abgeschlossen.', 8000)
