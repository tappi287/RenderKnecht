"""
tree_methods for py_knecht. Provides QtWidgets.QTreeWidget item iterating, sorting, adding functionality

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
import time
import copy
import re
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtGui import QColor, QBrush

from modules.knecht_deltagen import SendToDeltaGen
from modules.knecht_log import init_logging
from modules.app_globals import LEAD_ZEROS, ItemColumn, Msg, DEFAULT_TYPES
from modules.app_globals import Itemstyle, INVALID_CHR, DETAIL_PRESET_PREFIXS

# Initialize logging for this module
LOGGER = init_logging(__name__)

# Strings
Msg()
ItemColumn()

# Define item flags
TOP_LEVEL_ITEM_FLAGS = (
        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)

VAR_LEVEL_ITEM_FLAGS = (
        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)

DEFAULT_ITEM_FLAGS = (
        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | ~QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)

RENDER_SETTING_ITEM_FLAGS = (
        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | ~QtCore.Qt.ItemIsEditable | ~QtCore.Qt.ItemIsDragEnabled)

RENDER_PRESET_ITEM_FLAGS = (
        QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled)


def lead_zeros(num_string):
    """ Returns string with leading zeros """
    # Stay above zero
    if type(num_string) is int:
        max(0, num_string)
    # Return String
    return str(num_string).rjust(LEAD_ZEROS[0], LEAD_ZEROS[1])


def swap_item_order(src_item, dest_item, return_values: bool = False):
    """ Re-arrange item order """
    dest_order = int(dest_item.text(ItemColumn.ORDER))
    src_order = src_item.text(ItemColumn.ORDER)

    if src_order.isdigit():
        src_order = int(src_order)
    else:
        src_order = dest_order

    src_parent = src_item.parent()
    dest_parent = dest_item.parent()

    if src_parent and dest_parent:
        if src_parent is not dest_parent:
            src_order = dest_order
            dest_order += 1

    if src_parent is dest_parent:
        if src_order < dest_order:
            src_order = dest_order + 1
        else:
            src_order = dest_order
            dest_order += 1
    elif not src_parent:
        src_order = dest_order
        dest_order += 1

    new_src_order = lead_zeros(src_order)
    new_dest_order = lead_zeros(max(0, dest_order))

    if return_values:
        LOGGER.debug('New src order: %s, Dest: %s', src_order, dest_order)
        return src_order, dest_order

    src_item.setText(ItemColumn.ORDER, new_src_order)
    dest_item.setText(ItemColumn.ORDER, new_dest_order)


def re_order_items(src_item: QtWidgets.QTreeWidgetItem, new_order: int, preset: QtWidgets.QTreeWidgetItem):
    """ Swap item position and re-order destination preset """
    dest_item = preset.child(new_order)
    if dest_item:
        swap_item_order(src_item, dest_item)


def delete_command(widget):
    if not widget.selectedItems():
        widget.info_overlay.display(Msg.NOTHING_TO_DELETE, 1200)
        return

    AddRemoveItemsCommand.delete(widget)

    # Sort tree if filtering is inactive
    if widget.filter_txt_widget.text() == '':
        widget.sortBtn.pressed.emit()


class AddRemoveItemsCommand:
    """ Adds undo/redo commands to the treeWidget undo stack """

    @staticmethod
    def delete(widget, **kwargs):
        LOGGER.debug('Deleting selected items.')
        rem_command = AddRemoveItemsCommand.AddUndoCmd(widget.selectedItems(), widget, **kwargs)
        widget.undo_stack.push(rem_command)
        widget.undo_stack.setActive(True)

    @staticmethod
    def add(widget, items, new_parent=None, **kwargs):
        LOGGER.debug('Adding items to Undo stack.')
        add_command = AddRemoveItemsCommand.AddUndoCmd(items, widget, new_parent, False, **kwargs)
        widget.undo_stack.push(add_command)
        widget.undo_stack.setActive(True)

    class AddUndoCmd(QtWidgets.QUndoCommand):

        def __init__(self, item_list, widget=False, new_parent=None, remove=True, **kwargs):
            super(AddRemoveItemsCommand.AddUndoCmd, self).__init__()

            self.remove = remove
            self.new_parent = new_parent
            self.kwargs = {}

            if kwargs:
                if 'kwargs' in kwargs.keys():
                    self.kwargs = kwargs['kwargs']
                else:
                    self.kwargs = kwargs

            # Convert to list
            if type(item_list) != list:
                item_list = [item_list]

            # Get destination widget
            if widget:
                self.widget = widget
            else:
                if len(item_list) >= 1:
                    self.widget = item_list[0].treeWidget()

            # Create list of items
            self.item_list = []

            if self.new_parent:
                for item in item_list:
                    item_user_type = item.UserType
                    item = QtWidgets.QTreeWidgetItem(self.new_parent, get_column_values(item))
                    item.UserType = item_user_type
                    set_item_flags(item)
                    self.item_list.append(item)
                self.item_list.append(self.new_parent)
            else:
                # Unpack nested lists
                if item_list:
                    if item_list[0] == list:
                        item_list[:] = item_list[0]

                    self.item_list = item_list

            self.index_list = []
            self.was_missing_ref_item = []

        def redo(self):
            if self.remove:
                self.remove_items()
                self.create_undo_txt()
            else:
                self.add_items()
                self.create_undo_txt()

        def undo(self):
            if self.remove:
                self.add_items()
                self.create_undo_txt()
            else:
                self.remove_items()
                self.create_undo_txt()

        def remove_items(self):
            for item in self.item_list:
                # Clear Reference Item from missing Reference ID's
                if item.UserType in [1002]:
                    item_id = item.text(ItemColumn.REF)
                    LOGGER.debug('Clearing ID: %s from missing IDs', item_id)

                    if item_id in self.widget.missing_ids:
                        self.widget.missing_ids.remove(item_id)
                        self.was_missing_ref_item.append(item)

                # Store item for undo command
                if item.parent():
                    index = item.parent().indexOfChild(item)
                    self.index_list.append((index, item.parent()))
                    item.parent().takeChild(index)
                else:
                    index = self.widget.indexOfTopLevelItem(item)
                    self.index_list.append((index, False))
                    self.widget.takeTopLevelItem(index)

                del item

        def add_items(self):
            for index, item in zip(self.index_list, self.item_list):
                index, parent = index
                if parent:
                    parent.insertChild(index, item)
                else:
                    self.widget.insertTopLevelItem(index, item)

                # Restore missing status
                if item in self.was_missing_ref_item:
                    self.widget.missing_ids.add(item.text(ItemColumn.REF))

        def create_undo_txt(self):
            """ Create an undo / redo text """
            if len(self.item_list) >= 1:
                if self.remove:
                    txt = ' entfernen ('
                else:
                    txt = ' kopieren ('

                if 'txt' in self.kwargs.keys():
                    txt = ' ' + self.kwargs['txt'] + ' ('

                undo_msg = str(len(self.item_list)) + txt

                # List item name(s)
                item_names = ''
                for item in self.item_list:
                    item_names += item.text(ItemColumn.NAME)[0:14] + '; '

                item_names = item_names[0:50]

                undo_msg += item_names + ' ...)'

                self.setText(undo_msg)


def object_is_tree_widget(obj):
    """ Returns True if provided object is of class QtWidgets.QTreeWidget or TreeInternalDrop """
    if type(obj).__name__ == 'QTreeWidget' or type(obj).__name__ == 'TreeInternalDrop':
        return True
    return False


def get_item_index(widget: QtWidgets.QTreeWidget, item_list: list = list(), index_list: list = list()):
    """ Gets indicies of items and returns index list """
    for item in item_list:
        if item.parent():
            index = item.parent().indexOfChild(item)
            index_list.append((index, item.parent()))
        else:
            index = widget.indexOfTopLevelItem(item)
            index_list.append((index, False))

    return index_list


def toggle_ref_visibility(ui, widget):
    """ Toggle visibility of ref or default presets """
    if widget.toggle_preset_vis:
        widget.toggle_preset_vis = False
    else:
        widget.toggle_preset_vis = True

    ui.sort_tree_widget.sort_all(widget)


def shade_color(max_val, start_val, shade_val):
    __color = QColor(min(max_val, start_val + shade_val), min(max_val, start_val + shade_val),
                     min(max_val, start_val + shade_val))
    return __color


def style_database_preset(item, ui, hide: bool = False, type_txt: str = ''):
    """ Visual indication of default types """
    if not type_txt:
        type_txt = item.text(ItemColumn.TYPE)

    if type_txt == 'seperator':
        for __col in range(0, item.columnCount()):
            __shade = int(int(item.text(ItemColumn.ORDER)) * (__col * 0.2))

            __color = shade_color(240, 220, __shade)
            item.setBackground(__col, __color)
            item.setForeground(__col, QBrush(__color))

        item.UserType = 1005

        if item.parent():
            item.UserType = 1006

    if type_txt in Itemstyle.TYPES:
        icon_key = Itemstyle.TYPES[type_txt]
        item.setIcon(Itemstyle.COLUMN, ui.icon[icon_key])
    else:
        if not item.icon(Itemstyle.COLUMN).isNull():
            item.setIcon(Itemstyle.COLUMN, ui.icon['empty'])

    # Set Detail Img Icons
    if item.UserType == 1000:
        item_name = item.text(ItemColumn.NAME)
        __item_prefix = item_name[0:3]

        for __detail_prefix in DETAIL_PRESET_PREFIXS:
            if __item_prefix == __detail_prefix:
                icon_key = Itemstyle.TYPES[__item_prefix]
                item.setIcon(Itemstyle.COLUMN, ui.icon[icon_key])
                break

    # Hide / Show referenced and default presets
    is_ref_preset = False
    if item.icon(1) is ui.icon['link_intact']:
        is_ref_preset = True

    if type_txt in DEFAULT_TYPES or is_ref_preset:
        # Make sure we don not hide sub level references
        if not item.parent():
            if hide:
                item.setHidden(True)
            else:
                item.setHidden(False)


def tree_setup_header_format(widget_list, maximum_width: int = 650):
    """
    Sets header row sorting to column 0 and ascending for QtWidgets.QTreeWidgets
    Fits columns width to content and sets resize mode back to interactive
    """
    new_widget_list = []
    if type(widget_list) is not list:
        new_widget_list.append(widget_list)
    else:
        new_widget_list = widget_list

    for widget in new_widget_list:
        header = widget.header()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)

        widget_width = max(100, widget.width())
        oversize_width = 0

        # First pass calculate complete oversized width if every item text would be visible
        for column in range(1, header.count() - 1):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
            column_width = header.sectionSize(column) + 40
            oversize_width += column_width

        # Add last and first column width
        oversize_width += header.sectionSize(header.count()) + header.sectionSize(0)

        # Calculate scale factor needed to fit columns inside visible area
        column_scale_factor = max(1, widget_width) / max(1, oversize_width)

        for column in range(1, header.count() - 1):
            width = min((header.sectionSize(column) * column_scale_factor), maximum_width)
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
            header.resizeSection(column, width)

        # Set sorting order to ascending by column 0: order
        widget.sortByColumn(0, QtCore.Qt.AscendingOrder)


class render_settings_combo_box:
    """ Create Combo Box Widget for Render Setting row's """

    def __init__(self, item):
        self.widget = item.treeWidget()
        self.item = item

        item_type_txt = self.item.text(ItemColumn.TYPE)

        if item_type_txt == 'sampling':
            # AA
            self.aa_widget = create_combo_box(self.widget, self.item, 2,
                                              ['0', '8', '16', '32', '64', '128', '256', '512', '1024', '2048', '4096'],
                                              7)
        elif item_type_txt == 'file_extension':
            # File Extension
            self.fex_widget = create_combo_box(self.widget, self.item, 2,
                                               ['.exr', '.hdr', '.png', '.jpg', '.bmp', '.tif'], 1)
        elif item_type_txt == 'resolution':
            # Resolution
            self.res_widget = create_combo_box(self.widget, self.item, 2,
                                               ['1080 1080', '1280 720', '1280 960', '1920 1080', '2560 1920',
                                                '2880 1620', '3840 2160', '4096 2160'], 4, True)


class create_combo_box:
    """ Creates a combo box widget in given widget/item/column with given items/index/attributes """

    def __init__(self, widget, item, column: int, combo_items: list, start_index: int = 0, editable: bool = False, ):
        # Set combo box index to item value
        if item.text(column) in combo_items:
            start_index = combo_items.index(item.text(column))

        self.cb = item_combo_box(widget, item, column, combo_items, editable)

        if editable:
            self.cb.comboBox.currentTextChanged.connect(self.cb.comb_box_txt_edited)
        else:
            self.cb.comboBox.currentIndexChanged.connect(self.cb.comb_box_edited)

        self.cb.comboBox.setCurrentIndex(start_index)


class item_combo_box:
    """ Create combo box widget for item column with list of combobox-items """

    def __init__(self, widget, item, column, combo_items, editable=False):
        self.widget = widget
        self.item = item
        self.column = column
        self.combo_items = combo_items

        self.comboBox = QtWidgets.QComboBox(widget)

        self.comboBox.addItems(self.combo_items)

        if editable:
            self.comboBox.setEditable(True)

        self.widget.setItemWidget(self.item, self.column, self.comboBox)

    def comb_box_edited(self, idx):
        """ connected to current index changed """
        if idx <= len(self.combo_items):
            self.item.setText(self.column, self.combo_items[idx])
            LOGGER.debug('Combo Box index changed: %s', self.combo_items[idx])
        else:
            LOGGER.debug('Combo Box Items index exceeded.')

    def comb_box_txt_edited(self, txt):
        """ connected to current Text changed """
        self.item.setText(self.column, txt)
        LOGGER.debug('Combo Box text changed: %s', txt)


class SortTree:
    """
        Sorts by given column and re-writes that columns text in sorted order
        eg. from 001, 003, 008 to 001, 002, 003
        If passed object is item, childs will be sorted (fast)
        If passed object is TreeWidget, all items will be sorted (slow)
    """

    def __init__(self, ui, widget, column=0):
        self.widget = widget
        self.item_id_list = []
        self.render_widgets = []
        self.column = column
        self.ui = ui

        # Timer
        self.work_timer = QtCore.QTimer()
        self.work_timer.setInterval(100)
        self.work_timer.timeout.connect(self.sorting_worker)
        self.work_timer.stop()
        self.worker_items = (None, None, None)
        self.index_list = []
        self.sort_progress_factor = False

        # item counter
        self.item_idx = 0
        self.item_parent_idx = 0

        # Find references if Main Window class provided
        if self.ui:
            self.find_ref = self.ui.find_reference_items

    def sort_current_level(self, item=None, widget=False):
        self.item_idx = 0
        self.item_parent_idx = 0
        item_list = []

        # Catch Sort button in empty list
        if item is None:
            return

        if widget:
            self.widget = widget

        if item.parent():
            # If passed object has parent, sort only children(way faster)
            for item in self.ui.iter_tree.iterate_childs(item.parent()):
                item_list.append(item)
        else:
            # Sort top level items, fast
            item_list += self.widget.findItems('*', QtCore.Qt.MatchWildcard)

        # Map calls self.sort for every iterable, should be faster than for loop
        # Check if item is sorted ascending by order
        if self.check_tree_sort_order(self.widget, item):
            list(map(self.sort, item_list))

        if item is not None:
            LOGGER.debug('Sorting iterated top level: %s items for %s', len(item_list), item.text(1))

    def sort_all(self, widget=None):
        """
        Sorts everything in the widget but is super slow. Should only be connected to buttons.
        """
        self.item_idx = 0
        self.item_parent_idx = 0

        if widget:
            if not object_is_tree_widget(widget):
                self.widget = widget.treeWidget()
            else:
                self.widget = widget

        sort_start_time = time.time()

        # Disable sort btn
        if self.widget is self.ui.treeWidget_DestPreset:
            self.widget.sortBtn.setEnabled(False)

        # Iterate all
        item_list = []
        self.widget.unique_names = set()

        for item in iterate_tree_widget_items_flat(self.widget):
            item_list.append(item)

            # Prepare worker indices
            if item.UserType == 1000:
                # Generate unique preset name
                item_name = item.text(ItemColumn.NAME)
                if item_name in self.widget.unique_names:
                    item_name = create_unique_item_name(item_name, self.widget.unique_names)
                    item_id = item.text(ItemColumn.ID)

                    if item_id:
                        update_reference_names(item_name, item_id, self.widget)

                    item.setText(ItemColumn.NAME, item_name)

                self.widget.unique_names.add(item_name)
                self.index_list.append((self.widget.indexOfTopLevelItem(item), self.widget))

        # Reset to sort by Order ascending if not set
        if self.check_tree_sort_order(self.widget):
            # Sort items by order column
            list(map(self.sort, item_list))

        sort_time = time.time() - sort_start_time
        sort_time = str(sort_time)[0:8]
        LOGGER.debug('Sorting prepared %s items in %s seconds. Worker starting.', len(item_list), sort_time)
        self.start_sorting_worker()

    def sort(self, item):
        """ Sort Items numeric, write to column: self.column """
        if type(item) is list:
            LOGGER.error('Sorting item is list.')
            return

        # Re-order child items
        if item.parent():
            item.setText(self.column, lead_zeros(self.item_idx))
            self.item_idx += 1
        # Re-order parent items
        else:
            item.setText(self.column, lead_zeros(self.item_parent_idx))
            self.item_parent_idx += 1
            self.item_idx = 0

        # Create Item Widgets for render_settings
        if item.UserType == 1004 and item.treeWidget() is not self.ui.treeWidget_SrcPreset:
            if not item.treeWidget().itemWidget(item, ItemColumn.VALUE):
                # Create item widget if not already present
                LOGGER.debug('Creating Combo Box Widget for item %s', item.text(1))
                self.render_widgets.append(render_settings_combo_box(item))

        # Style default presets
        style_database_preset(item, self.ui, self.widget.toggle_preset_vis)

    def start_sorting_worker(self):
        if self.work_timer.isActive():
            return

        sort_item_count = len(self.index_list)
        if sort_item_count >= 200:
            self.sort_progress_factor = sort_item_count

        self.worker_items = ([], [], [])
        self.work_timer.start()

    def stop_sorting_worker(self):
        self.work_timer.stop()
        self.sort_progress_factor = False
        self.widget.sortBtn.setEnabled(True)
        LOGGER.debug('Sorting worker finished. Stopping work timer.')

    def sorting_worker(self, chunk_size: int = 100, item_work_list: list = []):
        """ Work asynchronusly thru remaining items to sort """
        if not self.index_list:
            self.stop_sorting_worker()
            return

        # Chunk of items to work with
        item_work_list = []
        chunk_size = min(chunk_size, len(self.index_list))

        for i in range(0, chunk_size):
            if self.index_list:
                work_index, work_widget = self.index_list.pop()
            else:
                return

            work_item = work_widget.topLevelItem(work_index)

            if work_item:
                item_work_list.append(work_item)

        if item_work_list:
            # Display progress
            if self.sort_progress_factor and self.index_list:
                pro_finished = self.sort_progress_factor - len(self.index_list)
                transfer_bar = 'Baum wird geprüft: ' + str(pro_finished) + '/' + str(self.sort_progress_factor)
                work_widget.info_overlay.display(transfer_bar, 500, True)

            # Do the actual work
            self.worker_items = self.find_ref.highlight_references(item_work_list, self.worker_items)

    def check_tree_sort_order(self, widget=None, item=None):
        """
            Check if the Tree widget is sorted ascending by 'order' column 0
            We do not want to rewirte order strings if eg. tree is sorted by name
        """
        if item:
            widget = item.treeWidget()

        if widget:
            # Sorted by column: order?
            if widget.sortColumn() == 0:
                # Sorted ascending?
                if widget.header().sortIndicatorOrder() == 0:
                    return True
                else:
                    tree_setup_header_format([widget])
                    self.widget.sortBtn.setEnabled(True)
                    self.widget.info_overlay.display(Msg.OVERLAY_SORTING_WARN, 7000, True)
                    return False
            else:
                tree_setup_header_format([widget])
                self.widget.sortBtn.setEnabled(True)
                self.widget.info_overlay.display(Msg.OVERLAY_SORTING_WARN, 7000, True)
                return False

        return False


def iterate_tree_widget_items_flat(widget):
    """ Creates an item list in flat hierachy of all QtWidgets.QTreeWidget items """
    it = QtWidgets.QTreeWidgetItemIterator(widget)

    while it.value():
        yield it.value()
        it += 1


class iterate_item_childs:
    """ Tree item child generator function """

    def __init__(self, widget):
        self.widget = widget

    def iterate_childs(self, item):
        # Iterate childs
        if item.childCount() > 0:
            for c in range(0, item.childCount()):
                yield item.child(c)


class add_variant:

    def __init__(self, ui, ui_tree_widget):
        self.ui = ui
        self.ui_tree_widget = ui_tree_widget

    def add_text(self, variant_set_str, variant_str):
        order = lead_zeros(self.ui_tree_widget.topLevelItemCount() + 1)

        # Set values
        new_var_item = add_top_level_item(self.ui_tree_widget, [order, variant_set_str, variant_str],
                                          VAR_LEVEL_ITEM_FLAGS, 1001)

        SortTree(self.ui, self.ui_tree_widget, 0)
        return new_var_item


def add_top_level_item(ui_tree_widget, column_strings: list, flags=None, item_type=1001):
    """
    Create and append top level item to ui_tree_widget
    column_strings[0] = order number
    column_strings[1] = item to add -OR- continue list with column values
    flags = optional item flags
    item_type = default variant type 1001
    """
    # Check if column_strings contains QtWidgets.QTreeWidget Item
    if type(column_strings[1]).__name__ == 'QTreeWidgetItem':
        # List contains item, use it to create new item
        new_items = deep_copy_items([column_strings[1]])

        # list to object
        item = new_items[0]

        # Set order string
        item.setText(0, lead_zeros(column_strings[0]))

    # List contains only item values, create new item
    else:
        item = QtWidgets.QTreeWidgetItem()

        # Set column text values
        for idx, text in enumerate(column_strings):
            item.setText(idx, str(text))

        # Set order string
        item.setText(0, lead_zeros(column_strings[0]))
        item.UserType = item_type

    # Create unique item name
    item_name = item.text(ItemColumn.NAME)
    if item_name in ui_tree_widget.unique_names:
        item_name = create_unique_item_name(item_name, ui_tree_widget.unique_names)

        item.setText(ItemColumn.NAME, item_name)
        ui_tree_widget.unique_names.add(item_name)

    # Set item flags
    if flags is not None:
        item.setFlags(flags)

    item.setHidden(False)

    # Add top level item
    ui_tree_widget.addTopLevelItem(item)

    return item


class CopySelectedToDest:
    """ Copy selected QtWidgets.QTreeWidgetItems incl. childs from src to dest """
    # Just for the log
    item_count = 0

    # Default chunk size and Timer intervals
    # Chunk size, timer interval
    big_chunk_param = (3, 30)
    # Small
    small_chunk_param = (2, 20)

    def __init__(self, ui):
        self.ui = ui
        # Timer
        self.copy_timer = QtCore.QTimer()
        self.copy_timer.setInterval(150)
        self.copy_timer.timeout.connect(self.run_copy_worker)
        self.copy_timer.stop()
        self.copy_index = 0
        self.copy_items = dict()
        self.chunk_size = (1, 10)
        self.create_ref_check = False
        self.progress = 0
        self.new_undo_items = []
        self.check_new_parent = None
        self.check_src_tree_ids = None
        self.new_src_order = None

    def Run(self, src,  # Source tree widget
            dest,  # Destination item or tree widget
            check_src_tree_ids=None,  # Update Tree ID's
            ref_check=False,  # Flag this as a reference check run
            src_is_itemlist=False,  # src is item list
            new_src_order=None  # Create copy's at this order
            ):
        """
            src, dest, check_src_tree_ids - when creating a new item, make sure id is
            neither in source_widget nor dest tree
        """
        if check_src_tree_ids:
            self.check_src_tree_ids = self.ui.treeWidget_SrcPreset

        self.new_src_order = new_src_order

        # Collect selected items
        if not ref_check:
            if src_is_itemlist:
                pass
            else:
                src = src.selectedItems()

                if not src:
                    return

            if new_src_order:
                self.new_src_order = max(0, new_src_order - (len(src) - 1))
        else:
            LOGGER.debug('Copy Worker reference check: %s items', len(src))

        # Index of copy action, can chain copy
        self.copy_index += 1

        # Dict to store all arguments of this chain
        self.copy_items[self.copy_index] = {
            'items'      : src,
            'dest'       : dest,
            'time'       : time.time(),
            'ref_checked': ref_check}

        num_items = len(self.copy_items[self.copy_index]['items'])

        if num_items > 15:
            self.chunk_size = self.big_chunk_param[0]
            self.copy_timer.setInterval(self.big_chunk_param[1])
            self.progress = num_items
        else:
            self.chunk_size = self.small_chunk_param[0]
            self.copy_timer.setInterval(self.small_chunk_param[1])

        # Fire the timer to call worker in intervals
        self.copy_timer.start()

    def move_index(self, dest):
        """ Chained index of copy operations, finishes when reaching zero """
        copy_time = self.copy_items[self.copy_index]['time']

        ref_checked = self.copy_items[self.copy_index]['ref_checked']

        dest = self.copy_items[self.copy_index]['dest']

        # Move index
        self.copy_index = max(0, self.copy_index - 1)

        if ref_checked:
            # Copy chain element chunks finished
            self.copy_finished(dest, copy_time)
        else:
            self.create_ref_check = (True, dest)

    def copy_finished(self, dest, copy_time):
        """ All chunks were copied, create references and """
        copy_time = time.time() - copy_time
        copy_time = str(copy_time)[0:8]

        if object_is_tree_widget(dest):
            # Add Undo Items to Destination Widget
            AddRemoveItemsCommand.add(dest, self.new_undo_items)
            self.ui.sort_tree_widget.sort_all(dest)
            dest.overlay.copy_created()
        else:
            dest = dest.treeWidget()
            # Add Undo Items to Destination Item with new parent
            AddRemoveItemsCommand.add(dest, self.new_undo_items)
            self.ui.sort_tree_widget.sort_all(dest)

        LOGGER.debug('Copy worker finished copying %s items in %s - missing ids: %s', len(self.new_undo_items),
                     copy_time, dest.missing_ids)
        self.new_undo_items = []
        self.check_new_parent = None
        self.progress = 0

    def stop_copy_worker(self):
        """ Stop new call intervals to worker """
        self.copy_timer.stop()

    def run_copy_worker(self):
        """ Works thru one chunk until chain index is zero """
        if self.copy_index == 0:
            self.stop_copy_worker()

            if self.create_ref_check:
                # Create copy's for the reference check run
                ref_check, dest = self.create_ref_check
                check_items = copy.copy(self.new_undo_items)

                if self.check_new_parent:
                    check_items.append(self.check_new_parent)

                # Reset reference check flag
                self.create_ref_check = False

                self.Run(src=check_items, dest=dest, ref_check=ref_check)
            return

        # Shortcut
        cpy = self.copy_items[self.copy_index]

        # Chunk of items we will pop out and work with
        item_chunk = []

        for i in range(0, self.chunk_size):
            if cpy['items']:
                item_chunk.append(cpy['items'].pop(0))

        if item_chunk:
            if not cpy['ref_checked']:
                prg_msg = 'Kopiervorgang '
                self.copy_worker(item_chunk, cpy['dest'])
            else:
                prg_msg = 'Prüfvorgang '
                self.reference_copy_worker(item_chunk, cpy['dest'])

            if self.progress:
                remaining = self.progress - len(cpy['items'])
                prg_msg += str(remaining) + '/' + str(self.progress)
                self.ui.treeWidget_DestPreset.info_overlay.display(prg_msg, 100, True)

        if not cpy['items']:
            self.move_index(cpy['dest'])

    def copy_worker(self, new_items, dest):
        """
            Finally copies something to the tree, collects references and stores
            items that we will add to undo/redo commands.
        """
        # Create deep copies of new items
        new_items = deep_copy_items(new_items)

        # --------------------------------------------
        # Destination is item
        if not object_is_tree_widget(dest):
            # Re-order new_items behind item's children
            try:
                if self.new_src_order is not None:
                    order = self.new_src_order
                    LOGGER.debug('Copy to item position: %s', self.new_src_order)
                else:
                    order = dest.childCount()
            except AttributeError:
                # Item has no children
                order = 0

            referenced_items = []

            for item in new_items:
                item.setText(ItemColumn.ORDER, lead_zeros(order))

                referenced_items = self.ui.find_reference_items.check_reference(order, item, dest)

                if not referenced_items:
                    if item.UserType in [1002]:
                        # Item to copy is reference, queue destination item to reference check
                        dest.insertChild(order, item)
                        self.check_new_parent = dest
                    else:
                        # Item is variant or reference-method created reference for preset
                        dest.insertChild(order, item)

                    self.new_undo_items.append(item)
                else:
                    self.new_undo_items += referenced_items

                order += 1
                if self.new_src_order:
                    self.new_src_order += 1

            if referenced_items:
                dest.treeWidget().overlay.ref_created()
            else:
                dest.treeWidget().overlay.copy_created()

        # --------------------------------------------
        # Destination is tree
        else:
            order = dest.topLevelItemCount()

            # Iterate new items and order behind existing items
            for item in new_items:
                order += 1

                # Update item_id
                item_id = update_tree_ids(dest, self.ui, item.text(ItemColumn.ID), self.check_src_tree_ids,
                                          error_item=item, item_name=item.text(ItemColumn.NAME))

                if item_id:
                    # Set new ID
                    item.setText(ItemColumn.ID, str(item_id))

                # Copy and append to Check List
                copied_item = add_top_level_item(dest, [order, item])
                self.new_undo_items.append(copied_item)

    def reference_copy_worker(self, check_items, dest):
        # Check for missing references after copy complete
        if not object_is_tree_widget(dest) and not self.check_new_parent:
            return

        if self.check_new_parent:
            order = self.check_new_parent.childCount()
        else:
            order = dest.topLevelItemCount()

        for item in check_items:
            order += 1

            # Item is preset
            if item.UserType in [1000, 1002, 1003]:
                # Check for missing references
                referenced_items = self.ui.find_reference_items.check_reference(order, item,
                                                                                self.ui.treeWidget_DestPreset)
                if referenced_items:
                    self.new_undo_items += referenced_items


def set_item_flags(item, create_ref_for_top_level=False):
    # Set Flags based on hierarchy level
    if item.parent():
        if item.UserType == 1004:
            # Render Settings uneditable
            item.setFlags(RENDER_SETTING_ITEM_FLAGS)
        elif item.UserType in [1001, 1002]:
            item.setFlags(VAR_LEVEL_ITEM_FLAGS)
    else:
        if not create_ref_for_top_level:
            item.setFlags(TOP_LEVEL_ITEM_FLAGS)
        else:
            pass


def deep_copy_items(item_list, create_ref_for_top_level=False, copy_flags=False):
    new_item_list = []

    for item in item_list:
        new_item = QtWidgets.QTreeWidgetItem()
        new_item.UserType = item.UserType

        # Set Flags based on hierachy level
        if not copy_flags:
            set_item_flags(new_item, create_ref_for_top_level)
        else:
            flags = item.flags()
            new_item.setFlags(flags)

        # Iterate columns and copy attributes
        for i in range(0, item.columnCount()):
            new_item.setText(i, item.text(i))
            new_item.setFont(i, item.font(i))
            new_item.setForeground(i, item.foreground(i))
            new_item.setBackground(i, item.background(i))

        # Copy children
        if item.childCount() > 0:
            new_children = list_child_items(item)

            # Recursive children copy
            new_item.addChildren(deep_copy_items(new_children, create_ref_for_top_level, copy_flags))

        new_item_list.append(new_item)

    CopySelectedToDest.item_count += len(new_item_list)
    return new_item_list


def list_child_items(item):
    children_list = []

    for child_idx in range(0, item.childCount()):
        children_list.append(item.child(child_idx))

    return children_list


def get_column_values(item):
    """ Iterates item columns and returns list of strings """
    value_list = []

    for i in range(0, item.columnCount()):
        value_list.append(item.text(i))

    return value_list


def add_selected_childs_as_top_level(src, dest, ui, src_is_itemlist=False):
    """ Copy selected QtWidgets.QTreeWidget children from src to dest """
    # Add with highest order behind existing items
    order = dest.topLevelItemCount()
    check_items = []
    new_undo_items = []
    new_item = False

    if src_is_itemlist:
        pass
    else:
        src = src.selectedItems()

    for s in src:
        order += 1

        # Make sure this is a child
        if s.UserType in (1001, 1002):
            new_item = add_top_level_item(dest, [order, s], VAR_LEVEL_ITEM_FLAGS)
            new_undo_items.append(new_item)

        # and iterate Childs
        for c in range(0, s.childCount()):
            if s.child(c).UserType not in (1005, 1006):
                # Add child Item as top level item
                new_item = add_top_level_item(dest, [order, s.child(c)], VAR_LEVEL_ITEM_FLAGS)
                new_undo_items.append(new_item)
                order += 1

        # Check for references in Presets
        if s.UserType == 1000:
            check_items.append(s)

        # Check if selected item is reference and check it's preset parent
        if s.UserType == 1002:
            if s.parent():
                check_items.append(s.parent())

    # Abort if no new item created
    if not new_undo_items:
        dest.info_overlay.display(Msg.NOTHING_TO_PASTE_VARIANTS, 2500)
        return

    # Check for missing references after copy complete
    order = dest.topLevelItemCount()

    for item in check_items:
        # Item is preset
        if item.UserType == 1000:
            # Check for missing references
            new_items = ui.find_reference_items.check_reference(order, item, ui.treeWidget_DestPreset)
            if new_items == list:
                for n_item in new_items:
                    new_undo_items.append(n_item)
            else:
                new_undo_items.append(new_item)

    if new_undo_items:
        AddRemoveItemsCommand.add(dest, new_undo_items, txt='zur Variantenliste hinzufügen')
        dest.overlay.copy_created()

    # Sort destination
    if not src_is_itemlist:
        ui.sort_tree_widget.sort_current_level(src[0], dest)
    else:
        ui.sort_tree_widget.sort_all(dest)

    generate_variants_tree_message(ui, src, dest)


def generate_variants_tree_message(ui, src, dest):
    """ Display Preset name in Variants Tree that was added. """
    if len(src) < 1:
        return

    if dest is not ui.treeWidget_Variants:
        return

    items = src
    src = src[0].treeWidget()

    # Clear btn overlay
    dest.info_overlay.display_exit()
    # Clear Preset name on Variant drop
    SendToDeltaGen.last_preset_added = ''

    if items:
        item = items[0]
    else:
        return

    if item.UserType != 1000:
        return

    # Display Preset Name if only items of source Preset were added
    if dest.topLevelItemCount() == item.childCount():
        SendToDeltaGen.last_preset_added = item

        def select_src_preset():
            if src:
                src.clearSelection()
                if item:
                    item.setSelected(True)
                    src.scrollToItem(item, QtWidgets.QAbstractItemView.PositionAtCenter)

        # If source widget is known (Drag n Drop)
        if src:
            # Display added Preset
            msg = Msg.DG_VARIANTS_ADDED.format(tree_name=ui.get_tree_name(src), preset_name=item.text(ItemColumn.NAME))
            dest.info_overlay.display_confirm(msg, ('Auswählen', select_src_preset), ('[X]', None))

        # If source widget is unknown (Copy n Paste)
        else:
            # Display added Preset
            msg = Msg.DG_VARIANTS_ADDED.format(tree_name='Zwischenablage', preset_name=item.text(ItemColumn.NAME))
            dest.info_overlay.display_confirm(msg, ('[X]', None))


def generate_number_outside_set(s, start_val: int = 0) -> int:
    """
        Returns all elements starting from min not in s.
    """
    n = len(s)

    if n > 0:
        l = sorted(s)
        for x in range(start_val, l[0]):
            yield x
        for i in range(0, n - 1):
            for x in range(l[i] + 1, l[i + 1]):
                yield x
        r = l.pop() + 1
    else:
        r = start_val
    while True:
        yield r
        r += 1


def update_tree_ids(widget, ui, search_id: str, source_widget=None, error_item=False, item_name=None):
    """
        Searches widget and source_widget(if provided) for search_id.
        Returns False if search_id is not in use. Returns new id string
        if it is in use.
    """
    search_id_int_set = set()

    def generate_id_int(search_widget):
        for item in search_widget.findItems('*', QtCore.Qt.MatchWildcard, ItemColumn.ID):
            id_str = item.text(ItemColumn.ID)
            if id_str.isdigit():
                yield int(id_str)

    def search_free_id(id_int=0):
        # Convert string set to integers
        for search_int in generate_id_int(widget):
            search_id_int_set.add(search_int)

        if source_widget:
            for search_int in generate_id_int(source_widget):
                search_id_int_set.add(search_int)

        # Add widget's missing Ids
        for id_str in widget.missing_ids:
            if id_str.isdigit():
                search_id_int_set.add(int(id_str))

        # Generate a free int number
        for id_int in generate_number_outside_set(search_id_int_set):
            if id_int:
                break

        return str(id_int)

    if search_id == '':
        return False

    # Match top level items with text in ID column
    item_matches = widget.findItems(search_id, QtCore.Qt.MatchWildcard, ItemColumn.ID)

    # Search source preset widget
    if source_widget is not None:
        source_item_matches = source_widget.findItems(search_id, QtCore.Qt.MatchWildcard, ItemColumn.ID)
        item_matches = item_matches + source_item_matches

    if item_name is not None:
        name_matches = widget.findItems(item_name, QtCore.Qt.MatchExactly, ItemColumn.NAME)

        if name_matches:
            name_matches = name_matches[0]

            if name_matches.text(ItemColumn.ID) == search_id:
                # Item with same name and ID exists
                source_widget = ui.treeWidget_SrcPreset
                new_id = search_free_id()
                return new_id

    if not item_matches:
        if search_id not in widget.missing_ids:
            return search_id

    if search_id in widget.missing_ids:
        new_id = search_free_id()

        # Report conflicting ID
        id_conflict(search_id, widget, new_id, source_widget, error_item)

        return new_id

    return search_free_id()


def id_conflict(search_id, widget, new_id, source_widget=None, error_item=False):
    if search_id in widget.missing_ids:
        # Report ID conflict
        error_items = []

        if not error_item:
            if source_widget:
                error_items = source_widget.findItems(search_id, QtCore.Qt.MatchExactly, ItemColumn.ID)

            if not error_items:
                error_items = widget.findItems(search_id, QtCore.Qt.MatchWildcard, ItemColumn.ID)

            if not error_items:
                error_items = widget.findItems(search_id, QtCore.Qt.MatchRecursive, ItemColumn.REF)

            if error_items:
                widget.report_conflict(error_items[0], new_id=new_id)
            else:
                widget.report_conflict(new_id=new_id)
        else:
            widget.report_conflict(error_item, new_id=new_id)


def create_unique_item_name(item_name, unique_names_set):
    # Item name contains eg. _001 at the end
    __item_num_label = re.search('(?<=_)\d\d\d$', item_name)

    if __item_num_label:
        count = int(__item_num_label.group(0))
        base_name = f'{item_name[0:-4]}'
    else:
        count = 0
        base_name = f'{item_name}'

    # Generate unique name
    while item_name in unique_names_set:
        count += 1
        item_name = f'{base_name}_{count:03d}'

        if count >= 99:
            break

    return item_name


def update_reference_names(item_name, item_id, widget):
    for __i in widget.findItems(item_id, QtCore.Qt.MatchRecursive, ItemColumn.REF):
        __i.setText(ItemColumn.NAME, item_name)


def replace_invalid_chars(chars: str):
    """ Replace invalid file name characters """
    for k, v in INVALID_CHR.items():
        chars = chars.replace(k, v)
    return chars


def delete_tree_item_without_undo(item):
    """ Remove item from QTreeWidget without undo """
    if item.parent():
        __idx = item.parent().indexOfChild(item)
        item.parent().takeChild(__idx)
    else:
        widget = item.treeWidget()
        __idx = widget.indexOfTopLevelItem(item)
        widget.takeTopLevelItem(__idx)

    del item
