"""
knecht_preset_editor_gui module provides functionality for the main GUI

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
import sys
from functools import partial
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QFontDatabase

from modules.app_globals import DEST_XML, ItemColumn, Itemstyle, Msg, SHOW_SPLASH, SRC_XML, UI_DARK_STYLE_SHEET, UI_SIZE
from modules.gui_log_window import LogWindow
from modules.gui_path_render_service import PathRenderService
from modules.gui_main_menu import MenuBar
from modules.gui_main_window import MainWindow
from modules.gui_splash_screen_movie import show_splash_screen_movie
from modules.knecht_log import init_logging
from modules.knecht_settings import knechtSettings
from modules.knecht_updater import VersionCheck, run_exe_updater
from modules.knecht_xml import XML
from modules.knecht_deltagen import SendToDeltaGen
from modules.tree_drag_drop import render_tree_drop, WidgetToWidgetDrop
from modules.tree_methods import AddRemoveItemsCommand, add_variant, toggle_ref_visibility, tree_setup_header_format
from modules.tree_overlay import IntroOverlay
from modules.tree_session import TreeSessionManager

LOGGER = init_logging(__name__)


def load_style(ui):
    if knechtSettings.app['app_style']:
        if knechtSettings.app['app_style'].casefold() == 'fusion-dark':
            # Set Fusion Style
            ui.setStyle('Fusion')

            # Load stylesheet
            try:
                with open(UI_DARK_STYLE_SHEET, mode='r') as sheet:
                    ui.setStyleSheet(sheet.read())
            except Exception as e:
                LOGGER.error('Error loading dark-stylesheet:\n%s', e)
        else:
            ui.setStyle(knechtSettings.app['app_style'])


class RenderKnechtGui(QtWidgets.QApplication):
    """ Main GUI Application """
    quit_timer = QtCore.QTimer()
    quit_timer.setSingleShot(True)
    quit_timer.setInterval(1000)

    intro_timer = QtCore.QTimer()
    intro_timer.setSingleShot(True)
    intro_timer.setInterval(500)
    intro_widget = None

    def __init__(self, version, knecht_except_hook):
        super(RenderKnechtGui, self).__init__(sys.argv)

        load_style(self)

        # Version
        self.version = version

        if SHOW_SPLASH:
            splash = show_splash_screen_movie(self)

            # Create GUI Windows
            self.ui = MainWindow(self)
        else:
            self.ui = MainWindow(self)

        font_id = QFontDatabase.addApplicationFont(Itemstyle.FONT['Inconsolata'])
        LOGGER.debug('Font loaded: %s', QFontDatabase.applicationFontFamilies(font_id))

        self.ui.setGeometry(*UI_SIZE)

        # Prepare exception handling
        knecht_except_hook.app = self
        knecht_except_hook.setup_signal_destination(self.report_exception)
        self.ui.exceptionBtn.pressed.connect(self.report_exception_test)
        self.ui.exceptionBtn.hide()

        # App Undo Group
        self.undo_grp = QtWidgets.QUndoGroup(self)

        # Create Undo Stacks with parent undo grp
        for tree_widget in self.ui.tree_widget_list:
            tree_widget.undo_stack = QtWidgets.QUndoStack(self.undo_grp)
            tree_widget.undo_stack.setUndoLimit(25)

        # Session mgr
        self.session = TreeSessionManager(self, self.ui)

        # Set app class for delete class
        AddRemoveItemsCommand.app = self

        # Will store last active undo stack
        self.undo_last_active = []

        # If undo stack cleaned, set last non-clean undo stack active
        self.undo_grp.cleanChanged.connect(self.set_undo_stack_active)

        # Undo / Redo menu
        self.undo_grp.canUndoChanged.connect(self.set_undo_enabled)
        self.undo_grp.canRedoChanged.connect(self.set_redo_enabled)
        self.undo_grp.undoTextChanged.connect(self.set_undo_txt)
        self.undo_grp.redoTextChanged.connect(self.set_redo_txt)
        # Bind menu undo / redo actions
        self.ui.actionUndo.triggered.connect(self.undo_grp.undo)
        self.ui.actionRedo.triggered.connect(self.undo_grp.redo)

        self.Log_Window = LogWindow(self.ui.actionLog_Window)
        self.Log_Window.setGeometry(1800, 150, 900, 1024)

        # Setup XML Files
        self.XML_src = XML(SRC_XML, self.ui.treeWidget_SrcPreset)
        self.XML_dest = XML(DEST_XML, self.ui.treeWidget_DestPreset)
        """
            Create Events
        """
        # Menu bar
        self.menu = MenuBar(self, self.ui, self.Log_Window, self.ui.treeWidget_SrcPreset, self.ui.treeWidget_DestPreset,
                            self.ui.actionOpen)

        self.menu.open_file.connect(self.ui.sort_tree_widget.stop_sorting_worker)

        if knechtSettings.app['log_window']:
            self.Log_Window.show()
            self.ui.actionLog_Window.setChecked(True)
        else:
            self.Log_Window.hide()
            self.ui.actionLog_Window.setChecked(False)

        try:
            self.menu.load_settings()
        except Exception as e:
            self.ui.generic_error_msg(e)

        # File > Open | Save | Save_as | Exit
        self.ui.actionOpen.triggered.connect(self.menu.FileOpen)
        self.ui.actionVarianten_CMD.triggered.connect(self.menu.ImportCMD)
        self.ui.action_vplus.triggered.connect(self.menu.ImportVplus)
        self.ui.action_fakom.triggered.connect(self.menu.ImportFakom)
        self.ui.actionPresetWizard.triggered.connect(self.menu.preset_wizard)
        self.ui.actionPNG_Konverter.triggered.connect(self.menu.png_converter)
        self.ui.actionSave.triggered.connect(self.menu.file_save)
        self.ui.actionSave_as.triggered.connect(partial(self.menu.file_save, True))
        self.ui.actionExit.triggered.connect(self.ui.close)
        # Info
        self.ui.actionInfo.triggered.connect(self.menu.infoScreen)
        self.ui.actionHelp.triggered.connect(self.menu.help)
        # DeltaGen
        self.ui.actionReset_senden.toggled.connect(self.menu.reset_switch)
        self.ui.actionFreeze_Viewer.toggled.connect(self.menu.freeze_viewer)
        self.ui.actionVarianten_Check.toggled.connect(self.menu.check_variants)
        self.ui.actionTreeStateCheck.toggled.connect(self.menu.tree_show_check_variants)

        # Edit Menu
        self.ui.menuEdit.aboutToShow.connect(self.menu.edit_menu_update)
        # Edit > Search and Replace
        self.ui.actionSearchReplace.triggered.connect(self.menu.search_and_replace)
        # Edit > Create
        self.menu.add_creation_menu(self.ui.menuCreation)
        # Edit > Copy / Cut / Paste
        self.ui.actionCopy.triggered.connect(self.menu.edit_copy)
        self.ui.actionCut.triggered.connect(self.menu.edit_cut)
        self.ui.actionPaste.triggered.connect(self.menu.edit_paste)

        # Edit > Selection
        self.ui.actionDeSelect.setText('Nichts selektieren\tCtrl+D')
        self.ui.actionDeSelect.triggered.connect(self.menu.edit_deselect)

        self.ui.actionSelectRef.setText('Referenz(en) selektieren\tCtrl+R')
        self.ui.actionSelectRef.triggered.connect(self.menu.edit_select_ref)

        # Update Menu
        self.version_check_thread = VersionCheck(self, version)
        self.version_check_thread.create_thread()
        self.ui.actionVersion_info.triggered.connect(self.menu.version_info)
        self.ui.actionVersionCheck.triggered.connect(partial(self.menu.version_check, self.version_check_thread))

        # View > Log Window | Splash Screen
        self.ui.actionLog_Window.triggered.connect(self.menu.ViewLogWindow)
        self.ui.actionSplash_Screen.triggered.connect(self.menu.ViewSplashScreen)
        self.ui.actionIntro.triggered.connect(self.show_intro)
        self.ui.actionStyle.triggered.connect(self.menu.ViewStyleSetting)

        # Source Tree Widget can drag and drop to Destination Tree Widget
        self.tree_src_to_dest = WidgetToWidgetDrop(self.ui, [self.ui.treeWidget_SrcPreset, self.ui.treeWidget_Variants],
                                                   self.ui.treeWidget_DestPreset, only_childs=False,
                                                   create_preset_on_drop_from=self.ui.treeWidget_Variants)
        # Destination and Source Tree Widgets can drag and drop child items to Variants Tree Widget
        self.tree_dest_to_variants = WidgetToWidgetDrop(self.ui,
                                                        [self.ui.treeWidget_DestPreset, self.ui.treeWidget_SrcPreset],
                                                        self.ui.treeWidget_Variants, only_childs=True)
        # Destination Tree drop to Render Tree
        self.tree_dest_to_rendering = render_tree_drop(self.ui, self.ui.treeWidget_DestPreset,
                                                       self.ui.treeWidget_render)

        # Item changed signal
        # Editing order strings will re-write with leading zeros
        # Editing reference column will change item to ref type
        self.ui.treeWidget_DestPreset.itemChanged.connect(self.item_changed)
        self.ui.treeWidget_Variants.itemChanged.connect(self.item_changed)

        # Show description of current item
        self.description_timer = QtCore.QTimer()
        self.description_timer.setSingleShot(True)
        self.description_timer.setInterval(250)
        self.ui.treeWidget_DestPreset.itemSelectionChanged.connect(
            partial(self.show_item_desc, self.ui.treeWidget_DestPreset))
        self.ui.treeWidget_SrcPreset.itemSelectionChanged.connect(
            partial(self.show_item_desc, self.ui.treeWidget_SrcPreset))
        self.ui.treeWidget_Variants.itemSelectionChanged.connect(
            partial(self.show_item_desc, self.ui.treeWidget_Variants))

        # Double click on label sorts headers
        self.ui.label_Src.mouseDoubleClickEvent = self.sort_all_headers_event
        self.ui.label_Dest.mouseDoubleClickEvent = self.sort_all_headers_event
        self.ui.label_Dest_File.mouseDoubleClickEvent = self.sort_all_headers_event
        self.ui.label_Renderlist.mouseDoubleClickEvent = self.sort_all_headers_event

        # Sort buttons
        self.ui.pushButton_Src_sort.pressed.connect(partial(self.sort_tree_btns, self.ui.treeWidget_SrcPreset))
        self.ui.pushButton_Dest_sort.pressed.connect(partial(self.sort_tree_btns, self.ui.treeWidget_DestPreset))
        self.ui.pushButton_Var_sort.pressed.connect(partial(self.sort_tree_btns, self.ui.treeWidget_Variants))
        self.ui.pushButton_Ren_sort.pressed.connect(partial(self.sort_tree_btns, self.ui.treeWidget_render))

        # Header sorting triggers warning message
        self.ui.treeWidget_DestPreset.header().sectionClicked.connect(
            partial(self.sort_header_clicked, self.ui.treeWidget_DestPreset))
        self.ui.treeWidget_Variants.header().sectionClicked.connect(
            partial(self.sort_header_clicked, self.ui.treeWidget_Variants))

        # Clear Buttons - bind to dbl click
        src_clear = self.ClearTree(self.ui.treeWidget_SrcPreset, self)
        self.ui.treeWidget_SrcPreset.clear_tree = src_clear.clear
        self.ui.pushButton_Src_clear.mouseDoubleClickEvent = src_clear.dbl_click

        dst_clear = self.ClearTree(self.ui.treeWidget_DestPreset, self, unset_save_file=True)
        self.ui.treeWidget_DestPreset.clear_tree = dst_clear.clear
        self.ui.pushButton_Dest_clear.mouseDoubleClickEvent = dst_clear.dbl_click

        var_clear = self.ClearTree(self.ui.treeWidget_Variants, self)
        self.ui.treeWidget_Variants.clear_tree = var_clear.clear
        self.ui.pushButton_delVariants.mouseDoubleClickEvent = var_clear.dbl_click

        ren_clear = self.ClearTree(self.ui.treeWidget_render, self)
        self.ui.treeWidget_render.clear_tree = ren_clear.clear
        self.ui.pushButton_delRender.mouseDoubleClickEvent = ren_clear.dbl_click

        # Eye buttons, hide ref and default presets
        self.ui.pushButton_Dest_show.toggled.connect(
            partial(toggle_ref_visibility, self.ui, self.ui.treeWidget_DestPreset))
        # self.ui.pushButton_Src_show.toggled.connect(partial(toggle_ref_visibility, self.ui, self.ui.treeWidget_SrcPreset))

        # Add button Variant text field
        self.ui.pushButton_addVariant.pressed.connect(self.add_text_to_variants_tree)
        self.ui.plainTextEdit_addVariant_Setname.returnPressed.connect(self.ui.pushButton_addVariant.click)
        self.ui.plainTextEdit_addVariant_Variant.returnPressed.connect(self.ui.pushButton_addVariant.click)

        # Send to DG threaded instances
        self.deltagen_send_instance = SendToDeltaGen(self, self.ui.pushButton_sendDG, self.ui.pushButton_abort,
                                                     self.ui.treeWidget_Variants, False)

        self.deltagen_render_instance = SendToDeltaGen(self, self.ui.pushButton_startRender,
                                                       self.ui.pushButton_abortRender, self.ui.treeWidget_render, True)


        # Rendering Path
        self.ui.toolButton_changeRenderPath.pressed.connect(self.menu.set_render_path)
        self.ui.lineEdit_currentRenderPath.textChanged.connect(self.menu.set_render_path_text)

        # Convert to PNG after rendering
        self.ui.checkBox_convertToPng.toggled.connect(self.menu.convert_to_png)

        # Toggle long feedback loop while rendering
        self.ui.checkBox_renderTimeout.toggled.connect(self.menu.render_receive_timeout)

        # Create Render Preset directory(s)
        self.ui.checkBox_createPresetDir.toggled.connect(self.menu.render_dir)

        # Apply background color to viewer while rendering
        self.ui.checkBox_applyBg.toggled.connect(self.menu.apply_viewer_bgr)
        self.ui.pushButton_Bgr.colorChanged.connect(self.dg_set_viewer_color)

        # Change Viewer Size
        self.ui.comboBox_ViewerSize.currentIndexChanged.connect(self.dg_resize_viewer)

        # Send variants to DeltaGen
        self.ui.pushButton_sendDG.pressed.connect(self.dg_send)

        # Start Rendering with DeltaGen
        self.ui.pushButton_startRender.pressed.connect(self.dg_render)

        # Update estimated render time
        self.ui.treeWidget_render.itemChanged.connect(self.dg_estimate_render_timer)

        # init path render service
        self.path_render_service = PathRenderService(self, self.ui)

        # Introduction movie
        intro_shown = knechtSettings.app.get('introduction_shown')

        if not intro_shown:
            self.intro_timer.timeout.connect(self.show_intro)
            self.intro_timer.start()

        # Load session
        self.session.load_session()

        # Show window and finish splash screen
        self.ui.show()
        splash.finish(self.ui)

        LOGGER.info('Preset Editor GUI initialized. Log Level root: %s',
                    logging.getLevelName(logging.root.getEffectiveLevel()))

        LOGGER.info('%s', Msg.WELCOME_MSG)

        # Report ImageIO Libary Path
        img_io = os.getenv('IMAGEIO_FREEIMAGE_LIB')
        LOGGER.info('ImageIO Freelib path: %s', img_io)

    def show_intro(self):
        # Reset GUI Size to default to play introduction
        x = self.ui.geometry().x()
        y = self.ui.geometry().y()
        self.ui.setGeometry(x, y, UI_SIZE[2], UI_SIZE[3])

        # Intro overlay
        self.intro_widget = IntroOverlay(self.ui.centralWidget())
        self.intro_widget.generic_center()
        self.intro_widget.intro()
        self.intro_widget.finished_signal.connect(self.del_intro)

    def del_intro(self):
        LOGGER.debug('Deleting intro widget.')
        self.intro_widget.deleteLater()
        self.intro_widget = None
        knechtSettings.app['introduction_shown'] = True

    def set_undo_stack_active(self, clean_state):
        """ Receives cleanChanged from Undo Grp to set last stack active if current stack is changed """
        # TODO Letzter Undo Stack wird unzugänglich
        # Wenn Undo Stack gewechelt wird sind Redos aus vorheriger Aktion in anderem Baum unzugänglich.
        if not clean_state:
            # Store current active
            LOGGER.debug('Appending non-clean Undo-Stack to stack list.')
            self.undo_last_active.append(self.undo_grp.activeStack())
            # Limit list size
            stack_list_size = len(self.undo_last_active)

            if stack_list_size >= 25:
                # Remove first list element
                self.undo_last_active = self.undo_last_active[1:stack_list_size]
                LOGGER.debug('Limiting undo last-stack-active-list size to: %s', len(self.undo_last_active))
        else:
            # Iterate backwards to last non-clean undo_stack
            stack_list_size = len(self.undo_last_active)
            for stack in reversed(self.undo_last_active):
                stack_list_size -= 1
                if not stack.isClean():
                    stack.setActive(True)
                    # Shorten list
                    self.undo_last_active = self.undo_last_active[0:stack_list_size]
                    LOGGER.debug(
                        'Current Undo-Stack clean state detected. Setting last non-clean stack active. Stack list size: %s',
                        stack_list_size)
                    break

    def set_undo_enabled(self, can_undo):
        self.ui.actionUndo.setEnabled(can_undo)

    def set_redo_enabled(self, can_redo):
        self.ui.actionRedo.setEnabled(can_redo)

    def set_undo_txt(self, txt):
        """ Set Undo menu text """
        if txt != '':
            self.ui.actionUndo.setText('Rückgängig: ' + txt + '\tCtrl+Z')
        else:
            self.ui.actionUndo.setText('Rückgängig\tCtrl+Z')

    def set_redo_txt(self, txt):
        """ Set Redo menu text """
        if txt != '':
            self.ui.actionRedo.setText('Wiederherstellen: ' + txt + '\tCtrl+Y')
        else:
            self.ui.actionRedo.setText('Wiederherstellen\tCtrl+Y')

    def sort_tree_btns(self, widget):
        """ Sorting btns, re-write order strings and setup header """
        self.ui.sort_tree_widget.sort_all(widget)
        if widget.sortColumn() == 0:
            tree_setup_header_format(widget)

    def report_exception(self, msg):
        """ Receives KnechtExceptHook exception signal """
        msg = Msg.APP_EXCEPTION + msg.replace('\n', '<br>')
        self.ui.generic_error_msg(msg)

    def report_exception_test(self):
        """ Produce an exception to test exception handling """
        try:
            a = 1 / 0
        except Exception:
            raise Exception

    @staticmethod
    def sort_header_clicked(widget):
        widget.info_overlay.display(Msg.OVERLAY_SORT_ORDER_WARNING, 6000)

    def set_unsaved_changes(self):
        if not self.ui.unsaved_changes_present:
            self.ui.unsaved_changes_present = True

            if self.menu.save_mgr.save_file:
                self.ui.set_window_title(Path(self.menu.save_mgr.save_file).name)

        if not self.ui.unsaved_changes_auto_save:
            self.ui.unsaved_changes_auto_save = True

    def item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """ Signal itemChanged (QTreeWidgetItem *item, int column) """
        # TODO Dateiänderung anzeigen * _ *
        if column == ItemColumn.ORDER or self.ui.sort_tree_widget.work_timer.isActive():
            # Avoid calls from sorting
            self.set_unsaved_changes()
            return

        self.set_unsaved_changes()

        item.treeWidget().sortBtn.setEnabled(True)

        if column == ItemColumn.ORDER:
            # Re-write order with leading zeros for pretty sorting
            if str(item.text(column)).isdigit():
                item.setText(column, item.text(column).rjust(3, '0'))

        # Change Type based on input to reference column
        if column == ItemColumn.REF:
            # Reference column empty
            if item.text(column) == '':
                # Item is child
                if item.parent():
                    # Change to variant type
                    item.UserType = 1001
                    LOGGER.debug('Changed Type for %s to variant 1001.', item.text(1))
                else:
                    # Change to preset type
                    item.UserType = 1000
                    LOGGER.debug('Changed Type for %s to preset 1000.', item.text(1))
            else:
                # Change to reference type if reference entered
                item.UserType = 1002
                LOGGER.debug('Changed item type for %s to %s. Column text: %s', item.text(1), item.UserType,
                             item.text(column))

        # Changing preset name/value/type, updates references
        if item.UserType == 1000 and column in [ItemColumn.NAME, ItemColumn.VALUE, ItemColumn.TYPE]:
            new_item_text = item.text(column)
            item_name = item.text(ItemColumn.NAME)
            item_id = item.text(ItemColumn.ID)

            # Update reference names
            if item_id:
                ref_items = item.treeWidget().findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.REF)

                # Make sure we don't compare names if name column has changed
                if column == ItemColumn.NAME:
                    ref_names = ref_items
                else:
                    ref_names = item.treeWidget().findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.REF)

                for ref_item in ref_items:
                    # Compare name
                    if ref_item in ref_names:
                        ref_item.setText(column, new_item_text)

                LOGGER.debug('Updated reference column %s from preset with value: %s', column, new_item_text)

        # Changing reference name/value/type, updates preset
        # Disabled, leads to recursion on name check
        if item.UserType == 1002 and column in [ItemColumn.NAME, ItemColumn.VALUE, ItemColumn.TYPE]:
            new_item_text = item.text(column)
            item_name = item.text(ItemColumn.NAME)
            item_id = item.text(ItemColumn.REF)

            if item_id:
                pre_items = item.treeWidget().findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.ID)

                # Make sure we don't compare names if name column has changed
                if column == ItemColumn.NAME:
                    pre_names = pre_items
                else:
                    pre_names = item.treeWidget().findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.ID)

                for pre_item in pre_items:
                    # Compare name
                    if pre_item in pre_names:
                        pre_item.setText(column, new_item_text)

                LOGGER.debug('Updated preset from reference: %s', new_item_text)

        # Check if name is unipue
        if column == ItemColumn.NAME and item.UserType == 1000:
            self.ui.check_item_name(item, item.text(ItemColumn.NAME))

        if item.text(ItemColumn.TYPE) == 'seperator':
            if item.parent():
                # Sub seperator
                item.UserType = 1006
                LOGGER.debug('Updated item type to 1006 - sub seperator')
            else:
                item.UserType = 1005
                LOGGER.debug('Updated item type to 1005 - seperator')

    def show_item_desc(self, widget: QtWidgets.QTreeWidget):
        """ Display information for the current item """
        if self.description_timer.isActive():
            # Add a delay between selection updates
            return
        else:
            self.description_timer.start()

        selected_items = widget.selectedItems()

        if selected_items:
            current_item = selected_items[len(selected_items) - 1]
        else:
            return

        if len(selected_items) > 1:
            child_count = 0

            for item in selected_items:
                child_count += item.childCount()

            txt = str(child_count) + Msg.OVERLAY_PRESET[0] + ' - ' + str(len(selected_items)) + Msg.OVERLAY_PRESET[1]

            widget.info_overlay.display(txt, 2800, immediate=True)

            return

        type_desc = ItemColumn.TYPE_DESC[current_item.UserType]

        # Description
        if current_item.UserType in [1001, 1002, 1004]:
            txt = current_item.text(ItemColumn.DESC)
            name = current_item.text(ItemColumn.NAME)

            if current_item.parent():
                item_idx = current_item.parent().indexOfChild(current_item)
            else:
                item_idx = widget.indexOfTopLevelItem(current_item)

            if txt != '':
                txt = '{} - {} - {}_{:03d}'.format(name, txt, type_desc, item_idx)
                widget.info_overlay.display(txt, 2800, True)
            else:
                txt = '{} - {}_{:03d}'.format(name, type_desc, item_idx)
                widget.info_overlay.display(txt, 1800, True)
        else:
            child_count = current_item.childCount()
            desc_txt = current_item.text(ItemColumn.DESC)

            if child_count > 0:
                txt = str(child_count) + Msg.OVERLAY_PRESET[0] + ' - ' + type_desc
                if desc_txt != '':
                    txt += ' ' + desc_txt

                widget.info_overlay.display(txt, 1400, True)
            else:
                widget.info_overlay.display(type_desc, 1400, True)

    def add_text_to_variants_tree(self):

        def add_undo_command(this, items):
            if items:
                AddRemoveItemsCommand.add(this.ui.treeWidget_Variants, items, txt='Varianten erstellen')

        # Add instance
        add_variant_to_tree = add_variant(self.ui, self.ui.treeWidget_Variants)
        undo_items = []

        # Get text from Variant Set field
        variant_set_str = self.ui.plainTextEdit_addVariant_Setname.text()
        self.ui.plainTextEdit_addVariant_Setname.clear()

        # Debug functionality
        if variant_set_str == 'ShowExceptionButton':
            self.ui.exceptionBtn.show()
            return
        elif variant_set_str == 'HideExceptionButton':
            self.ui.exceptionBtn.hide()
            return

        # Get text from Variant field
        variant_str = self.ui.plainTextEdit_addVariant_Variant.text()
        # Set to placeholder text if left empty
        if variant_str == '':
            variant_str = self.ui.plainTextEdit_addVariant_Variant.placeholderText()
        self.ui.plainTextEdit_addVariant_Variant.clear()

        # Text contains semicolons, guess as old RenderKnecht Syntax: "variant state;"
        if ';' in variant_set_str:
            for var in variant_set_str.split(';'):
                var = var.split(' ', 2)
                if var[0] != '':
                    if len(var) >= 2:
                        if var[1] != '':
                            new_item = add_variant_to_tree.add_text(var[0], var[1])
                            undo_items.append(new_item)

            add_undo_command(self, undo_items)
            return

        # Text contains new line \n and or carriage return \n characters, replace with spaces
        if '\r\n' in variant_set_str:
            variant_set_str = variant_set_str.replace('\r\n', ' ')
        if '\n' in variant_set_str:
            variant_set_str = variant_set_str.replace('\n', ' ')

        # Text contains spaces, create multiple lines
        if ' ' in variant_set_str:
            for variant in variant_set_str.split(' '):
                if variant != '':
                    new_item = add_variant_to_tree.add_text(variant, variant_str)
                    undo_items.append(new_item)

            add_undo_command(self, undo_items)
            return

        # Get placeholder text if field is empty
        if variant_set_str == '':
            variant_set_str = self.ui.plainTextEdit_addVariant_Setname.placeholderText()
        if variant_str == '':
            variant_str = self.ui.plainTextEdit_addVariant_Variant.placeholderText()

        # Add tree item and sort order
        new_item = add_variant_to_tree.add_text(variant_set_str, variant_str)
        undo_items.append(new_item)

        # Undo command
        if undo_items:
            add_undo_command(self, undo_items)

    def sort_all_headers_event(self, event):
        tree_setup_header_format(
            [self.ui.treeWidget_DestPreset, self.ui.treeWidget_SrcPreset, self.ui.treeWidget_Variants,
                self.ui.treeWidget_render])

    def dg_resize_viewer(self, *args):
        """ Resize DeltaGen Viewer """
        if args:
            LOGGER.debug('Resize Viewer args: %s', args)

        SendToDeltaGen.viewer_size = self.ui.comboBox_ViewerSize.currentText()
        knechtSettings.dg['viewer_size'] = self.ui.comboBox_ViewerSize.currentText()

        self.deltagen_send_instance.resize_viewer()

    def dg_estimate_render_timer(self):
        """ Update estimated render time """
        if self.ui.treeWidget_render.topLevelItemCount() > 0:
            self.deltagen_render_instance.collect_render_settings(skip_variants=True)

    def dg_send(self):
        self.deltagen_send_instance.create_thread()

    def dg_render(self):
        self.deltagen_render_instance.create_thread()

    def end_dg_threads(self):
        self.deltagen_send_instance.end_thread()
        self.deltagen_render_instance.end_thread()

    def dg_set_viewer_color(self, color):
        SendToDeltaGen.viewer_bgr_color = color
        knechtSettings.dg['viewer_bgr_color'] = color.rgba()
        LOGGER.debug('Viewer background color setting saved: %s', color.rgba())
        self.deltagen_render_instance.set_viewer_color()

    def exit_preset_editor(self):
        LOGGER.debug('File > Exit menu selected.')

        if self.deltagen_render_instance.thread_running() or self.deltagen_send_instance.thread_running():
            LOGGER.warning('Detected running operation, can not quit application!')

            # Threads running while close event, ask to abort
            answer = QtWidgets.QMessageBox.critical(self.ui, Msg.APP_EXIT_WHILE_THREAD_TITLE,
                Msg.APP_EXIT_WHILE_THREAD_RUNNING, QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Abort)

            if answer == QtWidgets.QMessageBox.Abort:
                LOGGER.warning('User was smart enough to abort close event.')
                return

        # Warn for unsaved changes
        save_file = False
        if self.menu.save_mgr.save_file:
            save_file = Path(self.menu.save_mgr.save_file).name

        answer = self.ui.unsaved_changes(save_file)

        if answer == QtWidgets.QMessageBox.Cancel:
            return

        if answer == QtWidgets.QMessageBox.Yes:
            save = self.menu.file_save()

            if not save:
                return

        # Disable tree widgets before session save
        for widget in self.ui.tree_widget_list:
            widget.setEnabled(False)

        # Save current session
        self.session.save_session()

        self.ui.end_threads()
        self.ui.close()

        self.end_dg_threads()

        run_exe_updater(self.ui)
        self.quit_timer.timeout.connect(self.quit)
        self.quit_timer.start()
        # self.quit()

    class ClearTree:

        def __init__(self, widget, app, unset_save_file=False):
            self.widget = widget
            self.app = app
            self.unset_save_file = unset_save_file

        def dbl_click(self, event):
            if not self.clear():
                event.ignore()
                return

            event.accept()

        def clear(self):
            if self.unset_save_file:
                LOGGER.debug('Clear tree is unsetting save file.')
                self.app.menu.save_mgr.save_file = ''
                self.app.ui.unsaved_changes_present = False
                self.app.ui.set_window_title('')

            if self.widget.topLevelItemCount() == 0:
                return False

            clr_command = self.ClearCommand(self.widget, self.app)
            self.widget.undo_stack.push(clr_command)
            self.widget.undo_stack.setActive(True)

        class ClearCommand(QtWidgets.QUndoCommand):

            def __init__(self, widget, app, *__args):
                super().__init__(*__args)
                self.widget, self.app = widget, app
                self.widget_content = []

                # Collect all top level items at initial command call
                self.item_list = self.widget.findItems('*', QtCore.Qt.MatchWildcard)

                # Undo Text
                widget_name = app.ui.get_tree_name(self.widget)
                self.setText(widget_name + ' leeren')

            def redo(self):
                for item in self.item_list:
                    # Get index of current item
                    index = self.widget.indexOfTopLevelItem(item)
                    # Take from tree and store
                    removed_item = self.widget.takeTopLevelItem(index)
                    # Store item and index
                    self.widget_content.append((index, removed_item))
                    # delete item
                    del item

                self.widget.missing_ids = set()
                self.app.ui.sort_tree_widget.sort_all(widget=self.widget)
                self.widget.info_overlay.display_exit()

            def undo(self):
                # Find current content
                current_index = self.widget.topLevelItemCount()
                # Insert old tree
                for widget_content in self.widget_content:
                    index, item = widget_content
                    index = current_index + index
                    self.widget.insertTopLevelItem(index, item)
