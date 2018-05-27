"""
py_knecht QUB 9000 preset wizard

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
from PyQt5.QtGui import QPixmap

from modules.knecht_log import init_logging
from modules.app_globals import WIZARD_PAGE_PRESET, Itemstyle, ENABLED_ITEM_FLAGS, DISABLED_ITEM_FLAGS, INVALID_CHR
from modules.app_strings import QobMsg
from modules.gui_widgets import load_ui_file
from modules.tree_events import TreeKeyEvents
from modules.tree_context_menus import WizardPresetContextMenu, WizardPresetSourceContext
from modules.tree_methods import style_database_preset, deep_copy_items
from modules.tree_methods import delete_tree_item_without_undo, iterate_item_childs
from modules.tree_methods import tree_setup_header_format
from modules.tree_overlay import InfoOverlay

LOGGER = init_logging(__name__)


class PresetWizardPage(QtWidgets.QWizardPage):
    """ Wizard Page displaying current preset to edit """
    complete_delay = 100
    selection_delay = 80
    fill_btn_delay = 500

    auto_magic_exclude = {'LEA', 'SIB', 'LUM', 'DAE', 'VOS'}

    pr_header_sorted = False

    def __init__(self, parent, idx):
        super(PresetWizardPage, self).__init__(parent)
        self.parent, self.app, self.ui = parent, parent.app, parent.ui
        self.idx, self.id = idx, None
        self.__used_pr_family = set()
        self.clean_up_on_start, self.display_clean_up_msg = True, False
        self.pkg_count, self.pr_count = 0, 0
        self.preset_name = dict(base_name='', options='', user_text='')

        self.load_ui()
        self.iterate_children = iterate_item_childs(self.treeWidget_Pkg)

        self.load_xml_content = None

        for widget in [self.treeWidget_Preset, self.treeWidget_Opt, self.treeWidget_Pkg]:
            # Info Overlay
            widget.info_overlay = InfoOverlay(widget)

            # Add filter txt widgets as attribute
            widget.filter_txt_widget = self.lineEditPreset
            # Connect text filter
            widget.preset_txt_filter = self.parent.TxtFiltering(self.parent.tree_filter_thread, widget, column=[0])
            self.lineEditPreset.textChanged.connect(widget.preset_txt_filter.filter_txt)

            # Add tree Key events
            widget.tree_keys = TreeKeyEvents(widget, self.ui, False, no_edit=True)
            widget.tree_keys.add_event_filter()

        # Tree events
        self.treeWidget_Preset.itemSelectionChanged.connect(self.preset_tree_selection_timer)
        self.treeWidget_Opt.itemSelectionChanged.connect(self.opt_tree_selection_changed)
        self.tree_drag_drop_events = PresetTreeEvents(self, self.treeWidget_Preset)

        # Button events
        self.hideBtn.toggled.connect(self.toggle_hide_or_lock_btn)
        self.lockBtn.toggled.connect(self.toggle_hide_or_lock_btn)
        self.hideColBtn.toggled.connect(self.show_columns)
        self.fillPresetBtn.pressed.connect(self.auto_fill_preset)

        # Events
        self.lineEditPresetTitle.textEdited.connect(self.update_preset_name_user_text)

        # Wizard events
        self.parent.currentIdChanged.connect(self.page_changed)

        # Setup timers
        self.ready_timer = QtCore.QTimer()
        self.ready_timer.setSingleShot(True)
        self.ready_timer.setInterval(self.complete_delay)
        self.ready_timer.timeout.connect(self.delay_completed)

        self.selection_timer = QtCore.QTimer()
        self.selection_timer.setSingleShot(True)
        self.selection_timer.setInterval(self.selection_delay)
        self.selection_timer.timeout.connect(self.preset_tree_selection_changed)

        self.fill_btn_timer = QtCore.QTimer()
        self.fill_btn_timer.setSingleShot(True)
        self.fill_btn_timer.setInterval(self.fill_btn_delay)
        self.fill_btn_timer.timeout.connect(self.fill_btn_delay_completed)

    @property
    def used_pr_family(self):
        return self.__used_pr_family

    @used_pr_family.setter
    def used_pr_family(self, val: set):
        self.__used_pr_family = self.__used_pr_family.union(val)
        self.__used_pr_family.discard('')

    @used_pr_family.deleter
    def used_pr_family(self):
        self.__used_pr_family = set()

    def load_ui(self):
        # Load page template
        load_ui_file(self, WIZARD_PAGE_PRESET)

        # Set logo pixmap
        logo = QPixmap(Itemstyle.ICON_PATH['car'])
        logo = logo.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, logo)

        # Hide preset data column, stores package PR
        self.treeWidget_Preset.hideColumn(3)

        # Package and PR-options context menu
        self.treeWidget_Opt.context = WizardPresetSourceContext(self.treeWidget_Opt, self, self.parent)
        self.treeWidget_Pkg.context = WizardPresetSourceContext(self.treeWidget_Pkg, self, self.parent)

        # Preset tree context menu
        self.treeWidget_Preset.context = WizardPresetContextMenu(self.treeWidget_Preset, self, self.ui)
        self.treeWidget_Preset.item_order_changed.connect(self.update_used_pr_families)

        self.splitter.setSizes([400, 500])

        # Button labels
        self.setButtonText(QtWidgets.QWizard.BackButton, QobMsg.back_preset)
        self.setButtonText(QtWidgets.QWizard.NextButton, QobMsg.next_preset)

        # Back button label on first page
        if self.idx == 0:
            self.setButtonText(QtWidgets.QWizard.BackButton, QobMsg.back_first_preset)

        # Last preset page next label
        if self.parent.fakom_presets:
            if self.idx == len(self.parent.fakom_presets) - 1:
                self.setButtonText(QtWidgets.QWizard.NextButton, QobMsg.last_preset_next)

    def initializePage(self):
        self.id = self.parent.currentId()

        if self.clean_up_on_start:
            self.clean_up_on_start = False

            if self.idx == 0:
                self.display_clean_up_msg = True
            LOGGER.debug('Preset Page #%s first visit, creating available items.', self.idx)

            self.treeWidget_Opt.clear()
            self.treeWidget_Pkg.clear()
            self.treeWidget_Preset.clear()

            self.create_available_options()

        self.update_sub_title()
        self.remember_btn_state()
        self.show_columns()
        self.show_nav_btn()
        self.ready_timer.start()

        if self.load_xml_content:
            LOGGER.debug('Loading Preset Page content.')
            self.load_session_content()

    def isComplete(self):
        if self.ready_timer.isActive():
            return False

        return True

    def validatePage(self):
        if self.parent.fakom_presets:
            # Save session if this is the last preset
            if self.idx == len(self.parent.fakom_presets) - 1:
                self.parent.session_data_mgr.save_session()

        return True

    def cleanupPage(self):
        # Update navigation menu
        self.show_nav_btn(True)

        if self.idx == 0:
            # Warn of fakomTree page edit's
            self.parent.lock_fakom_tree.emit()
            # Hide navigation menu outside preset pages
            self.show_nav_btn(False)

        self.remember_btn_state(go_back=True)

    def page_changed(self, page_id):
        if page_id == self.id:
            self.update_available_options()

            # Reset filter
            self.lineEditPreset.setText('')

            self.parent.button(QtWidgets.QWizard.BackButton).setEnabled(False)
            self.ready_timer.start()

    def delay_completed(self):
        """ Initial ready delay completed, layout ready for operations """
        if self.display_clean_up_msg:
            self.treeWidget_Preset.info_overlay.display(QobMsg.preset_cleanup, 3500)
            self.display_clean_up_msg = False

        # Setup Opt tree header on initial load
        if not self.pr_header_sorted:
            self.pr_header_sorted = True
            tree_setup_header_format([self.treeWidget_Opt], 350)

        self.parent.button(QtWidgets.QWizard.BackButton).setEnabled(True)
        self.completeChanged.emit()

    def load_session_content(self):
        for __i in self.load_xml_content.iterfind('.//'):
            __name = __i.get('name')
            __type = __i.get('type')

            if __type == 'package':
                items = self.treeWidget_Pkg.findItems(__i.get('id'), QtCore.Qt.MatchExactly, 1)
            else:
                items = self.treeWidget_Opt.findItems(__name, QtCore.Qt.MatchExactly)
                __type = 'options'

            if items:
                __items = deep_copy_items(items)
                self.treeWidget_Preset.addTopLevelItems(__items)

                for __s in __items:
                    __s.setFlags(ENABLED_ITEM_FLAGS)
                    style_database_preset(__s, self.ui, type_txt=__type)

        self.load_xml_content = None
        self.update_used_pr_families()

    def show_nav_btn(self, show_btn: bool = True):
        self.parent.setOption(QtWidgets.QWizard.HaveCustomButton1, show_btn)

    def show_columns(self):
        if self.hideColBtn.isChecked():
            for __c in range(1, 3):
                self.treeWidget_Preset.hideColumn(__c)
                self.treeWidget_Pkg.hideColumn(__c)
        else:
            for __c in range(1, 3):
                self.treeWidget_Preset.showColumn(__c)
                self.treeWidget_Pkg.showColumn(__c)

    def opt_tree_selection_changed(self):
        """ Deselect items within same PR Family """
        __c = self.treeWidget_Opt.currentItem()
        __pr_fam = __c.text(2)

        for __i in self.treeWidget_Opt.selectedItems():
            if __i is not __c:
                if __i.text(2) == __pr_fam:
                    __i.setSelected(False)

    def preset_tree_selection_timer(self):
        self.selection_timer.start()

    def preset_tree_selection_changed(self):
        __i = self.treeWidget_Preset.selectedItems()

        if len(__i):
            __i = __i[0]
        else:
            return

        if __i:
            __ovr_msg = f'{__i.text(1)} - {__i.text(2)}'
            self.treeWidget_Preset.info_overlay.display(__ovr_msg, 1500, immediate=True)

    def toggle_hide_or_lock_btn(self):
        # Hide Btn toggled
        self.update_available_options()

    def preset_selection_changed(self):
        """ User selected different presets, clear preset pages """
        self.clean_up_on_start = True

    def setlogo(self, preset_type, icon_key=None):
        if preset_type in Itemstyle.TYPES.keys():
            icon_key = Itemstyle.TYPES[preset_type]

        if not icon_key:
            return

        # Set logo pixmap
        logo = QPixmap(Itemstyle.ICON_PATH[icon_key])
        logo = logo.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, logo)

    def remember_btn_state(self, go_back: bool = False):
        # Previous page
        __page = self.parent.page(self.id - 1)

        # Set previous page button state
        if go_back and self.idx > 0:
            __lock_state = self.lockBtn.isChecked()
            __col_state = self.hideColBtn.isChecked()
            __hide_state = self.hideBtn.isChecked()

            __page.lockBtn.setChecked(__lock_state)
            __page.hideBtn.setChecked(__hide_state)
            __page.hideColBtn.setChecked(__col_state)

        # Get previous page button state
        if not go_back and self.idx > 0:
            __lock_state = __page.lockBtn.isChecked()
            __col_state = __page.hideColBtn.isChecked()
            __hide_state = __page.hideBtn.isChecked()

            self.lockBtn.setChecked(__lock_state)
            self.hideBtn.setChecked(__hide_state)
            self.hideColBtn.setChecked(__col_state)

    def update_sub_title(self):
        __n = len(self.parent.fakom_presets)
        __desc = f' Referenzbildpreset: {self.idx + 1:02d} von {__n:02d} - ' \
                 f'<i>{self.pr_count: 2d} Optionen, {self.pkg_count: 2d} Pakete</i>' \
                 f'<p style="font-family: Inconsolata; font-size: 11pt">{self.preset_name["name"]}</p>'

        self.setSubTitle(__desc)

    def create_available_options(self):
        # Get current FaKom preset Id
        __name = self.parent.fakom_presets[self.idx].text(0)
        __id = self.parent.fakom_presets[self.idx].text(1)
        __current_model = self.parent.fakom_presets[self.idx].text(2)
        __type = self.parent.fakom_presets[self.idx].text(3)

        # Update logo from preset type
        self.setlogo(__type)

        # Get complete model name
        __search = f'./*/preset[@value="{__current_model}"][@type="trim_setup"]'
        __e = self.parent.vplus_xml.root.find(__search)
        __model_name = self.parent.get_elem_attribute(__e, 'name')

        # Fill package and option widgets
        __search = f'[@value="{__current_model}"][@type="options"]'
        self.read_pr_options(self.parent.vplus_xml.root, __current_model, __search, self.treeWidget_Opt)
        self.read_pkg_options(__current_model)

        # Display trim setup in Preset Widget
        __search = f'[@value="{__current_model}"][@type="trim_setup"]'
        __preset_items = self.read_pr_options(self.parent.vplus_xml.root, __current_model, __search,
                                              self.treeWidget_Preset, create_top_level=True)

        # Display FaKom setup in Preset Widget
        __search = f'[@value="{__current_model}"][@id="{__id}"]'
        __preset_items += self.read_pr_options(self.parent.fakom_xml.root, __current_model, __search,
                                               self.treeWidget_Preset, create_top_level=True)

        for __i in __preset_items:
            # Disable default content
            __i.setFlags(DISABLED_ITEM_FLAGS)

        self.pkg_count, self.pr_count = 0, 0

        self.update_used_pr_families()
        self.update_available_options()

        self.preset_name['base_name'] = __name[:-9].replace(' ', '_')
        self.preset_name['complete_model_name'] = __model_name
        self.update_preset_name_user_text()

        __title = f'#{self.idx:03d} - {__name} - {__model_name}'
        self.setTitle(__title)
        self.labelOptions.setText(f'{QobMsg.label_avail_options} - {__model_name}')

    def update_preset_name_user_text(self):
        __user_text = self.lineEditPresetTitle.text().replace(' ', '_')
        for __s in INVALID_CHR:
            __user_text.replace(__s, '')

        self.preset_name['user_text'] = __user_text
        self.update_preset_name()

    def update_preset_name(self, pkg_pr_names: list = list(), pr_names: list = list()):
        __base_name, __user_text = self.preset_name['base_name'], ''
        if self.preset_name['user_text']:
            __user_text = f'_{self.preset_name["user_text"]}'

        __options = self.preset_name['options']

        if pkg_pr_names or pr_names:
            __options = ''
            for __s in pkg_pr_names:
                __options += f'_{__s}'
            for __s in pr_names:
                __options += f'_{__s}'

            self.preset_name['options'] = __options

        self.preset_name['name'] = f'{__base_name}{__user_text}{__options}'
        self.labelPresetTree.setText(self.preset_name['name'])

        self.update_sub_title()

    def update_used_pr_families(self, items_to_remove: list = list()):
        __pr_fam = set()
        __pkg_count, __pr_count = 0, 0
        __pkg_pr_names, __pr_names = list(), list()

        if items_to_remove:
            __iterator = items_to_remove
        else:
            __iterator = self.treeWidget_Preset.findItems('*', QtCore.Qt.MatchWildcard)

        for __i in __iterator:
            if __i.flags() & QtCore.Qt.ItemIsEnabled:
                __name = __i.text(0)
                __type = __i.text(2)

                if __type == 'package':
                    __pkg_count += 1
                    __pkg_id = __i.text(1)
                    __pkg_pr = __i.text(3)
                    __pkg_pr_names.append(__pkg_pr)

                    if items_to_remove:
                        self.parent.used_pr_options = f'~{__pkg_pr}'
                    else:
                        self.parent.used_pr_options = __pkg_pr
                        style_database_preset(__i, self.parent.ui, type_txt=__type)

                    __pkg_fam_set, __pkg_elements = self.read_package_fam(__pkg_id)

                    # Add used package PR families
                    if not items_to_remove:
                        __pr_fam = __pr_fam.union(__pkg_fam_set)

                    # Add/Rem used package PR options
                    for __e in __pkg_elements:
                        __pkg_e_pr = self.parent.get_elem_attribute(__e, 'name')

                        if items_to_remove:
                            self.parent.used_pr_options = f'~{__pkg_e_pr}'
                        else:
                            self.parent.used_pr_options = __pkg_e_pr
                else:
                    __pr_count += 1
                    __pr_names.append(__name)

                    # Add/Rem used option
                    if items_to_remove:
                        self.parent.used_pr_options = f'~{__name}'
                    else:
                        self.parent.used_pr_options = __name
                        style_database_preset(__i, self.parent.ui, type_txt='options')

                    # Add used option PR family
                    __pr_fam.add(__type)

        if not items_to_remove:
            # Update option count
            self.pkg_count = __pkg_count
            self.pr_count = __pr_count

            # Update used pr families property for this preset widget
            del self.used_pr_family
            self.used_pr_family = __pr_fam

            self.update_preset_name(__pkg_pr_names, __pr_names)

            """
            Find duplicate PR families eg. in trim setup and choosen options
            and mark only the last one as used
            
            Not used for now. We avoid missing options by creating
            additonal -base trim setups- per trim / model on result page.
            
            for __fam in self.used_pr_family:
                __items = self.treeWidget_Preset.findItems(__fam, QtCore.Qt.MatchRecursive, 2)

                for __idx, __i in enumerate(__items, start=1):
                    # Mark as unused
                    self.parent.used_pr_options = f'~{__i.text(0)}'

                    if __idx == len(__items):
                        # Mark last one as used
                        self.parent.used_pr_options = __i.text(0)
            """

        self.update_available_options()

    def enable_item(self, enable, item):
        if enable == 1:
            # Enable item
            item.setFlags(ENABLED_ITEM_FLAGS)
            item.UserType = 1000
            item.setHidden(False)
        elif enable == 2 and not self.lockBtn.isChecked():
            # Mark item in use but still interactable
            item.setFlags(ENABLED_ITEM_FLAGS)
            item.UserType = 1001
            style_database_preset(item, self.parent.ui, type_txt='checkmark')

            if self.hideBtn.isChecked():
                item.setHidden(True)
        elif enable == 0 or (enable == 2 and self.lockBtn.isChecked()):
            # Disable item, forbid user interaction
            item.setFlags(DISABLED_ITEM_FLAGS)
            item.UserType = 1002
            style_database_preset(item, self.parent.ui, type_txt='checkmark')

            if self.hideBtn.isChecked():
                item.setHidden(True)

    def update_available_options(self):
        # iterate PR options
        for __i in self.treeWidget_Opt.findItems('*', QtCore.Qt.MatchWildcard):
            __name = __i.text(0)
            __fam = __i.text(2)

            style_database_preset(__i, self.parent.ui, type_txt='options')

            if __fam in self.used_pr_family or __name in self.parent.used_pr_options:
                self.enable_item(2, __i)
            else:
                self.enable_item(1, __i)

        # Iterate packages
        for __i in self.treeWidget_Pkg.findItems('*', QtCore.Qt.MatchWildcard):
            __pkg_pr = __i.text(3)

            style_database_preset(__i, self.parent.ui, type_txt='package')

            if __pkg_pr in self.parent.used_pr_options:
                self.enable_item(2, __i)
            else:
                self.enable_item(1, __i)

            # Iterate package contents
            for __c in self.iterate_children.iterate_childs(__i):
                if __c.text(2) in self.used_pr_family:
                    self.enable_item(2, __i)
                    self.enable_item(0, __c)

    def context_add_used_pr(self, items, context_pr_set):
        """ Used from context menu to lock an item """
        for __i in items:
            # Can not add already locked items
            if __i.UserType != 1000:
                items.remove(__i)

        for __pr in self.context_update_pr(items):
            context_pr_set.add(__pr)
            # Add to global used PR options
            self.parent.used_pr_options = __pr

        self.update_used_pr_families()

    def context_rem_used_pr(self, items, context_pr_set):
        """ Used from context menu to unlock an item """
        for __pr in self.context_update_pr(items):
            if __pr in context_pr_set:
                # Remove from global used PR Options
                self.parent.used_pr_options = f'~{__pr}'
                # Remove from context pr set
                context_pr_set.remove(__pr)

        LOGGER.debug('Context menu PR Options: %s', context_pr_set)
        self.update_used_pr_families()

    @staticmethod
    def context_update_pr(items):
        """ Read PR code from items """
        for __i in items:
            __pr, __type = __i.text(0), __i.text(2)

            if __type == 'package':
                __pr = __i.text(3)

            yield __pr

    def read_pr_options(self, xml_tree, model, search_str, widget, create_top_level: bool = False):
        """ Generic Xml Element reader and return QTreeWidgetItems """
        __xpath = f'./*/preset{search_str}'
        __read = self.parent.get_elem_attribute
        __return_items = []
        __references = list()

        for __i in xml_tree.iterfind(__xpath):
            top_level_item = None

            # Create top level item
            if create_top_level:
                __name = __read(__i, 'name')
                __id = __read(__i, 'id')
                __type = __read(__i, 'type')

                top_level_item = QtWidgets.QTreeWidgetItem(widget, [__name, model, __id, __type])
                style_database_preset(top_level_item, self.ui, type_txt=__type)
                __return_items.append(top_level_item)

            # Read options
            for __o in __i.iterfind('.//'):
                __name = __read(__o, 'name')
                __desc = __read(__o, 'description')
                __pr_fam = __read(__o, 'type')
                __ref_id = __read(__o, 'reference')

                # Create item
                if top_level_item:
                    __n = QtWidgets.QTreeWidgetItem(top_level_item, [__name, __desc, __pr_fam])
                    __return_items.append(__n)
                else:
                    __n = QtWidgets.QTreeWidgetItem(widget, [__name, __desc, __pr_fam])
                    __return_items.append(__n)

                if __ref_id:
                    __references.append(f'[@id="{__ref_id}"]')

        for __r in __references:
            __return_items += self.read_pr_options(xml_tree, model, __r, widget, create_top_level)

        # Return created items
        return __return_items

    def read_pkg_options(self, model):
        __xpath = './*/preset[@type="package"]'
        __read = self.parent.get_elem_attribute

        for __i in self.parent.vplus_xml.root.iterfind(__xpath):
            __name = __read(__i, 'name')
            __pkg_pr = __read(__i, 'value')
            __id = __read(__i, 'id')

            if model in __name:
                # Create item
                pkg = QtWidgets.QTreeWidgetItem(self.treeWidget_Pkg, [__name, __id, 'package', __pkg_pr])

                # Create sub items
                _, pkg_elements = self.read_package_fam(__id)
                for __e in pkg_elements:
                    __name = __read(__e, 'name')
                    __desc = __read(__e, 'description')
                    __pr_fam = __read(__e, 'type')
                    __pkg_child = QtWidgets.QTreeWidgetItem(pkg, [__name, __desc, __pr_fam])
                    __pkg_child.setFlags(DISABLED_ITEM_FLAGS)

    def read_package_fam(self, pkg_id):
        __xpath = f'./*/preset[@id="{pkg_id}"]//'
        __pr_fam = set()
        __sub_elements = []

        # Get PR familys used in package
        for __o in self.parent.vplus_xml.root.iterfind(__xpath):
            __sub_elements.append(__o)
            __pr_fam.add(self.parent.get_elem_attribute(__o, 'type'))

        return __pr_fam, __sub_elements

    def fill_btn_delay_completed(self):
        self.fillPresetBtn.setEnabled(True)

    def auto_fill_find(self, widget, __i=None):
        for __i in widget.findItems('*', QtCore.Qt.MatchWildcard):
            if __i.UserType == 1000:
                __type = __i.text(2)

                if __type == 'package':
                    __pr_fam, _ = self.read_package_fam(__i.text(1))

                    if __pr_fam.difference(self.auto_magic_exclude) == __pr_fam:
                        return __i

                if __type not in self.auto_magic_exclude and __type != 'package':
                    return __i

        return None

    def auto_fill_preset(self):
        self.fillPresetBtn.setEnabled(False)
        self.fill_btn_timer.start()
        __pr_range = max(0, 15 - self.pr_count)
        __pkg_range = max(0, 3 - self.pkg_count)

        # Fill in options and packages automagically
        for _ in range(0, __pkg_range):
            __pkg_item = self.auto_fill_find(self.treeWidget_Pkg)

            if __pkg_item:
                __new_items = deep_copy_items([__pkg_item], copy_flags=True)
                self.treeWidget_Preset.addTopLevelItems(__new_items)
                self.update_used_pr_families()

        for _ in range(0, __pr_range):
            __pr_item = self.auto_fill_find(self.treeWidget_Opt)

            if __pr_item:
                __new_items = deep_copy_items([__pr_item], copy_flags=True)
                self.treeWidget_Preset.addTopLevelItems(__new_items)
                self.update_used_pr_families()

    @staticmethod
    def delete_all_preset_items(widget, wizard_page):
        __iterator = widget.findItems('*', QtCore.Qt.MatchWildcard)
        widget.clearSelection()

        for __i in __iterator:
            if __i.flags() & QtCore.Qt.ItemIsEnabled:
                __i.setSelected(True)

        PresetWizardPage.delete_preset_items(widget, wizard_page)

    @staticmethod
    def delete_preset_items(widget, wizard_page):
        """ Delete selected items from wizard Preset tree widget """
        __items_to_remove = list()

        for __i in widget.selectedItems():
            # Only delete top level items
            if not __i.parent():
                __items_to_remove.append(__i)

        if not __items_to_remove:
            return

        # Remove from used PR options and families
        wizard_page.update_used_pr_families(__items_to_remove)

        # Remove from tree
        for __i in __items_to_remove:
            delete_tree_item_without_undo(__i)

        wizard_page.update_used_pr_families()


class TreePresetDrop(QtWidgets.QTreeWidget):
    """ Preset Wizard custom QTreeWidget """
    drop_signal = QtCore.pyqtSignal(object, object, object)
    item_order_changed = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(TreePresetDrop, self).__init__(parent)
        self.parent = parent
        self.parent.setMouseTracking(True)

        # Worker class instance
        self.internal_drag_drop = PresetInternalDragDrop(self)

        # Connect internal drop signal
        self.drop_signal.connect(self.internal_drag_drop.drop_action)

    def dropEvent(self, drop_event):
        source = drop_event.source()
        item_list = self.selectedItems()
        destination_item = self.itemAt(drop_event.pos())

        if source is self:
            self.drop_signal.emit(source, item_list, destination_item)

        drop_event.ignore()


class PresetTreeEvents(QtCore.QObject):
    def __init__(self, parent, widget):
        super(PresetTreeEvents, self).__init__(parent)
        self.parent, self.widget = parent, widget
        self.widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.DragEnter:

            # Indicate that item will be copied
            if obj in [self.parent.treeWidget_Pkg, self.parent.treeWidget_Opt]:
                event.setDropAction(QtCore.Qt.CopyAction)

            event.accept()
            return True

        if event.type() == QtCore.QEvent.DragMove:
            event.accept()
            return True

        if event.type() == QtCore.QEvent.DragLeave:
            event.accept()
            return True

        if event.type() == QtCore.QEvent.Drop:
            __src = event.source()
            __type = 'options'
            if __src is self.parent.treeWidget_Pkg:
                __type = 'package'

            # Copy items
            __items = deep_copy_items(__src.selectedItems(), copy_flags=True)
            self.widget.addTopLevelItems(__items)

            # Set item style
            for __i in __items:
                style_database_preset(__i, self.parent.ui, type_txt=__type)

            self.parent.update_used_pr_families()

            return True

        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Delete:  # Delete selected
                self.parent.delete_preset_items(self.widget, self.parent)

                return True
        return False


class PresetInternalDragDrop(QtCore.QObject):
    """ Internal drop actions for preset tree widgets """

    def __init__(self, widget):
        super(PresetInternalDragDrop, self).__init__()
        self.widget = widget
        self.index_move = TreeKeyEvents.index_move

    def drop_action(self, source, item_list, dest_item):
        # Move item to destination item
        if dest_item:
            # Test of bitwise flag operator
            if not dest_item.flags() & QtCore.Qt.ItemIsEnabled:
                # Item is not editable / is default item
                return False

            # Move only first item in selection
            item = item_list[0]
            dest_idx = self.widget.indexOfTopLevelItem(dest_item)
        else:
            # Move to end of tree
            item = item_list[0]
            dest_idx = self.widget.topLevelItemCount() - 1

        if not item.parent():
            self.index_move(item, 0, self.widget, new_idx=dest_idx)
            self.widget.item_order_changed.emit()
            LOGGER.debug('Item Order changed.')
            return True

        return False
