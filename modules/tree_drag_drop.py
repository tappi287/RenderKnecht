"""
knecht_preset_editor_drag_drop for py_knecht. Provides drag and drop functioniality.

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
from pathlib import Path

from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5 import QtCore

from modules.knecht_img_viewer import KnechtImageViewer
from modules.knecht_log import init_logging
from modules.app_globals import ItemColumn
from modules.tree_methods import add_selected_childs_as_top_level, add_top_level_item
from modules.tree_methods import get_column_values, AddRemoveItemsCommand, swap_item_order, re_order_items
from modules.tree_methods import update_tree_ids, VAR_LEVEL_ITEM_FLAGS, object_is_tree_widget
from modules.tree_methods import tree_setup_header_format, lead_zeros, TOP_LEVEL_ITEM_FLAGS

# Initialize logging for this module
LOGGER = init_logging(__name__)


class TreeInternalDrop(QTreeWidget):
    """
        Sub class QTreeWidget to emit signal on internal drag and drop
        class name is promoted in QtDesigner
    """
    internalDrop = QtCore.pyqtSignal(QTreeWidget, list, object)
    overlayPos = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, parent):
        super(TreeInternalDrop, self).__init__()
        self.parent = parent
        self.parent.setMouseTracking(True)

        # Worker class instance
        self.internal_drag_drop = InternalDragDrop(self)

        # Connect internal drop signal
        self.internalDrop.connect(self.internal_drag_drop.drop_action)

    def dropEvent(self, QDropEvent):
        mime = QDropEvent.mimeData()  # type: QtCore.QMimeData
        source = QDropEvent.source()
        item_list = self.selectedItems()
        destination_item = self.itemAt(QDropEvent.pos())

        if source is self:
            self.internalDrop.emit(source, item_list, destination_item)
            self.overlayPos.emit(QDropEvent.pos())

        QDropEvent.ignore()


def get_item_at_drop_pos(widget, drop_pos):
    """ Get TreeWidget item at drop / mouse position """
    # Substract header from drop position
    header_height = widget.header().height()
    corrected_drop_pos = QtCore.QPoint(drop_pos.x(),
                                       drop_pos.y() - header_height)

    # Match cursor drop position in items
    item = widget.itemAt(corrected_drop_pos)

    # Emit position for overlay
    widget.overlayPos.emit(corrected_drop_pos)

    # LOGGER.debug('Corrected drop position: %s', corrected_drop_pos)

    return item


class WidgetToWidgetDrop(QtCore.QObject):
    """
    Makes src QTreeWidget items dropable in dest QTreeWidget
    and copies the items incl child items.
    """

    def __init__(self, ui, ui_tree_widget_src, ui_tree_widget_dest, **kwargs):
        # Init QtCore.QObject because installEventFilter will init on a QtCore.QObject instance(self)
        super(WidgetToWidgetDrop, self).__init__()

        self.ui = ui
        self.ui_tree_widget_src = ui_tree_widget_src
        self.ui_tree_widget_dest = ui_tree_widget_dest

        # Get kwargs attributes
        options = {
            # Copy top level items or only child items
            'only_childs': False,
            # Create new preset if dropped from Widget
            'create_preset_on_drop_from': None
        }

        options.update(kwargs)

        self.only_childs = options['only_childs']
        self.create_preset_on_drop_from = options['create_preset_on_drop_from']

        # Count created 'User Presets' for unique naming
        self.preset_name_count = 0

        # Adjust column widths on first drop
        self.first_drop = True

        # Install event filter
        self.ui_tree_widget_dest.installEventFilter(self)

    def eventFilter(self, obj, event):
        # ------------------------------
        # Widget to Widget Drag and Drop
        # ------------------------------
        if event.type() == QtCore.QEvent.DragEnter:
            # Indicate that item will be copied
            if obj is self.ui_tree_widget_dest:
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
            src = event.source()
            LOGGER.debug('Widget to Widget Drop_event')

            mime = event.mimeData()
            if self.file_drop(mime):
                return True

            # Drop to destination
            if obj is self.ui_tree_widget_dest:
                event.setDropAction(QtCore.Qt.CopyAction)

                # Get item at drop position
                dest = get_item_at_drop_pos(obj, event.pos())

                # If dropped on child item, destination to parent
                if dest is not None:
                    if dest.parent():
                        dest = dest.parent()

                    if dest.UserType == 1005:
                        # Don't drop on seperator
                        dest = None

                # If no item was hit
                if dest is None:
                    # Set destination to destination QTreeWidget
                    dest = self.ui_tree_widget_dest

                    # Set destination to new preset(topLevelItem) if self.create_preset
                    # on_drop_from QTreeWidget equals source QTreeWidget
                    if src is self.create_preset_on_drop_from:
                        # Create "unique" name
                        self.preset_name_count += 1

                        # Id in use?
                        item_id = update_tree_ids(dest, self.ui, '0', self.ui.treeWidget_SrcPreset)
                        preset_name = 'User_Preset_' + lead_zeros(
                            self.preset_name_count)

                        # Create new preset item behind existing items and set as destination
                        order = dest.topLevelItemCount() + 1

                        # ['order', 'name', 'value', 'type', 'reference', 'item_id']
                        dest = add_top_level_item(
                            dest, [order, preset_name, '', 'preset', '', item_id],
                            TOP_LEVEL_ITEM_FLAGS, 1000)

                        self.ui.sort_tree_widget.sort_all(dest)
                else:
                    # Ignore drop on item if only childs should be copied
                    if self.only_childs:
                        dest = self.ui_tree_widget_dest

                # Source widget(s) is list of widgets or single widget
                if type(self.ui_tree_widget_src) is list:
                    for src_widget in self.ui_tree_widget_src:
                        if src is src_widget:
                            self.drop_action(src, dest)
                            event.accept()
                else:
                    if src is self.ui_tree_widget_src:
                        self.drop_action(src, dest)
                        event.accept()

                return True

            # Ignore if neither source or destination widget is hit
            event.ignore()
            return False

        return False

    def drop_action(self, src, dest):
        """ Copy selected items """

        if not self.only_childs:
            LOGGER.debug('Drop from %s to %s',
                         type(src).__name__,
                         type(dest).__name__)

            # Copy to destination item or tree_widget
            self.ui.add_selected_top_level_items.Run(src, dest)
        else:
            # Copy only the child items
            add_selected_childs_as_top_level(src, dest, self.ui)

        # Adjust column widths on first drop
        if self.first_drop:
            # Make sure this is a Widget and no item
            if object_is_tree_widget(dest):
                self.first_drop = False
                tree_setup_header_format(dest)

    def file_drop(self, mime):
        if not mime.hasUrls():
            return False

        if not mime.urls()[0].isLocalFile():
            return False

        file_url = mime.urls()[0].toLocalFile()

        if Path(file_url).suffix.casefold() in KnechtImageViewer.FILE_TYPES:
            # Start image viewer
            self.ui.app_class.menu.start_image_viewer(file_url)
            return True

        return False


class InternalDragDrop(QtCore.QObject):
    """ Internal Drag and Drop """

    def __init__(self, widget):
        super(InternalDragDrop, self).__init__()
        self.widget = widget
        self.ui = self.copy = self.no_internal_drag_drop = None

    def setup_ui(self, ui, no_internal_drag_drop=False):
        """ Main Window provides it's class on construction """
        self.ui = ui
        self.copy = self.ui.add_selected_top_level_items.Run
        self.no_internal_drag_drop = no_internal_drag_drop

    def drop_action(self, source_widget, src_item_list, dest_item):
        if self.no_internal_drag_drop:
            return False

        sort_items = self.ui.sort_tree_widget
        # SortTree(self.ui, source_widget)
        # just for visual indication
        copy = False

        # Dropped to empty area, create copy
        if dest_item is None:
            self.copy(source_widget, self.widget)
            source_widget.overlay.copy_created()
            return

        for src_item in src_item_list:
            # ---------------------
            # Destination and Source are var / ref
            if dest_item.UserType in [1001, 1002] and src_item.UserType in [1001, 1002]:
                if src_item.parent() and dest_item.parent():
                    if src_item.parent() is dest_item.parent():
                        # Re-order
                        swap_item_order(src_item, dest_item)

                        # Re-Order all children
                        sort_items.sort_current_level(src_item)

                        LOGGER.debug('Variant %s moved to %s', src_item.text(ItemColumn.NAME),
                                     dest_item.text(ItemColumn.NAME))
                    else:
                        order = int(dest_item.text(ItemColumn.ORDER))

                        # Copy all selected items at once
                        self.copy(src_item_list,
                                  dest_item.parent(),
                                  src_is_itemlist=True,
                                  new_src_order=order)

                        # Cancel loop, copy worker started with item list
                        return

            # ---------------------
            # Destination is preset and Source is var / ref
            elif dest_item.UserType == 1000 and src_item.UserType in [1001, 1002]:
                if dest_item != src_item.parent():
                    # Destination is different preset, copy variant to top
                    value_list = get_column_values(src_item)
                    # Re-order to top
                    value_list[0] = lead_zeros(0)

                    # Create new item in destination
                    new_item = QTreeWidgetItem(dest_item, value_list)
                    new_item.UserType = src_item.UserType
                    new_item.setFlags(VAR_LEVEL_ITEM_FLAGS)

                    # Re-order
                    re_order_items(new_item, 0, dest_item)
                    sort_items.sort_current_level(new_item)

                    # Undo command
                    AddRemoveItemsCommand.add(
                        self.widget, [new_item], txt='zu Preset hinzufügen')

                    # Visual indication
                    copy = True
                    LOGGER.debug('Variant %s copied to top of %s',
                                 src_item.text(ItemColumn.NAME), dest_item.text(ItemColumn.NAME))
                else:
                    # Destination is same preset put variant to top
                    re_order_items(src_item, 0, dest_item)

                    # Re-Order all children
                    sort_items.sort_current_level(src_item)
                    LOGGER.debug('Variant %s re-ordered to top of %s',
                                 src_item.text(ItemColumn.NAME), dest_item.text(ItemColumn.NAME))

            # ---------------------
            # Source is preset, create reference
            if src_item.UserType == 1000:
                # Create reference at top of preset
                if dest_item.UserType in [1000, 1003]:
                    new_items = self.ui.find_reference_items.check_reference(
                        0, src_item, dest_item)

                    # Undo command
                    if new_items:
                        # Re-order item position
                        re_order_items(new_items[0], 0, dest_item)

                        AddRemoveItemsCommand.add(
                            self.widget, new_items, txt='Referenz erstellen')

                        # Re-order
                        sort_items.sort_current_level(new_items[0])

                    LOGGER.debug('Reference created %s at to top of %s',
                                 src_item.text(1), dest_item.text(1))

                # Create reference at variant position
                if dest_item.UserType in [1001, 1002]:
                    order = int(dest_item.text(ItemColumn.ORDER))
                    new_items = self.ui.find_reference_items.check_reference(
                        order, src_item, dest_item.parent())

                    if new_items:
                        # Swap order
                        swap_item_order(new_items[0], dest_item)

                        # Undo command
                        AddRemoveItemsCommand.add(
                            self.widget,
                            new_items,
                            txt='Referenz an Varianten Position erstellen')

                        # Re-order
                        sort_items.sort_current_level(new_items[0])

                    LOGGER.debug(
                        'Reference created %s at variant position %s in %s',
                        src_item.text(1), order,
                        dest_item.parent().text(1))

        if copy:
            source_widget.overlay.copy_created()


class render_tree_drop(QtCore.QObject):

    def __init__(self, ui, tree_widget_src, tree_widget_dest, **kwargs):
        # Init QtCore.QObject because installEventFilter will init on a QtCore.QObject instance(self)
        super().__init__()
        self.ui = ui
        self.src_widget = tree_widget_src
        self.dest_widget = tree_widget_dest

        # self.ui_tree_widget_dest.setAcceptDrops(True)

        self.dest_widget.installEventFilter(self)

    @staticmethod
    def check_items(items):
        """ Check if items contain either *only* Preset or
        *only* Render Preset items """
        __contains_only_render = True
        __contains_only_preset = True

        for item in items:
            # Allow either RenderPreset or Preset items
            # but not both at the same time
            if item.UserType != 1003:
                __contains_only_render = False

            if item.UserType != 1000:
                __contains_only_preset = False

        return __contains_only_render, __contains_only_preset

    def copy_items(self):
        self.ui.add_selected_top_level_items.Run(
            self.src_widget, self.dest_widget)

        self.ui.sort_tree_widget.sort_all(
            self.dest_widget)

    def eventFilter(self, obj, event):
        if obj is self.dest_widget:
            if event.type() == QtCore.QEvent.DragEnter:
                if event.source() is self.src_widget:
                    self.drop_allowed = False

                    only_presets, only_render = self.check_items(
                        self.src_widget.selectedItems())

                    if only_presets or only_render:
                        self.drop_allowed = True

                    if self.drop_allowed:
                        # Indicate that item will be copied
                        event.setDropAction(QtCore.Qt.CopyAction)
                        event.accept()
                        return True

                    event.ignore()
                    return False

            if event.type() == QtCore.QEvent.DragMove:
                event.accept()
                return True
            if event.type() == QtCore.QEvent.DragLeave:
                event.accept()
                return True

            if event.type() == QtCore.QEvent.Drop:
                if event.source() is self.src_widget:
                    is_render, is_preset = self.check_items(
                        self.src_widget.selectedItems())

                    if is_render:
                        self.copy_items()
                        return True
                    elif is_preset:
                        # Create Render Preset from selection
                        self.src_widget.context.render_preset_action.trigger()
                        # Context changes selection to created render preset
                        self.copy_items()
                        return True
        return False
