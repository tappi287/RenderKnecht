"""
knecht_search_replace module provides search and replace functionality for the main GUI

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
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from modules.app_globals import HELPER_DIR, UI_FILE_SEARCH_DIALOG, COLUMN_NAMES, ItemColumn
from modules.knecht_log import init_logging

# Initialize logging for this module
LOGGER = init_logging(__name__)


class SearchReplace(QtWidgets.QDialog):
    """ Search and replace dialog """

    def __init__(self, ui, widget_list, current_tree: int=0):
        """ Init ui as parent """
        super(SearchReplace, self).__init__(ui)
        self.ui = ui
        self.widget_list = widget_list

        # Hide context help
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)
        loadUi(UI_FILE_SEARCH_DIALOG, self)
        logging.root.setLevel(log_level)

        self.current_tree = current_tree
        self.current_column = ItemColumn.NAME

        self.lineEdit_search.textChanged.connect(self.set_filter_txt)
        self.pushButton_search.pressed.connect(self.search_tree)
        self.pushButton_replace.pressed.connect(self.replace_single_item)
        self.pushButton_replace_all.pressed.connect(self.replace_all_items)

        self.comboBox_column.addItems(COLUMN_NAMES)
        self.comboBox_column.setCurrentIndex(ItemColumn.NAME)
        self.comboBox_column.currentIndexChanged.connect(self.set_filter_column)

        self.comboBox_tree.addItems(self.get_tree_names())
        self.comboBox_tree.setCurrentIndex(current_tree)
        self.comboBox_tree.currentIndexChanged.connect(self.set_current_tree)
        self.checkBox_filter.toggled.connect(self.filter_toggle)

    def set_filter_txt(self, txt, widget=False):
        if self.checkBox_filter.isChecked():
            if not widget:
                widget = self.widget_list[self.current_tree]
            widget.filter_txt_widget.setText(txt)

    def set_filter_column(self, idx: int, reset: bool = False):
        for widget in self.widget_list:
            if reset:
                # Restore default filter columns
                widget.filter.change_column(widget.filter_column)
            else:
                widget.filter.change_column(idx)
                self.current_column = idx

        if not reset:
            self.search_tree()

    def filter_toggle(self):
        """ Reset widget filter if search-filter-checkbox is unchecked """
        if not self.checkBox_filter.isChecked():
            for widget in self.widget_list:
                widget.filter_txt_widget.setText('')
            self.set_filter_column(0, True)

    def set_current_tree(self, idx: int):
        self.current_tree = idx

        # Lock Replace on Source tree
        if self.widget_list[self.current_tree] is self.ui.treeWidget_SrcPreset:
            self.unlock_replace(False)
        else:
            self.unlock_replace(True)

        self.search_tree()

    def unlock_replace(self, enabled):
        self.pushButton_replace.setEnabled(enabled)
        self.pushButton_replace_all.setEnabled(enabled)

    def update_text(self, lineEdit_widget):
        txt = lineEdit_widget.text()

        # Make sure we trigger an update event
        lineEdit_widget.setText('')
        lineEdit_widget.setText(txt)

        return txt

    def search_tree(self):
        widget = self.widget_list[self.current_tree]
        txt = self.update_text(self.lineEdit_search)
        widget.clearSelection()

        if txt:
            item_list = widget.findItems(
                txt, Qt.MatchContains | Qt.MatchRecursive, self.current_column)

            for item in item_list:
                item.setSelected(True)
                item.setHidden(False)

                if item.parent():
                    item.parent().setExpanded(True)

            # Update status field
            status_str = 'Suche ergab ' + str(
                len(item_list)) + ' exakte Treffer. '
            if self.checkBox_filter.isChecked():
                status_str += 'Tabellenfilter aktualisiert. '
            status_str += 'Exakte Treffer selektiert.'
            self.search_replace_status.setText(status_str)
        else:
            self.search_replace_status.setText('')

    def replace(self, single: bool = True):
        widget = self.widget_list[self.current_tree]
        search_txt = self.lineEdit_search.text()
        replace_txt = self.lineEdit_replace.text()

        item_list = widget.findItems(search_txt,
                                     Qt.MatchContains | Qt.MatchRecursive,
                                     self.current_column)

        if item_list:
            if single:
                Replace.replace(widget, [item_list[0]], search_txt, replace_txt,
                                self.current_column)
                self.search_replace_status.setText(
                    search_txt[0:15] + ' mit ' + replace_txt[0:15] + ' ersetzt.'
                )
            else:
                Replace.replace(widget, item_list, search_txt, replace_txt,
                                self.current_column)
                self.search_replace_status.setText(
                    search_txt[0:15] + ' mit ' + replace_txt[0:15] + ' für ' +
                    str(len(item_list)) + ' Objekte ersetzt.')
        else:
            self.search_replace_status.setText(
                'Keine exakten Treffer zum Ersetzen gefunden.')

    def replace_single_item(self):
        self.replace(True)

    def replace_all_items(self):
        self.replace(False)

    def closeEvent(self, QCloseEvent=False):
        """ hide window on close event and reset filtering """
        if QCloseEvent:
            QCloseEvent.ignore()

        # update status label
        self.search_replace_status.setText('')

        # Clear line_edit input fields
        for widget in self.widget_list:
            self.set_filter_txt('', widget)

        # Reset filter columns
        self.set_filter_column(0, True)
        self.hide()

    def showEvent(self, QShowEvent):
        """ Re-apply filter on dialog show """
        self.set_filter_column(self.comboBox_column.currentIndex())
        self.set_filter_txt(self.lineEdit_search.text())

    def reject(self):
        """ Called by Qt by user Escape key press """
        self.closeEvent()

    def get_tree_names(self):
        widget_names = []
        for widget in self.widget_list:
            widget_names.append(self.ui.get_tree_name(widget))
        return widget_names


class Replace:

    def replace(widget, item_list, search_txt, replace_txt, column, **kwargs):
        LOGGER.debug('Deleting selected items.')
        replace_command = Replace.ReplaceUndoCommand(
            item_list, search_txt, replace_txt, column, **kwargs)
        widget.undo_stack.push(replace_command)
        widget.undo_stack.setActive(True)

    class ReplaceUndoCommand(QtWidgets.QUndoCommand):

        def __init__(self, item_list, search_txt, replace_txt, column,
                     **kwargs):
            super(Replace.ReplaceUndoCommand, self).__init__()
            self.search_txt = search_txt
            self.replace_txt = replace_txt
            self.undo_string_list = list()
            self.column = column
            self.item_list = item_list

        def redo(self):
            self.replace(self.search_txt, self.replace_txt)
            self.setText('Text ' + self.search_txt[0:20] + ' mit ' +
                         self.replace_txt[0:20] + ' für ' +
                         str(len(self.item_list)) + ' Objekte ersetzen.')

        def undo(self):
            self.undo_replace()
            self.setText('Text ' + self.replace_txt[0:20] + ' mit ' +
                         self.search_txt[0:20] + ' für ' +
                         str(len(self.item_list)) + ' Objekte ersetzen.')

        def undo_replace(self):
            """ Restores previous item text with stored string """
            for idx, item in enumerate(self.item_list):
                item.setText(self.column, self.undo_string_list[idx])

        def replace(self, search_txt, replace_txt):
            for item in self.item_list:
                # Store item text string before manipulation
                self.undo_string_list.append(item.text(self.column))

                # Replace search_txt with replace_txt
                self.replace_item_text(item, search_txt, replace_txt)

                # Expand parent and make item visible
                if item.parent():
                    item.parent().setExpanded(True)

        def replace_item_text(self, item, search_txt, replace_txt):
            item.setSelected(True)
            item.setHidden(False)
            txt = item.text(self.column).replace(search_txt, replace_txt)

            item.setText(self.column, txt)
