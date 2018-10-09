from modules.pos_schnuffi_xml_diff import PosDiff

from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5 import QtCore


class GuiCompare(QtCore.QThread):
    add_item = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    error_report = QtCore.pyqtSignal(str)

    item_flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)

    def __init__(self, old_path, new_path, widgets, cmp_queue):
        super(GuiCompare, self).__init__()
        self.old_path, self.new_path = old_path, new_path
        self.cmp_queue = cmp_queue

        self.widgets = widgets

    def run(self):
        diff = PosDiff(self.new_path, self.old_path)

        # Populate added tree widget
        self.add_action_list_items(diff.add_action_ls, 0)

        # Populate modified tree widget
        self.add_action_list_items(diff.mod_action_ls, 1)

        # Populate removed tree widget
        self.add_action_list_items(diff.rem_action_ls, 2)

        # Populate error tab widget
        self.error_report.emit(diff.error_report)

        # Populate actor widgets
        self.add_actor_items(diff)

        self.finished.emit()

    def add_action_list_items(self, action_list, target: int=0):
        """
        Create QTreeWidgetItem and add to target[int]
            0 - added widget
            1 - modified widget
            2 - removed widget
        """
        for al in action_list:
            item = self.__create_action_list_item(al)
            self.add_item_queued(item, self.widgets[target])

    def add_actor_items(self, diff_cls: PosDiff):
        """
        Create switches/looks items
            target 0 - switches, 1 - looks
        """
        for target in range(0, 2):
            add_item = QTreeWidgetItem(['0 Actors - hinzugefügt(kommen -nur- in neuer Xml vor)'])
            rem_item = QTreeWidgetItem(['1 Actors - entfernt(in neuer Xml nicht mehr verwendet)'])
            mod_item = QTreeWidgetItem(['2 Actors - geändert(Häufigkeit der Verwendung oder Werte verändert)'])

            if target == 0:
                widget = self.widgets[3 + target]
                add_set, rem_set, mod_set = diff_cls.add_switches, diff_cls.rem_switches, diff_cls.mod_switches
            elif target == 1:
                widget = self.widgets[3 + target]
                add_set, rem_set, mod_set = diff_cls.add_looks, diff_cls.rem_looks, diff_cls.mod_looks

            for parent, actor_set in zip(
                    [add_item, rem_item, mod_item],
                    [add_set, rem_set, mod_set]
                    ):
                for actor in actor_set:
                    item = QTreeWidgetItem(parent, [actor])
                    item.setFlags(self.item_flags)

                if parent.childCount():
                    self.add_item_queued(parent, widget)

    def add_item_queued(self, item, widget):
        self.add_item.emit()
        __q = (item, widget)
        self.cmp_queue.put(__q)

    @classmethod
    def __create_action_list_item(cls, al):
        list_item = QTreeWidgetItem([al.name])
        list_item.setFlags(cls.item_flags)

        for __a in al.actors.items():
            actor, a = __a
            value = a.get('new_value') or ''
            old_value = a.get('old_value') or ''
            actor_type = a.get('type') or ''

            if not actor:
                actor = ''

            actor_item = QTreeWidgetItem(list_item, [actor, value, old_value, actor_type])
            actor_item.setFlags(cls.item_flags)

        return list_item
