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
from modules.knecht_log import QPlainTextEditHandler
from modules.app_globals import UI_FILE_LOG_WINDOW
from modules.knecht_settings import knechtSettings

# Initialize logging for this module
LOGGER = init_logging('gui_logger')


class LogWindow(QtWidgets.QWidget):
    """ Log Window that displays log entries """
    gui_handler = None

    def __init__(self, action_widget=None):
        super(LogWindow, self).__init__()

        # Avoid UIC Debug messages
        log_level = LOGGER.getEffectiveLevel()
        logging.root.setLevel(20)

        loadUi(UI_FILE_LOG_WINDOW, self)

        logging.root.setLevel(log_level)

        # Get menu item that toggles window visibility and check it
        if action_widget:
            self.action_widget = action_widget
            self.action_widget.setChecked(True)

        # Text window
        self.plainTextEdit_log.setCenterOnScroll(True)
        self.plainTextEdit_log.setMaximumBlockCount(300)

        # Initialize Log Window functions
        self.init_functions()

    def change_log_level(self):
        # ComboBox Index eg. Debug - 0 to logging.setLevel() eg DEBUG - 10
        # Index + 1 * 10
        log_level = (self.comboBox_logLevel.currentIndex() + 1) * 10

        self.gui_handler.setLevel(log_level)
        LOGGER.critical('Changed Log Window log level to: %s',
                        logging.getLevelName(self.gui_handler.level)
                       )

    def init_functions(self):
        # Create log handler that writes to this window QPlainTextEdit
        self.gui_handler = QPlainTextEditHandler()

        try:
            # Format from already loaded logConfig if available
            formatter = LOGGER.handlers[0].formatter
            level = LOGGER.handlers[0].level
            fallback_log = False
        except Exception as e:
            print(e)

            # No config available
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            formatter = logging.Formatter(format_str)
            level = 10
            fallback_log = True

        self.gui_handler.setFormatter(formatter)
        self.gui_handler.setLevel(level)
        logging.root.addHandler(self.gui_handler)

        for handler in logging.root.handlers:
            print('Global logging handlers:', handler)

        # ComboBox index to current Log Level
        combo_box_level = (self.gui_handler.level - 1) / 10
        try:
            self.comboBox_logLevel.setCurrentIndex(combo_box_level)
        except Exception as e:
            print(e)

        # Bind logger signal to textBox update
        self.gui_handler.log_message.connect(self.update_log)

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
        self.plainTextEdit_log.appendPlainText(msg)

    def toggle_window(self):
        LOGGER.debug('Toggle log window.')
        if self.isHidden():
            self.show()
            if self.action_widget:
                self.action_widget.setChecked(True)
            LOGGER.debug('Displaying log window.')
        else:
            self.hide()
            if self.action_widget:
                self.action_widget.setChecked(False)
            LOGGER.debug('Hiding log window.')

    def closeEvent(self, QCloseEvent):
        LOGGER.debug(
            'Log Window close event triggerd. Ignoring close event and hiding window instead.'
        )
        QCloseEvent.ignore()
        if self.action_widget: self.action_widget.setChecked(False)
        knechtSettings.app['log_window'] = False
        self.hide()

    def close_window(self):
        self.destroy()
