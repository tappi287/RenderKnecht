"""py_knecht package for creating RenderKnecht functionality eg. DeltaGen batch rendering and extending thiswith features for Autodesks Maya.Copyright (C) 2017-2018 Stefan Tapper, All rights reserved.    This file is part of RenderKnecht Strink Kerker.    RenderKnecht Strink Kerker is free software: you can redistribute it and/or modify    it under the terms of the GNU General Public License as published by    the Free Software Foundation, either version 3 of the License, or    (at your option) any later version.    RenderKnecht Strink Kerker is distributed in the hope that it will be useful,    but WITHOUT ANY WARRANTY; without even the implied warranty of    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the    GNU General Public License for more details.    You should have received a copy of the GNU General Public License    along with RenderKnecht Strink Kerker.  If not, see <http://www.gnu.org/licenses/>.Freeze Instructions:    - PyQt5 Fix window style in frozen:      pip install https://github.com/bjones1/pyinstaller/archive/pyqt5_fix.zip    - from:      https://stackoverflow.com/questions/48626999/packaging-with-pyinstaller-pyqt5-setstyle-ignored    - GitHub:      https://github.com/pyinstaller/pyinstaller/pull/3233#issuecomment-362094587    - Visual Studio 14 dll's:      Add your VS Install to Path:      C:/Program Files (x86)/Microsoft Visual Studio 14.0/Common7/IDE/Remote Debugger/x64"""__author__ = 'Stefan Tapper'__copyright__ = 'Copyright 2017 - 2018 Stefan Tapper'__credits__ = [    'Python Community', 'Stackoverflow', 'The Webs',    'Paul Barry HEAD FIRST Python - a brainfriendly guide',    'PyCharm Community Edition'    ]__license__ = 'GPL v3'__version__ = '1.2.8'__email__ = 'tapper.stefan@gmail.com'__status__ = 'Stabil'import loggingimport sysimport gui.preset_editor_rsc_rcfrom pathlib import Pathimport modules.app_globalsfrom multiprocessing import Queuefrom modules.app_strings import InfoMessagefrom modules.knecht_log import init_logging, setup_logging, setup_log_queue_listenerfrom modules.gui_renderknecht import RenderKnechtGuifrom modules.gui_widgets import KnechtExceptionHookfrom modules.knecht_settings import knechtSettings# Prepare exception handlingsys.excepthook = KnechtExceptionHook.exception_hook# Initialize logging with a dictConf and pass a multiprocess queue# to the global queueHandler classlogging_queue = Queue(-1)setup_logging(logging_queue)LOGGER = init_logging('knechtLog')# Set info messageinfo_dict = {    'ver': __version__,    'lic': __license__,    'auth': __author__,    'mail': __email__,    'cred': __credits__,    'stat': __status__    }for k, v in info_dict.items():    setattr(InfoMessage, k, v)del info_dictknechtSettings.load_settings()def create_version_info():    """ If run from debug location, create version txt for remote updater """    local_dist_path = Path('dist')    if local_dist_path.exists():        LOGGER.debug('Distribution directory found. Updating version info txt.')        if __version__:            local_dist_path = local_dist_path / 'version.txt'            try:                with open(local_dist_path, 'w') as f:                    f.write(str(__version__))            except OSError:                passif __name__ == "__main__":    # This will move all handlers from LOGGER to the queue listener    log_listener = setup_log_queue_listener(LOGGER, logging_queue)    # Start log queue listener in it's own thread    log_listener.start()    if modules.app_globals.run_in_ide:        create_version_info()    app = RenderKnechtGui(__version__, KnechtExceptionHook, logging_queue)    qt_exitcode = app.exec_()    LOGGER.info('---------------------------------------')    LOGGER.info('Qt application finished with exitcode %s', qt_exitcode)    # Shutdown logging and remove handlers    log_listener.stop()    logging.shutdown()    # Save version info    knechtSettings.app['version'] = __version__    # Save Settings    knechtSettings.save_settings()    modules.app_globals.save_last_log()    sys.exit()