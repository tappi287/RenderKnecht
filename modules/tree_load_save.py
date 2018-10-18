"""
knecht_load_save_preset for py_knecht. Saves XML with Presets

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

XML Structure:

        <renderknecht_varianten> -0-
        |
        |
        |----<origin /> -1-
        |
        |
        |----<renderknecht_settings /> -2-
        |
        |
        |----<variant_presets> -3-
        |    |
        |	 |
        |    |----<preset @name @order @type="preset" | "viewset" | "reset" | "package" | "model" @id=int[0:999]> -preset_0-
        |	 |    |
        |	 |    |
        |	 |    |----<variant @name @order @value> -variant_0-
        |	 |	  |    |
        |	 |	  |	   |
        |	 |	  |	   |----value (legacy) -> will be changed to attribute!
        |	 |	  |	   |
        |	 |	  |	   |
        |	 |	  |----</variant>
        |	 |	  |
        |	 |	  |----<reference @name @order @reference=<preset @id> @type=<preset @type> @value=information for user>
        |	 |	  |----</reference>
        |	 |	  |
        |	 |	  |
        |	 |----</preset>
        |    |
        |    |
        |----</variant_presets>
        |
        |
        </renderknecht_varianten>

"""
import os
import time
from pathlib import Path

from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTreeWidget
from PyQt5 import QtCore

from modules.knecht_threads import ConvertLegacyVariants, ExcelConversionThread
from modules.app_globals import Msg, HELPER_DIR
from modules.knecht_log import init_logging
from modules.tree_methods import SortTree
from modules.knecht_settings import knechtSettings

LOGGER = init_logging(__name__)

# Strings
Msg()


class SavePreset:
    save_file = ''

    def __init__(self, XML_dest, widget, ui):
        self.XML_dest = XML_dest
        self.widget = widget
        self.ui = ui

        # Disable Auto save for now, we will auto save the session instead
        # self.auto_save_mgr = AutoSave(self, ui)
        # self.auto_save_mgr.enable()

    def save(self, save_path='', save_successful=False):
        if save_path:
            self.save_file = save_path

        if not self.save_file:
            return False, Msg.SAVE_NOT_SET

        # Save to file
        save_successful, save_msg = self.save_items(self.save_file)

        self.widget.overlay.save_anim()
        self.widget.info_overlay.display(save_msg, 8000)

        return save_successful, save_msg

    def auto_save(self, save_path):
        if save_path:
            save_successful, save_msg = self.save_items(save_path)

            if save_successful:
                msg = Msg.SAVE_AUTO_OVERLAY.format(name=Path(save_path).name)
                self.widget.info_overlay.display(msg, 6000)
                return save_successful

        return False

    def save_items(self, save_path=''):
        if not save_path:
            return False, Msg.SAVE_NOT_SET

        # Measure time it took to parse from Tree Widget and save to file
        save_start_time = time.time()

        # Update xmlTree from TreeWidget
        has_data = self.XML_dest.update_xml_tree_from_widget()

        # Return if no presets were found
        if not has_data:
            return False, Msg.SAVE_EMPTY

        del has_data

        # Save to file
        try:
            self.XML_dest.save_tree(save_path)

            save_time = time.time() - save_start_time
            save_time = str(save_time)[0:4]
            LOGGER.info('Succesfully saved Xml file in %s secs:\n%s', save_time, save_path)

            save_successful = True
            save_msg = Msg.SAVE_MSG + save_time + 'secs - ' + str(save_path)

        except Exception as e:
            LOGGER.error('Could not save Xml file:\n%s\n%s', save_path, e)
            save_successful = False
            save_msg = Msg.SAVE_ERROR

        return save_successful, save_msg


class AutoSave(QtCore.QObject):
    # Default file name
    file_name = '{name}_auto_save_{index:04d}.xml'
    file_glob = '*_auto_save_????.xml'
    default_file_prefix = '_Automatic'

    # Interval 5 Minutes - 300000ms
    save_interval = 300000

    # Initial auto save interval
    # Provides an quick save after application launch
    initial_auto_save = True
    initial_auto_save_interval = 40000

    def __init__(self, parent, ui):
        super(AutoSave, self).__init__()
        self.parent = parent
        self.ui = ui

        # index we append to file name's
        self.index = 0

        # Prepare default file
        self.file = HELPER_DIR / AutoSave.file_name.format(
            name=AutoSave.default_file_prefix,
            index=self.index)

        # Auto save timer
        self.auto_save_timer = QtCore.QTimer()
        self.auto_save_timer.setTimerType(QtCore.Qt.VeryCoarseTimer)
        self.auto_save_timer.timeout.connect(self.save)

        if AutoSave.initial_auto_save:
            self.auto_save_timer.setInterval(AutoSave.initial_auto_save_interval)
        else:
            self.auto_save_timer.setInterval(AutoSave.save_interval)

    def enable(self):
        if not self.auto_save_timer.isActive():
            self.auto_save_timer.start()

    def disable(self):
        self.auto_save_timer.stop()

    @staticmethod
    def collect_clean_up(save_file=Path(''), file_set=set()):
        for auto_save_file in Path(HELPER_DIR).glob(AutoSave.file_glob):
            if auto_save_file.exists():
                    file_set.add(auto_save_file)

        if save_file:
            for auto_save_file in Path(save_file.parent).glob(save_file.stem + AutoSave.file_glob):
                if auto_save_file.exists():
                        file_set.add(auto_save_file)

        return file_set

    def clean_up(self, file_set=set(), temp_set=set()):
        for file in file_set:
            if file.exists():
                try:
                    os.remove(file)
                except OSError as e:
                    LOGGER.error('Failed to delete auto save file: %s', e)
            else:
                temp_set.add(file)

        return file_set.difference(temp_set)

    def set_save_file(self, save_file_path):
        current_path = Path(save_file_path)

        if not current_path.parent.exists():
            return

        self.file = current_path.parent / AutoSave.file_name.format(
            name=current_path.stem,
            index=self.index)

    def save(self):
        if not self.ui.unsaved_changes_present:
            return

        if not self.ui.unsaved_changes_auto_save:
            return

        # Check for current save file
        if self.parent.save_file:
            save_file = self.parent.save_file
        else:
            save_file = HELPER_DIR / AutoSave.default_file_prefix

        # Clean existing saves
        clean_up_file_set = self.collect_clean_up(save_file=Path(save_file))

        # Set Auto Save file and save it
        self.set_save_file(save_file)
        save_successful = self.parent.auto_save(self.file)

        # Report and clean up existing auto saves
        if save_successful:
            clean_up_file_set.discard(self.file)
            clean_up_file_set = self.clean_up(clean_up_file_set)

            # Update index
            self.index += 1
            if self.index >= 9999:
                self.index = 0

            # Report to Log
            msg_names = ''
            for f in clean_up_file_set:
                msg_names += f.name + ', '
            LOGGER.debug('Automatic save in %s. Cleaned up: %s', self.file.name, msg_names[:-2])

            # initial auto save performed, disable and return to long interval
            if AutoSave.initial_auto_save:
                AutoSave.initial_auto_save = False
                self.auto_save_timer.setInterval(AutoSave.save_interval)

            self.ui.unsaved_changes_auto_save = False
        else:
            LOGGER.warning('Automatic save could not save file\n%s', self.file)


class OpenPresetFile:

    def __init__(self, app, XML_src, ui, tree_widget_source: QTreeWidget,
                 ui_open_action):
        self.app = app
        self.XML_src = XML_src
        self.ui = ui
        self.tree_widget_source = tree_widget_source
        self.ui_open_action = ui_open_action
        self.sort = SortTree(ui, tree_widget_source)

    def stop_load_overlay(self):
        """ Enable widget and stop load indicator """
        self.tree_widget_source.overlay.load_finished()
        self.tree_widget_source.setEnabled(True)

    def open_file_menu(self, log_window, dir='', file_type='XML'):
        # QtCore.Qt doesn't accept WindowsPath, convert to string
        dir = str(dir)

        # Create and configure File Dialog
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)

        # Show File Dialog
        if file_type == 'XML':
            file, file_ext = dlg.getOpenFileName(self.ui, Msg.DIALOG_TITLE, dir,
                                                 Msg.FILTER)
            load_start_time = time.time()
        elif file_type == 'XLSX':
            file, file_ext = dlg.getOpenFileName(self.ui, Msg.EXCEL_TITLE, dir,
                                                 Msg.EXCEL_FILTER)
            load_start_time = time.time()
        elif file_type == 'CMD':
            file, file_ext = dlg.getOpenFileName(self.ui, Msg.CMD_TITLE, dir,
                                                 Msg.CMD_FILTER)
            load_start_time = time.time()
        elif file_type == 'FaKom':
            file, file_ext = dlg.getOpenFileName(self.ui, Msg.FAKOM_TITLE, dir,
                                                 Msg.FAKOM_FILTER)
            load_start_time = time.time()
        elif file_type == 'WizardSession':
            file, file_ext = dlg.getOpenFileName(self.ui, Msg.WIZARD_TITLE, dir,
                                                 Msg.WIZARD_FILTER)
            load_start_time = time.time()

        # Remember current path
        if file and not file_type == 'WizardSession':
            self.ui.current_path = os.path.dirname(file)
            knechtSettings.app['current_path'] = self.ui.current_path

        # Disable Widget and start load indicator
        self.tree_widget_source.overlay.load_start()
        self.tree_widget_source.setEnabled(False)

        # CMD File
        if file.endswith('.cmd'):
            # Create conversion thread
            LOGGER.info('Creating conversion thread for: %s', file)
            self.conversion_thread = ConvertLegacyVariants(
                self, file, self.ui)
            self.conversion_thread.create_thread()
            # Inform user
            self.tree_widget_source.info_overlay.display(Msg.CMD_FILE_MSG, 8000)
            # self.ui.info_box(msg.MSG_BOX_TITLE, msg.CMD_FILE_MSG, Path(file).name)

            return
        # XML File
        elif file.endswith('.xml') and file_type not in ['FaKom', 'WizardSession']:
            LOGGER.debug('XML File selected: %s, %s', file, file_ext)
            self.parse_xml(file)
        # XML WIzard Session File
        elif file.endswith('.xml') and file_type == 'WizardSession':
            # Wizard Session, simply return the Filename
            file = Path(file)
        # Excel file
        elif file.endswith('.xlsx'):
            # Create excel conversion thread
            LOGGER.debug('Excel File selected: %s', file)
            self.excel_conv_thread = ExcelConversionThread(self, file, self.tree_widget_source)
            self.excel_conv_thread.create_thread()

            return
        # No File or wrong type
        else:
            if file is not '':
                self.ui.info_box(Msg.MSG_BOX_TITLE, Msg.NO_FILE_MSG)

            LOGGER.debug('No or wrong file: %s', file)
            self.stop_load_overlay()
            return

        load_time = time.time() - load_start_time
        load_time = str(load_time)[0:8]
        LOGGER.info('%s loaded and parsed in %s seconds',
                    os.path.basename(file), load_time)
        self.stop_load_overlay()
        return file

    def parse_xml(self, xmlFile):
        # Clear Tree Widget
        self.tree_widget_source.clear()
        # Parse new xml file, returns True on success
        current_file = self.XML_src.parse_file(xmlFile)

        # Xml had valid content
        if current_file:
            self.ui.set_window_title(Path(xmlFile).name)

            xml_message = Msg.XML_FILE_LOADED + Path(xmlFile).name
            self.tree_widget_source.info_overlay.display(xml_message, 4000)

            # Add to recent files
            knechtSettings.add_recent_file('variants_xml', Path(xmlFile).as_posix())

            # Sort tree widget
            self.ui.sort_tree_widget.sort_all(self.tree_widget_source)

            # Clear Undo stack
            self.tree_widget_source.undo_stack.clear()
        else:
            self.ui.warning_box(Msg.ERROR_BOX_TITLE, Msg.XML_ERROR_MSG,
                                Path(xmlFile).name)
