"""
knecht_gui_log_window module provides a log window

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
import sys
import logging
from functools import partial
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi
from modules.knecht_log import init_logging
from modules.knecht_log import QPlainTextEditLogger
from modules.app_globals import UI_FILE_LOG_WINDOW
from modules.knecht_settings import knechtSettings

# Initialize logging for this module
LOGGER = init_logging(__name__)


class LogWindow(QtWidgets.QWidget):
    """ Log Window that displays log entries """

    def __init__(self, widget=None):
        super(LogWindow, self).__init__()

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)

        loadUi(UI_FILE_LOG_WINDOW, self)

        logging.root.setLevel(log_level)

        # Get menu item that toggles window visibility and check it
        if widget:
            self.widget = widget
            self.widget.setChecked(True)

        # Text window
        self.plainTextEdit_log.setCenterOnScroll(True)
        self.plainTextEdit_log.setMaximumBlockCount(300)

        # Initialize Log Window functions
        self.init_functions()

    def change_log_level(self):
        # ComboBox Index eg. Debug - 0 to logging.setLevel() eg DEBUG - 10
        # Index + 1 * 10
        log_level = (self.comboBox_logLevel.currentIndex() + 1) * 10

        self.gui_logger.setLevel(log_level)
        try:
            LOGGER.warning('Changed Log Window log level to: %s',
                           logging.getLevelName(logging.root.handlers[3].level))
        except IndexError:
            LOGGER.error(
                'Log handler not found. Log Configuration is probably missing!')

    def init_functions(self):
        # Create log handler that writes to this window QPlainTextEdit
        self.gui_logger = QPlainTextEditLogger()

        try:
            # Format from already loaded logConfig if available
            format_str = logging.root.handlers[1].formatter._fmt
            formatter = logging.Formatter(format_str)
            level = logging.root.handlers[1].level
            fallback_log = False
        except:
            # No config available
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            formatter = logging.Formatter(format_str)
            level = 10
            fallback_log = True

        self.gui_logger.setFormatter(formatter)
        self.gui_logger.setLevel(level)
        logging.root.addHandler(self.gui_logger)

        # ComboBox index to current Log Level
        comboBox_level = (self.gui_logger.level - 1) / 10
        try:
            self.comboBox_logLevel.setCurrentIndex(comboBox_level)
        except:
            pass

        # Bind logger signal to textBox update
        self.gui_logger.log_message.connect(self.update_log)

        # Bind ComboBox to log level
        self.comboBox_logLevel.currentIndexChanged.connect(
            self.change_log_level)

        # Complain in Log Window
        if fallback_log:
            LOGGER.error(
                'Log Configuration missing! Can not properly log application events!'
            )

    def update_log(self, msg):
        """ Receives Signal from Logger """
        msg = msg.replace('modules.', '')
        self.plainTextEdit_log.appendPlainText(msg)

    def toggle_window(self):
        LOGGER.debug('Toggle log window.')
        if self.isHidden():
            self.show()
            if self.widget: self.widget.setChecked(True)
            LOGGER.debug('Displaying log window.')
        else:
            self.hide()
            if self.widget: self.widget.setChecked(False)
            LOGGER.debug('Hiding log window.')

    def closeEvent(self, QCloseEvent):
        LOGGER.debug(
            'Log Window close event triggerd. Ignoring close event and hiding window instead.'
        )
        QCloseEvent.ignore()
        if self.widget: self.widget.setChecked(False)
        knechtSettings.app['log_window'] = False
        self.hide()

    def close_window(self):
        self.destroy()
