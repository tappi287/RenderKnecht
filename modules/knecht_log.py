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


def setup_log_file():
    log_conf = {
        'version': 1, 'disable_existing_loggers': True,
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
            },
        'loggers': {
            'knechtLog': {
                'handlers': ['file', 'guiHandler', 'console'], 'propagate': False, 'level': 'DEBUG',
                },
            'gui_logger': {
                'handlers': ['guiHandler'], 'propagate': False, 'level': 'INFO'
                },
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


def setup_queued_logger(name, queue):
    queue_handler = QueueHandler(queue)
    logger = logging.getLogger(name)
    logger.addHandler(queue_handler)
    logger.debug('Added log queue handler.')
    return logger


def add_queue_handler(logger, queue):
    for handler in logger.handlers:
        # Handler already preset
        logger.debug('Not adding logging queue handler. Handler present: %s', handler)
        print(logger.name, 'Not adding logging queue handler. Handler present: ', handler)
        break
    else:
        queue_handler = QueueHandler(queue)
        queue_handler.setLevel(logging.DEBUG)
        logger.addHandler(queue_handler)
        logger.debug('Added log queue handler: %s', queue_handler)
        print(logger.name, 'Added log queue handler:', queue_handler)


def init_root_file_handler():
    """
        File handler is added
    """
    fh = logging.FileHandler(LOG_FILE, 'w')

    # Try to read format from configured root log handler
    try:
        formatter = logging.Formatter(logging.root.handlers[0].formatter._fmt)
    except Exception as e:
        logging.root.debug(
            'No handler found to read format from for File Handler. %s', e)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Set log file format
    fh.setFormatter(formatter)

    # Add Handler to Logger
    logging.root.addHandler(fh)


def init_logging(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    return logger


def legacy_init_logging(logger_name):
    try:
        logging.config.fileConfig(LOG_CONF_FILE, disable_existing_loggers=False)

        #create logger
        logger = logging.getLogger(logger_name)
        log_conf = True
    except AttributeError as e:
        logging.root.setLevel(logging.DEBUG)

        #create logger
        logger = logging.getLogger(logger_name)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        ch = logging.StreamHandler(sys.stderr, )
        ch.setFormatter(formatter)

        logger.addHandler(ch)
        logger.error('%s', e)

        log_conf = False

    if log_conf:
        logger.debug('Log configuration loaded from %s and set to log file %s',
                     LOG_CONF_FILE, LOG_FILE)
    else:
        logger.warning(
            "No log file configuration found or configuration contains errors: %s. Setting log level to debug.",
            LOG_CONF_FILE)

    return logger


class QPlainTextEditLogger(logging.Handler, QObject):
    """ Log handler that appends text to QPlainTextEdit """
    log_message = pyqtSignal(str)

    def __init__(self):
        super(QPlainTextEditLogger, self).__init__()
        QObject.__init__(self)

    def emit(self, record):
        msg = None

        try:
            msg = self.format(record)
            self.log_message.emit(msg)
        except:
            # MS Visual Studio 15.4.x BUG ?, channel is not defined
            pass
