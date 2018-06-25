"""
gui_main_window module provides main GUI window

Copyright (C) 2017 Stefan Tapper, All rights reserved.

    This file is part of RenderKnecht Strink Kerker.

    RenderKnecht Strink Kerker is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RenderKnecht Strink Kerker is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with RenderKnecht Strink Kerker.  If not, see <http://www.gnu.org/licenses/>.

"""
import logging

from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.uic import loadUi

from modules.app_strings import InfoMessage, Msg
from modules.app_globals import UI_FILE_PRESET_EDITOR, Itemstyle, ItemColumn
from modules.gui_widgets import LedCornerWidget
from modules.knecht_settings import knechtSettings
from modules.knecht_deltagen import SendToDeltaGen
from modules.tree_events import TreeKeyEvents, CopyVariantsKeyEvents
from modules.tree_context_menus import TreeContextMenu
from modules.tree_filter_thread import filter_on_timer
from modules.tree_methods import tree_setup_header_format, iterate_item_childs, CopySelectedToDest
from modules.tree_methods import SortTree, create_unique_item_name
from modules.tree_overlay import InfoOverlay, Overlay
from modules.tree_references import FindReferenceItems
from modules.tree_search_replace import SearchReplace
from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """ SchnuffiWindow of the RenderKnecht Preset Editor """

    def __init__(self, app_class):
        super(MainWindow, self).__init__()

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(40)

        # Load Ui file
        loadUi(UI_FILE_PRESET_EDITOR, self)

        # Add LED Overlay to tabWidget
        # Spams the log with Debug messages, so initialize in this block
        self.led_ovr = LedCornerWidget(parent=self.tabWidget)

        logging.root.setLevel(log_level)

        # Clipboard
        self.clipboard = []
        self.clipboard_src = None

        # Undo Redo Menu
        self.actionUndo.setText('Rückgängig\tCtrl+Z')
        self.actionRedo.setText('Wiederherstellen\tCtrl+Y')
        self.actionUndo.setEnabled(False)
        self.actionRedo.setEnabled(False)

        # Add version to Window title
        self.ver = InfoMessage.ver
        self.title = self.windowTitle()
        self.set_window_title()

        self.load_settings()

        # Unsaved changes status
        self.unsaved_changes_present = False
        self.unsaved_changes_auto_save = True

        # App class so we can override the window exit method [x] with the exit method of the app class
        self.app_class = app_class

        self.tree_widget_list = [self.treeWidget_SrcPreset, self.treeWidget_DestPreset, self.treeWidget_Variants,
            self.treeWidget_render]

        # Set tree column width to content resize and sort ascending by order
        tree_setup_header_format(self.tree_widget_list)

        # Icons
        self.icon = dict()
        for icon_name, icon_path in Itemstyle.ICON_PATH.items():
            self.icon[icon_name] = QIcon(icon_path)

        # Tree iterator instance
        self.iter_tree = iterate_item_childs(self.treeWidget_DestPreset)

        # Make reference modules instance available to the working classes
        self.find_reference_items = FindReferenceItems(self, self.iter_tree)
        self.add_selected_top_level_items = CopySelectedToDest(self)

        # Worker class instances
        self.sort_tree_widget = SortTree(self, self.treeWidget_SrcPreset)
        self.context_menus = []
        self.widget_pairs = [(self.treeWidget_SrcPreset, self.pushButton_Src_sort, self.lineEdit_Src_filter, [1, 2]),
                        (self.treeWidget_DestPreset, self.pushButton_Dest_sort, self.lineEdit_Dest_filter, [1, 2]),
                        (self.treeWidget_Variants, self.pushButton_Var_sort, self.lineEdit_Var_filter, 1),
                        (self.treeWidget_render, self.pushButton_Ren_sort, self.lineEdit_Ren_filter, 1)]

        # Init widget pairs
        for w_tuple in self.widget_pairs:
            tree_widget, sort_button, line_edit, filter_col = w_tuple

            # Sorting and reference highlight
            tree_widget.sortBtn = sort_button

            # Store Id's to missing items as strings
            # so we avoid to assign them to new items
            tree_widget.missing_ids = set()

            # Store topLevelItem names
            tree_widget.unique_names = set()

            # Default Filter column
            tree_widget.filter_column = filter_col

            # Store LineEdit text filter widget as tree attribute
            tree_widget.filter_txt_widget = line_edit

            # Init Filter
            tree_widget.filter = filter_on_timer(line_edit, tree_widget, filter_column=filter_col)
            line_edit.textChanged.connect(tree_widget.filter.start_timer)

            # Default preset visibility
            tree_widget.toggle_preset_vis = False

            # Info Overlay
            tree_widget.info_overlay = InfoOverlay(tree_widget)
            # Animated overlay
            tree_widget.overlay = Overlay(tree_widget)
            # Update overlay position on event
            tree_widget.overlayPos.connect(tree_widget.overlay.update_position)

            # Context menu
            tree_widget.context = TreeContextMenu(tree_widget, self)

            # Bind keys
            tree_widget.keys = TreeKeyEvents(tree_widget, self, self.app_class)
            tree_widget.keys.add_event_filter()

            # Report conflict shortcut
            tree_widget.report_conflict = self.report_conflict

        # Forbid editing in SrcWidget
        self.treeWidget_SrcPreset.keys.no_edit = True

        # Search Replace dialog
        self.search_replace = SearchReplace(self, [self.treeWidget_SrcPreset,
                                                   self.treeWidget_DestPreset,
                                                   self.treeWidget_Variants],
                                            current_tree=1)

        # Copy variants key events
        variant_keys_tree = CopyVariantsKeyEvents(self.treeWidget_Variants, self)
        variants_keys_txt = CopyVariantsKeyEvents(self.plainTextEdit_addVariant_Setname, self)
        variant_keys_add = CopyVariantsKeyEvents(self.plainTextEdit_addVariant_Variant, self)

        # Internal drag_drop worker
        self.treeWidget_DestPreset.internal_drag_drop.setup_ui(self)
        self.treeWidget_Variants.internal_drag_drop.setup_ui(self)
        self.treeWidget_render.internal_drag_drop.setup_ui(self, True)

        # hide variants type column
        self.treeWidget_Variants.header().hideSection(ItemColumn.TYPE)

    def enable_load_actions(self, enabled: bool = True):
        self.menuImport.setEnabled(enabled)
        self.actionOpen.setEnabled(enabled)

    def load_settings(self):
        # Load Viewer Size
        for idx in range(0, self.comboBox_ViewerSize.count()):
            self.comboBox_ViewerSize.setCurrentIndex(idx)
            if knechtSettings.dg['viewer_size'] == self.comboBox_ViewerSize.currentText():
                # Set current viewer size
                SendToDeltaGen.viewer_size = self.comboBox_ViewerSize.currentText()
                LOGGER.debug('Setting viewer combo box to index: %s', idx)
                break

    def add_file_string(self, message, file_path):
        if file_path:
            message = message + '<br><i>' + str(file_path) + '</i>'
        return message

    def generic_error_msg(self, msg: str=''):
        __msg = Msg.GENERIC_ERROR + msg
        self.warning_box(Msg.GENERIC_ERROR_TITLE, __msg)

    def warning_box(self, title_txt: str = Msg.ERROR_BOX_TITLE, message: str = '', file_path=False, parent=None):
        message = self.add_file_string(message, file_path)

        if not parent:
            parent = self

        QtWidgets.QMessageBox.warning(parent, title_txt, message)

    def question_box(self, title_txt: str = Msg.ERROR_BOX_TITLE, message: str = '', file_path=False, parent=None):
        """ Pop-Up Warning Box ask to continue or break, returns True on abort """
        message = self.add_file_string(message, file_path)

        if not parent:
            parent = self

        msg_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question,
                                        title_txt, message, parent=parent)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok |
                                   QtWidgets.QMessageBox.Abort)

        msg_box.button(QtWidgets.QMessageBox.Ok).setText(Msg.QUESTION_OK)
        msg_box.button(QtWidgets.QMessageBox.Abort).setText(Msg.QUESTION_ABORT)

        answer = msg_box.exec()

        if answer == QtWidgets.QMessageBox.Abort:
            # User selected abort
            return True

        # User selected -Ok-, continue
        return False

    def info_box(self, title_txt: str = Msg.INFO_TITLE, message: str = '', file_path=False, parent=None):
        message = self.add_file_string(message, file_path)

        if not parent:
            parent = self

        QtWidgets.QMessageBox.information(parent, title_txt, message)

    # noinspection PyArgumentList
    def unsaved_changes(self, file_path=False, title_txt: str = Msg.UNSAVED_CHANGES_TITLE,
                        message: str = Msg.UNSAVED_CHANGES):
        """ Creates Question Box if unchanged changes in Dest widget detected """
        if not self.unsaved_changes_present:
            return QtWidgets.QMessageBox.No

        message = self.add_file_string(message, file_path)

        msg_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, title_txt, message, parent=self)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)

        msg_box.button(QtWidgets.QMessageBox.Yes).setText(Msg.UNSAVED_CHANGES_YES)
        msg_box.button(QtWidgets.QMessageBox.Yes).setIcon(self.icon[Itemstyle.MAIN['save']])
        msg_box.button(QtWidgets.QMessageBox.No).setText(Msg.UNSAVED_CHANGES_NO)
        msg_box.button(QtWidgets.QMessageBox.No).setIcon(self.icon[Itemstyle.MAIN['sad']])
        msg_box.button(QtWidgets.QMessageBox.Cancel).setText(Msg.UNSAVED_CHANGES_CANCEL)

        answer = msg_box.exec_()
        LOGGER.debug('Asked for unsaved changes, user answered: %s', answer)
        return answer

    def set_window_title(self, file_info: str = ''):
        self.setWindowTitle(self.title + ' - ' + self.ver)

        if file_info != '':
            if self.unsaved_changes_present:
                file_info = '*' + file_info + '*'
                self.setWindowTitle('*' + self.title + ' ' + self.ver + '*')
            self.label_Dest_File.setText(file_info)
        else:
            self.label_Dest_File.setText(Msg.NO_FILE_INFO)

    def report_conflict(self, item=False, new_id=False):
        """ Report ID Conflict """
        if item:
            err_msg = Msg.OVERLAY_MISSING_REF[0] + item.text(ItemColumn.NAME) + Msg.OVERLAY_MISSING_REF[1]
            err_msg += item.text(ItemColumn.ID)

            if not new_id:
                # Copy not created
                err_msg += Msg.OVERLAY_MISSING_REF[2]
            else:
                # New Id created instead
                err_msg += Msg.OVERLAY_MISSING_REF[3] + new_id
        else:
            err_msg = Msg.OVERLAY_MISSING_REF[4]

        self.treeWidget_DestPreset.info_overlay.display_confirm(err_msg, ('[X]', None), immediate=True)

    def report_name_clash(self, name, id, new_id):
        self.treeWidget_DestPreset.info_overlay.display(
            Msg.OVERLAY_NAME_CLASH.format(name=name, id=id, new_id=new_id), 3500)

    def get_tree_name(self, widget):
        """ Return user readable tree names """
        if widget is self.treeWidget_SrcPreset:
            return 'Preset Vorgaben'
        if widget is self.treeWidget_DestPreset:
            return 'Benutzer Vorgaben'
        if widget is self.treeWidget_Variants:
            return 'Varianten Liste'
        if widget is self.treeWidget_render:
            return 'Render Liste'
        return ''

    def tree_with_focus(self):
        """ Return the current QTreeWidget in focus """
        widget_in_focus = self.focusWidget()

        if widget_in_focus in self.tree_widget_list:
            return widget_in_focus

        return False

    class send_to_dg:
        """ Pseudeo clas.s if send_to_dg was never called from GUI """

        def thread_running(self=None):
            """
                This will return true from overwritten
                clas.s if rendering / sending to deltagen is in progress.
            """
            return False

    def check_item_name(self, item, item_name, __new_item_name: str=None):
        """ If item name already in unique names, return new name """
        unique_names = item.treeWidget().unique_names

        if not unique_names:
            return

        if item_name in unique_names:
            __new_item_name = create_unique_item_name(item_name, unique_names)

        if __new_item_name:
            item.setText(ItemColumn.NAME, __new_item_name)

        self.sort_tree_widget.sort_current_level(item, item.treeWidget())

        return __new_item_name

    def end_threads(self):
        for w_tuple in self.widget_pairs:
            tree_widget, sort_button, line_edit, filter_col = w_tuple
            tree_widget.filter.end_thread()

    def closeEvent(self, QCloseEvent):
        LOGGER.debug('Preset Editor SchnuffiWindow close event triggered. Closing SchnuffiWindow.')
        QCloseEvent.ignore()
        self.app_class.exit_preset_editor()
