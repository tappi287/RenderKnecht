"""
gui_main_menu module provides menu functionality for the main GUI

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
import os
from functools import partial
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QColor, QDesktopServices

from modules.app_strings import Msg, InfoMessage
from modules.app_globals import RENDER_BASE_PATH, HELPER_DIR, Itemstyle, DOC_FILE
from modules.gui_splash_screen_movie import show_splash_screen_movie
from modules.gui_widgets import FakomWindow, styleChooser, AboutBox
from modules.gui_set_path import SetDirectoryPath
from modules.gui_preset_wizard import PresetWizard
from modules.knecht_img_viewer import KnechtImageViewer
from modules.knecht_settings import knechtSettings
from modules.knecht_deltagen import SendToDeltaGen
from modules.knecht_threads import PngConvertThread
from modules.tree_context_menus import TreeContextMenu
from modules.tree_load_save import OpenPresetFile, SavePreset
from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)


class MenuBar(QtCore.QObject):
    """ Erwartet Fenster class object und stellt Funktionalitaet fuer die Menu Bar bereit. """
    render_path = QtCore.pyqtSignal(Path)
    open_file = QtCore.pyqtSignal()

    # Future thread or window instances
    fakom_window = None
    preset_wizard_win = None
    png_convert = None
    img_viewer = None

    def __init__(self, app, ui, log, tree_widget_source, tree_widget_dest, ui_action_open):
        super(MenuBar, self).__init__()

        # App class instance
        self.app = app

        # SchnuffiWindow class instance
        self.ui = ui

        # LogWindow class instance
        self.log = log

        # Recent files action's list
        self.recent_file_list = []

        # Creation menu context menu instance
        self.contextMenu = None

        # Generic file directory dialog
        self.set_dir = SetDirectoryPath(app, ui)
        self.get_directory_file_dialog = self.set_dir.get_directory_file_dialog

        # Dest Overlay
        self.dest_overlay = self.ui.treeWidget_DestPreset.info_overlay

        # Module instance that opens Xml or converts CMD
        self.file_mgr = OpenPresetFile(self.app, self.app.XML_src, self.ui, tree_widget_source, ui_action_open)
        self.save_mgr = SavePreset(self.app.XML_dest, tree_widget_dest, self.ui)

        # RENDER_BASE_PATH
        self.render_path.connect(self.display_render_path)
        self.render_path.emit(RENDER_BASE_PATH)

    def add_creation_menu(self, parent_menu: QtWidgets.QMenu):
        """ Adds the Context Creation Menu for DestinationWidget to parent menu """
        self.contextMenu = TreeContextMenu(self.ui.treeWidget_DestPreset, self.ui)
        self.contextMenu.create_creation_menu(parent_menu)

    def FileOpen(self):
        self.open_file.emit()
        LOGGER.debug('File > Open menu selected.')
        self.file_mgr.open_file_menu(self.log, self.ui.current_path, 'XML')
        self.load_recent_files()

    def ImportVplus(self):
        LOGGER.debug('File > Import > V Plus')
        self.file_mgr.open_file_menu(self.log, self.ui.current_path, 'XLSX')
        self.load_recent_files()

    def ImportCMD(self):
        LOGGER.debug('File > Import > CMD')
        self.file_mgr.open_file_menu(self.log, self.ui.current_path, 'CMD')
        self.load_recent_files()

    def ImportFakom(self):
        LOGGER.debug('File > Import > FaKom')
        # Fakom Window instance
        self.fakom_window = FakomWindow(self.ui, self.app)
        self.fakom_window.exec()
        LOGGER.debug('FaKom Window closed, continuing.')

    def preset_wizard(self):
        LOGGER.debug('File > Import > QUB 9000')
        # Preset Wizard Window instance
        self.preset_wizard_win = PresetWizard(self.ui, self.app)
        self.preset_wizard_win.exec()

    def file_save(self, save_as=False):
        LOGGER.debug('File > Save menu selected.')

        if not self.save_mgr.save_file or save_as:
            # User select save file dialog
            self.save_mgr.save_file, file_type = QtWidgets.QFileDialog.getSaveFileName(
                self.ui,
                Msg.SAVE_DIALOG_TITLE,
                self.ui.current_path,
                Msg.SAVE_FILTER)

            # Nothing selected, abort
            if self.save_mgr.save_file == '':
                return
        else:
            # Save File set, ask to overwrite
            message = Msg.SAVE_OVER[0] + Path(self.save_mgr.save_file).name + Msg.SAVE_OVER[1]
            answer = QtWidgets.QMessageBox.question(self.ui, Msg.SAVE_DIALOG_TITLE, message, QtWidgets.QMessageBox.Yes,
                                                    QtWidgets.QMessageBox.No)

            if answer == QtWidgets.QMessageBox.No:
                return

        # Save File
        save_succeeded, save_msg = self.save_mgr.save()

        if not save_succeeded:
            QtWidgets.QMessageBox.warning(self.ui, Msg.SAVE_DIALOG_TITLE, save_msg)
            return

        # Save successful
        self.ui.unsaved_changes_present = False
        self.ui.current_path = str(Path(self.save_mgr.save_file))
        LOGGER.info('UI Current Path: %s', self.ui.current_path)
        knechtSettings.app['current_path'] = Path(self.save_mgr.save_file).parent
        knechtSettings.add_recent_file('variants_xml', Path(self.save_mgr.save_file).as_posix())
        self.ui.set_window_title(Path(self.save_mgr.save_file).name)

        # Update recent files menu
        self.load_recent_files()

        # Show save message in status bar
        self.ui.statusbar.showMessage(save_msg)
        return True

    def search_and_replace(self):
        self.ui.search_replace.show()

    def png_converter(self):
        img_list = []
        conv_path = self.get_directory_file_dialog(self.ui.current_path, Msg.PNG_CONV_TITLE)

        if not conv_path:
            self.dest_overlay.display(Msg.PNG_CONV_NO_DIR, 8000)
            return

        if conv_path.exists():
            for img_file in conv_path.glob('*.*'):
                if img_file.suffix in ['.hdr', '.exr', '.jpg', '.bmp', '.tif']:
                    img_list.append(img_file)

        if not img_list:
            self.dest_overlay.display(Msg.PNG_CONV_NO_FILES, 8000)

        if img_list:
            self.png_convert = PngConvertThread(self.ui, self.ui.actionPNG_Konverter, img_list)
            self.png_convert.create_thread()

    def start_image_viewer(self, dropped_file=None):
        if not self.img_viewer:
            self.img_viewer = KnechtImageViewer(self.app, self.ui)

        if dropped_file:
            self.img_viewer.path_dropped(dropped_file)
            if not self.img_viewer.isHidden():
                return

        if self.img_viewer.isHidden():
            self.img_viewer.show_all()
        elif not dropped_file:
            self.img_viewer.close()

    def set_render_path_text(self):
        render_path = Path(self.ui.lineEdit_currentRenderPath.text())

        self.set_render_path(render_path)

    def set_render_path(self, render_path=''):
        """ Get the render path and set it """
        if render_path == '':
            render_path = self.get_directory_file_dialog(self.ui.current_path, Msg.RENDER_FILE_DIALOG)

        if render_path is None:
            return

        # os.path is more robust in catching weird strings
        if os.path.exists(render_path):
            SendToDeltaGen.render_user_path = render_path
            knechtSettings.app['render_path'] = str(render_path)
            self.render_path.emit(render_path)
        else:
            LOGGER.info('%s is not a valid render path. Ignoring yo non-sense.', render_path)

    def display_render_path(self, render_path):
        """ Receives render_path signal """
        if render_path.exists():
            self.ui.lineEdit_currentRenderPath.setText(str(render_path))
            LOGGER.info('Setting render path: %s', render_path)
        else:
            user_path = SendToDeltaGen.render_user_path
            if user_path:
                render_path = user_path
            else:
                render_path = RENDER_BASE_PATH

            self.ui.lineEdit_currentRenderPath.setText(render_path)

    def edit_deselect(self):
        """ De-select all Ctrl+D """
        widget = self.ui.tree_with_focus()

        if widget:
            widget.clearSelection()

    def edit_select_ref(self):
        widget = self.ui.tree_with_focus()

        if widget:
            widget.context.show_ref.trigger()

    def edit_menu_update(self):
        """ En-/Disable main menu edit actions according to widget in focus """
        self.copy_paste_call(3)

    def edit_copy(self):
        self.copy_paste_call(0)

    def edit_cut(self):
        self.copy_paste_call(1)

    def edit_paste(self):
        self.copy_paste_call(2)

    def copy_paste_call(self, clipboard_action):
        widget = self.ui.tree_with_focus()
        LOGGER.debug('Copy Paste Focus: %s', self.ui.get_tree_name(widget))

        if widget:
            try:
                copy_enabled = widget.context.copy_clip.isEnabled()
                cut_enabled = widget.context.cut_clip.isEnabled()
                paste_enabled = widget.context.paste_clip.isEnabled()
            except AttributeError as e:
                LOGGER.error('Copy Paste is not supported in this widget\n%s', e)
                copy_enabled = cut_enabled = paste_enabled = False

            # 0: Copy 1: Cut 2: Paste
            if clipboard_action == 0 and copy_enabled:
                widget.context.copy_clip.trigger()
            elif clipboard_action == 1 and cut_enabled:
                widget.context.cut_clip.trigger()
            elif clipboard_action == 2 and paste_enabled:
                widget.context.paste_clip.trigger()

            # 3: En-/Disable Edit menu actions
            if clipboard_action == 3:
                self.ui.actionCopy.setEnabled(copy_enabled)
                self.ui.actionCut.setEnabled(cut_enabled)
                self.ui.actionPaste.setEnabled(paste_enabled)

    def reset_switch(self):
        if self.ui.actionReset_senden.isChecked():
            SendToDeltaGen.reset = True
        else:
            SendToDeltaGen.reset = False

        knechtSettings.dg['send_reset'] = self.ui.actionReset_senden.isChecked()

    def freeze_viewer(self):
        SendToDeltaGen.viewer = self.ui.actionFreeze_Viewer.isChecked()

        knechtSettings.dg['viewer_freeze'] = self.ui.actionFreeze_Viewer.isChecked()

    def apply_viewer_bgr(self):
        SendToDeltaGen.set_viewer_bgr = self.ui.checkBox_applyBg.isChecked()
        SendToDeltaGen.viewer_bgr_color = self.ui.pushButton_Bgr.color()
        self.app.deltagen_render_instance.set_viewer_color()

        knechtSettings.dg['viewer_apply_bgr'] = self.ui.checkBox_applyBg.isChecked()

    def check_variants(self):
        if self.ui.actionVarianten_Check.isChecked():
            SendToDeltaGen.check_variants = True
        else:
            SendToDeltaGen.check_variants = False
            # Render Feedbackloop has no effect without state check
            self.ui.checkBox_renderTimeout.setChecked(False)

        knechtSettings.dg['check_variant'] = self.ui.actionVarianten_Check.isChecked()

    def tree_show_check_variants(self):
        knechtSettings.dg['tree_state_check'] = self.ui.actionTreeStateCheck.isChecked()

    def convert_to_png(self):
        if self.ui.checkBox_convertToPng.isChecked():
            SendToDeltaGen.convert_to_png = True
        else:
            SendToDeltaGen.convert_to_png = False

        knechtSettings.dg['convert_to_png'] = self.ui.checkBox_convertToPng.isChecked()

    def render_dir(self):
        if self.ui.checkBox_createPresetDir.isChecked():
            SendToDeltaGen.create_render_preset_dir = True
        else:
            SendToDeltaGen.create_render_preset_dir = False

        knechtSettings.dg['create_render_preset_dir'] = self.ui.checkBox_createPresetDir.isChecked()

    def render_receive_timeout(self):
        if self.ui.checkBox_renderTimeout.isChecked():
            SendToDeltaGen.long_render_timeout = True
            # Make sure variant state check is enabled
            self.ui.actionVarianten_Check.setChecked(True)
            self.ui.treeWidget_render.info_overlay.display(Msg.RENDER_TOGGLE_TIMEOUT_ON, 3000)
        else:
            SendToDeltaGen.long_render_timeout = False
            self.ui.treeWidget_render.info_overlay.display(Msg.RENDER_TOGGLE_TIMEOUT_OFF, 4000)

        knechtSettings.dg['render_timeout'] = self.ui.checkBox_renderTimeout.isChecked()

    def ViewLogWindow(self):
        self.log.toggle_window()
        knechtSettings.app['log_window'] = self.ui.actionLog_Window.isChecked()

    def ViewSplashScreen(self):
        show_splash_screen_movie(self.app)

    def ViewStyleSetting(self):
        style_chooser = styleChooser(self.ui)
        style_setting = style_chooser.exec_()

        if style_setting:
            style_msg = Msg.STYLE_CHANGED + knechtSettings.app['app_style']
            self.dest_overlay.display(style_msg, 4000)

    def infoScreen(self):
        info_text, info_msg = InfoMessage.get()[0], InfoMessage.get()[1]
        info_box = AboutBox(self.ui, 'Infobox', info_text, info_msg)
        info_box.exec()
        # QtWidgets.QMessageBox.information(self.ui, 'Infobox', info_msg)
        self.greeting()

    def version_info(self):
        title_txt = Msg.APP_UPDATE_TITLE
        msg_txt = Msg.APP_UPDATE
        self.ui.info_box(title_txt, msg_txt)

    def version_check(self, version_thread):
        version_thread = version_thread
        version_thread.create_thread(skip_wait=True)

        def info_btn():
            self.infoScreen()
            self.dest_overlay.display_exit()

        self.dest_overlay.display_confirm(
            Msg.VERSION_MSG,
            ('Info', info_btn),
            ('[X]', None),
            immediate=True)

    @staticmethod
    def help(self):
        """ Open Windows Help *.chm file """
        __q = QUrl.fromLocalFile(str(DOC_FILE))
        try:
            QDesktopServices.openUrl(__q)
        except Exception as e:
            self.ui.generic_error_msg(e)

    def greeting(self):
        def ext_link_btn():
            link = QUrl(Msg.APP_EXT_LINK)
            QDesktopServices.openUrl(link)

        greeting = Msg.APP_VERSION_GREETING.format(version=self.app.version)
        self.dest_overlay.display_confirm(greeting,
                                          (Msg.APP_EXT_LINK_BTN, ext_link_btn),
                                          ('[X]', None))

    def load_settings(self):
        log_msg = '\nLoading Application settings:'

        # Version greeting
        if knechtSettings.app['version'] != self.app.version:
            self.greeting()
            log_msg += '\nSetting Version: {}'.format(knechtSettings.app['version'])

        # Keep the last file open / save action
        if knechtSettings.app['current_path'] == '':
            self.ui.current_path = str(HELPER_DIR)
        else:
            self.ui.current_path = knechtSettings.app['current_path']
            log_msg += '\nSaved Current Path:\n{}'.format(self.ui.current_path)

        # Load StartUp file
        """
        if START_UP_FILE:
            self.file_mgr.parse_xml(START_UP_FILE)
            load_msg = Msg.LOAD_MSG + str(START_UP_FILE)
            self.ui.statusbar.showMessage(load_msg)

            self.ui.current_path = str(Path(START_UP_FILE))
            log_msg += '\nStart up file found and parsed:\n{}'.format(START_UP_FILE)
        """

        # Load last render path
        if not knechtSettings.app['render_path'] == '':
            render_path = Path(knechtSettings.app['render_path'])
            SendToDeltaGen.render_user_path = render_path
            self.render_path.emit(render_path)
            log_msg += '\nSaved Render Path:\n{}'.format(render_path)

        # Viewer Background
        color = knechtSettings.dg['viewer_bgr_color']
        if color:
            if color.isdigit():
                c = QColor()
                c.setRgba(int(color))
                self.ui.pushButton_Bgr.setColor(c)
                log_msg += '\nViewer Background color: {}'.format(c.name())

        # Apply Viewer background setting
        self.ui.checkBox_applyBg.setChecked(knechtSettings.dg['viewer_apply_bgr'])
        SendToDeltaGen.set_viewer_bgr = self.ui.checkBox_applyBg.isChecked()

        # Recent files
        self.load_recent_files()

        # Load and call menu settings
        self.ui.actionReset_senden.setChecked(knechtSettings.dg['send_reset'])
        self.reset_switch()

        self.ui.actionFreeze_Viewer.setChecked(knechtSettings.dg['viewer_freeze'])
        self.freeze_viewer()

        self.ui.actionVarianten_Check.setChecked(knechtSettings.dg['check_variant'])
        self.check_variants()

        self.ui.actionTreeStateCheck.setChecked(knechtSettings.dg['tree_state_check'])

        self.ui.checkBox_convertToPng.setChecked(knechtSettings.dg['convert_to_png'])
        self.convert_to_png()

        self.ui.checkBox_renderTimeout.setChecked(knechtSettings.dg['render_timeout'])
        self.render_receive_timeout()

        self.ui.checkBox_createPresetDir.setChecked(knechtSettings.dg['create_render_preset_dir'])
        self.render_dir()

        log_msg += '\n\n' \
                   'Send Reset:     {:<5} Freeze Viewer:      {:^5} Variant State Check:      {:>1}\n' \
                   'Convert to PNG: {:<5} Long Feedback Loop: {:^5} Create Render Preset Dir: {:>1}\n' \
                   'Set Viewer bgr: {:<5}'.format(knechtSettings.dg['send_reset'], knechtSettings.dg['viewer_freeze'],
            knechtSettings.dg['check_variant'], knechtSettings.dg['convert_to_png'],
            knechtSettings.dg['render_timeout'], knechtSettings.dg['create_render_preset_dir'],
            knechtSettings.dg['viewer_apply_bgr'])

        LOGGER.debug(log_msg)

    def load_recent_files(self):
        """ Load recent files and create actions accordingly """
        enable_menu = False

        if knechtSettings.recent_files_set:
            self.ui.menuRecent.clear()

            for recent_item in sorted(knechtSettings.recent_files_set):
                if enable_menu:
                    self.create_recent_item(*recent_item)
                else:
                    enable_menu = self.create_recent_item(*recent_item)

        # Enable recent files menu
        if enable_menu:
            self.ui.menuRecent.setEnabled(True)
        else:
            self.ui.menuRecent.setEnabled(False)

    def create_recent_item(self, order, type, file):
        if type == 'variants_xml':
            file = Path(file)

            if file.exists():
                action_name = file.name
                self.recent_file_list.append(action_name)

                # Create Action
                xml_file_action = QtWidgets.QAction(action_name, self.ui.menuRecent)
                xml_file_action.triggered.connect(partial(self.recent_xml_open, file))
                xml_file_action.setIcon(self.ui.icon[Itemstyle.TYPES['preset']])

                # Append to menu
                self.ui.menuRecent.addAction(xml_file_action)
                # Enable menu
                return True

    def recent_xml_open(self, file):
        self.file_mgr.parse_xml(str(file))
        self.load_recent_files()
