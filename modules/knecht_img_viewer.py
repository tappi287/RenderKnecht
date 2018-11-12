from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize, QRect, QEvent, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

from modules.app_globals import Itemstyle, TCP_IP, TCP_PORT
from modules.gui_set_path import SetDirectoryPath
from modules.knecht_img_viewer_control import ViewerShortcuts, FileDropWidget, ControllerWidget, KnechtLoadImage, AnimateOpacity
from modules.knecht_log import init_logging
from modules.knecht_socket import Ncat
from modules.tree_overlay import InfoOverlay


class KnechtImageViewer(FileDropWidget):
    button_timeout = QTimer()
    button_timeout.setInterval(100)
    button_timeout.setSingleShot(True)

    shortcut_timeout = QTimer()
    shortcut_timeout.setInterval(50)
    shortcut_timeout.setSingleShot(True)

    slider_timeout = QTimer()
    slider_timeout.setInterval(20)
    slider_timeout.setSingleShot(True)

    dg_btn_timeout = QTimer()
    dg_btn_timeout.setInterval(1000)
    dg_btn_timeout.setSingleShot(True)

    dg_poll_timer = QTimer()
    dg_poll_timer.setInterval(500)

    load_timeout = QTimer()
    load_timeout.setInterval(5000)
    load_timeout.setSingleShot(True)

    DEFAULT_SIZE = (800, 450)
    MARGIN = 400

    MAX_SIZE = QSize(4096, 4096)

    MAX_SIZE_FACTOR = 2.5
    MIN_SIZE_FACTOR = 0.25
    SIZE_INCREMENT = 0.25

    ICON = Itemstyle.ICON_PATH['img']

    FILE_TYPES = ['.png', '.jpg', '.jpeg', '.tif', '.tga', '.hdr', '.exr']

    def __init__(self, app, ui):
        super(KnechtImageViewer, self).__init__(
            flags=Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.CustomizeWindowHint
            )
        global LOGGER
        LOGGER = init_logging(__name__)

        self.app, self.ui = app, ui
        self.setWindowIcon(QIcon(QPixmap(self.ICON)))
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AcceptDrops, True)
        self.setWindowTitle('Image Viewer')
        self.setStyleSheet("QWidget{background-color: darkgray;}")
        self.setFocusPolicy(Qt.StrongFocus)

        self.animation = AnimateOpacity(self, 200)

        # Dg
        self.sync_dg = False
        self.dg_btn_timeout.timeout.connect(self.dg_reset_btn)
        self.dg_poll_timer.timeout.connect(self.dg_set_viewer)
        self.ncat = Ncat(TCP_IP, TCP_PORT)

        self.img_dir = Path('.')
        self.current_img = None
        self.img_list = list()
        self.img_index = 0
        self.img_size_factor = 1.0
        self.img_size = QSize(*self.DEFAULT_SIZE)
        self.img_loader = None  # will be the loader thread

        # Save window position for drag
        self.oldPos = self.pos()

        self.current_opacity = 1.0
        self.setWindowOpacity(1.0)

        self.control = ControllerWidget(self)

        # Image canvas
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.img_canvas = QtWidgets.QLabel(self)
        self.layout().addWidget(self.img_canvas)
        self.img_canvas.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.img_canvas.setScaledContents(True)
        self.img_canvas.setObjectName('img_canvas')
        self.set_default_image()

        # Overlay
        self.overlay = InfoOverlay(self.img_canvas)

        # App logic
        self.path_dlg = SetDirectoryPath(app, ui,
                                         mode='file',
                                         line_edit=self.control.line_edit,
                                         tool_button=self.control.path_btn,
                                         parent=self)
        self.path_dlg.path_changed.connect(self.set_img_path)

        self.slider_timeout.timeout.connect(self.set_opacity_from_slider)
        self.control.slider.sliderReleased.connect(self.slider_timeout.start)
        self.control.slider.valueChanged.connect(self.slider_timeout.start)

        self.control.size_box.currentIndexChanged.connect(self.combo_box_size)
        self.set_combo_box_to_current_factor()

        self.control.bck_btn.pressed.connect(self.iterate_bck)
        self.control.fwd_btn.pressed.connect(self.iterate_fwd)

        self.control.min_btn.released.connect(self.minimize)

        self.control.toggle_btn.pressed.connect(self.toggle_img_canvas)
        self.control.toggle_dg_btn.pressed.connect(self.dg_toggle_sync)

        self.control.help_btn.pressed.connect(self.display_shortcut_overlay)

        self.shortcuts = ViewerShortcuts(self, self.control)
        self.shortcuts.set_shortcuts(self)
        self.shortcuts.set_shortcuts(self.control)

        self.file_dropped.connect(self.path_dropped)
        self.control.file_dropped.connect(self.path_dropped)

        self.load_timeout.timeout.connect(self.kill_load_thread)
        self.place_in_screen_center()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if event.oldState() and Qt.WindowMinimized:
                self.restore()
            elif event.oldState() == Qt.WindowNoState:
                LOGGER.debug('Image Viewer minimized.')

    def restore(self):
        self.showNormal()
        self.control.showNormal()
        self.activateWindow()  # Gain window focus

    def minimize(self):
        self.showMinimized()
        self.control.showMinimized()

    def display_shortcut_overlay(self):
        self.overlay.display_exit()
        self.overlay.display(
            'Shortcuts<br>'
            '+/&#45; oder Q/E &#45; Bildanzeige vergößern/verkleinern<br>'
            '&lt;/&gt; oder A/D          &#45; Nächste/Vorherige Bilddatei im Ordner<br>'
            'STRG+/STRG&#45; oder W/S  &#45; Transparenz erhöhen/verringern<br><br>'
            'Leertaste oder X &#45; Bildanzeige ein&#45;/ausschalten<br>'
            'F &#45; DeltaGen Viewer Sync ein&#45;/ausschalten<br><br>'
            'Pfad auswählen oder Dateien in das Fenster ziehen.',
            duration=6000,
            immediate=True)

    def set_default_image(self):
        self.current_img = QPixmap(Itemstyle.ICON_PATH['img_viewer'])
        self.img_canvas.setStyleSheet('background: rgba(0, 0, 0, 0);')
        self.img_canvas.setPixmap(self.current_img)
        self.img_size = self.current_img.size()
        self.img_size_factor = 1.0

        self.control.line_edit.setText('')
        self.control.grabber_top.setText(self.windowTitle())

        self.change_viewer_size()

    # ------ DeltaGen Sync -------
    def dg_start_sync(self):
        if self.sync_dg:
            if not self.dg_poll_timer.isActive():
                self.dg_poll_timer.start()

    def dg_set_viewer(self):
        self.ncat.check_connection()

        position = f'{self.frameGeometry().x()} {self.frameGeometry().y()}'
        size = f'{self.size().width()} {self.size().height()}'
        command = f'UNFREEZE VIEWER;BORDERLESS VIEWER TRUE;SIZE VIEWER {size};POSITION VIEWER {position};'

        try:
            self.ncat.send(command)
        except Exception as e:
            LOGGER.error('Sending viewer size command failed. %s', e)

        self.control.toggle_dg_btn.setEnabled(True)
        self.dg_poll_timer.stop()

    def dg_reset_btn(self):
        self.control.toggle_dg_btn.setEnabled(True)

    def dg_reset_viewer(self):
        self.dg_poll_timer.stop()
        self.dg_btn_timeout.stop()
        self.dg_reset_btn()

        self.ncat.check_connection()
        try:
            self.ncat.send('BORDERLESS VIEWER FALSE;')
        except Exception as e:
            LOGGER.error('Sending viewer size command failed. %s', e)

    def dg_close_connection(self):
        if self.sync_dg:
            self.dg_reset_viewer()
            self.ncat.close()

    def dg_toggle_sync(self):
        self.sync_dg = not self.sync_dg
        self.control.toggle_dg_btn.setChecked(self.sync_dg)
        self.control.toggle_dg_btn.setEnabled(False)

        if self.sync_dg:
            self.dg_start_sync()
        else:
            self.dg_reset_viewer()

    # ------ IMAGES -------
    def path_dropped(self, file_url):
        self.path_dlg.set_path(Path(file_url))
        self.restore()  # Gain window focus on file drop

    def set_img_path(self, file_path: Path):
        if file_path.is_file():
            self.img_dir = file_path.parent
        else:
            self.img_dir = file_path

        self.path_dlg.set_path_text(self.img_dir)
        self.list_img_files(file_path)
        self.iterate_images()

    def list_img_files(self, current_file: Path):
        self.img_index = 0
        self.img_list = list()

        for img_file in self.img_dir.glob('*.*'):
            if f'{img_file.suffix}'.casefold() in self.FILE_TYPES:
                self.img_list.append(img_file)

        if current_file in self.img_list:
            current_idx = self.img_list.index(current_file)
            self.img_index = current_idx
            LOGGER.debug('Current file set to: %s', current_idx)

    def iterate_fwd(self):
        if not self.check_image_loader():
            return

        self.img_index += 1
        self.iterate_images()

    def iterate_bck(self):
        if not self.check_image_loader():
            return

        self.img_index -= 1
        self.iterate_images()

    def iterate_images(self):
        if not self.img_list or self.button_timeout.isActive():
            if not self.img_list:
                self.set_default_image()
                self.overlay.display_exit()
                self.overlay.display('Kein unterstützen Bilddaten im Ordner gefunden oder '
                                     'kein Bildordner gewählt.', 3000)
            return

        if self.img_index < 0:
            self.img_index = len(self.img_list) - 1

        if self.img_index >= len(self.img_list):
            self.img_index = 0

        img_path = self.img_list[self.img_index]

        self.create_image_load_thread(img_path)

        self.button_timeout.start()

    def check_image_loader(self):
        if self.img_loader is not None and self.img_loader.isRunning():
            self.overlay.display_exit()
            self.overlay.display('Bildverarbeitung ist beschäftigt. Später erneut versuchen.', 5000, immediate=True)
            return False
        return True

    def create_image_load_thread(self, img_path):
        if not self.img_loader:
            self.img_loader = KnechtLoadImage(self, img_path)
            self.img_loader.start()
            self.load_timeout.start()

    def kill_load_thread(self):
        LOGGER.error('Image load timeout exceeded. Trying to kill load thread.')

        if self.img_loader is not None and self.img_loader.isRunning():
            self.img_loader.exit()
            LOGGER.error('Waiting for Image loader to exit.')
            self.img_loader.wait(msecs=3000)

            if self.img_loader.isRunning():
                LOGGER.error('Image loader exit took too long. Trying to terminate the QThread.')
                self.img_loader.terminate()

                img_path = self.img_list[self.img_index]

                # Thread terminated, application should be restarted
                self.close()
                self.ui.generic_error_msg(f'Das Laden der Datei <br>{img_path.as_posix()}<br>'
                                          f'ist fehlgeschlagen! Der Ladeprozess musste unsanft beendet werden.<br><br>'
                                          f'Um Speicherlecks und Fehler bei Zugriffsberechtigungen zu vermeiden<br>'
                                          f'sollte diese Anwendung möglichst bald neu gestartet werden.'
                                          )

                if self.img_loader.isRunning():
                    LOGGER.error('Could not terminate Image loader QThread.')

                self.image_load_failed()
            self.img_loader = None

    def image_load_failed(self, error_msg=''):
        img_path = self.img_list[self.img_index]

        if not error_msg:
            error_msg = img_path.as_posix()

        LOGGER.error('Could not load image file:\n%s', error_msg)

        self.set_default_image()
        self.overlay.display_exit()
        self.overlay.display(f'<span style="font-size: 11pt;">'
                             f'Datei <b>{img_path.name}</b> konnt nicht geladen werden!'
                             f'</span>', 5000, immediate=True)
        self.img_loader = None
        self.load_timeout.stop()

    def image_loaded(self, image):
        if not image:
            self.image_load_failed()
            return

        self.current_img = image

        self.img_canvas.setPixmap(self.current_img)
        self.img_size = self.current_img.size()
        self.change_viewer_size()

        self.overlay.display_exit()
        img_path = self.img_list[self.img_index]
        self.overlay.display(f'<span style="font-size: 11pt;">'
                             f'{self.img_index + 1:02d}/{len(self.img_list):02d} - '
                             f'<b>{img_path.name}</b> - '
                             f'{self.img_size.width()}x{self.img_size.height()}px'
                             f'</span>', 1200, immediate=True)
        self.img_loader = None
        self.control.grabber_top.setText(f'{self.windowTitle()} - {img_path.name}')
        self.load_timeout.stop()

    # ------ RESIZE -------
    def combo_box_size(self, idx):
        data = self.control.size_box.currentData()
        self.img_size_factor = data
        self.change_viewer_size()

    def set_combo_box_to_current_factor(self):
        idx = self.control.size_box.findData(self.img_size_factor)
        self.control.size_box.setCurrentIndex(idx)

    def increase_size(self):
        self.img_size_factor += self.SIZE_INCREMENT
        self.change_viewer_size()

    def decrease_size(self):
        self.img_size_factor -= self.SIZE_INCREMENT
        self.change_viewer_size()

    def change_viewer_size(self):
        self.img_size_factor = max(self.MIN_SIZE_FACTOR, min(self.img_size_factor, self.MAX_SIZE_FACTOR))
        self.set_combo_box_to_current_factor()

        w = round(self.img_size.width() * self.img_size_factor)
        h = round(self.img_size.height() * self.img_size_factor)
        new_size = QSize(w, h)

        self.resize_image_viewer(new_size)

    def resize_image_viewer(self, new_size: QSize):
        width = max(50, min(new_size.width(), self.MAX_SIZE.width()))
        height = max(50, min(new_size.height(), self.MAX_SIZE.height()))
        new_size = QSize(width, height)

        self.dg_start_sync()
        self.resize(new_size)

    # ------ OPACITY -------
    def increase_window_opacity(self):
        opacity = self.windowOpacity() + 0.15
        self.update_opacity_slider()
        self.set_window_opacity(opacity)

    def decrease_window_opacity(self):
        opacity = self.windowOpacity() - 0.15
        self.update_opacity_slider()
        self.set_window_opacity(opacity)

    def update_opacity_slider(self):
        self.control.slider.setValue(round(self.windowOpacity() * self.control.slider.maximum()))

    def set_opacity_from_slider(self):
        opacity = self.control.slider.value() * 0.1
        self.set_window_opacity(opacity)

    def set_window_opacity(self, opacity):
        if self.shortcut_timeout.isActive():
            return

        opacity = max(0.05, min(1.0, opacity))
        self.current_opacity = opacity
        self.setWindowOpacity(opacity)

        self.shortcut_timeout.start()

    # ------ VISIBILITY -------
    def toggle_img_canvas(self):
        if self.shortcut_timeout.isActive():
            return

        if self.control.toggle_btn.isChecked():
            self.setWindowOpacity(0.0)
        else:
            self.setWindowOpacity(self.current_opacity)

        self.shortcut_timeout.start()

    def hide_all(self):
        self.control.hide()
        self.hide()

    def show_all(self):
        self.place_inside_screen()
        self.control.show()
        self.show()
        self.display_shortcut_overlay()

        self.control.animation.setup_animation(duration=800)
        self.control.animation.play()
        self.animation.setup_animation(duration=800)
        self.current_opacity = 1.0
        self.control.slider.setValue(self.control.slider.maximum())
        self.animation.play()

    # ------ OVERRIDES -------
    def moveEvent(self, event):
        if self.moved_out_of_limit():
            event.ignore()
            return

        event.accept()

    def resizeEvent(self, event):
        if self.moved_out_of_limit():
            event.ignore()
            return

        event.accept()

    def moved_out_of_limit(self):
        limit = self.calculate_screen_limits()
        pos = self.geometry().topLeft()

        if not self.is_inside_limit(limit, pos):
            x = min(limit.width(), max(limit.x(), self.geometry().x()))
            y = min(limit.height(), max(limit.y(), self.geometry().y()))
            self.move(x, y)
            return True

        return False

    def place_inside_screen(self):
        limit = self.calculate_screen_limits()
        pos = self.geometry().topLeft()

        if not self.is_inside_limit(limit, pos):
            self.place_in_screen_center()

    def place_in_screen_center(self):
        screen = self.app.desktop().availableGeometry(self)

        center_x = screen.center().x() - self.geometry().width() / 2
        center_y = screen.center().y() - self.geometry().height() / 2

        self.move(center_x, center_y)

    def calculate_screen_limits(self):
        screen = QRect(self.app.desktop().x(), self.app.desktop().y(),
                       self.app.desktop().width(), self.app.desktop().availableGeometry().height())

        width_margin = self.geometry().width() / 2
        height_margin = self.geometry().height() / 2

        min_x = screen.x() - width_margin
        min_y = screen.y() - height_margin
        max_x = screen.width() - width_margin
        max_y = screen.height() - height_margin

        # LOGGER.debug('MinX %s MinY %s MaxX %s MaxY %s', min_x, min_y, max_x, max_y)
        return QRect(min_x, min_y, max_x, max_y)

    def closeEvent(self, QCloseEvent):
        self.dg_close_connection()
        self.control.close()
        QCloseEvent.accept()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)

        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

        self.dg_start_sync()

    @staticmethod
    def is_inside_limit(limit: QRect, pos: QPoint):
        if pos.x() < limit.x() or pos.x() > limit.width():
            return False
        elif pos.y() < limit.y() or pos.y() > limit.height():
            return False

        return True
