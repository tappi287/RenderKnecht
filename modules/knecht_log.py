"""

Logging module for py_knecht. Initializes logger objects from a log configuration ini file.

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

Target is to have a logger for every module involved. Logger needs to be in ini file:

[logger_logger_name]
qualname=logger_name

DEBUG 		Detailed information, typically of interest only when diagnosing problems.
INFO 		Confirmation that things are working as expected.
WARNING 	An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected.
ERROR		Due to a more serious problem, the software has not been able to perform some function.
CRITICAL 	A serious error, indicating that the program itself may be unable to continue running.

"""
import logging
import logging.config
import sys
from logging.handlers import QueueHandler, QueueListener
from PyQt5.QtCore import pyqtSignal, QObject
from modules.app_globals import LOG_CONF_FILE, LOG_FILE


def setup_logging(logging_queue):
    log_conf = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
                },
            'simple': {
                'format': '%(asctime)s %(name)s %(levelname)s: %(message)s',
                'datefmt': '%d.%m.%Y %H:%M'
                },
            'guiFormatter': {
                'format': '%(name)s %(levelname)s: %(message)s',
                'datefmt': '%d.%m.%Y %H:%M',
                },
            'file_formatter': {
                'format': '%(asctime)s %(name)s %(levelname)s: %(message)s',
                'datefmt': '%d.%m.%Y %H:%M'
                },
            },
        'handlers': {
            'console': {
                'level': 'DEBUG', 'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout', 'formatter': 'simple'
                },
            'guiHandler': {
                'level': 'INFO', 'class': 'logging.NullHandler',
                'formatter': 'simple',
                },
            'file': {
                'level': 'DEBUG', 'class': 'logging.handlers.RotatingFileHandler',
                'filename': LOG_FILE.as_posix(), 'maxBytes': 5000000, 'backupCount': 4,
                'formatter': 'file_formatter',
                },
            'queueHandler': {
                'level': 'DEBUG', 'class': 'logging.handlers.QueueHandler',
                'queue': logging_queue, 'formatter': 'file_formatter',
                },
            },
        'loggers': {
            # Main logger, handler will be moved to QueueListener
            'knechtLog': {
                'handlers': ['file', 'guiHandler', 'console'], 'propagate': False, 'level': 'DEBUG',
                },
            # Log Window Logger
            'gui_logger': {
                'handlers': ['guiHandler', 'queueHandler'], 'propagate': False, 'level': 'INFO'
                },
            # Default loggers
            '': {
                'handlers': ['queueHandler'], 'propagate': False, 'level': 'DEBUG',
                }
            }
        }

    logging.config.dictConfig(log_conf)


def setup_log_queue_listener(logger, queue):
    """
        Moves handlers from logger to QueueListener and returns the listener
        The listener needs to be started afterwwards with it's start method.
    """
    handler_ls = list()
    for handler in logger.handlers:
        print('Removing handler that will be added to queue listener: ', str(handler))
        handler_ls.append(handler)

    for handler in handler_ls:
        logger.removeHandler(handler)

    handler_ls = tuple(handler_ls)
    queue_handler = QueueHandler(queue)
    logger.addHandler(queue_handler)

    listener = QueueListener(queue, *handler_ls)
    return listener


def init_logging(logger_name):
    logger = logging.getLogger(logger_name)
    return logger


class QPlainTextEditHandler(logging.Handler, QObject):
    """ Log handler that appends text to QPlainTextEdit """
    log_message = pyqtSignal(str)

    def __init__(self):
        super(QPlainTextEditHandler, self).__init__()
        QObject.__init__(self)

    def emit(self, record):
        msg = None

        try:
            msg = self.format(record)
            self.log_message.emit(msg)
        except:
            # MS Visual Studio 15.4.x BUG ?, channel is not defined
            pass
