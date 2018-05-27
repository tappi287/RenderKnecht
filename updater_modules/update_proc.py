import sys
import gui.preset_editor_rsc_rc

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.uic import loadUi


class UpdaterWidget(QWidget):
    def __init__(self, parent):
        super(UpdaterWidget, self).__init__()

        self.parent = parent
        loadUi('gui/RenderKnecht_Updater.ui', self)


class UpdaterGui(QApplication):
    """ Main GUI Application """
    def __init__(self):
        super(UpdaterGui, self).__init__(sys.argv)

        self.widget = UpdaterWidget(self)
        self.widget.show()


class UpdaterApp:
    def __init__(self):
        update_app = UpdaterGui()

        update_app.exec_()


if __name__ == "__main__":
    update_app = UpdaterGui()

    update_app.exec_()