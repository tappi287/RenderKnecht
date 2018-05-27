"""
knecht_widgets stores widgets for the main GUI

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

import logging
import qt_ledwidget
from functools import partial
from pathlib import Path
from datetime import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUi

from modules.knecht_fakom_lutscher import FakomLutscher
from modules.app_globals import Itemstyle, UI_FILE_FAKOM_WINDOW, UI_FILE_ABOUT_WINDOW, HELPER_DIR
from modules.knecht_settings import knechtSettings
from modules.app_strings import Msg
from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)


class AboutBox(QtWidgets.QDialog):

    def __init__(self, parent, title: str = '', headline: str = '', message: str = ''):
        super(AboutBox, self).__init__(parent)

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)
        loadUi(UI_FILE_ABOUT_WINDOW, self)
        logging.root.setLevel(log_level)

        # Hide context help
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        rect = parent.geometry()
        w, h = 700, 800
        x, y = rect.width() / 2 - 450, rect.y() + 50
        self.setGeometry(x, y, w, h)

        if title:
            self.setWindowTitle(title)
        if headline:
            self.titleLabel.setText(headline)
        if message:
            self.descLabel.setText(message)


class styleChooser(QtWidgets.QDialog):

    def __init__(self, parent):
        super(styleChooser, self).__init__()
        rect = parent.geometry()

        self.setGeometry(rect.x() + 100, rect.y() + 100, 400, 70)
        self.setWindowTitle('Anwendungsstil')
        self.setWindowIcon(parent.icon[Itemstyle.TYPES['options']])

        # Hide context help
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        self.v_layout = QtWidgets.QVBoxLayout(self)
        self.v_layout.setContentsMargins(13, 13, 13, 13)
        self.v_layout.setSpacing(9)
        self.box_layout = QtWidgets.QHBoxLayout(self)
        self.box_layout.setContentsMargins(0, 0, 0, 0)
        self.box_layout.setSpacing(9)

        self.label = QtWidgets.QLabel(self)
        self.label.setText('Anwendung zum übernehmen neu starten.')
        self.v_layout.addWidget(self.label)
        self.v_layout.addLayout(self.box_layout)

        # Current style options
        box_items = ['windowsvista', 'Windows', 'Fusion', 'Fusion-dark']

        # Combo box
        self.combo_box = QtWidgets.QComboBox(self)
        self.combo_box.addItems(box_items)
        self.combo_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.box_layout.addWidget(self.combo_box)

        # Set combo box to current style
        for idx, style_setting in enumerate(box_items):
            if style_setting == knechtSettings.app['app_style']:
                self.combo_box.setCurrentIndex(idx)

        # OK btn
        self.btn = QtWidgets.QPushButton(self)
        self.btn.setText('Okay')
        self.btn.pressed.connect(self.set_style)
        self.box_layout.addWidget(self.btn)

    def set_style(self):
        style = self.combo_box.currentText()
        knechtSettings.app['app_style'] = style
        self.accept()


class FakomWindow(QtWidgets.QDialog):
    """ FakomLutscher window to determine paths """

    def __init__(self, parent, app, wizard: bool=False, widget=None):
        super(FakomWindow, self).__init__(parent)

        # Parent should be MainWindow
        self.parent, self.app, self.ui, self.wizard, self.widget = parent, app, app.ui, wizard, widget

        # Instance
        self.fakom_lutscher = ''

        # Paths
        self.fakom_path = False
        self.vplus_path = False

        # Hide context help
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)
        loadUi(UI_FILE_FAKOM_WINDOW, self)
        logging.root.setLevel(log_level)

        # Ok | Cancel btns
        self.buttonBox.accepted.connect(self.exit_accept)
        self.buttonBox.rejected.connect(self.exit_abort)

        # Tool btns FileDialog
        self.toolButton_changeFakomPath.pressed.connect(partial(self.path_dialog, 0))
        self.toolButton_changeVplusPath.pressed.connect(partial(self.path_dialog, 1))
        self.lineEdit_fakomPath.mousePressEvent = self.fakomPath_clickEvent
        self.lineEdit_vplusPath.mousePressEvent = self.vplusPath_clickEvent

        # Read package option
        self.create_pkg_box.stateChanged.connect(self.toggle_pkg_checkbox)

    def toggle_pkg_checkbox(self, e):
        LOGGER.debug('FaKom read pkg option: %s', self.create_pkg_box.isChecked())

    def fakomPath_clickEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.path_dialog(0)

    def vplusPath_clickEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.path_dialog(1)

    def path_dialog(self, path_id, dlg_path=''):
        """ Get the path and set it """
        dlg = QtWidgets.QFileDialog()
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)

        if dlg_path == '':
            if path_id == 0:
                dlg_path, file_ext = dlg.getOpenFileName(self.parent, Msg.FAKOM_TITLE, self.ui.current_path,
                                                         Msg.FAKOM_FILTER)

            elif path_id == 1:
                dlg_path, file_ext = dlg.getOpenFileName(self.parent, Msg.EXCEL_TITLE, self.ui.current_path,
                                                         Msg.EXCEL_FILTER)

        dlg_path = Path(dlg_path)
        self.verify_display_path(path_id, dlg_path)

    def verify_display_path(self, path_id, dlg_path):
        if dlg_path.exists():
            pass
        else:
            if path_id == 0:
                self.lineEdit_fakomPath.setText('Ungültiger POS Varianten Pfad.')

            if path_id == 1:
                self.lineEdit_vplusPath.setText('Ungültiger V Plus Browser Pfad')

            LOGGER.error('Invalid FakomLutscher path.')
            return False

        if path_id == 0 and (dlg_path.suffix == '.xml' or dlg_path.suffix == '.pos'):
            self.lineEdit_fakomPath.setText(str(dlg_path))
            self.fakom_path = dlg_path

            LOGGER.info('Setting Fakom POS path: %s', dlg_path)

        elif path_id == 1 and dlg_path.suffix == '.xlsx':
            self.lineEdit_vplusPath.setText(str(dlg_path))
            self.vplus_path = dlg_path

            LOGGER.info('Setting Fakom V plus path: %s', dlg_path)
        return True

    def exit_accept(self):
        if not self.vplus_path or not self.fakom_path:
            self.app.ui.warning_box(Msg.FAKOM_PATH_ERR_TITLE, Msg.FAKOM_PATH_ERR_MSG, parent=self.parent)

            LOGGER.error('Fakom settings rejected. No valid paths detected.')
            self.reject()
            return

        read_pkg_option = self.create_pkg_box.isChecked()

        self.fakom_lutscher = FakomLutscher(self.fakom_path,
                                            self.vplus_path,
                                            self.app,
                                            read_pkg_option,
                                            parent=self.parent,
                                            widget=self.widget)

        if self.wizard:
            self.fakom_lutscher.wizard_fakom_signal.connect(self.parent.fakom_result)

        self.fakom_lutscher.start()

        LOGGER.debug('Fakom settings accepted. Converting.')
        self.accept()

    def exit_abort(self):
        LOGGER.info('Fakom settings abort.')
        self.reject()

    def closeEvent(self, QCloseEvent):
        LOGGER.info('Fakom settings window close event triggerd. Rejecting Fakom conversion.')
        self.reject()
        QCloseEvent.accept()


class LedCornerWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LedCornerWidget, self).__init__(parent=parent)
        parent.setCornerWidget(self, QtCore.Qt.TopRightCorner)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.box_layout = QtWidgets.QVBoxLayout(self)
        self.box_layout.setContentsMargins(0, 0, 4, 5)
        self.box_layout.setSpacing(0)

        self.led_widget = qt_ledwidget.LedWidget(self, led_size=20, show_red=False)
        self.led_widget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.box_layout.addWidget(self.led_widget)

    def led(self, idx, action, blink_count=1, timer=0):
        if action == 0:
            self.led_widget.led_on(idx)
        elif action == 1:
            self.led_widget.led_off(idx)
        elif action == 2:
            self.led_widget.led_blink(idx, blink_count, timer)

    # Argument less method targets for signals etc.
    def green_on(self):
        self.led(2, 0)

    def green_off(self):
        self.led(2, 1)

    def green_blink(self):
        self.led(2, 2)

    def yellow_on(self):
        self.led(1, 0)

    def yellow_off(self):
        self.led(1, 1)

    def yellow_blink(self):
        self.led(1, 2)


class QColorButton(QtWidgets.QPushButton):
    """
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).
    """

    colorChanged = QtCore.pyqtSignal(object)
    style_id = '.QColorButton'
    bg_style = 'background-color: rgb(230, 230, 230);'
    border_style = 'border: 1px solid rgb(0, 0, 0);'

    def __init__(self, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(color)

        if self._color:
            self.setStyleSheet(
                "{!s} {{background-color: {!s}; {!s}}}"
                .format(self.style_id, self._color.name(), self.border_style))
        else:
            self.setStyleSheet(
                "{!s} {{{!s}{!s}}}"
                .format(self.style_id, self.bg_style, self.border_style))

    def color(self):
        return self._color

    def onColorPicker(self):
        """
        Show color-picker dialog to select color.

        Qt will use the native dialog by default.

        """
        dlg = QtWidgets.QColorDialog(self)
        # dlg.setStyleSheet(self.button_style)

        # We will need an RGBA color value
        dlg.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, True)

        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        if dlg.exec_():
            self.setColor(dlg.currentColor())

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.setColor(QColor(255, 255, 255, 255))

        return super(QColorButton, self).mousePressEvent(e)


class ExceptionSignal(QtCore.QObject):
    exception_signal = QtCore.pyqtSignal(str)


class KnechtExceptionHook(object):
    app = None
    signals = None
    signal_destination = None

    @classmethod
    def exception_hook(cls, etype, value, tb):
        """ sys.excepthook will call this method """
        import traceback

        # Print exception
        traceback.print_exception(etype, value, tb)

        # Log exception
        stacktrace_msg = ''.join(traceback.format_tb(tb))
        if etype:
            exception_msg = '{0}: {1}'.format(etype, value)
        else:
            exception_msg = 'Exception: {}'.format(value)

        LOGGER.critical(stacktrace_msg)
        LOGGER.critical(exception_msg)

        # Write to exception log file
        exception_file_name = datetime.now().strftime('RenderKnecht_Exception_%Y-%m-%d_%H%M%S.log')
        exception_file = HELPER_DIR / exception_file_name

        with open(exception_file, 'w') as f:
            traceback.print_exception(etype, value, tb, file=f)

        # Inform GUI of exception if QApplication set
        if cls.app:
            gui_msg = f'{stacktrace_msg}\n{exception_msg}'
            cls.send_exception_signal(gui_msg)

    @classmethod
    def setup_signal_destination(cls, dest):
        """ Setup GUI exception receiver from QApplication"""
        cls.signal_destination = dest

    @classmethod
    def send_exception_signal(cls, msg):
        """ This will fail if not run inside a QApplication """
        cls.signals = ExceptionSignal()
        cls.signals.exception_signal.connect(cls.signal_destination)
        cls.signals.exception_signal.emit(msg)

def load_ui_file(instance, ui_file):
    """ Suppres uic debug messages and load ui file """
    log_level = LOGGER.getEffectiveLevel()

    logging.root.setLevel(20)

    loadUi(ui_file, instance)

    logging.root.setLevel(log_level)