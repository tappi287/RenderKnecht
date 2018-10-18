"""
py_knecht QUB 9000 preset wizard, Source Page

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
import random
from pathlib import Path

from PyQt5 import QtWidgets, QtCore

from modules.knecht_log import init_logging
from modules.app_globals import WIZARD_PAGE_SOURCE, PACKAGE_FILTER
from modules.app_strings import QobMsg
from modules.gui_widgets import FakomWindow, load_ui_file
from modules.knecht_threads import ExcelConversionThread
from modules.tree_load_save import OpenPresetFile
from modules.tree_methods import tree_setup_header_format
from modules.tree_overlay import InfoOverlay, Overlay

LOGGER = init_logging(__name__)


class SourceWizardPage(QtWidgets.QWizardPage):
    """
        --- Introduction Wizard Page ---
        User needs to select source files to read.
    """
    qob_quotes = QobMsg.QOB_QUOTES
    quote_timer = QtCore.QTimer()
    quote_timer.setSingleShot(True)

    def __init__(self, parent):
        super(SourceWizardPage, self).__init__(parent)
        self.parent = parent
        self.app, self.ui = parent.app, parent.ui
        self.open_file_dialog = None

        self.load_ui()

        # Prepare Xml read / write in parent Wizard
        self.parent.setup_xml_read_write(self.treeWidget_Src)
        self.src_tree_setup_header()

        self.fakomLutscherBtn.pressed.connect(self.read_fakom)
        self.vplusBtn.pressed.connect(self.read_vplus)

        # Prepare import windows
        self.fakom_window = None
        self.vplus_reader = None

        self.reloadBtn.setEnabled(False)

        self.check_for_last_session_file()

    def check_for_last_session_file(self):
        if self.parent.session_data_mgr.session_available():
            self.reloadBtn.setEnabled(True)

    def load_session(self, file: Path=None):
        """ Previous session found and loaded """
        self.reloadBtn.setEnabled(False)

        if not file:
            __display_file = self.parent.last_session_file.name
        else:
            __display_file = file.name

        if self.parent.session_data_mgr.load_session(file):
            # Session load sucessful
            self.fakomCheckbox.setChecked(True)
            self.vplusCheckbox.setChecked(True)
            self.parent.source_changed.emit()

            self.treeWidget_Src.info_overlay.display(
                QobMsg.loaded_message.format(__display_file), 3000, immediate=True)

            __filter_string = self.load_pkg_filter_string()
            self.plainTextEditFilter.setPlainText(__filter_string)

            self.completeChanged.emit()
        else:
            # Session load unsucessful
            self.treeWidget_Src.info_overlay.display_confirm(
                QobMsg.load_error.format(__display_file),
                ('[X]', None), immediate=True)

            self.check_for_last_session_file()

    def save_session_user(self):
        result = self.parent.session_data_mgr.user_save()

        if result:
            self.treeWidget_Src.info_overlay.display(QobMsg.user_saved_message.format(result), 6000)

    def save_empty(self):
        self.treeWidget_Src.info_overlay.display_confirm(
                QobMsg.user_save_empty, ('[X]', None), immediate=True)

    def save_error(self):
        self.treeWidget_Src.info_overlay.display_confirm(
            QobMsg.user_save_error, ('[X]', None), immediate=True)

    def initializePage(self):
        LOGGER.debug('Source Page initialize.')

        # Hide error message labels
        self.fakomLabel.hide()
        self.vplusLabel.hide()

        self.setup_qob_9000()

    def isComplete(self):
        """ Validate page and decide if next is enabled """
        if self.vplusCheckbox.isChecked() and self.fakomCheckbox.isChecked():
            return True
        else:
            return False

    def validatePage(self):
        """ Final validation if next button pressed """
        # Set package text filter
        self.parent.pkg_text_filter = self.read_pkg_filter()

        # Save session input
        self.parent.session_data_mgr.save_session()
        return True

    def load_ui(self):
        # Load page template
        load_ui_file(self, WIZARD_PAGE_SOURCE)

        # Setup tree widget overlay
        self.treeWidget_Src.info_overlay = InfoOverlay(self.treeWidget_Src)
        self.treeWidget_Src.overlay = Overlay(self.treeWidget_Src)
        self.treeWidget_Src.missing_ids = set()  # Dummy Attribute

        self.open_file_dialog = OpenPresetFile(self.app,
                                               None,
                                               self.ui,
                                               self.treeWidget_Src,
                                               self.openBtn)

        self.openBtn.pressed.connect(self.load_session_file)
        self.saveBtn.pressed.connect(self.save_session_user)
        self.reloadBtn.pressed.connect(self.load_session)

        self.parent.save_empty.connect(self.save_empty)
        self.parent.save_error.connect(self.save_error)

        # Setup filter text edit widget
        self.plainTextEditFilter.hide()

        # Show package filter as ; seperated string
        __filter_string = self.load_pkg_filter_string()

        self.plainTextEditFilter.setPlainText(__filter_string)

    def src_tree_setup_header(self):
        tree_setup_header_format([self.parent.src_widget])

    def load_session_file(self):
        __result = self.open_file_dialog.open_file_menu(None, file_type='WizardSession')
        LOGGER.debug('Open file wizard session: %s', __result)

        if __result:
            if __result.exists():
                self.load_session(__result)

    def load_pkg_filter_string(self):
        __filter_string = ''

        for __f in self.parent.pkg_text_filter:
            __filter_string += f'{__f}; '

        return __filter_string

    def read_pkg_filter(self):
        if not self.checkBoxCountryPkg.isChecked():
            return list()

        filter_string = self.plainTextEditFilter.toPlainText()
        filter_string = filter_string.replace('; ', ';').replace('\n', '')
        filter_string = filter_string.replace('\r', '').replace('\t', '')

        __filter_list = filter_string.split(';')

        for __s in ('', ' ', ' ;'):
            if __s in __filter_list:
                __filter_list.remove(__s)

        return __filter_list

    def setup_vplus(self, vplus_path):
        """ Prepare V Plus button method after Fakom setup """
        self.vplus_reader = ExcelConversionThread(self,
                                                  vplus_path,
                                                  self.parent.src_widget,
                                                  wizard=True)
        self.vplusBtn.setEnabled(True)

    def read_vplus(self):
        self.vplusCheckbox.setChecked(False)
        self.vplusBtn.setEnabled(False)
        self.vplusLabel.hide()

        self.treeWidget_Src.overlay.load_start()
        # self.parent.overlay.load_start()

        self.vplus_reader.create_thread()

    def read_fakom(self):
        __fakom_check_state = self.fakomCheckbox.isChecked()
        __vplus_check_state = self.vplusCheckbox.isChecked()

        self.fakomCheckbox.setChecked(False)
        self.vplusCheckbox.setChecked(False)
        self.fakomLutscherBtn.setEnabled(False)
        self.fakomLabel.hide()
        # self.parent.overlay.load_start()

        self.fakom_window = FakomWindow(self, self.app, wizard=True, widget=self.treeWidget_Src)
        result = self.fakom_window.exec()

        if result == 0:
            # FaKom Window aborted, no data touched, reset previous state
            self.fakomCheckbox.setChecked(__fakom_check_state)
            self.vplusCheckbox.setChecked(__vplus_check_state)

            # self.parent.overlay.load_finished()
            self.fakomLutscherBtn.setEnabled(True)

    def parse_xml(self, xml_file):
        """ Receives xml file from V Plus excel conversion thread """
        self.parent.src_widget.clear()

        valid_xml_file = self.parent.vplus_xml.parse_file(xml_file)

        if not valid_xml_file:
            self.vplus_result(valid_xml_file)
            return

        has_data = self.parent.vplus_xml.update_xml_tree_from_widget()

        if not has_data:
            self.vplusLabel.show()
            self.vplus_result(False)
            return

        self.parent.source_changed.emit()
        self.vplus_result(True)
        self.parent.src_widget.clear()

    def abort_vplus(self):
        """ Receives abort signal from excel thread """
        self.treeWidget_Src.overlay.load_finished()
        # self.parent.overlay.load_finished()
        self.vplus_result(False)

    def fakom_result(self, fakom_read_success, vplus_path):
        """ Will be activated by external signal """
        LOGGER.debug('Wizard received FaKom result: %s', fakom_read_success)

        self.fakomCheckbox.setChecked(fakom_read_success)
        self.fakomLutscherBtn.setEnabled(True)
        self.src_tree_setup_header()
        # self.parent.overlay.load_finished()

        if fakom_read_success:
            # Save FaKom Result to Xml
            has_data = self.parent.fakom_xml.update_xml_tree_from_widget()

            if has_data:
                self.setup_vplus(vplus_path)
            else:
                self.fakomLabel.show()
                self.fakomCheckbox.setChecked(has_data)

        self.completeChanged.emit()

    def vplus_result(self, vplus_read_success):
        """ Will be activated by external signal """
        LOGGER.debug('Wizard received V Plus result: %s', vplus_read_success)
        self.vplusBtn.setEnabled(True)
        self.src_tree_setup_header()

        self.treeWidget_Src.overlay.load_finished()
        # self.parent.overlay.load_finished()
        self.vplusCheckbox.setChecked(vplus_read_success)

        self.completeChanged.emit()

    def setup_qob_9000(self):
        quote_interval = 8000 + random.randint(1000, 30000)
        self.quote_timer.start(quote_interval)
        self.quote_timer.timeout.connect(self.qob_9000_speaks)

        self.parent.ui.qob9000_restarted = False

    def qob_9000_speaks(self):
        quote = random.choice(self.qob_quotes)
        message = '<b>QOB 9000 Nachricht:</b><br><i>{}</i>'.format(quote)
        self.QobQuote.setText(message)