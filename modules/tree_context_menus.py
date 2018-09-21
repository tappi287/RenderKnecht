"""
tree_context_menus for py_knecht. Provides context functioniality.

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
import copy
from functools import partial

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QBrush, QColor

from modules.knecht_log import init_logging
from modules.app_globals import Itemstyle, ItemColumn
from modules.app_strings import Msg, QobMsg
from modules.knecht_xml import XML
from modules.tree_methods import delete_command, deep_copy_items, add_selected_childs_as_top_level
from modules.tree_methods import lead_zeros, add_top_level_item, render_settings_combo_box
from modules.tree_methods import RENDER_SETTING_ITEM_FLAGS, update_tree_ids, AddRemoveItemsCommand
from modules.tree_methods import TOP_LEVEL_ITEM_FLAGS, VAR_LEVEL_ITEM_FLAGS, RENDER_PRESET_ITEM_FLAGS

LOGGER = init_logging(__name__)


def add_context_action(menu, action_call, icon_type, desc='Description',
                       inactive_widgets=list(), active_widgets=list(),
                       action_parent=None):
    if not action_parent:
        action_parent = menu

    new_action = QtWidgets.QAction(desc, action_parent)

    if icon_type:
        new_action.setIcon(menu.ui.icon[icon_type])

    new_action.triggered.connect(action_call)

    action_parent.addAction(new_action)

    # Black or White Filter context functionality to certain widgets
    if active_widgets:
        new_action.setEnabled(False)
    elif inactive_widgets:
        new_action.setEnabled(True)

    if menu.parent in inactive_widgets:
        new_action.setEnabled(False)

    if menu.parent in active_widgets:
        new_action.setEnabled(True)

    return new_action


class JobManagerContextMenu(QtWidgets.QMenu):
    cancel_job = QtCore.pyqtSignal(object)
    move_job = QtCore.pyqtSignal(object, bool)
    force_psd = QtCore.pyqtSignal(object)

    def __init__(self, widget, ui):
        super(JobManagerContextMenu, self).__init__(widget)
        self.widget, self.ui = widget, ui

        add_context_action(self, self.cancel_job_item, Itemstyle.MAIN['close'], desc='Job abbrechen')
        add_context_action(self, self.force_psd_creation, Itemstyle.MAIN['reset_state'],
                           desc='PSD Erstellung erzwingen.')
        add_context_action(self, self.open_output_dir, Itemstyle.MAIN['folder'], desc='Ausgabe Verzeichnis öffnen')
        add_context_action(self, self.remove_render_file, Itemstyle.MAIN['trash'], desc='Maya Rendering Szene löschen')
        add_context_action(self, self.move_job_top, Itemstyle.TYPES['options'], desc='An den Anfang der Warteschlange')
        add_context_action(self, self.move_job_back, Itemstyle.TYPES['options'], desc='An das Ende der Warteschlange')

        self.widget.installEventFilter(self)

    def get_item(self):
        if len(self.widget.selectedItems()) > 0:
            return self.widget.selectedItems()[0]

    def cancel_job_item(self):
        item = self.get_item()

        if item:
            self.cancel_job.emit(item)

    def force_psd_creation(self):
        item = self.get_item()

        if item:
            self.force_psd.emit(item)

    def open_output_dir(self):
        item = self.get_item()

        if item:
            self.widget.manager_open_item(item)

    def remove_render_file(self):
        item = self.get_item()

        if item:
            self.widget.manager_delete_render_file(item)

    def move_job_top(self):
        self.__move_job(True)

    def move_job_back(self):
        self.__move_job(False)

    def __move_job(self, to_top):
        item = self.get_item()

        if item:
            self.move_job.emit(item, to_top)

    def eventFilter(self, obj, event):
        if obj is self.widget:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.popup(event.globalPos())
                return True

        return False


class WizardPresetContextMenu(QtWidgets.QMenu):
    def __init__(self, widget, wizard, ui):
        super(WizardPresetContextMenu, self).__init__(widget)
        self.widget, self.wizard, self.ui = widget, wizard, ui

        add_context_action(self, self.clear_preset, Itemstyle.TYPES['reset'], desc='Alle Optionen entfernen')

        add_context_action(self, self.delete_action, Itemstyle.MAIN['close'], desc='Entferne Selektierte\tEntf')

        self.widget.installEventFilter(self)

    def delete_action(self):
        """ Delete selected items """
        self.wizard.delete_preset_items(self.widget, self.wizard)

    def clear_preset(self):
        """ Delete all optional content from Preset Tree """
        if self.ui.question_box(QobMsg.clear_preset_title, QobMsg.clear_preset_msg, parent=self.wizard):
            return

        self.wizard.delete_all_preset_items(self.widget, self.wizard)

    def eventFilter(self, obj, event):
        if obj is self.widget:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.popup(event.globalPos())
                return True

        return False


class WizardPresetSourceContext(QtWidgets.QMenu):
    def __init__(self, widget, wizard_page, wizard):
        super(WizardPresetSourceContext, self).__init__(widget)
        self.widget, self.wizard_page, self.ui, self.wizard = widget, wizard_page, wizard.ui, wizard

        add_context_action(self, self.exclude_pr_family, Itemstyle.MAIN['checkmark'],
                           desc='Option bei automagischer Befüllung einschließen')

        add_context_action(self, self.include_pr_family, Itemstyle.MAIN['close'],
                           desc='Option von automagischer Befüllung ausschließen')

        self.widget.installEventFilter(self)

    def exclude_pr_family(self):
        """ Exclude selected items from auto fill """
        self.wizard_page.context_rem_used_pr(self.widget.selectedItems(), self.wizard.context_excluded_pr_families)

    def include_pr_family(self):
        """ Include selected items in auto fill """
        self.wizard_page.context_add_used_pr(self.widget.selectedItems(), self.wizard.context_excluded_pr_families)

    def eventFilter(self, obj, event):
        if obj is self.widget:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.popup(event.globalPos())
                return True

        return False


class SelectionContextMenu(QtWidgets.QMenu):
    """
        Creates a context menu for provided parent QTreeWidget
        which selects or deselects all items
        or checks the items if checkable set to True / not set
    """
    all_deselected = QtCore.pyqtSignal()

    def __init__(self, parent, ui, checkable: bool = True):
        super().__init__()
        self.parent = parent
        self.checkable = checkable

        # Select all
        select_all = QtWidgets.QAction('Alle auswählen', self)
        select_all.triggered.connect(self.select_all_items)
        select_all.setIcon(ui.icon[Itemstyle.TYPES['options']])
        self.addAction(select_all)

        # Select None
        select_none = QtWidgets.QAction('Alle abwählen', self)
        select_none.triggered.connect(self.select_no_items)
        self.addAction(select_none)

        # Select selected
        if checkable:
            selected = QtWidgets.QAction('Selektierte auswählen', self)
            selected.triggered.connect(self.selected_items)
            selected.setIcon(ui.icon[Itemstyle.TYPES['render_preset']])
            self.addAction(selected)

        self.parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.popup(event.globalPos())
                return True

        return False

    def select_all_items(self):
        items = self.parent.findItems('*', QtCore.Qt.MatchWildcard | QtCore.Qt.MatchRecursive)
        self.check_items(items, True)

    def select_no_items(self):
        self.all_deselected.emit()

        if not self.checkable:
            self.parent.clearSelection()
            return

        items = self.parent.findItems('*', QtCore.Qt.MatchWildcard | QtCore.Qt.MatchRecursive)
        self.check_items(items, False)

    def selected_items(self):
        items = self.parent.selectedItems()
        self.check_items(items, True)

    def check_items(self, items, check=True):
        for item in items:
            if not item.isHidden():
                if self.checkable:
                    if check:
                        item.setCheckState(0, QtCore.Qt.Checked)
                    else:
                        item.setCheckState(0, QtCore.Qt.Unchecked)
                else:
                    item.setSelected(True)


class TreeContextMenu(QtWidgets.QMenu):
    """ Creates a context menu for provided parent widget """
    purple = QBrush(QColor(*Itemstyle.COLOR['PURPLE']), QtCore.Qt.SolidPattern)
    yellow = QBrush(QColor(*Itemstyle.COLOR['YELLOW']), QtCore.Qt.SolidPattern)
    cyan = QBrush(QColor(*Itemstyle.COLOR['CYAN']), QtCore.Qt.SolidPattern)
    grey = QBrush(QColor(*Itemstyle.COLOR['GREY']), QtCore.Qt.SolidPattern)
    darkgrey = QBrush(QColor(*Itemstyle.COLOR['DARKGREY']), QtCore.Qt.SolidPattern)

    render_preset_count = 0

    # noinspection PyUnresolvedReferences
    def __init__(self, parent, ui):
        super(TreeContextMenu, self).__init__()
        self.parent = parent
        self.ui = ui
        self.preset_count = 0
        self.render_widgets = []
        self.xmlTagDict = XML.xmlTagDict

        # Shortcut
        self.add = self.add_menu_action

        # -----------------------
        # Create Render preset
        self.render_preset_action = self.add(self.create_render_preset, Itemstyle.TYPES['render_preset'],
                                             'Render Preset aus Selektion erstellen',
                                             active_widgets=[self.ui.treeWidget_DestPreset])

        # Create Preset from selected
        self.add(self.create_preset_from_selected, Itemstyle.TYPES['preset'], 'Preset aus Selektion erstellen')

        # Create masked Preset from selected presets
        if self.parent is self.ui.treeWidget_DestPreset:
            self.add(self.create_masked_presets_from_selected, Itemstyle.TYPES['preset_mask'],
                     'Masken Presets aus selektierten Presets erstellen')

        # -----------------------
        # Create menu
        self.create_menu = None
        self.create_creation_menu()
        if self.parent is not self.ui.treeWidget_DestPreset:
            self.create_menu.setEnabled(False)

        # Copy selected
        add_copy = self.add(self.copy_to_dest, Itemstyle.TYPES['copy'], 'Markierte in Benutzer Presets kopieren')
        if self.parent in [self.ui.treeWidget_SrcPreset, self.ui.treeWidget_Variants]:
            self.addAction(add_copy)
        else:
            self.removeAction(add_copy)

        # Variants Tree Shortcuts
        if self.parent is self.ui.treeWidget_Variants:
            self.addSeparator()
            self.add_var_preset = self.add(self.create_preset_from_variants, Itemstyle.TYPES['preset'],
                                           'Preset aus Varianten erstellen und Baum leeren\tStrg+Links')
            self.add_var = self.add(self.copy_variants_to_dest, Itemstyle.TYPES['copy'],
                                    'Varianten in Benutzer Presets kopieren und Baum leeren\tAlt+Links')

            self.add(self.clear_variants, Itemstyle.MAIN['trash'], 'Varianten Baum leeren\tStrg+Entf')

        self.addSeparator()

        # -----------------------
        # Copy to clipboard
        self.copy_clip = self.add(self.copy_to_clipboard, Itemstyle.MAIN['copy'], 'Kopieren\tStrg+C')

        # Cut to clipboard
        self.cut_clip = self.add(self.cut_to_clipboard, Itemstyle.MAIN['cut'], 'Ausschneiden\tStrg+X',
                                 inactive_widgets=[self.ui.treeWidget_SrcPreset, self.ui.treeWidget_render])

        # Paste from clipboard
        self.paste_clip = self.add(self.paste_from_clipboard, Itemstyle.MAIN['paste'], 'Einfügen\tStrg+V',
                                   inactive_widgets=[self.ui.treeWidget_SrcPreset, self.ui.treeWidget_render])

        self.addSeparator()

        # -----------------------
        # Report items that did not changed switch state
        self.add(self.report_variants, Itemstyle.TYPES['options'], 'Nicht geschaltete Varianten berichten(Log)',
                 active_widgets=[self.ui.treeWidget_DestPreset, self.ui.treeWidget_Variants])

        # Show and select items that match selected reference or preset
        self.show_ref = self.add(self.show_references, Itemstyle.MAIN['link_intact'],
                                 'Referenzen der Selektion zeigen\tCtrl+R')

        # -----------------------
        # Row color menu
        self.color_menu = self.addMenu('Zeilenfarbe: ')
        self.color_menu.setIcon(self.ui.icon[Itemstyle.MAIN['paint']])

        # Reset item background / switch state
        self.add(self.reset_variants, Itemstyle.MAIN['reset_state'],
                 'Schaltstatus Indikatoren/Alle Zeilenfarben zurücksetzen', action_parent=self.color_menu)

        # Reset selected columns
        self.add(self.color_selected_rows, Itemstyle.MAIN['c_darkgrey'], 'Farben markierter Zeilen zurücksetzen',
                 action_parent=self.color_menu)

        # Color row purple
        self.add(partial(self.color_selected_rows, self.purple), Itemstyle.MAIN['c_purple'], 'Violett',
                 action_parent=self.color_menu)
        # Color row yellow
        self.add(partial(self.color_selected_rows, self.yellow), Itemstyle.MAIN['c_yellow'], 'Gelb',
                 action_parent=self.color_menu)
        # Color row cyan
        self.add(partial(self.color_selected_rows, self.cyan), Itemstyle.MAIN['c_cyan'], 'Cyan',
                 action_parent=self.color_menu)
        # Color row grey
        self.add(partial(self.color_selected_rows, self.grey), Itemstyle.MAIN['c_grey'], 'Grau',
                 action_parent=self.color_menu)
        # Color row dark grey
        self.add(partial(self.color_selected_rows, self.darkgrey), Itemstyle.MAIN['c_darkgrey'], 'Dunkelgrau',
                 action_parent=self.color_menu)

        self.addSeparator()

        # -----------------------
        # Delete selected items
        self.add(self.delete_func, Itemstyle.MAIN['close'], 'Lösche Selektierte\tEntf',
                 inactive_widgets=[self.ui.treeWidget_SrcPreset])

        # Install context menu event filter
        self.parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent:
            if event.type() == QtCore.QEvent.ContextMenu:
                self.popup(event.globalPos())
                return True

            return False
        return False

    def add_menu_action(self, action_call, icon_type, desc='Description', inactive_widgets=list(),
                        active_widgets=list(), action_parent=None):
        return add_context_action(self, action_call, icon_type, desc, inactive_widgets, active_widgets, action_parent)

    def delete_func(self):
        delete_command(self.parent)

    def color_reset(self):
        self.color_selected_rows(None)

    def color_selected_rows(self, bgr_color=None):
        __items = self.parent.selectedItems()

        if not __items:
            return

        for __item in __items:
            for __col in range(0, __item.columnCount()):
                if not bgr_color:
                    # Reset background
                    __item.setData(__col, QtCore.Qt.BackgroundRole, None)
                else:
                    # Set background color
                    __item.setBackground(__col, bgr_color)

    def cut_to_clipboard(self):
        """ Copy and delete selected items """
        if not self.parent.selectedItems():
            self.parent.info_overlay.display(Msg.NOTHING_TO_COPY, 1500)
            return

        self.copy_to_clipboard()
        self.delete_func()

    def copy_to_clipboard(self):
        """ Copy selected items to clipboard """
        copy_items = self.parent.selectedItems()

        if not copy_items:
            self.parent.info_overlay.display(Msg.NOTHING_TO_COPY, 1500)
            return

        self.parent.info_overlay.display(str(len(copy_items)) + Msg.COPIED, 2500, immediate=True)
        self.ui.clipboard = deep_copy_items(copy_items)
        self.ui.clipboard_src = self.parent

    def paste_from_clipboard(self):
        """ Paste items from clipboard """
        # Copy from clipboard to keep clipboard content
        paste_items = copy.copy(self.ui.clipboard)

        if not paste_items:
            self.parent.info_overlay.display(Msg.NOTHING_TO_PASTE, 1500)
            return

        # Overlay display to widget center
        self.parent.overlay.generic_center()

        # Paste to Variants as children
        if self.parent is self.ui.treeWidget_Variants:
            add_selected_childs_as_top_level(paste_items, self.parent, self.ui, src_is_itemlist=True)
            return

        dest = self.parent.selectedItems()

        if not dest:
            # Nothing selected, paste to widget
            dest = self.parent
        else:
            # Paste to items
            dest_items = []

            # Items selected, paste item
            for dest_item in dest:
                # Make sure we paste to Preset or Render Preset
                if dest_item.UserType in [1000, 1003]:

                    self.ui.add_selected_top_level_items.Run(paste_items, dest_item,
                                                             src_is_itemlist=True)
                    dest_items.append(dest_item)

                elif dest_item not in dest_items:
                    if dest_item.parent():
                        dest_item = dest_item.parent()

                        if dest_item.UserType in [1000, 1003]:
                            self.ui.add_selected_top_level_items.Run(paste_items, dest_item,
                                                                     src_is_itemlist=True)
                            dest_items.append(dest_item)

            return

        self.ui.add_selected_top_level_items.Run(paste_items, dest,
                                                 src_is_itemlist=True)

    def copy_to_dest(self):
        """ Copy items to destination widget """
        dest_tree = self.ui.treeWidget_DestPreset
        self.ui.add_selected_top_level_items.Run(self.parent, dest_tree)

    def show_references(self):
        """ Show and select items that match selected reference or preset """
        selected_items = self.parent.selectedItems()

        if self.parent is self.ui.treeWidget_Variants:
            dest_tree = self.ui.treeWidget_DestPreset
        else:
            dest_tree = self.parent

        for item in selected_items:
            item.setSelected(False)
            item_id = item.text(ItemColumn.ID)
            ref_id = item.text(ItemColumn.REF)

            # Show references
            if item_id:
                ref_items = dest_tree.findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.REF)

                for ref_item in ref_items:
                    ref_item.setSelected(True)
                    if ref_item.parent():
                        ref_item.parent().setExpanded(True)
                    dest_tree.scrollToItem(ref_item)

            if ref_id:
                preset_items = dest_tree.findItems(ref_id, QtCore.Qt.MatchRecursive, ItemColumn.ID)

                for preset in preset_items:
                    preset.setSelected(True)
                    dest_tree.scrollToItem(preset)

    def create_render_preset(self):
        """ Create new Render Preset with default Settings """
        self.render_preset_count += 1
        # Item attributes
        order = lead_zeros(self.parent.topLevelItemCount() + 1)
        name = 'Render_Preset_' + str(self.render_preset_count)
        preset_type = 'render_preset'
        render_preset_item = add_top_level_item(self.parent, [order, name, '', preset_type], RENDER_PRESET_ITEM_FLAGS,
                                                1003)

        # Add default settings
        # order, name, value
        desc = 'Setzt das globale Sampling Level. Benutzt Clamping Einstellungen der geladenen Szene!'
        sampling = ['000', 'Anti-Aliasing Samples', None, 'sampling', '', '', desc]
        desc = 'Setzt die Ausgabe Dateiendung. HDR wird als 8bit ausgegeben und ' \
               'berücksichtigt Viewport Display Adaption.'
        file_extension = ['001', 'Datei Erweiterung', None, 'file_extension', '', '', desc]
        desc = 'Auflösung kann auch manuell, mit einem Leerzeichen getrennt, eingegeben ' \
               'werden: X Y'
        resolution = ['002', 'Auflösung', None, 'resolution', '', '', desc]

        for item_values in [sampling, file_extension, resolution]:
            item = QtWidgets.QTreeWidgetItem(render_preset_item, item_values)
            self.render_widgets.append(render_settings_combo_box(item))

            item.UserType = 1004
            item.setFlags(RENDER_SETTING_ITEM_FLAGS)

        self.add_selected_items(render_preset_item, 3, True)
        self.parent.clearSelection()
        render_preset_item.setSelected(True)
        self.ui.sort_tree_widget.sort_current_level(render_preset_item, self.parent)

    def create_masked_presets_from_selected(self):
        # Collect selected presets
        preset_ls = []

        for item in self.parent.selectedItems():
            if item.UserType != 1000:
                # Skip everything but User Presets
                continue
            preset_ls.append(item)

        for preset in preset_ls:
            # Clear selection and select current preset only
            self.parent.clearSelection()
            preset.setSelected(True)

            # Define preset name
            name = preset.text(ItemColumn.NAME) + '_Mask'

            # Create preset and add selected preset
            self.create_preset_from_selected(True, True, preset_name=name, skip_name_count=True)

    def create_preset_from_selected(self, action_bool, add_selected=True, **kwargs):
        """ Create new User Preset from selected items """
        self.preset_count += 1
        dest_tree = self.ui.treeWidget_DestPreset

        # Get kwargs attributes
        options = {
            # Preset Name
            'preset_name': 'User_Preset_',  # Preset Type
            'preset_type': 'preset', 'preset_items': [],  # Preset child items as list of tuples (type, name, value)
            'has_id': True, 'skip_name_count': False
            }

        options.update(kwargs)

        # Item attributes
        order = lead_zeros(dest_tree.topLevelItemCount() + 1)

        if not options['skip_name_count']:
            name = options['preset_name'] + lead_zeros(self.preset_count)
        else:
            name = options['preset_name']

        preset_type = options['preset_type']
        item_user_type = 1000  # Preset
        if preset_type == 'seperator':
            name = ' '
            item_user_type = 1005
            LOGGER.debug('Creating seperator.')

        item_id = ''
        if options['has_id']:
            item_id = update_tree_ids(dest_tree, self.ui, '0', self.ui.treeWidget_SrcPreset)

        preset_item = add_top_level_item(dest_tree, [order, name, '', preset_type, '', item_id],
                                         TOP_LEVEL_ITEM_FLAGS,
                                         item_user_type)

        # Create preset sub items / variants
        for item_tuple in options['preset_items']:
            item_type = item_tuple[0]
            item_values = item_tuple[1:]

            item = QtWidgets.QTreeWidgetItem(preset_item, list(item_values))
            item.UserType = self.xmlTagDict[item_type]
            item.setFlags(VAR_LEVEL_ITEM_FLAGS)

        if add_selected:
            self.add_selected_items(preset_item)
        else:
            # Undo command
            if preset_item:
                AddRemoveItemsCommand.add(dest_tree, [preset_item], txt='Preset erstellen')
        self.ui.sort_tree_widget.sort_all(dest_tree)

    """
    def create_reference_presets_from_selected(self):
        # Create reference images presets from selected items
        # Worker class instance
        collect = CollectOptions(self.ui)

        # Collect selected items and return True if mandatory items present
        if not collect.collect_items():
            self.parent.info_overlay.display_confirm(Msg.REF_IMG_ERR,
                                                     ('[X]', None))
            return

        # Create preset items
        collect.create_presets()
    """

    def add_selected_items(self, parent_item, order: int = 0, only_references: bool = False, new_items=False):
        if not new_items:
            new_items = deep_copy_items(self.parent.selectedItems())

        for item in new_items:
            if item.UserType == 1001 and not only_references:
                # Add selected variants
                order += 1
                item.setText(ItemColumn.ORDER, lead_zeros(order))
                parent_item.addChild(item)

            elif item.UserType == 1002:
                # Add selected references
                order += 1
                item.setText(ItemColumn.ORDER, lead_zeros(order))
                parent_item.addChild(item)

            elif item.UserType == 1000:
                # Add selected presets as references
                order += 1
                ref_items = self.ui.find_reference_items.check_reference(order, item, parent_item)

        # Undo command
        undo_items = [parent_item]
        if undo_items:
            AddRemoveItemsCommand.add(parent_item.treeWidget(), undo_items, txt='erstellen')

        self.ui.sort_tree_widget.sort_current_level(parent_item)

    def copy_variants_to_dest(self):
        item = None

        for item in self.ui.treeWidget_Variants.findItems('*', QtCore.Qt.MatchWildcard):
            item.setSelected(True)

        if item:
            self.ui.add_selected_top_level_items.Run(self.parent, self.ui.treeWidget_DestPreset)

        self.parent.clear_tree()

    def create_preset_from_variants(self):
        item = None

        for item in self.ui.treeWidget_Variants.findItems('*', QtCore.Qt.MatchWildcard):
            item.setSelected(True)

        if item:
            self.create_preset_from_selected(True)

        self.parent.clear_tree()

    def clear_variants(self):
        self.parent.clear_tree()

    def create_creation_menu(self, widget: QtWidgets.QMenu = None):
        """ Creates Creation-Menu for given menu widget or current menu instance(self) """
        if widget is not None:
            self.create_menu = widget
        else:
            self.create_menu = self.addMenu('Erstellen: ')
        """
        # Create reference images presets
        action_name = 'Referenz Bild Presets aus Selektion erstellen\tErstellt Referenzpresets aus Selektion in ' \
                      'Benutzer Vorgaben'
        add_reference_presets = QtWidgets.QAction(action_name, self)
        add_reference_presets.triggered.connect(self.create_reference_presets_from_selected)
        add_reference_presets.setIcon(self.ui.icon[Itemstyle.TYPES['preset_ref']])
        self.create_menu.addAction(add_reference_presets)
        """

        self.create_menu.ui = self.ui

        # Create Render preset
        action_name = 'Render Preset erstellen\tEnthät User Presets, Viewsets und Rendereinstellungen'
        add_render_preset = QtWidgets.QAction(action_name, self)
        add_render_preset.triggered.connect(self.create_render_preset)
        add_render_preset.setIcon(self.ui.icon[Itemstyle.TYPES['render_preset']])
        self.create_menu.addAction(add_render_preset)

        # Add preset
        add_preset_selected = QtWidgets.QAction('User Preset\tEnthält Varianten und/oder Referenzen', self)
        add_preset_selected.triggered.connect(self.create_preset_from_selected)
        add_preset_selected.setIcon(self.ui.icon[Itemstyle.TYPES['preset']])
        self.create_menu.addAction(add_preset_selected)

        # Add Viewset
        add_viewset = QtWidgets.QAction('Viewset\tEnthält **eine** Shot Variante', self)
        preset_item_list = [('variant', '000', '#_Shot', 'Shot_05', '', '', '', 'Schalter des Shot Varianten Sets')]
        add_viewset.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='Viewset_', preset_type='viewset',
                    preset_items=preset_item_list))
        add_viewset.setIcon(self.ui.icon[Itemstyle.TYPES['viewset']])
        self.create_menu.addAction(add_viewset)

        # Add masked viewset
        add_masked_view = QtWidgets.QAction('Maskiertes Viewset\tEnthält **eine** Shot '
                                            'Variante und einen Pfad zur Maske', self)
        shot = ('variant', '000', '#_Shot', 'Shot_05_Lightplanes', '', '', '', 'Schalter des Shot Varianten Sets')
        mask = ('variant', '001', 'Pfad zum Maskenordner angeben...', 'Button', 'mask_path', '', '',
                'Pfad zur Maskenbilddatei.')
        preset_item_list = [shot, mask]
        add_masked_view.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='Masked_Viewset_',
                    preset_type='viewset_mask', preset_items=preset_item_list))
        add_masked_view.setIcon(self.ui.icon[Itemstyle.TYPES['viewset_mask']])
        self.create_menu.addAction(add_masked_view)

        # Add Reset
        add_reset = QtWidgets.QAction('Reset\tVarianten für eine Resetschaltung', self)
        reset_on = (
            'variant', '000', 'reset', 'on', '', '', '', 'Sollte einen im Modell vorhanden Reset Schalter betätigen')
        reset_off = (
            'variant', '001', 'reset', 'off', '', '', '', 'Sollte einen im Modell vorhanden Reset Schalter betätigen')
        reset_options = ('variant', '002', 'RTTOGLRT', 'on', '', '', '',
                         'Benötigte Optionen müssen eventuell nach dem Reset erneut geschaltet werden.')
        preset_item_list = [reset_on, reset_off, reset_options]
        add_reset.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='Reset_', preset_type='reset',
                    preset_items=preset_item_list))
        add_reset.setIcon(self.ui.icon[Itemstyle.TYPES['reset']])
        self.create_menu.addAction(add_reset)

        # Add trim line
        add_trim = QtWidgets.QAction('Trimline Preset\tVarianten für eine Serienschaltung', self)
        preset_item_list = [('variant', '000', 'Motorschalter', 'on', '', '', '', 'Variante des Modells'),
                            ('variant', '001', 'Serien_Optionen', 'on', '', '', '', 'Varianten der Serienumfänge')]
        add_trim.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='OEM Derivat Form Trimline Motor ',
                    preset_type='trim_setup', preset_items=preset_item_list))
        add_trim.setIcon(self.ui.icon[Itemstyle.TYPES['trim_setup']])
        self.create_menu.addAction(add_trim)

        # Add package
        add_package = QtWidgets.QAction('Paket Preset\tVarianten eines Pakets', self)
        preset_item_list = [('variant', '000', 'Paket_Variante', 'on', '', '', '', 'Varianten der Paket Option')]
        add_package.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='Paket ', preset_type='package',
                    preset_items=preset_item_list))
        add_package.setIcon(self.ui.icon[Itemstyle.TYPES['package']])
        self.create_menu.addAction(add_package)

        # Add fakom_setup
        add_fakom = QtWidgets.QAction('FaKom Serien Preset\tVarianten einer Serien Farbkombination', self)
        fakom_pr = ('variant', '000', 'XX_Farbschluessel', 'on', '', '', '', 'Zweistelliger Farbschluessel')
        fakom_sib = ('variant', '001', 'PRN_Sitzbezug', 'on', 'SIB', '', '', 'Sitzbezug Option')
        fakom_vos = ('variant', '002', 'PRN_Vordersitze', 'on', 'VOS', '', '', 'Sitzart Option')
        fakom_lum = ('variant', '003', 'PRN_Lederumfang', 'on', 'LUM', '', '', 'Lederpaket Option')
        preset_item_list = [fakom_pr, fakom_sib, fakom_vos, fakom_lum]
        add_fakom.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='FaKom Modell PR_SIB_VOS_LUM ',
                    preset_type='fakom_setup', preset_items=preset_item_list))
        add_fakom.setIcon(self.ui.icon[Itemstyle.TYPES['fakom_setup']])
        self.create_menu.addAction(add_fakom)

        # Add fakom_option
        add_fakom_opt = QtWidgets.QAction('FaKom optionales Preset\tVarianten einer Farbkombination', self)
        add_fakom_opt.triggered.connect(
            partial(self.create_preset_from_selected, True, False, preset_name='FaKom Modell PR_SIB_VOS_LUM Option ',
                    preset_type='fakom_option', preset_items=preset_item_list))
        add_fakom_opt.setIcon(self.ui.icon[Itemstyle.TYPES['fakom_option']])
        self.create_menu.addAction(add_fakom_opt)

        # Add seperator
        add_context_action(self.create_menu,
                           partial(self.create_preset_from_selected, True, False, preset_name=' ',
                                   preset_type='seperator', has_id=False),
                           Itemstyle.MAIN['empty'], 'Separator\tNicht-interagierbares Ordnungselement')

    def reset_variants(self):
        self.report_variants(True)

    def report_variants(self, reset_item_bg=False):

        def iterate_items(tree_items, reset_bg):
            report_msg = ''
            for item in tree_items:
                color_name = item.background(ItemColumn.NAME).color()
                # color_value = item.background(ItemColumn.VALUE).color()

                if color_name.red() > 0:
                    rgb = (color_name.red(), color_name.green(), color_name.blue())

                    if rgb == Itemstyle.COLOR['ORANGE']:
                        report_msg += item.text(ItemColumn.NAME) + ' ' + item.text(ItemColumn.VALUE) + '\n'

                    if reset_bg:
                        for __col in range(0, item.columnCount()):
                            item.setData(__col, QtCore.Qt.BackgroundRole, None)

            return report_msg

        if not reset_item_bg:
            LOGGER.info('Reporting items that did not change variant state when send to DeltaGen.')
        else:
            LOGGER.info('Reseting item backgrounds.')

        report = ''

        # Destination Tree Widget
        report += iterate_items(
            self.ui.treeWidget_DestPreset.findItems('*', QtCore.Qt.MatchRecursive | QtCore.Qt.MatchWildcard,
                                                    ItemColumn.NAME), reset_item_bg)

        # Variants Tree Widget
        report += iterate_items(
            self.ui.treeWidget_Variants.findItems('*', QtCore.Qt.MatchRecursive | QtCore.Qt.MatchWildcard,
                                                  ItemColumn.NAME), reset_item_bg)

        # Report to Log
        if not reset_item_bg:
            LOGGER.info('\n\n%s', report)
