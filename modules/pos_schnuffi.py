import logging
from queue import Queue

from pathlib import Path
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QBrush, QColor

from modules.app_globals import UI_POS_WIN, UI_POS_FILE
from modules.app_strings import Msg
from modules.gui_set_path import SetDirectoryPath
from modules.pos_schnuffi_compare import GuiCompare
from modules.knecht_settings import knechtSettings
from modules.knecht_log import init_logging
from modules.tree_filter_thread import filter_on_timer
from modules.tree_events import TreeKeyEvents
from modules.tree_overlay import InfoOverlay, Overlay
from modules.tree_methods import iterate_item_childs
from modules.pos_schnuffi_export import ExportActionList

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

    def __init__(self, knecht_app, pos_ui):
        super(FileWindow, self).__init__()
        self.knecht_app, self.pos_ui = knecht_app, pos_ui

        LOGGER.setLevel(logging.ERROR)
        loadUi(UI_POS_FILE, self)
        LOGGER.setLevel(logging.DEBUG)

        self.old_file_dlg = SetDirectoryPath(knecht_app, pos_ui,
                                             mode='file',
                                             line_edit=self.OldLineEdit,
                                             tool_button=self.OldToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )
        self.old_file_dlg.path_changed.connect(self.save_old_path_setting)

        self.new_file_dlg = SetDirectoryPath(knecht_app, pos_ui,
                                             mode='file',
                                             line_edit=self.NewLineEdit,
                                             tool_button=self.NewToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )
        self.new_file_dlg.path_changed.connect(self.save_new_path_setting)

        self.okBtn.pressed.connect(self.validate_and_close)
        self.cancelBtn.pressed.connect(self.close)
        self.swapBtn.pressed.connect(self.swap_paths)

        self.load_settings()

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

    def load_settings(self):
        old_path = Path(knechtSettings.app['pos_old_path'])
        new_path = Path(knechtSettings.app['pos_new_path'])

        if self.verify_pos_path(old_path):
            self.old_file_dlg.set_path(old_path)

        if self.verify_pos_path(new_path):
            self.new_file_dlg.set_path(new_path)

    @staticmethod
    def save_old_path_setting(old_path: Path):
        knechtSettings.app['pos_old_path'] = old_path.as_posix()

    @staticmethod
    def save_new_path_setting(new_path: Path):
        knechtSettings.app['pos_new_path'] = new_path.as_posix()

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
    def __init__(self, app_class, pos_app):
        super(SchnuffiWindow, self).__init__()
        self.knecht_app = app_class
        self.pos_app = pos_app

        LOGGER.setLevel(logging.ERROR)
        loadUi(UI_POS_WIN, self)
        LOGGER.setLevel(logging.DEBUG)

    @staticmethod
    def get_tree_name(widget):
        return widget.objectName()

    def widget_with_focus(self):
        """ Return the current QTreeWidget in focus """
        widget_in_focus = self.focusWidget()
        LOGGER.debug('Widget in Focus: %s', widget_in_focus.objectName())

        if widget_in_focus in self.pos_app.widget_list:
            return widget_in_focus

    def closeEvent(self, close_event):
        self.pos_app.end_app()
        close_event.accept()


class SchnuffiApp(QtCore.QObject):
    # File dialog window
    file_win = None

    # Comparision thread
    cmp_thread = None
    cmp_queue = Queue(-1)

    # Error signal
    err_sig = QtCore.pyqtSignal(str)
    export_sig = QtCore.pyqtSignal()

    intro_timer = QtCore.QTimer()
    intro_timer.setSingleShot(True)
    intro_timer.setInterval(500)

    expand_worker = QtCore.QTimer()
    expand_worker.setInterval(25)
    chunk_size = 5
    expand_item_ls = list()

    def __init__(self, app):
        super(SchnuffiApp, self).__init__()
        self.app = app
        self.pos_ui = SchnuffiWindow(app, self)
        self.export = ExportActionList(self, self.pos_ui)

        self.widget_list = [self.pos_ui.AddedWidget, self.pos_ui.ModifiedWidget, self.pos_ui.RemovedWidget,
                            self.pos_ui.switchesWidget, self.pos_ui.looksWidget]
        self.setup_widgets()

        self.pos_ui.show()

    def setup_widgets(self):
        # Buttons
        self.pos_ui.filterLabel.mouseDoubleClickEvent = self.sort_all_headers
        self.pos_ui.expandBtn.pressed.connect(self.expand_all_items)
        self.expand_worker.timeout.connect(self.expand_work_chunk)

        # Menu
        self.pos_ui.actionOpen.triggered.connect(self.open_file_window)
        self.pos_ui.actionBeenden.triggered.connect(self.pos_ui.close)
        self.pos_ui.actionExport.triggered.connect(self.export.export_selection)
        self.pos_ui.actionExportPos.triggered.connect(self.export.export_updated_pos_xml)

        for widget in self.widget_list:
            widget.clear()

            # Setup Filtering
            widget.filter_txt_widget = self.pos_ui.lineEditFilter
            widget.filter_column = [0, 1, 2]
            widget.filter = filter_on_timer(self.pos_ui.lineEditFilter,
                                            widget, filter_column=widget.filter_column, filter_children=False)

            self.pos_ui.lineEditFilter.textChanged.connect(widget.filter.start_timer)

            # Widget overlay
            widget.info_overlay = InfoOverlay(widget)
            widget.overlay = Overlay(widget)

            # Add key events
            widget.keys = TreeKeyEvents(widget, self.app.ui, self.app,
                                        wizard=True, no_edit=True)
            widget.keys.add_event_filter()

        self.intro_timer.timeout.connect(self.show_intro_msg)
        self.intro_timer.start()

        # Exporter signals
        self.err_sig.connect(self.error_msg)
        self.export_sig.connect(self.export_success)

    def end_app(self):
        if self.cmp_thread:
            self.cmp_thread.quit()
            self.cmp_thread.wait(5000)

        for widget in self.widget_list:
            try:
                widget.filter.end_thread()
            except Exception as e:
                LOGGER.debug('Could not end widget filter thread! %s', e)

    def show_intro_msg(self):
        self.pos_ui.ModifiedWidget.info_overlay.display_confirm(Msg.POS_INTRO, ('[X]', None))

    def export_success(self):
        self.pos_ui.ModifiedWidget.overlay.save_anim()

    def error_msg(self, error_str):
        self.pos_ui.widgetTabs.setCurrentIndex(0)
        self.pos_ui.ModifiedWidget.info_overlay.display_exit()
        self.pos_ui.ModifiedWidget.info_overlay.display_confirm(error_str, ('[X]', None))

    def sort_all_headers(self, event = None):
        for widget in self.widget_list:
            sort_widget(widget)

    def expand_all_items(self):
        for widget in self.widget_list:
            self.expand_item_ls += widget.findItems('*', QtCore.Qt.MatchWildcard)

        self.expand_worker.start()

    def expand_work_chunk(self):
        count = self.chunk_size

        while count > 0:
            if self.expand_item_ls:
                item = self.expand_item_ls.pop(0)
                item.setExpanded(True)
            else:
                self.expand_worker.stop()
                break

            count -= 1

    def open_file_window(self):
        self.file_win = FileWindow(self.app, self.pos_ui)
        self.file_win.compare.connect(self.compare)

    def compare(self):
        for widget in self.widget_list:
            widget.clear()

        self.pos_ui.widgetTabs.setCurrentIndex(0)
        self.pos_ui.ModifiedWidget.overlay.load_start()

        self.cmp_thread = GuiCompare(self.file_win.old_file_dlg.path,
                                     self.file_win.new_file_dlg.path,
                                     self.widget_list,
                                     self.cmp_queue)

        self.cmp_thread.add_item.connect(self.add_widget_item)
        self.cmp_thread.finished.connect(self.finished_compare)

        self.cmp_thread.start()
        self.pos_ui.statusBar().showMessage('POS Daten werden geladen und verglichen...', 8000)

    def add_widget_item(self):
        item, target_widget = self.cmp_queue.get()
        self.color_items(item)
        target_widget.addTopLevelItem(item)

    @staticmethod
    def color_items(parent_item):
        iter_children = iterate_item_childs(parent_item.treeWidget())

        for item in iter_children.iterate_childs(parent_item):
            value = item.text(1)
            old_value = item.text(2)

            # Skip actor's without values
            if not value and not old_value:
                continue

            if not value:
                # No new value, actor removed
                for c in range(0, 4):
                    item.setForeground(c, QBrush(QColor(190, 90, 90)))
            elif not old_value and value:
                # New actor added
                for c in range(0, 4):
                    item.setForeground(c, QBrush(QColor(90, 140, 90)))

    def finished_compare(self):
        self.sort_all_headers()

        self.pos_ui.widgetTabs.setCurrentIndex(0)
        self.pos_ui.ModifiedWidget.overlay.load_finished()

        self.pos_ui.statusBar().showMessage('POS Daten laden und vergleichen abgeschlossen.', 8000)
