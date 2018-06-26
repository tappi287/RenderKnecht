"""
knecht_tree_filter_thread for py_knecht. Asynchronos tree filtering

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
import re
import time
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QColor, QPalette

from modules.knecht_log import init_logging
from modules.app_globals import ItemColumn
from modules.tree_methods import iterate_item_childs

LOGGER = init_logging(__name__)


class filter_on_timer(QtCore.QObject):

    def __init__(self, txt_widget, tree_widget, **kwargs):
        super(filter_on_timer, self).__init__(txt_widget)
        # Init filter thread
        self.tree_filter_thread = TreeFilterThread()
        self.tree_filter_thread.create_thread()

        filter_children = True
        if kwargs.get('filter_children') is not None:
            filter_children = kwargs.get('filter_children')

        # Init filter
        self.filter = filter(self.tree_filter_thread, txt_widget, tree_widget,
                             kwargs['filter_column'], filter_children)

        # Init timer
        self.typing_timer = QtCore.QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.filter.filter_tree)

    def start_timer(self):
        self.typing_timer.start(350)

    def change_column(self, column):
        self.filter.change_column(column)

    def end_thread(self):
        self.tree_filter_thread.end_thread()


class filter:
    """ Filter TreeWidget with text from text widget """

    def __init__(self, filter_thread, txt_widget, tree_widget, column, filter_children=True):
        self.txt_widget = txt_widget
        self.tree_widget = tree_widget
        self.column = column
        self.filter_thread = filter_thread
        self.filter_children = filter_children

        self.txt_anim = BgrAnimation(txt_widget, (255, 255, 255))

    def filter_tree(self):
        txt = self.txt_widget.text()
        LOGGER.debug('Calling filter thread %s %s filtering children: %s', self.column, txt, self.filter_children)
        # Call filter thread
        self.filter_thread.filter_items(self.column, txt, self.tree_widget,
                                        pattern=1, filter_children=self.filter_children)

        if txt:
            self.txt_anim.active_pulsate()
        else:
            self.txt_anim.blink(1)

    def change_column(self, column):
        self.column = column


class TreeFilterThread(QtCore.QObject):
    """ Creates a worker thread to take search operations of the main GUI thread """
    request_filter = QtCore.pyqtSignal(list, str, QtWidgets.QTreeWidget, int, bool)

    def __init__(self):
        super(TreeFilterThread, self).__init__()
        self.thread = QtCore.QThread()
        self.obj = tree_worker_thread()

    def create_thread(self):
        # Move to thread
        self.obj.moveToThread(self.thread)

        # Signals from thread obj
        self.obj.item_idx.connect(self.hide_item)
        self.obj.scroll_to_item.connect(self.scroll_to)

        # Signals to thread obj
        self.request_filter.connect(self.obj.filter_widget)

        self.thread.finished.connect(self.report_thread_finish)

        # Start thread
        self.thread.start()

    def end_thread(self):
        self.thread.quit()

    @staticmethod
    def report_thread_finish():
        LOGGER.debug('Filter thread finished.')

    def filter_items(self,
                     column,
                     filter_txt: str,
                     tree_widget: QtWidgets.QTreeWidget,
                     pattern=1,
                     filter_children=True):
        # Search column to list
        if type(column) is not list:
            column = [column]

        self.request_filter.emit(column, filter_txt, tree_widget, pattern, filter_children)

    def get_item_from_index(self, index, widget):
        try:
            return widget.itemFromIndex(index)
        except Exception as e:
            LOGGER.error(
                'Tree filter thread could not manipulate item at index %s\n%s',
                index, e)
            return False

    def hide_item(self, index, widget, hide=False, expand: int = 0):
        """ Receives thread signal to hide/unhide or expand/collapse items """
        item = self.get_item_from_index(index, widget)
        if not item:
            return

        if hide:
            item.setHidden(True)
        else:
            item.setHidden(False)

        if expand == 1:
            item.setExpanded(True)
        elif expand == 2:
            item.setExpanded(False)

    def scroll_to(self, index, widget):
        item = self.get_item_from_index(index, widget)
        if not item:
            return

        widget.horizontalScrollBar().setSliderPosition(0)
        widget.scrollToItem(item)


class tree_worker_thread(QtCore.QObject):
    """ thread filters by provided string or id and signals items to show/hide """
    # ItemIndex, Tree Widget, hide true/false, expand = 0:skip 1:expand 2:collapse
    item_idx = QtCore.pyqtSignal(QtCore.QModelIndex, QtWidgets.QTreeWidget,
                                 bool, int)
    scroll_to_item = QtCore.pyqtSignal(QtCore.QModelIndex,
                                       QtWidgets.QTreeWidget)

    def __init__(self):
        super(tree_worker_thread, self).__init__()

    def filter_widget(self, column: int, txt, tree_widget, pattern, filter_children=True):
        """ Filter TreeWidget with text from text widget """

        def search_pattern(txt, pattern):
            if pattern == 1:
                search_pattern = ['(?=.*', ')']
                reg_search = search_pattern[0] + txt + search_pattern[1]
            elif pattern == 2:
                search_pattern = ['', '|']
                reg_search = search_pattern[0] + txt + search_pattern[1]

            return reg_search

        def iterate_parents(__item, __widget):
            def get_parent(__i):
                if __i.parent():
                    return __i.parent()
                return False

            __parent_item_list = list()

            while get_parent(__item):
                __c = get_parent(__item)
                __parent_item_list.append(__c)
                __item = __c

            __parent_item_list.append(__item)
            return __parent_item_list

        # Find "id 001" or "id 1 002 55 800" with regex
        # we extract groups of digits behind "id "
        id_search, result = False, False
        id = re.search('(id\s)(\d+)*(.*?\d+)+', txt)
        if id:
            match = id.group()
            id_search = set(re.split('.*?(\d+)', match))
            id_search.remove('')

        if txt is not '':
            LOGGER.debug('Filtering children: %s', filter_children)

            for item in self.iterate_tree_widget_items_flat(tree_widget):
                if not filter_children and item.parent():
                    continue

                index = tree_widget.indexFromItem(item)

                match = False

                # Match filter string(s)
                item_string = ''
                for c in column:
                    if item_string: item_string += ' '
                    item_string += item.text(c)

                reg_search = search_pattern(txt, 1)

                # Match multiple, space seperated, strings
                if ' ' in txt:
                    # Iterate every search string, separated by spaces
                    txt_string_set = set(txt.split(' '))

                    reg_search = ''
                    for txt_word in txt_string_set:
                        reg_search += search_pattern(txt_word, pattern)

                    if reg_search.endswith('|'):
                        reg_search = reg_search[:-1]

                # Search
                try:
                    result = re.search(
                        reg_search, item_string, flags=re.IGNORECASE)
                except Exception as e:
                    LOGGER.error(
                        'Invalid search pattern in filter. Skipping search.\n%s', e)

                if result:
                    match = True

                # Match Id String
                if id_search:
                    for item_id_str in [
                            item.text(ItemColumn.REF),
                            item.text(ItemColumn.ID)
                    ]:
                        for id_match in id_search:
                            if id_match == item_id_str:
                                match = True

                if match:
                    # Show result
                    self.delayed_signal(index, tree_widget, False, 0)

                    # Item has parents?
                    for parent in iterate_parents(item, tree_widget):
                        parent_index = tree_widget.indexFromItem(parent)

                        if parent_index:
                            # Show and expand parent
                            self.delayed_signal(parent_index, tree_widget, False, 1)
                else:
                    # Hide items
                    self.delayed_signal(index, tree_widget, True, 0)
        else:
            for item in self.iterate_tree_widget_items_flat(tree_widget):
                # Show everything and collapse parents
                index = tree_widget.indexFromItem(item)
                parent_index = tree_widget.indexFromItem(item.parent())

                # Un-hide all
                self.delayed_signal(index, tree_widget, False, 0)

                if parent_index:
                    # Show and collapse parent
                    self.delayed_signal(parent_index, tree_widget, False, 2)

                # Scroll to selection
                if item.isSelected():
                    self.scroll_to_item.emit(index, tree_widget)

    def iterate_tree_widget_items_flat(self, widget):
        """ Creates an item list in flat hierachy of all TreeWidget items """
        item_list = []
        it = QtWidgets.QTreeWidgetItemIterator(widget)

        while it.value():
            # item_list.append(it.value())
            yield it.value()
            it += 1

        # return item_list

    def delayed_signal(self, index: QtCore.QModelIndex,
                       widget: QtWidgets.QTreeWidget, hide: bool, expand: int):
        self.item_idx.emit(index, widget, hide, expand)


class BgrAnimation(QtCore.QObject):

    def __init__(self, parent, bg_color: tuple=None):
        super(BgrAnimation, self).__init__(parent)
        self.parent = parent
        self._color = QColor()

        self.bg_color = self.parent.palette().color(QPalette.Background)

        if bg_color:
            self.bg_color = QColor(*bg_color)

        self.color_anim = QtCore.QPropertyAnimation(self, b'backColor')
        self.color_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        self.setup_blink()

        self.pulsate_anim = QtCore.QPropertyAnimation(self, b'backColor')
        self.pulsate_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuint)
        self.setup_pulsate()

    def setup_blink(self, anim_color: tuple=(26, 118, 255)):
        start_color = self.bg_color
        anim_color = QColor(*anim_color)

        self.color_anim.setStartValue(start_color)
        self.color_anim.setKeyValueAt(0.5, anim_color)
        self.color_anim.setEndValue(start_color)

        self.color_anim.setDuration(600)

    def blink(self, num: int=1):
        self.pulsate_anim.stop()
        self.color_anim.setLoopCount(num)
        self.color_anim.start()

    def setup_pulsate(self, anim_color: tuple=(255, 80, 50)):
        start_color = self.bg_color
        anim_color = QColor(*anim_color)

        self.pulsate_anim.setStartValue(start_color)
        self.pulsate_anim.setKeyValueAt(0.5, anim_color)
        self.pulsate_anim.setEndValue(start_color)

        self.pulsate_anim.setDuration(4000)

    def active_pulsate(self, num: int=-1):
        self.pulsate_anim.setLoopCount(num)
        self.pulsate_anim.start()

    def get_back_color(self):
        return self._color

    def set_back_color(self, color):
        self._color = color

        qss_color = f'rgb({color.red()}, {color.green()}, {color.blue()})'
        try:
            self.parent.setStyleSheet('background-color: ' + qss_color + ';')
        except AttributeError as e:
            LOGGER.debug('Error setting widget background color: %s', e)

    backColor = QtCore.pyqtProperty(QColor, get_back_color, set_back_color)
