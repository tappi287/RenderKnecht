from modules.pos_schnuffi_xml_diff import PosDiff

from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5 import QtCore


class GuiCompare(QtCore.QThread):
    add_item = QtCore.pyqtSignal(object, object)
    finished = QtCore.pyqtSignal()

    item_flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)

    def __init__(self, old_path, new_path, widgets):
        super(GuiCompare, self).__init__()
        self.old_path, self.new_path = old_path, new_path

        self.widgets = widgets

    def run(self):
        diff = PosDiff(self.new_path, self.old_path)

        # Populate added tree widget
        self.add_list_items(diff.add_action_ls, 0)

        # Populate modified tree widget
        self.add_list_items(diff.mod_action_ls, 1)

        # Populate removed tree widget
        self.add_list_items(diff.rem_action_ls, 2)

        self.finished.emit()

    def add_list_items(self, action_list, target: int=0):
        """
        Create QTreeWidgetItem and add to target[int]
            0 - added widget
            1 - modified widget
            2 - removed widget
        """
        for al in action_list:
            item = self.__create_list_item(al)
            self.add_item.emit(item, self.widgets[target])

    @classmethod
    def __create_list_item(cls, al):
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
