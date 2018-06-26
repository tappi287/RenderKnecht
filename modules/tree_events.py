"""
tree_events for py_knecht. Provides keyboard functioniality.

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

from PyQt5 import QtCore
from PyQt5.QtGui import QMouseEvent

from modules.app_globals import ItemColumn
from modules.app_strings import Msg
from modules.knecht_log import init_logging
from modules.tree_methods import delete_command, lead_zeros

# Initialize logging for this module
LOGGER = init_logging(__name__)

# Initialize column values
ItemColumn()


class TreeKeyEvents(QtCore.QObject):
    """
    Bind key events to tree widgets
    """
    mouse_signal = QtCore.pyqtSignal(QtCore.QPoint)

    def __init__(self, widget, ui, app, wizard: bool = False, no_edit: bool = False, **kwargs):
        # Init QtCore.QObject because installEventFilter will init on a QtCore.QObject instance(self)
        super().__init__()
        self.widget = widget
        self.ui = ui
        self.app = app
        self.wizard = wizard
        self.no_edit = no_edit

    def tab_key_pressed(self):
        """ Jump to next item and enter edit mode """
        item = self.widget.currentItem()
        if item is None:
            return False
        col = self.widget.currentColumn()

        # Jump to next column
        if col < self.widget.columnCount():
            col += 1
            self.widget.setCurrentItem(item, col)
            self.widget.editItem(item, col)
            return True

        return False

    def add_event_filter(self):
        # Install event filter
        self.widget.installEventFilter(self)

    def rem_event_filter(self):
        # Uninstall event filter
        self.widget.removeEventFilter(self)

    def eventFilter(self, obj, event):
        # Prevent super rare occasion were NoneType calls happen
        if obj is None:
            return False
        if event is None:
            return False

        if obj is self.widget:
            # LOGGER.debug('Event: %s - %s - %s', event.type(), type(event), event)

            if event.type() == QtCore.QEvent.KeyPress:
                # numpad_mod = int(event.modifiers()) & QtCore.Qt.KeypadModifier

                if event.key() == QtCore.Qt.Key_Delete and not self.no_edit:  # Delete
                    if self.wizard:
                        return False
                    delete_command(self.widget)
                    return True

                if event.key() == QtCore.Qt.Key_Up and not self.no_edit:  # Up Arrow | NUM_PAD 8
                    self.move(-1)
                    return True

                if event.key() == QtCore.Qt.Key_Down and not self.no_edit:  # Down Arrow | NUM_PAD 2
                    self.move(1)
                    return True

                if event.key() == QtCore.Qt.Key_PageUp and not self.no_edit:  # Page up
                    self.move(-10)
                    return True

                if event.key() == QtCore.Qt.Key_PageDown and not self.no_edit:  # Page down
                    self.move(10)
                    return True

                if event.key() == QtCore.Qt.Key_multiply:  # NUM_PAD *
                    if self.wizard:
                        return False
                    self.ui.sort_tree_widget.sort_current_level(self.widget.currentItem())
                    return True

                if event.key() == QtCore.Qt.Key_Tab and not self.no_edit:  # Tab Key in non-edit mode
                    if self.wizard:
                        return False
                    if not self.tab_key_pressed():
                        return False
                    return True

                if event.key() == QtCore.Qt.Key_D and event.modifiers() == QtCore.Qt.ControlModifier:
                    # De-select
                    self.widget.clearSelection()
                    return True

                # Undo, Redo
                if self.app:
                    if event.key() == QtCore.Qt.Key_Z and event.modifiers() == QtCore.Qt.ControlModifier:
                        if self.wizard:
                            return False
                        self.app.undo_grp.undo()
                        return True

                    if event.key() == QtCore.Qt.Key_Y and event.modifiers() == QtCore.Qt.ControlModifier:
                        if self.wizard:
                            return False
                        self.app.undo_grp.redo()
                        return True

                    if event.key() == QtCore.Qt.Key_R and event.modifiers() == QtCore.Qt.ControlModifier:
                        # Select Ref
                        if self.wizard:
                            return False
                        self.ui.actionSelectRef.trigger()
                        return True

                    # Copy, Cut, Paste - redundant but doesn't work flawlessly with only shortcuts in SchnuffiWindow
                    if event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
                        # Select Ref
                        if self.wizard:
                            return False
                        self.ui.actionCopy.trigger()
                        return True

                    if event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
                        # Select Ref
                        if self.wizard:
                            return False
                        self.ui.actionPaste.trigger()
                        return True

                    if event.key() == QtCore.Qt.Key_X and event.modifiers() == QtCore.Qt.ControlModifier:
                        # Select Ref
                        if self.wizard:
                            return False
                        self.ui.actionCut.trigger()
                        return True

                if event.key() in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Escape):  # Backspace clears filter
                    if self.widget.filter_txt_widget.text() == '':
                        # Make sure we trigger a filter event
                        self.widget.filter_txt_widget.setText('-')

                    self.widget.filter_txt_widget.setText('')
                    self.widget.info_overlay.display(Msg.OVERLAY_FILTER_RESET, 2000, True)
                    return True

                # Send alphanumeric keys to LineEdit filter widget
                filter_keys = [QtCore.Qt.Key_Space, QtCore.Qt.Key_Underscore, QtCore.Qt.Key_Minus]

                if event.text().isalnum() or event.key() in filter_keys:
                    filter_txt = self.widget.filter_txt_widget.text()
                    filter_txt += event.text()
                    overlay_txt = Msg.OVERLAY_FILTER + filter_txt

                    self.widget.info_overlay.display(overlay_txt, 1500, True)
                    self.widget.filter_txt_widget.setText(filter_txt)
                    return True

                return False

            return False

        return False

    def move(self, amount: int):
        item_list = self.widget.selectedItems()
        self.amount = amount

        if self.amount > 0:
            # Iterate backwards if items should be moved down
            for item in item_list[::-1]:
                self.move_item(item)
        else:
            # Iterate forward if items should be moved up
            for item in item_list:
                self.move_item(item)

    def move_item(self, item):
        # Collapse if top level Item
        # otherwise itemBelow will return children if expanded
        if not item.parent():
            item.setExpanded(False)

        if not item.text(ItemColumn.ORDER).isdigit():
            self.index_move(item, self.amount, self.widget)
            return

        # Calculate new order
        order = self.sum(int(item.text(ItemColumn.ORDER)), self.amount)

        # Move items below or above that have matching/conflicting order
        self.move_item_with_conflicting_order(item, order)

        # Rewrite order value
        item.setText(ItemColumn.ORDER, order)

        # Scroll to item
        self.widget.scrollToItem(item)

        # Sort items on same level
        self.ui.sort_tree_widget.sort_current_level(item)

    @staticmethod
    def index_move(item, amount, widget, new_idx: int = None):
        parent = item.parent()

        if parent:
            idx = parent.indexOfChild(item)

            max_idx = parent.childCount() - 1
            if not new_idx:
                new_idx = max(0, min(max_idx, idx + amount))

            item = parent.takeChild(idx)
            parent.insertChild(new_idx, item)
            widget.clearSelection()
            item.setSelected(True)
        else:
            idx = widget.indexOfTopLevelItem(item)

            max_idx = widget.topLevelItemCount() - 1
            if not new_idx:
                new_idx = max(0, min(max_idx, idx + amount))

            item = widget.takeTopLevelItem(idx)
            widget.insertTopLevelItem(new_idx, item)
            widget.clearSelection()
            item.setSelected(True)

    def move_item_with_conflicting_order(self, item, order):
        """ If item with that order num exists move it one above/below """
        conflicting_order = False

        if self.amount > 0:
            if self.widget.itemBelow(item) is not None:
                conflicting_order = self.widget.itemBelow(item).text(ItemColumn.ORDER)
                conflicting_item = self.widget.itemBelow(item)
        else:
            if self.widget.itemAbove(item) is not None:
                conflicting_order = self.widget.itemAbove(item).text(ItemColumn.ORDER)
                conflicting_item = self.widget.itemAbove(item)

        if conflicting_order:
            # Get order sring of conflicting_item
            if order == conflicting_order:
                conflicting_order = self.sum(order, -self.amount)
                conflicting_item.setText(ItemColumn.ORDER, conflicting_order)

    def sum(self, order, amount: int):
        # Set to zero if order string is not a number
        if not str(order).isdigit(): order = 0

        # Add amount, stay above zero
        order = max(0, int(order) + amount)

        # Return as string with leading zeros
        return lead_zeros(order)


class CopyVariantsKeyEvents(QtCore.QObject):
    """ Keyboard Shortcuts to copy Variants to destination tree """
    def __init__(self, parent, ui):
        super(CopyVariantsKeyEvents, self).__init__(parent)
        self.parent = parent
        self.ui = ui

        self.parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        # Prevent super rare occasion were NoneType calls happen
        if obj is None:
            return False
        if event is None:
            return False

        if obj is self.parent:
            if event.type() == QtCore.QEvent.KeyPress:
                if event.key() == QtCore.Qt.Key_Left and event.modifiers() == QtCore.Qt.ControlModifier:
                    # Select Ref
                    self.ui.treeWidget_Variants.context.add_var_preset.trigger()
                    return True

                if event.key() == QtCore.Qt.Key_Left and event.modifiers() == QtCore.Qt.AltModifier:
                    # Select Ref
                    self.ui.treeWidget_Variants.context.add_var.trigger()
                    return True

                if event.key() == QtCore.Qt.Key_Delete and event.modifiers() == QtCore.Qt.ControlModifier:
                    # Clear Variants tree
                    self.ui.treeWidget_Variants.clear_tree()
                    return True

        return False
