from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject, pyqtSlot

from modules.app_globals import TCP_IP, TCP_PORT
from modules.knecht_socket import Ncat
from modules.knecht_log import init_logging
import win32gui
import re


class Win32WindowMgr:
    """Encapsulates some calls to the winapi for window management"""
    def __init__ (self):
        """Constructor"""
        self._handle = None

    def has_handle(self):
        if self._handle:
            return True
        return False

    def clear_handle(self):
        self._handle = None

    def find_window(self, class_name, window_name=None):
        """find a window by its class_name"""
        self._handle = win32gui.FindWindow(class_name, window_name)

    def _window_enum_callback(self, hwnd, wildcard):
        """Pass to win32gui.EnumWindows() to check all the opened windows"""
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) is not None:
            self._handle = hwnd

    def find_window_wildcard(self, wildcard):
        """find a window whose title matches the wildcard regex"""
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)

    def set_foreground(self):
        """put the window in the foreground"""
        if self._handle:
            win32gui.SetForegroundWindow(self._handle)


class KnechtImageViewerDgSync(QObject):
    set_btn_enabled_signal = pyqtSignal(bool)
    set_btn_checked_signal = pyqtSignal(bool)
    activate_viewer_window = pyqtSignal()

    viewer_name_wildcard = '.* \[Camer.*\]$'  # Looking for window with name Scene_Name * [Camera]

    def __init__(self, viewer):
        """ Worker object to sync DG Viewer to Image Viewer position and size

        :param KnechtImageViewer viewer: Image viewer parent
        """
        super(KnechtImageViewerDgSync, self).__init__()
        self.viewer = viewer
        self.dg_window = Win32WindowMgr()

        self.dg_btn_timeout = QTimer()
        self.dg_btn_timeout.setInterval(800)
        self.dg_btn_timeout.setSingleShot(True)
        self.dg_btn_timeout.timeout.connect(self.dg_reset_btn)

        self.dg_poll_timer = QTimer()
        self.dg_poll_timer.setInterval(600)
        self.dg_poll_timer.timeout.connect(self.dg_set_viewer)

        self.dg_viewer_pull_timer = QTimer()
        self.dg_viewer_pull_timer.setInterval(1500)
        self.dg_viewer_pull_timer.setSingleShot(True)
        self.dg_viewer_pull_timer.timeout.connect(self.viewer_pull_window)

        self.sync_dg = False
        self.pull_viewer_foreground = False
        self.pull_viewer_on_sync_start = True

        self.ncat = Ncat(TCP_IP, TCP_PORT)
        self.ncat.signals.recv_end.connect(self.viewer_pull_window)

        self.set_btn_enabled_signal.connect(self.viewer.dg_toggle_btn)
        self.set_btn_checked_signal.connect(self.viewer.dg_check_btn)

    def dg_reset_btn(self):
        self.set_btn_enabled_signal.emit(True)

    def dg_set_viewer(self):
        self.ncat.check_connection()

        position = f'{self.viewer.frameGeometry().x()} {self.viewer.frameGeometry().y()}'
        size = f'{self.viewer.size().width()} {self.viewer.size().height()}'
        command = f'UNFREEZE VIEWER;BORDERLESS VIEWER TRUE;SIZE VIEWER {size};POSITION VIEWER {position};'

        try:
            self.ncat.send(command)
        except Exception as e:
            LOGGER.error('Sending viewer size command failed. %s', e)

        if not self.dg_viewer_pull_timer.isActive():
            self.dg_viewer_pull_timer.start()

        if not self.pull_viewer_foreground:
            self.dg_poll_timer.stop()

    def dg_reset_viewer(self):
        self.dg_poll_timer.stop()

        self.ncat.check_connection()
        try:
            self.ncat.send('BORDERLESS VIEWER FALSE;')
        except Exception as e:
            LOGGER.error('Sending viewer size command failed. %s', e)

        self.dg_reset_btn()

    def dg_close_connection(self):
        self.dg_viewer_pull_timer.stop()
        self.dg_poll_timer.stop()

        if self.sync_dg:
            self.dg_reset_viewer()
            self.ncat.close()

    @pyqtSlot()
    def dg_start_sync(self):
        """ Image Viewer Window <> DeltaGen Viewer sync requested """
        if self.sync_dg:
            if not self.dg_poll_timer.isActive():
                self.dg_poll_timer.start()

    @pyqtSlot()
    def dg_toggle_sync(self):
        self.sync_dg = not self.sync_dg
        self.set_btn_checked_signal.emit(self.sync_dg)
        self.set_btn_enabled_signal.emit(False)
        self.dg_btn_timeout.start()

        if self.sync_dg:
            if self.ncat.deltagen_is_alive():
                self.dg_start_sync()
                self.viewer_clear()
                self.viewer_window_find()
            else:
                self.dg_toggle_sync()  # No connection, toggle sync off
        else:
            self.dg_reset_viewer()

    @pyqtSlot(bool)
    def viewer_toggle_pull(self, enabled: bool):
        LOGGER.debug('Setting pull_viewer_foreground: %s', enabled)
        self.pull_viewer_foreground = enabled

        if self.sync_dg:
            self.dg_poll_timer.start()

    def viewer_clear(self):
        self.dg_window.clear_handle()

    def viewer_window_find(self):
        """ Tries to find the MS Windows window handle and pulls the viewer window to foreground """
        try:
            self.dg_window.find_window_wildcard(self.viewer_name_wildcard)

            self.pull_viewer_on_sync_start = True
        except Exception as e:
            LOGGER.error('Error finding DeltaGen Viewer window.\n%s', e)

    def viewer_pull_window(self):
        # Pull DeltaGen Viewer to foreground
        if not self.pull_viewer_foreground and not self.pull_viewer_on_sync_start:
            return

        if not self.dg_window.has_handle():
            self.viewer_window_find()

        try:
            self.dg_window.set_foreground()
            LOGGER.debug('Pulling viewer window to foreground.')
            self.activate_viewer_window.emit()
        except Exception as e:
            LOGGER.error('Error setting DeltaGen Viewer foreground.\n%s', e)

        # Initial pull done, do not pull to front on further sync
        self.pull_viewer_on_sync_start = False


class KnechtImageViewerSendThread(QThread):
    def __init__(self, controller):
        super(KnechtImageViewerSendThread, self).__init__()
        self.controller = controller
        self.worker = None

    def setup_worker(self):
        self.worker = KnechtImageViewerDgSync(self.controller.viewer)

        self.controller.toggle_sync_signal.connect(self.worker.dg_toggle_sync)
        self.controller.toggle_pull_signal.connect(self.worker.viewer_toggle_pull)
        self.controller.request_sync_signal.connect(self.worker.dg_start_sync)
        self.worker.activate_viewer_window.connect(self.controller.viewer.restore)

        self.worker.pull_viewer_foreground = not self.controller.viewer.control.toggle_pull_btn.isChecked()
        self.finished.connect(self.worker.dg_close_connection)

    def run(self):
        self.setup_worker()
        self.worker.moveToThread(self)

        self.exec()


class KnechtImageViewerSendController(QObject):
    toggle_sync_signal = pyqtSignal()
    toggle_pull_signal = pyqtSignal(bool)
    request_sync_signal = pyqtSignal()
    
    def __init__(self, viewer):
        super(KnechtImageViewerSendController, self).__init__(viewer)
        global LOGGER
        LOGGER = init_logging(__name__)

        self.viewer = viewer
        self.thread = KnechtImageViewerSendThread(self)

    def toggle_sync(self):
        self.toggle_sync_signal.emit()

    def toggle_pull(self):
        enabled = not self.viewer.control.toggle_pull_btn.isChecked()
        self.toggle_pull_signal.emit(enabled)

    def request_sync(self):
        self.request_sync_signal.emit()

    def start(self):
        if not self.thread.isRunning():
            self.thread.start()
        
    def exit(self):
        if self.thread.isRunning():
            self.thread.exit()
            self.thread.wait(msecs=3000)
