"""
py_knecht QUB 9000 preset wizard, FaKom Page

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
from PyQt5 import QtWidgets, QtCore

from modules.knecht_log import init_logging
from modules.app_globals import WIZARD_PAGE_FAKOM, FAKOM_GRP_ITEM_FLAGS
from modules.app_strings import QobMsg
from modules.gui_preset_wizard_page_presets import PresetWizardPage
from modules.gui_preset_wizard_page_result import ResultWizardPage
from modules.gui_widgets import load_ui_file
from modules.tree_events import TreeKeyEvents
from modules.tree_context_menus import SelectionContextMenu
from modules.tree_methods import iterate_item_childs, deep_copy_items, style_database_preset
from modules.tree_methods import delete_tree_item_without_undo, create_unique_item_name, iterate_tree_widget_items_flat
from modules.tree_overlay import InfoOverlay
from modules.tree_filter_thread import filter_on_timer

LOGGER = init_logging(__name__)


class FakomWizardPage(QtWidgets.QWizardPage):
    """
        --- Preset Wizard Page ---
        Populate FaKom Tree and let the user select the items he wants.
    """
    count = 0

    save_display_delay = QtCore.QTimer()
    save_display_delay.setSingleShot(True)
    save_display_delay.setInterval(500)

    warn_display_delay = QtCore.QTimer()
    warn_display_delay.setSingleShot(True)
    warn_display_delay.setInterval(200)

    s_timer = QtCore.QTimer()
    s_timer.setSingleShot(True)
    s_timer.setInterval(300)

    clear_preset_pages = False
    clear_fakom_tree = False
    load_fakom_tree = False
    load_preset_page_content = False

    def __init__(self, parent):
        super(FakomWizardPage, self).__init__(parent)
        self.parent = parent
        self.selected_ids = set()
        self.ui, self.app = parent.ui, parent.app

        # Load page template
        load_ui_file(self, WIZARD_PAGE_FAKOM)

        self.setButtonText(QtWidgets.QWizard.BackButton, QobMsg.back_fakom)

        # Info Overlay
        self.fakomTree.info_overlay = InfoOverlay(self.fakomTree)
        self.treeWidget_Selected.info_overlay = InfoOverlay(self.treeWidget_Selected)

        # Add filter txt widgets as attribute
        self.fakomTree.filter_txt_widget = self.lineEditFilter
        # Connect text filter
        self.fakom_txt_filter = self.parent.TxtFiltering(
            self.parent.tree_filter_thread, self.fakomTree, column=[0], pattern=1)
        self.lineEditFilter.textChanged.connect(self.fakom_txt_filter.filter_txt)

        # Add Key events
        self.fakom_tree_keys = TreeKeyEvents(self.fakomTree, self.ui, self.app,
                                             wizard=True, no_edit=True)
        self.fakom_tree_keys.add_event_filter()

        # Selection context menu
        self.fakom_menu = SelectionContextMenu(self.fakomTree, self.ui, checkable=False)
        self.fakom_menu.all_deselected.connect(self.context_all_deselected)

        # Tree helpers
        self.iter_childs = iterate_item_childs(self.fakomTree)
        self.fakomTree.hideColumn(1)
        self.fakomTree.hideColumn(2)
        self.fakomTree.hideColumn(3)
        self.treeWidget_Selected.hideColumn(1)
        self.splitterSizes = self.treeSplitter.sizes()
        self.last_selection_size = 0

        # Selection update timer
        self.s_timer.timeout.connect(self.selection_changed)
        # Warning delay timer
        self.warn_display_delay.timeout.connect(self.warn_fakom)

        # Events
        self.fakomTree.itemSelectionChanged.connect(self.s_timer.start)
        self.treeWidget_Selected.itemClicked.connect(self.display_tree_item_clicked)
        self.checkBox_models.toggled.connect(self.list_by_model)
        self.checkBoxSort.toggled.connect(self.sort_btn_toggled)

    def initializePage(self):
        if self.load_fakom_tree:
            self.load_session()
        elif self.clear_fakom_tree:
            self.selected_ids = set()

        if self.clear_fakom_tree:
            LOGGER.debug('FaKom Page initialize.')
            self.clear_fakom_tree = False
            self.fakomTree.clear()
            self.create_fakom_items()

            # Hide Display Widget
            self.treeSplitter.setSizes([500, 0])

        self.fakomTree.setEnabled(True)

    def set_clear_fakom_tree(self):
        """ Receives source changed signal """
        self.clear_fakom_tree = True

    def set_load_session_selection(self):
        self.load_fakom_tree = True

    def set_load_preset_page_content(self):
        self.load_preset_page_content = True

    def isComplete(self):
        __items = self.get_selected_fakom_items()

        if __items:
            self.parent.fakom_presets = __items
            self.treeWidget_Selected.info_overlay.display_exit()
            return True
        else:
            return False

    def validatePage(self):
        if self.clear_preset_pages:
            self.remove_preset_pages()
            self.create_preset_pages()

            self.clear_preset_pages = False

        # Save session input
        self.parent.session_data_mgr.save_session()

        return True

    def load_session(self):
        LOGGER.debug('FaKom Tree loading %s selected items.', len(self.parent.fakom_tree_items))
        self.load_fakom_tree = False

        if not len(self.parent.fakom_tree_items):
            return

        for __i in self.parent.fakom_tree_items.iterfind('.//'):
            self.selected_ids.add(__i.get('id'))

    def load_session_preset_pages(self):
        dom_pg = self.parent.session_data_mgr.session_xml_dom['page']

        for page_id in self.parent.preset_pages_ids:
            page = self.parent.page(page_id)

            __search = f'./{dom_pg}[@id="{page_id}"]'
            __page_xml = self.parent.preset_page_content.find(__search)

            if __page_xml:
                page.load_xml_content = __page_xml

        self.load_preset_page_content = False

    def create_preset_pages(self):
        self.sort_fakom_presets()

        # Create preset wizard pages
        for __idx, preset in enumerate(self.parent.fakom_presets):
            __id = self.parent.currentId() + 1 + __idx

            __title = f'#{__idx:03d} - {preset.text(0)}'

            next_preset_page = PresetWizardPage(self.parent, __idx)
            self.parent.setPage(__id, next_preset_page)
            self.parent.page(__id).setTitle(__title)

            # Update Wizard propertys
            self.parent.preset_pages_ids = __id

        if self.load_preset_page_content:
            LOGGER.debug('Preparing load of Preset Page content.')
            self.load_session_preset_pages()

        # Add result page
        result_page = ResultWizardPage(self.parent)
        self.parent.setPage(__id + 1, result_page)

        LOGGER.debug('Created Preset Pages: %s', self.parent.preset_pages_ids)

    def remove_preset_pages(self):
        """ Clear all pages """
        __s = set()

        # Remove preset wizard pages
        while 1:
            __p_id = self.parent.nextId()
            if __p_id == -1:
                break

            self.parent.removePage(__p_id)
            __s.add(__p_id)

        # Clean up propertys
        del self.parent.preset_pages_ids
        del self.parent.used_pr_options

        # Update used PR options with Trimline and FaKom contents
        self.parent.add_preset_contents_to_used_pr()

        LOGGER.debug('Removed Preset Pages %s', __s)

    def display_session_saved(self):
        """ Will be called from parent """
        # Overlay message after delay
        self.save_display_delay.timeout.connect(self.display_session_saved_ovr)
        self.save_display_delay.start()

    def display_session_saved_ovr(self):
        self.fakomTree.info_overlay.display(QobMsg.saved_message, 6000, immediate=True)

    def warn_fakom_changes(self):
        self.warn_display_delay.start()

    def warn_fakom(self):
        def enable_tree():
            self.fakomTree.setEnabled(True)
            self.treeWidget_Selected.info_overlay.display_exit()

        self.fakomTree.setEnabled(False)

        __msg = QobMsg.warn_fakom_tree[0]
        __btn_label = QobMsg.warn_fakom_tree[1]

        self.treeWidget_Selected.info_overlay.display_confirm(
            __msg, (__btn_label, enable_tree), immediate=True)

        if self.treeSplitter.sizes()[1] == 0:
            if self.splitterSizes[1] > 0:
                self.treeSplitter.setSizes(self.splitterSizes)
            else:
                self.treeSplitter.setSizes([500, 200])

    def list_by_model(self):
        # Toggle list by model
        self.fakomTree.clear()
        self.create_fakom_items()

    def context_all_deselected(self):
        self.selected_ids = set()

    def sort_btn_toggled(self):
        self.last_selection_size = 0
        self.fakomTree.setEnabled(True)
        self.selection_changed()

    def sort_fakom_presets(self):
        """ Sort FaKom presets alphabetically """
        def sort_key(__i):
            return __i.text(0)

        if not self.checkBoxSort.isChecked():
            return

        __sorted_fakom_presets = []
        for item in sorted(self.parent.fakom_presets, key=sort_key):
            __sorted_fakom_presets.append(item)

        self.parent.fakom_presets = __sorted_fakom_presets

    def display_tree_item_clicked(self, item, column):
        """ Item in display Tree selected - jump to item in fakomTree """
        __i = self.fakomTree.findItems(item.text(0), QtCore.Qt.MatchRecursive, 0)

        if __i:
            self.fakomTree.scrollToItem(__i[0], QtWidgets.QAbstractItemView.PositionAtCenter)

    def update_display_tree(self):
        __num_items = len(self.parent.fakom_presets)

        if __num_items:
            # Show display widget
            if self.treeSplitter.sizes()[1] == 0:
                if self.splitterSizes[1] > 0:
                    LOGGER.debug('Setting saved splitter sizes: %s', self.splitterSizes)
                    self.treeSplitter.setSizes(self.splitterSizes)
                else:
                    self.treeSplitter.setSizes([500, 200])
        else:
            # Hide display widget
            self.splitterSizes = self.treeSplitter.sizes()
            self.treeSplitter.setSizes([self.splitterSizes[0], 0])

        self.treeWidget_Selected.clear()
        if __num_items > 0:
            __items = deep_copy_items(self.parent.fakom_presets)

            for __idx, __i in enumerate(__items):
                style_database_preset(__i, self.ui, hide=False, type_txt='preset_ref')
                self.treeWidget_Selected.insertTopLevelItem(__idx, __i)
                __i.setFlags(FAKOM_GRP_ITEM_FLAGS)

        info_txt = f'Presets {__num_items:03d} / {self.count:03d}'
        self.label_Selected.setText(info_txt)

    def update_preset_tree(self):
        """ Update FaKom preset tree appearance """
        def style_iter_parents(item):
            p = item.parent()
            if p and p.text(1) == 'group_item':
                style_database_preset(p, self.ui, hide=False, type_txt='checkmark')
                if p.parent():
                    style_iter_parents(p)

        # Display number of selected presets per model
        __preset_num_per_model = dict()

        # Iterate group items and it's childs
        for __i in self.fakomTree.findItems('group_item', QtCore.Qt.MatchRecursive, 1):
            style_database_preset(__i, self.ui, hide=False, type_txt='preset')

            # Iterate SIB group items
            if __i.text(2) == 'sib_item':
                style_database_preset(__i, self.ui, hide=False, type_txt='options')

                for __c in self.iter_childs.iterate_childs(__i):
                    __model = __c.text(2)

                    if __c.text(3):
                        style_database_preset(__c, self.ui, hide=False, type_txt=__c.text(3))
                    else:
                        style_database_preset(__c, self.ui, hide=False, type_txt='fakom_option')

                    if __c.isSelected():
                        style_database_preset(__c, self.ui, hide=False, type_txt='checkmark')
                        self.selected_ids.add(__c.text(1))

                        style_iter_parents(__c)

                        if __model not in __preset_num_per_model.keys():
                            __preset_num_per_model[__model] = 1
                        else:
                            __preset_num_per_model[__model] += 1

        for __m in __preset_num_per_model.keys():
            for __g in self.fakomTree.findItems(__m, QtCore.Qt.MatchExactly, 1):
                if not __g.text(3):
                    __g.setText(3, __g.text(0))

                __g.setText(0, f'{__g.text(3)} - {__preset_num_per_model[__m]:02d}')

    def get_selected_fakom_items(self):
        """ Return selected QTreeWidget items *including hidden items* """
        selected_items = list()

        for __i in self.fakomTree.findItems('sib_item', QtCore.Qt.MatchRecursive, 2):
            for __c in self.iter_childs.iterate_childs(__i):
                if __c.isSelected():
                    selected_items.append(__c)

        return selected_items

    def selection_changed(self):
        # buildin method does not return selected, hidden(filtered) items
        # __items = self.fakomTree.selectedItems()

        __items = self.get_selected_fakom_items()

        # Avoid selection signal for unselectable grouping items
        # who emit selectionChanged anyway
        if len(__items) == self.last_selection_size:
            return

        del self.parent.fakom_presets
        self.update_preset_tree()
        self.parent.fakom_presets = __items
        self.sort_fakom_presets()

        self.update_display_tree()

        # Signal preset pages clean-up required
        self.clear_preset_pages = True
        self.completeChanged.emit()

        self.last_selection_size = len(__items)

    def create_fakom_items(self):
        """
        __fakom = {'color_key: {'sib_key': {('name', 'id digit', 'type')}}
        """
        __fakom = dict()
        __model_dict = dict()
        __read = self.parent.get_elem_attribute
        __fakom_names = set()
        self.count = 0

        # Read xml into __fakom dict/set
        for __node in self.parent.iterate_fakom_xml():
            self.count += 1

            # Create item name
            __name, __v = __read(__node, 'name'), __read(__node, 'value')

            # Avoid duplicate names
            if __name in __fakom_names:
                __name = create_unique_item_name(__name, __fakom_names)

            __fakom_names.add(__name)

            # Append model code to preset name
            __name = f'{__name} - {__v}'

            # Read id and type
            __id, __type = __read(__node, 'id'), __read(__node, 'type')

            # Read first child element (FaKom PR Code)
            __n = __node.find('./variant')
            __n = __read(__n, 'name')
            # Read SIB variant
            __sib_item = __node.find('./variant[@type="SIB"]')

            # No SIB found, search for package reference
            if __sib_item is None:
                __pkg = __node.find('./reference[@type="package"]')
                __pkg_id = __read(__pkg, 'reference')

                __pkg = self.parent.fakom_xml.root.find(f'./*/preset[@id="{__pkg_id}"]')
                if __pkg:
                    __s = __read(__pkg, 'value')
                else:
                    __s = 'PKG'
            else:
                __s = __read(__sib_item, 'name')

            # Update FaKom dict
            if __n not in __fakom.keys():
                __fakom[__n] = dict()
            if __s not in __fakom[__n].keys():
                __fakom[__n][__s] = set()

            __fakom[__n][__s].add((__name, __id, __type, __v))

            # Save model name
            if __v:
                __model_name = 'Nicht gefunden'
                __e = self.parent.vplus_xml.root.find(f'./*/preset[@value="{__v}"][@type="trim_setup"]')
                if __e:
                    __model_name = __read(__e, 'name')

                __model_dict[__v] = f'{__model_name} - {__v}'

        # Create tree widget items of fakom items
        # grouped by color PR and seating SIB and optionally by model
        for __m in __model_dict.keys():
            __parent = self.fakomTree

            if self.checkBox_models.isChecked():
                __m_item = QtWidgets.QTreeWidgetItem(__parent, [__model_dict[__m], __m])
                __m_item.setFlags(FAKOM_GRP_ITEM_FLAGS)
                __parent = __m_item
                style_database_preset(__m_item, self.parent.ui, hide=False, type_txt='trim_setup')

            for __i in __fakom.items():
                __grp_name = __i[0]
                __sib_dict = __i[1]

                # Create color group item
                __grp_item = QtWidgets.QTreeWidgetItem(__parent, [__grp_name, 'group_item'])
                __grp_item.setFlags(FAKOM_GRP_ITEM_FLAGS)
                style_database_preset(__grp_item, self.parent.ui, hide=False, type_txt='preset')

                for __sib in __sib_dict.items():
                    __sib_name = __sib[0]
                    __grp_items = __sib[1]

                    # Create SIB group item
                    __sib_item = QtWidgets.QTreeWidgetItem(__grp_item, [__sib_name, 'group_item', 'sib_item'])
                    __sib_item.setFlags(FAKOM_GRP_ITEM_FLAGS)
                    style_database_preset(__sib_item, self.parent.ui, hide=False, type_txt='options')

                    for __preset in __grp_items:
                        __name, __id, __type, __model = __preset

                        # Create preset item, id is stored in invisible column 2
                        __p_item = QtWidgets.QTreeWidgetItem(__sib_item, [__name, __id, __model, __type])
                        style_database_preset(__p_item, self.parent.ui, hide=False, type_txt=__type)

                        if __id in self.selected_ids:
                            __p_item.setSelected(True)

                        if self.checkBox_models.isChecked():
                            if __model != __m:
                                delete_tree_item_without_undo(__p_item)

            if not self.checkBox_models.isChecked():
                # No need to further iterate models
                break

        # Delete empty groups
        for __i in self.fakomTree.findItems('sib_item', QtCore.Qt.MatchRecursive, 2):
            if not __i.childCount():
                delete_tree_item_without_undo(__i)

        for __i in self.fakomTree.findItems('group_item', QtCore.Qt.MatchRecursive, 1):
            if not __i.childCount():
                delete_tree_item_without_undo(__i)