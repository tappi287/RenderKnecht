from pathlib import Path

import imageio
import numpy as np
from PIL import Image, ImageQt
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QImage, QKeySequence, QPalette, QColor

from modules.app_globals import Itemstyle, TCP_IP, TCP_PORT
from modules.gui_set_path import SetDirectoryPath
from modules.knecht_log import init_logging
from modules.knecht_socket import Ncat

LOGGER = init_logging(__name__)


def read_to_qpixmap(image_path: Path):
    """ Read an image using imageio and return as QPixmap """
    # Read with imageio for format compatibility
    img = imageio.imread(image_path.as_posix())

    # Convert type to numpy array
    img = np.array(img)

    if img.dtype != np.uint8:
        # Convert to integer and rescale to 0 - 255
        # original values are float 0.0 - 1.0
        img = np.uint8(img * 255)

    # Return as PIL Image
    pil_im = Image.fromarray(img)
    return pil_2_pixmap(pil_im)


def pil_2_pixmap(im):
    if im.mode == "RGB":
        r, g, b = im.split()
        im = Image.merge("RGB", (b, g, r))
    elif im.mode == "RGBA":
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (b, g, r, a))
    elif im.mode == "L":
        im = im.convert("RGBA")

    # Bild in RGBA konvertieren, falls nicht bereits passiert
    im2 = im.convert("RGBA")
    data = im2.tobytes("raw", "RGBA")
    qim = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)
    pixmap = QPixmap.fromImage(qim)
    return pixmap


class ControllerWidget(QtWidgets.QWidget):
    y_margin = 10
    height = 70

    def __init__(self, viewer):
        super(ControllerWidget, self).__init__(
            flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint,
            )

        self.viewer = viewer

        # Window
        self.setWindowTitle(f'{viewer.windowTitle()} - Controller')
        self.setWindowIcon(viewer.windowIcon())
        self.setStyleSheet("QWidget#not_me { background: rgba(100, 100, 100, 120); border-radius: 5px; }"
                           "QLabel { background: rgba(0, 0, 0, 0); }"
                           "QPushButton, QLineEdit {"
                           "    height: 26px; margin: 0 5px 0 5px;"
                           "    background-color: rgb(80, 80, 80); border: 1px solid rgb(50, 50, 50);"
                           "    border-radius: 5px; color: rgb(210, 210, 210);"
                           "}"
                           "QPushButton:pressed {"
                           "    background-color: rgb(84, 92, 98);"
                           "}"
                           "QPushButton#exit_btn {"
                           "    min-width: 26px; margin-right: 0; float: right; "
                           "}"
                           "QPushButton#fwd_btn {"
                           "    min-width: 100px; margin-left: 0; float: right;"
                           "}"
                           "QPushButton#bck_btn {"
                           "    min-width: 100px; float: right;"
                           "}"
                           "QPushButton#toggle_btn {"
                           "    min-width: 52px; float: right;"
                           "}"
                           "QPushButton#toggle_dg_btn {"
                           "    padding: 0 10px;"
                           "}"
                           "QPushButton#toggle_dg_btn:checked, QPushButton#toggle_btn:checked {"
                           "    background-color: rgb(150, 150, 150);"
                           "}"
                           "QToolButton {"
                           "    height: 22px; margin: 0 0 0 5px;"
                           "    background-color: rgb(80, 80, 80); border: 1px solid rgb(50, 50, 50);"
                           "    border-radius: 5px; color: rgb(210, 210, 210);"
                           "}"
                           "QLineEdit {"
                           "    margin-left:0;"
                           "}")

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        # Widget Layout
        self.btn_row = QtWidgets.QHBoxLayout(self)
        self.btn_row.setContentsMargins(0, 0, 0, 0)
        self.btn_row.setSpacing(0)
        self.path_row = QtWidgets.QHBoxLayout(self)
        self.path_row.setContentsMargins(0, 0, 0, 0)
        self.path_row.setSpacing(0)
        self.layout().addLayout(self.path_row)
        self.layout().addLayout(self.btn_row)
        self.spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.btn_row.addSpacerItem(self.spacer)

        # Buttons
        self.toggle_dg_btn = QtWidgets.QPushButton(
            QIcon(QPixmap(Itemstyle.ICON_PATH['compare'])), 'Sync DeltaGen Viewer', self)
        self.toggle_dg_btn.setObjectName('toggle_dg_btn')
        self.toggle_dg_btn.setFlat(True)
        self.toggle_dg_btn.setCheckable(True)
        self.toggle_dg_btn.setChecked(False)
        self.btn_row.addWidget(self.toggle_dg_btn)

        self.toggle_btn = QtWidgets.QPushButton(QIcon(QPixmap(Itemstyle.ICON_PATH['eye-on'])), '', self)
        self.toggle_btn.setObjectName('toggle_btn')
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.btn_row.addWidget(self.toggle_btn)

        self.bck_btn = QtWidgets.QPushButton(QIcon(), '<<', self)
        self.bck_btn.setObjectName('fwd_btn')
        self.bck_btn.setFlat(True)
        self.btn_row.addWidget(self.bck_btn)

        self.fwd_btn = QtWidgets.QPushButton(QIcon(), '>>', self)
        self.fwd_btn.setObjectName('bck_btn')
        self.fwd_btn.setFlat(True)
        self.btn_row.addWidget(self.fwd_btn)

        self.exit_btn = QtWidgets.QPushButton(QIcon(QPixmap(Itemstyle.ICON_PATH['close'])), '', self)
        self.exit_btn.pressed.connect(self._close_viewer)
        self.exit_btn.setObjectName('exit_btn')
        self.exit_btn.setFlat(True)
        self.btn_row.addWidget(self.exit_btn)

        self.line_edit = QtWidgets.QLineEdit('Bildpfad', self)
        self.path_btn = QtWidgets.QToolButton(self)
        self.path_btn.setObjectName('path_btn')
        self.path_btn.setText('...')

        self.path_row.addWidget(self.line_edit)
        self.path_row.addWidget(self.path_btn)

        # Install viewer move and resize wrapper
        self.org_viewer_resize_event = self.viewer.resizeEvent
        self.viewer.resizeEvent = self._viewer_resize_wrapper
        self.org_viewer_move_event = self.viewer.moveEvent
        self.viewer.moveEvent = self._viewer_move_wrapper

    def _viewer_move_wrapper(self, event):
        self.org_viewer_move_event(event)
        self._adapt_viewer_position()
        event.accept()

    def _viewer_resize_wrapper(self, event):
        self.org_viewer_resize_event(event)
        self._adapt_viewer_position()
        event.accept()

    def _adapt_viewer_position(self):
        x = self.viewer.x()
        y = self.viewer.y() + self.viewer.size().height() + self.y_margin
        width = self.viewer.size().width()
        self.setGeometry(x, y, width, self.height)

    def _close_viewer(self):
        self.close()
        self.viewer.close()


class KnechtImageViewer(QtWidgets.QWidget):
    button_timeout = QTimer()
    button_timeout.setInterval(100)
    button_timeout.setSingleShot(True)

    shortcut_timeout = QTimer()
    shortcut_timeout.setInterval(50)
    shortcut_timeout.setSingleShot(True)

    dg_btn_timeout = QTimer()
    dg_btn_timeout.setInterval(1000)
    dg_btn_timeout.setSingleShot(True)

    dg_poll_timer = QTimer()
    dg_poll_timer.setInterval(500)

    DEFAULT_SIZE = (640, 360)
    DEFAULT_POS = (150, 150)
    MAX_SIZE = QSize(4096, 4096)
    ICON = Itemstyle.ICON_PATH['img']

    FILE_TYPES = ['.png', '.jpg', '.jpeg', '.tif', '.tga']

    def __init__(self, app, ui):
        super(KnechtImageViewer, self).__init__(
            flags=Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
            )
        self.app, self.ui = app, ui
        self.setWindowIcon(QIcon(QPixmap(self.ICON)))
        self.setWindowTitle('Image Viewer')
        self.setStyleSheet("QWidget{background-color: darkgray;}")

        # Dg
        self.sync_dg = False
        self.dg_btn_timeout.timeout.connect(self.dg_reset_btn)
        self.dg_poll_timer.timeout.connect(self.dg_set_viewer)
        self.ncat = Ncat(TCP_IP, TCP_PORT)

        self.img_dir = Path('.')
        self.current_img = None
        self.img_list = list()
        self.img_index = 0

        # Save window position for drag
        self.oldPos = self.pos()

        self.setGeometry(*self.DEFAULT_POS, *self.DEFAULT_SIZE)
        self.setWindowOpacity(0.5)
        self.old_opacity = self.windowOpacity()

        self.control = ControllerWidget(self)

        # Image canvas
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.img_canvas = QtWidgets.QLabel(self)
        self.layout().addWidget(self.img_canvas)
        self.img_canvas.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.img_canvas.setScaledContents(True)

        # App logic
        self.path_dlg = SetDirectoryPath(app, ui,
                                         mode='file',
                                         line_edit=self.control.line_edit,
                                         tool_button=self.control.path_btn,
                                         parent=self)
        self.path_dlg.path_changed.connect(self.set_img_path)

        self.control.bck_btn.pressed.connect(self.iterate_bck)
        self.control.fwd_btn.pressed.connect(self.iterate_fwd)

        self.control.toggle_btn.pressed.connect(self.toggle_viewer)
        self.control.toggle_dg_btn.pressed.connect(self.dg_toggle_sync)

        # Shortcuts
        toggle_view = QtWidgets.QShortcut(QKeySequence(Qt.Key_Space), self)
        toggle_view.activated.connect(self.toggle_viewer)

        size_hi = QtWidgets.QShortcut(QKeySequence(Qt.Key_Plus), self)
        size_hi.activated.connect(self.increase_size)

        size_lo = QtWidgets.QShortcut(QKeySequence(Qt.Key_Minus), self)
        size_lo.activated.connect(self.decrease_size)

        opa_hi = QtWidgets.QShortcut(QKeySequence('Ctrl++'), self)
        opa_hi.activated.connect(self.increase_window_opacity)

        opa_lo = QtWidgets.QShortcut(QKeySequence('Ctrl+-'), self)
        opa_lo.activated.connect(self.decrease_window_opacity)

        esc = QtWidgets.QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.close)

        fwd = QtWidgets.QShortcut(QKeySequence(Qt.Key_Right), self)
        fwd.activated.connect(self.control.fwd_btn.animateClick)

        bck = QtWidgets.QShortcut(QKeySequence(Qt.Key_Left), self)
        bck.activated.connect(self.control.bck_btn.animateClick)

    # ------ DeltaGen Sync -------
    def dg_start_sync(self):
        if self.sync_dg:
            if not self.dg_poll_timer.isActive():
                self.dg_poll_timer.start()

    def dg_set_viewer(self):
        self.ncat.check_connection()

        position = f'{self.frameGeometry().x()} {self.frameGeometry().y()}'
        size = f'{self.size().width()} {self.size().height()}'
        command = f'SIZE VIEWER {size};POSITION VIEWER {position};BORDERLESS VIEWER TRUE;UNFREEZE VIEWER;'

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
    def set_img_path(self, file_path: Path):
        if file_path.is_file():
            self.img_dir = file_path.parent
        else:
            self.img_dir = file_path

        self.path_dlg.set_path_text(self.img_dir)
        self.list_img_files()
        self.iterate_images()

    def list_img_files(self):
        self.img_index = 0
        self.img_list = list()

        for img_file in self.img_dir.glob('*.*'):
            if f'{img_file.suffix}'.casefold() in self.FILE_TYPES:
                self.img_list.append(img_file)

    def iterate_fwd(self):
        self.img_index += 1
        self.iterate_images()

    def iterate_bck(self):
        self.img_index -= 1
        self.iterate_images()

    def iterate_images(self):
        if not self.img_list or self.button_timeout.isActive():
            return

        if self.img_index < 0:
            self.img_index = len(self.img_list) - 1

        if self.img_index >= len(self.img_list):
            self.img_index = 0

        img_path = self.img_list[self.img_index]

        try:
            self.current_img = read_to_qpixmap(img_path)
        except Exception as e:
            LOGGER.error('Could not load image file: %s\n%s', img_path.asposix(), e)

        if self.current_img:
            self.img_canvas.setPixmap(self.current_img)

        self.resize_image_viewer(self.current_img.size())

        self.button_timeout.start()

    # ------ RESIZE -------
    def increase_size(self):
        self.change_viewer_size(0.25)

    def decrease_size(self):
        self.change_viewer_size(-0.25)

    def change_viewer_size(self, factor):
        # TODO: Save Resize factor and apply to next img
        add_width = round(self.size().width() * factor)
        add_height = round(self.size().height() * factor)
        new_size = QSize(self.size().width() + add_width, self.size().height() + add_height)

        self.resize_image_viewer(new_size)

    def resize_image_viewer(self, new_size: QSize):
        width = max(50, min(new_size.width(), self.MAX_SIZE.width()))
        height = max(50, min(new_size.height(), self.MAX_SIZE.height()))
        new_size = QSize(width, height)

        self.dg_start_sync()
        self.resize(new_size)

    # ------ OPACITY -------
    def increase_window_opacity(self):
        opacity = self.windowOpacity() + 0.1
        self.set_window_opacity(opacity)

    def decrease_window_opacity(self):
        opacity = self.windowOpacity() - 0.1
        self.set_window_opacity(opacity)

    def set_window_opacity(self, opacity):
        if self.shortcut_timeout.isActive():
            return

        opacity = max(0.1, min(1.0, opacity))
        self.old_opacity = opacity
        self.setWindowOpacity(opacity)

        self.shortcut_timeout.start()

    # ------ VISIBILITY -------
    def toggle_viewer(self):
        if self.shortcut_timeout.isActive():
            return

        if self.windowOpacity() == 0.0:
            self.control.toggle_btn.setChecked(True)
            self.setWindowOpacity(self.old_opacity)
        else:
            self.control.toggle_btn.setChecked(False)
            self.setWindowOpacity(0.0)

        self.shortcut_timeout.start()

    def hide_all(self):
        self.control.hide()
        self.hide()

    def show_all(self):
        self.control.show()
        self.show()

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
