"""
knecht_updater module provides functionality for remote application updates

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

import ctypes
import os
import shutil
import time
# import ctypes
from subprocess import Popen
from pathlib import Path
from requests import get as requests_get

from PyQt5.QtCore import QObject, QThread, pyqtSignal, QUrl

from modules.app_globals import _UPDATER_NAME, HELPER_DIR, EXE_NAME, run_in_ide, Itemstyle, VERSION_URL, UPDATE_EXE_URL
from modules.knecht_log import init_logging

# Initialize logging for this module
LOGGER = init_logging(__name__)


def run_as_admin(argv=None):
    shell32 = ctypes.windll.shell32
    if argv is None and shell32.IsUserAnAdmin():
        return True

    arguments = argv[1:]
    argument_line = u' '.join(arguments)
    executable = argv[0]

    LOGGER.debug('Command line: %s %s', executable, argument_line)

    ret = shell32.ShellExecuteW(None, u"runas", executable, argument_line, None, 1)

    if int(ret) <= 32:
        return False

    return None


def run_exe_updater(ui):
    # Skip updater from debug Env
    local_dist_path = Path('dist')

    if local_dist_path.exists():
        LOGGER.debug('Not running updater from debug.')
        updater_path = local_dist_path / _UPDATER_NAME
        new_updater_path = HELPER_DIR / _UPDATER_NAME
        try:
            if new_updater_path.exists(): os.remove(new_updater_path)
            shutil.copy(updater_path, new_updater_path)
        except Exception as e:
            LOGGER.error('Could not replace Updater exe in helper dir.\n%s', e)

    if ui.menuUpdate.isEnabled():
        # Move Updater exe to settings dir, because TEMP exe dir will be removed on exit
        new_updater_path = HELPER_DIR / _UPDATER_NAME

        if not new_updater_path.exists():
            return

        # Path to executable to be replaced
        exe_path = HELPER_DIR.parent / EXE_NAME
        exe_path = exe_path.resolve()

        # Start updater process
        """
        ret = run_as_admin([str(new_updater_path), str(exe_path)])
        if ret is True:
            LOGGER.debug('I have admin privilege.')
        elif ret is None:
            LOGGER.debug('I am elevating to admin privilege.')
        else:
            LOGGER.debug('Error(%s): cannot elevate privilege.', ret)
            return
        """
        Popen([str(new_updater_path), str(exe_path)])

        LOGGER.info('Update detected. Running updater: \n%s',
                    str(new_updater_path))


class VersionCheck(QObject):
    """
    If executed in PyInstaller bundle, check for updates on remote server.
    Download updated executable and inform user that an update is available.
    """
    def __init__(self, app, version):
        super().__init__()
        self.app = app
        self.version = version

        # Prepare thread
        self.thread = QThread()
        self.first_run = True
        self.obj = VersionCheckWorker(self.version)

    def create_thread(self, skip_wait=False):
        # Skip updater from debug Env
        if run_in_ide and self.first_run:
            LOGGER.debug('Not running initial version check from debug.')
            self.first_run = False
            return

        if self.thread.isRunning():
            return

        # Skip wait if version check called from menu
        if skip_wait:
            self.obj.set_skip_wait()

        # hide updater menu
        self.app.ui.actionVersion_info.setVisible(False)
        self.app.ui.menuUpdate.setEnabled(False)

        # Move the Worker object to the Thread object
        self.obj.moveToThread(self.thread)

        self.obj.version_info.connect(self.new_version)
        self.obj.finished.connect(self.thread.quit)

        self.thread.started.connect(self.obj.version_check)

        # 6 - Start the thread
        self.thread.start()

    def new_version(self, version_info):
        if version_info > self.version:
            version_text = 'Aktualisierung auf ' + version_info + ' steht bereit.'
            self.app.ui.actionVersion_info.setText(version_text)
            # Display update menu
            self.app.ui.menuUpdate.setEnabled(True)
            self.app.ui.menuUpdate.setIcon(
                self.app.ui.icon[Itemstyle.MAIN['update']])
            self.app.ui.actionVersion_info.setVisible(True)
        else:
            self.app.ui.menuUpdate.setTitle('Version aktuell')


class VersionCheckWorker(QObject):
    finished = pyqtSignal()
    version_info = pyqtSignal(str)

    def __init__(self, version):
        super(VersionCheckWorker, self).__init__()
        self.current_version = version
        self.remote_version = '0.0.0'
        self.skip_wait = False

    def set_skip_wait(self):
        self.skip_wait = True

    def version_check(self):
        # Make sure we do not connect if user immediately closes app after start
        if not self.skip_wait:
            time.sleep(10)

        # Download version.txt
        try:
            version_remote_file = requests_get(VERSION_URL)
        except Exception as e:
            LOGGER.error('%s', e)
            self.abort()
            return

        # Read version.txt
        try:
            self.remote_version = version_remote_file.text
        except Exception as e:
            LOGGER.error('%s', e)
            self.abort()
            return

        if self.remote_version > self.current_version:
            LOGGER.info('Update to version %s found.', self.remote_version)

            # Prepare new executable location
            new_exe = HELPER_DIR / EXE_NAME

            # Remove existing update file
            if new_exe.exists():
                try:
                    os.remove(new_exe)
                except Exception as e:
                    LOGGER.error('Could not remove existing update file. %s', e)
                    self.abort()
                    return

            # Download remote version
            try:
                update_file = requests_get(UPDATE_EXE_URL)
                LOGGER.debug('Downloading remote file %s', new_exe.name)

                with open(new_exe, 'wb') as f:
                    f.write(update_file.content)
            except Exception as e:
                LOGGER.error('%s', e)
                self.abort()
                return

        # Report version
        self.version_info.emit(self.remote_version)

        LOGGER.debug(
            'Version check finished. Closing connection and finishing thread.')
        self.finished.emit()

    def abort(self):
        LOGGER.debug('Remote version check failed.')
        self.finished.emit()
        return
