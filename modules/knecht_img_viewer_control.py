from pathlib import Path

import imageio
import numpy as np
from PIL import Image
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QIcon
from modules.app_globals import Itemstyle
from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)


class KnechtLoadImage(QThread):
    loaded_img = pyqtSignal(object)
    load_failed = pyqtSignal(str)

    def __init__(self, parent, img_file):
        super(KnechtLoadImage, self).__init__()
        self.parent = parent
        self.img_file = img_file

    def run(self):
        self.loaded_img.connect(self.parent.image_loaded)
        self.load_failed.connect(self.parent.image_load_failed)

        try:
            image = read_to_qpixmap(self.img_file)
            self.loaded_img.emit(image)
        except Exception as e:
            self.load_failed.emit(str(e))


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


class ViewerShortcuts:
    def __init__(self, viewer, control):
        self.viewer, self.control = viewer, control

    def set_shortcuts(self, parent):
        # Viewer Image Canvas Display On/Off
        toggle_view = QtWidgets.QShortcut(QKeySequence(Qt.Key_Space), parent)
        toggle_view.activated.connect(self.control.toggle_btn.animateClick)
        toggle_view_x = QtWidgets.QShortcut(QKeySequence(Qt.Key_X), parent)
        toggle_view_x.activated.connect(self.control.toggle_btn.animateClick)

        # Increase Image Size
        size_hi = QtWidgets.QShortcut(QKeySequence(Qt.Key_Plus), parent)
        size_hi.activated.connect(self.viewer.increase_size)
        size_hi_e = QtWidgets.QShortcut(QKeySequence(Qt.Key_E), parent)
        size_hi_e.activated.connect(self.viewer.increase_size)
        # Decrease Image Size
        size_lo = QtWidgets.QShortcut(QKeySequence(Qt.Key_Minus), parent)
        size_lo.activated.connect(self.viewer.decrease_size)
        size_lo_q = QtWidgets.QShortcut(QKeySequence(Qt.Key_Q), parent)
        size_lo_q.activated.connect(self.viewer.decrease_size)

        # Increase Viewer Window Opacity
        opa_hi_w = QtWidgets.QShortcut(QKeySequence(Qt.Key_W), parent)
        opa_hi_w.activated.connect(self.viewer.increase_window_opacity)
        opa_hi = QtWidgets.QShortcut(QKeySequence('Ctrl++'), parent)
        opa_hi.activated.connect(self.viewer.increase_window_opacity)
        # Decrease Viewer Window Opacity
        opa_lo_s = QtWidgets.QShortcut(QKeySequence(Qt.Key_S), parent)
        opa_lo_s.activated.connect(self.viewer.decrease_window_opacity)
        opa_lo = QtWidgets.QShortcut(QKeySequence('Ctrl+-'), parent)
        opa_lo.activated.connect(self.viewer.decrease_window_opacity)

        # Exit
        esc = QtWidgets.QShortcut(QKeySequence(Qt.Key_Escape), parent)
        esc.activated.connect(self.viewer.close)

        # Load Next Image
        fwd = QtWidgets.QShortcut(QKeySequence(Qt.Key_Right), parent)
        fwd.activated.connect(self.control.fwd_btn.animateClick)
        fwd_d = QtWidgets.QShortcut(QKeySequence(Qt.Key_D), parent)
        fwd_d.activated.connect(self.control.fwd_btn.animateClick)
        # Load Previous Image
        bck = QtWidgets.QShortcut(QKeySequence(Qt.Key_Left), parent)
        bck.activated.connect(self.control.bck_btn.animateClick)
        bck_a = QtWidgets.QShortcut(QKeySequence(Qt.Key_A), parent)
        bck_a.activated.connect(self.control.bck_btn.animateClick)

        # Toggle DeltaGen Viewer Sync
        dg = QtWidgets.QShortcut(QKeySequence(Qt.Key_F), parent)
        dg.activated.connect(self.viewer.dg_toggle_sync)


class FileDropWidget(QtWidgets.QWidget):
    file_dropped = pyqtSignal(str)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e is None or not e.mimeData().hasUrls:
            e.ignore()
            return

        for url in e.mimeData().urls():
            if url.isLocalFile():
                file_url = url.toLocalFile()
                # LOGGER.info('Dropped URL: %s', file_url)
                self.file_dropped.emit(file_url)


class ControllerWidget(FileDropWidget):
    logo_row_height = 35
    logo_margin = 4
    y_margin = 8
    control_height = 88

    def __init__(self, viewer):
        super(ControllerWidget, self).__init__(
            flags=Qt.FramelessWindowHint |
                  Qt.WindowStaysOnTopHint |
                  Qt.Tool |  # Hide Taskbar entry
                  Qt.CustomizeWindowHint
            )

        self.viewer = viewer

        # Window
        self.setWindowTitle(f'{viewer.windowTitle()} - Controller')
        self.setWindowIcon(viewer.windowIcon())
        self.setStyleSheet("QWidget#not_me { background: rgba(100, 100, 100, 120); border-radius: 5px; }"
                           "QPushButton, QLineEdit, QComboBox, QLabel, QToolButton {"
                           "    max-height: 30px; height: 30px; margin: 5px;"
                           "    background-color: rgb(80, 80, 80); border: 1px solid rgb(50, 50, 50);"
                           "    border-radius: 5px; color: rgb(210, 210, 210);"
                           "}"
                           "QComboBox {"
                           "    padding: 0 10px;"
                           "}"
                           "QLabel#logo_top {"
                           "    padding: 0; text-align: center; max-height: 39px; max-width: 35px; margin: 0;"
                           "    height: 39px; width: 35px;"
                           "    background: none; border: none;"
                           "}"
                           "QPushButton#exit_btn, QPushButton#help, QPushButton#min_btn {"
                           "    width: 30px; height: 26px; margin: 0 0 0 5px;"
                           "}"
                           "QLabel#grabber_top {"
                           "    padding: 0 0 2px 5px; margin: 0; height: 26px; font-weight: bold;"
                           "}"
                           "QLabel#grabber {"
                           "    padding: 0; max-width: 120px; max-height: 30px; margin-left: 0;"
                           "}"
                           "QPushButton:pressed {"
                           "    background-color: rgb(210, 210, 210);"
                           "}"
                           "QPushButton#fwd_btn {"
                           "    min-width: 100px;"
                           "}"
                           "QPushButton#bck_btn {"
                           "    min-width: 100px; margin: 5px 0 5px 5px;"
                           "}"
                           "QPushButton#toggle_btn {"
                           "    min-width: 52px;"
                           "}"
                           "QPushButton#toggle_dg_btn {"
                           "    padding: 0 10px;"
                           "}"
                           "QPushButton#toggle_btn {"
                           "    background-color: rgb(150, 150, 150);"
                           "}"
                           "QPushButton#toggle_btn:checked {"
                           "    background-color: rgb(80, 80, 80);"
                           "}"
                           "QPushButton#toggle_dg_btn:checked {"
                           "    background-color: rgb(150, 150, 150);"
                           "}"
                           "QToolButton {"
                           "    margin: 0 0 0 5px;"
                           "}"
                           "QSlider {"
                           "    min-width: 100px; max-width: 120px; height: 30px; margin-right: 5px;"
                           "    border-radius: 5px; border: none;"
                           "}"
                           "QSlider::groove:horizontal {"
                           "    border: none; border-radius: 5px;"
                           "    height: 26px;"
                           "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
                           "                stop:0 rgb(120, 120, 120), stop:1 rgb(210, 210, 210));"
                           "}"
                           "QSlider::handle:horizontal {"
                           "    background: rgb(120, 120, 120);"
                           "    border: 1px solid rgb(50, 50, 50);"
                           "    width: 18px;"
                           "    margin: -2px 0;"
                           "    border-radius: 5px;"
                           "}"
                           "QSlider::sub-page:horizontal {"
                           "    background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,"
                           "                stop: 0 rgb(50, 50, 50), stop: 1 rgb(120, 120, 120));"
                           "    border: none;"
                           "    border-radius: 5px;"
                           "}"
                           "QLineEdit {"
                           "    margin: 0 5px 0 5px;"
                           "}")

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AcceptDrops, True)

        self.widget_layout = QtWidgets.QVBoxLayout(self)
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(0)

        # Widget Layout
        self.top_layout = QtWidgets.QHBoxLayout(self)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)

        self.exit_btn = QtWidgets.QPushButton(QIcon(QPixmap(Itemstyle.ICON_PATH['close'])), '', self)
        self.exit_btn.pressed.connect(self._close_viewer)
        self.exit_btn.setObjectName('exit_btn')
        self.exit_btn.setFlat(True)

        self.min_btn = QtWidgets.QPushButton(QIcon(QPixmap(Itemstyle.ICON_PATH['window_min'])), '', self)
        self.min_btn.setObjectName('min_btn')
        self.min_btn.setIconSize(QSize(15, 19))

        self.help_btn = QtWidgets.QPushButton(QIcon(QPixmap(Itemstyle.ICON_PATH['window_help'])), '', self)
        self.help_btn.setObjectName('help')
        self.help_btn.setIconSize(QSize(15, 19))

        self.grabber_top = QtWidgets.QLabel('Knecht Image Viewer', self)
        self.grabber_top.setObjectName('grabber_top')
        self.grabber_top.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.logo_top = QtWidgets.QLabel('', self)
        self.logo_top.setPixmap(QPixmap(Itemstyle.ICON_PATH['compare']))
        self.logo_top.setScaledContents(True)
        self.logo_top.setObjectName('logo_top')

        self.top_layout.addWidget(self.logo_top)
        self.top_layout.addWidget(self.grabber_top)
        self.top_layout.addWidget(self.help_btn)
        self.top_layout.addWidget(self.min_btn)
        self.top_layout.addWidget(self.exit_btn)
        self.widget_layout.addLayout(self.top_layout)

        spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.widget_layout.addItem(spacer)

        # Button Row
        self.btn_row = QtWidgets.QHBoxLayout(self)
        self.btn_row.setContentsMargins(0, 0, 0, 0)
        self.btn_row.setSpacing(0)

        self.path_row = QtWidgets.QHBoxLayout(self)
        self.path_row.setContentsMargins(0, 0, 0, 0)
        self.path_row.setSpacing(0)

        self.widget_layout.addLayout(self.path_row)
        self.widget_layout.addLayout(self.btn_row)

        self.slider = QtWidgets.QSlider(Qt.Horizontal, self)
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.slider.setObjectName('slider')
        self.slider.setRange(1, 10)
        self.slider.setValue(10)
        self.slider.setSingleStep(1)

        self.btn_row.addWidget(self.slider)

        self.size_box = QtWidgets.QComboBox(self)
        min = round(viewer.MIN_SIZE_FACTOR * 100)
        max = round((viewer.MAX_SIZE_FACTOR + viewer.SIZE_INCREMENT) * 100)
        step = round(viewer.SIZE_INCREMENT * 100)
        for s in range(min, max, step):
            self.size_box.addItem(f'{s:02d}%', s * 0.01)

        self.btn_row.addWidget(self.size_box)

        self.toggle_dg_btn = QtWidgets.QPushButton(
            QIcon(QPixmap(Itemstyle.ICON_PATH['compare'])), 'Sync DeltaGen Viewer', self)
        self.toggle_dg_btn.setObjectName('toggle_dg_btn')
        self.toggle_dg_btn.setFlat(True)
        self.toggle_dg_btn.setCheckable(True)
        self.toggle_dg_btn.setChecked(False)
        self.btn_row.addWidget(self.toggle_dg_btn)

        toggle_icon = QIcon()
        toggle_icon.addPixmap(QPixmap(Itemstyle.ICON_PATH['eye-off']), QIcon.Normal, QIcon.Off)
        toggle_icon.addPixmap(QPixmap(Itemstyle.ICON_PATH['eye-on']), QIcon.Normal, QIcon.On)
        self.toggle_btn = QtWidgets.QPushButton(toggle_icon, '', self)
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

        # Path Row
        self.grabber = QtWidgets.QLabel('', self)
        self.grabber.setObjectName('grabber')
        self.grabber.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.path_row.addWidget(self.grabber)
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

        # Allow window dragging with mouse press
        self.mouseMoveEvent = self.viewer.mouseMoveEvent
        self.mousePressEvent = self.viewer.mousePressEvent

    def _viewer_move_wrapper(self, event):
        self.org_viewer_move_event(event)
        self._adapt_viewer_position()
        event.accept()

    def _viewer_resize_wrapper(self, event):
        self.org_viewer_resize_event(event)
        self._adapt_viewer_position()
        event.accept()

    def _adapt_viewer_position(self):
        viewer_height = self.viewer.size().height()

        x = self.viewer.x()
        y = self.viewer.y() - self.logo_row_height - self.logo_margin

        height = self.logo_row_height + viewer_height + self.control_height + self.logo_margin
        width = self.viewer.size().width()

        self.setGeometry(x, y, width, height)

    def _close_viewer(self):
        self.close()
        self.viewer.close()
