"""
gui_set_path module provides a file dialog for selecting paths or a line edit to paste and display the chosen path

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
import os.path
from pathlib import Path
from PyQt5 import QtCore, QtWidgets

from modules.app_strings import Msg


class SetDirectoryPath(QtCore.QObject):
    path_changed = QtCore.pyqtSignal(Path)

    def __init__(self, app, ui, mode='dir',
                 line_edit=None,
                 tool_button=None,
                 dialog_args=()):
        super(SetDirectoryPath, self).__init__()
        self.app, self.ui, self.line_edit, self.tool_button = app, ui, line_edit, tool_button
        self.mode = mode

        self.path = None

        if self.tool_button:
            self.dialog_args = dialog_args
            self.tool_button.pressed.connect(self.btn_open_dialog)

        if self.line_edit:
            self.line_edit.editingFinished.connect(self.path_text_changed)

    def btn_open_dialog(self):
        current_path = Path('.') or self.ui.current_path

        if self.line_edit:
            line_edit_path = Path(self.line_edit.text())

            if line_edit_path.exists():
                current_path = line_edit_path
            else:
                current_path = Path('.')

        self.get_directory_file_dialog(current_path, *self.dialog_args)

    def get_directory_file_dialog(self, current_path, title=Msg.PATH_DIALOG, file_filter='(*.*)'):
        if not Path(current_path).exists() or current_path == '':
            current_path = Path(self.ui.current_path)
        else:
            current_path = Path(current_path)

        if self.mode == 'dir':
            current_path = QtWidgets.QFileDialog.getExistingDirectory(
                self.ui, caption=title, directory=current_path.as_posix()
            )
            if not current_path:
                return
        else:
            current_path, file_type = QtWidgets.QFileDialog.getOpenFileName(
                self.ui, caption=title, directory=current_path.as_posix(), filter=file_filter
            )
            if not file_type:
                return

        current_path = Path(current_path)

        self.set_path(current_path)

        return current_path

    def set_path(self, current_path):
        current_path = Path(current_path)
        if not current_path.exists():
            return

        # Update line edit
        self.set_path_text(current_path)

        # Emit change
        self.path_changed.emit(current_path)

        # Set own path var
        self.path = current_path

    def set_path_text(self, current_path):
        if not self.line_edit:
            return

        self.line_edit.setText(current_path.as_posix())

    def path_text_changed(self):
        """ line edit text changed """
        text_path = self.line_edit.text()

        if os.path.exists(text_path):
            text_path = Path(text_path)

            if self.path:
                if text_path != self.path:
                    self.set_path(text_path)
            else:
                self.set_path(text_path)
