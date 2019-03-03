"""

gui_excel_dialog for py_knecht. Provides V Plus Browser Excel import file dialog

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
import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.uic import loadUi

from modules.knecht_log import init_logging
from modules.app_strings import Msg
from modules.app_globals import UI_FILE_EXCEL_WINDOW, PR_FAM_INT, PR_FAM_EXT, Itemstyle, FAKOM_READER_PR_FAM
from modules.knecht_parse_excel import LoadVplus
from modules.tree_events import TreeKeyEvents
from modules.tree_context_menus import SelectionContextMenu
from modules.tree_filter_thread import TreeFilterThread, filter_on_timer
from modules.tree_overlay import InfoOverlay

LOGGER = init_logging(__name__)


class VplusWindow(QtWidgets.QDialog):
    """ Vplus Browser import window """
    asked_for_close = False

    def __init__(self, parent, pr_fam_set, model_list, file,
                 fakom_reader: bool=False, wizard: bool=False):
        super(VplusWindow, self).__init__()

        self.ui = parent.open_dialog.ui

        self.parent = parent
        self.fakom_reader, self.wizard = fakom_reader, wizard

        # Filename
        self.filename = os.path.basename(file)

        # List of lists of Models [Value, Name]
        self.model_list = model_list
        # List of lists of PR-Familys [Name, Description]
        self.pr_fam_set = pr_fam_set
        # Update with document PR-Familys [Name]
        self.doc_pr_fam_list = []

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)
        loadUi(UI_FILE_EXCEL_WINDOW, self)
        logging.root.setLevel(log_level)

        # Overlay instances
        self.treeWidget_PR_fam.info_overlay = InfoOverlay(self.treeWidget_PR_fam)
        self.treeWidget_Models.info_overlay = InfoOverlay(self.treeWidget_Models)

        # Lock model selection in wizard Vplus import
        if not fakom_reader and wizard:
            self.treeWidget_Models.setEnabled(False)

        # Populate tree widgets
        self.create_pr_family_tree(PR_FAM_INT + PR_FAM_EXT)
        self.create_model_tree()

        # Set options for special Fakom Reader or wizard cases
        self.setup_options()

        # Ok | Cancel btns
        self.buttonBox.accepted.connect(self.exit_accept)
        # self.buttonBox.rejected.connect(self.exit_abort)

        # Filter btns
        self.skip_filter = False
        self.btn_filter_all.stateChanged.connect(self.set_btn_filter)
        self.btn_filter_int.stateChanged.connect(self.set_btn_filter)
        self.btn_filter_ext.stateChanged.connect(self.set_btn_filter)

        # Reset initial checkbox status
        self.set_options()

        # Option Checkboxes
        self.check_short_names.stateChanged.connect(self.set_options)
        self.check_read_trim.stateChanged.connect(self.set_options)
        self.check_short_pkg_names.stateChanged.connect(self.set_options)
        self.check_read_options.stateChanged.connect(self.set_options)
        self.check_read_packages.stateChanged.connect(self.set_options)

        # Add filter txt widgets as attributes
        self.treeWidget_Models.filter_txt_widget = self.lineEdit_filter_Models
        self.treeWidget_PR_fam.filter_txt_widget = self.lineEdit_filter_PR_Fam

        # Setup filter threads and connect line Edits
        self.treeWidget_Models.filter = filter_on_timer(self.lineEdit_filter_Models,
                                                        self.treeWidget_Models,
                                                        filter_column=[0, 1])
        self.lineEdit_filter_Models.textChanged.connect(self.treeWidget_Models.filter.start_timer)

        self.treeWidget_PR_fam.filter = filter_on_timer(self.lineEdit_filter_PR_Fam,
                                                        self.treeWidget_PR_fam,
                                                        filter_column=[0, 1])
        self.lineEdit_filter_PR_Fam.textChanged.connect(self.treeWidget_PR_fam.filter.start_timer)

        # Create line_edit filtering thread
        # self.tree_filter_thread = TreeFilterThread()
        # self.tree_filter_thread.create_thread()

        # # Connect text filter class PR Family
        # self.pr_fam_txt_filter = self.txt_filtering(self.tree_filter_thread, self.treeWidget_PR_fam, column=[0, 1])
        # self.lineEdit_filter_PR_Fam.textChanged.connect(self.pr_fam_txt_filter.filter_txt)
        # # Connect text filter class Models
        # self.model_txt_filter = self.txt_filtering(self.tree_filter_thread, self.treeWidget_Models, column=[0, 1])
        # self.lineEdit_filter_Models.textChanged.connect(self.model_txt_filter.filter_txt)

        # Add Key events
        self.model_tree_keys = TreeKeyEvents(self.treeWidget_Models, self.parent, False, no_edit=True)
        self.model_tree_keys.add_event_filter()
        self.prfam_tree_keys = TreeKeyEvents(self.treeWidget_PR_fam, self.parent, False, no_edit=True)
        self.prfam_tree_keys.add_event_filter()

        # Context Menu
        ui = self.parent.open_dialog.ui
        self.pr_menu = SelectionContextMenu(self.treeWidget_PR_fam, ui)
        self.mod_menu = SelectionContextMenu(self.treeWidget_Models, ui)

        # Store filename
        LoadVplus.last_file = self.filename

    class txt_filtering:

        def __init__(self, filter_thread, tree_widget, **kwargs):
            self.filter_thread = filter_thread
            self.tree_widget = tree_widget
            self.column = kwargs['column']

        def filter_txt(self, txt):
            LOGGER.debug('Filter txt: %s', txt)
            self.filter_thread.filter_items(self.column, txt, self.tree_widget, 2)

    def create_pr_family_tree(self, filter):
        """ Fill the tree with PR-Familys from document """
        for pr_fam in self.pr_fam_set:
            item = QtWidgets.QTreeWidgetItem(self.treeWidget_PR_fam, pr_fam)
            self.doc_pr_fam_list.append(pr_fam[0])

            if pr_fam[0] in filter:
                # Uncheck non-image related PR-Familys
                item.setCheckState(0, QtCore.Qt.Unchecked)
            else:
                item.setCheckState(0, QtCore.Qt.Checked)

            self.treeWidget_PR_fam.addTopLevelItem(item)

        self.treeWidget_PR_fam.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def create_model_tree(self):
        """ Fill the tree with models from document
            Apply model filter from last file if identical filename
        """
        model_filter = LoadVplus.model_filter
        last_file = LoadVplus.last_file

        for model in self.model_list:
            item = QtWidgets.QTreeWidgetItem(self.treeWidget_Models, model)
            item.setCheckState(0, QtCore.Qt.Checked)

            if self.filename == last_file:
                if model[0] not in model_filter:
                    item.setCheckState(0, QtCore.Qt.Unchecked)

            self.treeWidget_Models.addTopLevelItem(item)

        if self.filename == last_file:
            LOGGER.debug('Applied filter from previous file: %s Model Filter: %s', self.filename, model_filter)
            self.treeWidget_Models.info_overlay.display(Msg.OVERLAY_EXCEL_MODEL + self.filename, duration=8000,
                immediate=True)

        self.treeWidget_Models.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def set_btn_filter(self):
        all = self.btn_filter_all.isChecked()
        int = self.btn_filter_int.isChecked()
        ext = self.btn_filter_ext.isChecked()

        btn_pr_fam_filter = pr_fam_all_filter = set()
        pr_fam_msg = ''

        if int:
            pr_fam_msg = 'Interior scope'
            # Filter Interior scope Status: 09/01/2017 (I/VX-13)
            btn_pr_fam_filter.update(PR_FAM_INT)

        if ext:
            pr_fam_msg += ' and Exterior scope'
            # Filter Exterior scope Status: 09/01/2017 (I/VX-13)
            btn_pr_fam_filter.update(PR_FAM_EXT)

        if all:
            pr_fam_msg = 'All items'

            pr_fam_items = self.treeWidget_PR_fam.findItems('*', QtCore.Qt.MatchWildcard)
            for pr_fam_item in pr_fam_items:
                pr_fam_all_filter.add(pr_fam_item.text(0))

            btn_pr_fam_filter.update(pr_fam_all_filter)

        LOGGER.debug('%s added to PR-Family Filter.', pr_fam_msg)
        self.set_pr_fam_filter(btn_pr_fam_filter)

    def set_model_filter(self):
        model_items = self.treeWidget_Models.findItems('*', QtCore.Qt.MatchWildcard)
        model_filter = set()

        for item in model_items:
            if item.checkState(0) == QtCore.Qt.Checked:
                model_filter.add(item.text(0))

        LoadVplus.model_filter = model_filter

    def set_pr_fam_filter(self, filter_set=None):
        if filter_set is None:
            filter_set = {}

        pr_fam_items = self.treeWidget_PR_fam.findItems('*', QtCore.Qt.MatchWildcard)
        pr_fam_filter = set()

        if filter_set:
            # Update from provided whitelist filter
            for item in pr_fam_items:
                if item.text(0) in filter_set:
                    item.setCheckState(0, QtCore.Qt.Checked)
                    pr_fam_filter.add(item.text(0))
                else:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
        else:
            # Read filter from tree widget
            for item in pr_fam_items:
                if item.checkState(0) == QtCore.Qt.Checked:
                    pr_fam_filter.add(item.text(0))

        # Filter Packages with PR-Family filter
        if self.check_pr_fam_filter_packages.isChecked():
            LoadVplus.package_pr_fam_filter = True
        else:
            LoadVplus.package_pr_fam_filter = True

        LoadVplus.pr_fam_filter = pr_fam_filter

    def set_options(self):
        # Short model names
        if self.check_short_names.isChecked():
            LoadVplus.shorten_names = True
        else:
            LoadVplus.shorten_names = False
        # Read Trimlines
        if self.check_read_trim.isChecked():
            LoadVplus.read_trim = True
        else:
            LoadVplus.read_trim = False
        # Short package names
        if self.check_short_pkg_names.isChecked():
            LoadVplus.shorten_pkg_name = True
        else:
            LoadVplus.shorten_pkg_name = False
        # Create optional PR-Codes presets
        if self.check_read_options.isChecked():
            LoadVplus.read_options = True
        else:
            LoadVplus.read_options = False
        # Create packages presets
        if self.check_read_packages.isChecked():
            LoadVplus.read_packages = True
        else:
            LoadVplus.read_packages = False

    def setup_options(self):
        if self.fakom_reader:
            # Pre-select options for FaKom Reader
            for option_box in [self.check_short_names, self.check_short_pkg_names, self.check_read_packages,
                               self.check_read_options, self.check_read_trim, self.btn_filter_all,
                               self.btn_filter_int, self.btn_filter_ext, self.check_pr_fam_filter_packages]:
                option_box.setDisabled(True)
                option_box.setChecked(False)

            self.check_read_options.setChecked(True)
            self.check_read_trim.setChecked(True)

            self.set_pr_fam_filter(FAKOM_READER_PR_FAM)
            self.treeWidget_PR_fam.setDisabled(True)
        elif not self.fakom_reader and self.wizard:
            # Pre-select options for Preset Wizard Vplus Import
            for option_box in [self.check_short_names, self.check_short_pkg_names,
                               self.check_read_packages, self.check_read_trim]:
                option_box.setDisabled(True)
                option_box.setChecked(False)

            self.check_read_packages.setChecked(True)
            self.check_read_trim.setChecked(True)

            # init PR family button filter
            self.set_btn_filter()
        else:
            # init PR family button filter
            self.set_btn_filter()

        # Transfer set options to excel reader class
        self.set_options()

    def close_threads(self):
        self.treeWidget_Models.filter.end_thread()
        self.treeWidget_PR_fam.filter.end_thread()

        self.model_tree_keys.rem_event_filter()
        self.prfam_tree_keys.rem_event_filter()

    def exit_accept(self):
        LOGGER.debug('V Plus Browser settings accepted. Converting.')

        # End filter thread
        self.close_threads()
        self.set_pr_fam_filter()
        self.set_model_filter()
        self.accept()

    def ask_close(self):
        if not self.asked_for_close:
            if self.ui.question_box(
                    title_txt=Msg.EXC_CLOSE_TITLE,
                    message=Msg.EXC_CLOSE_MSG,
                    parent=self):
                return True

        self.asked_for_close = True
        return False

    def reject(self):
        if self.ask_close():
            return False

        self.close()

    def closeEvent(self, QCloseEvent):
        if not self.asked_for_close:
            if not self.reject():
                QCloseEvent.ignore()
                return

        LOGGER.info('V Plus Browser window close event triggerd. Aborting excel conversion')
        # End filter thread
        self.close_threads()

        QCloseEvent.accept()
