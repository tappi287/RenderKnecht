from pathlib import Path

import imageio
import numpy as np
from PIL import Image, ImageQt
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize, QRect, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QImage, QKeySequence, QPalette, QColor

from modules.app_globals import Itemstyle, TCP_IP, TCP_PORT
from modules.gui_set_path import SetDirectoryPath
from modules.knecht_log import init_logging
from modules.knecht_socket import Ncat
from modules.tree_overlay import InfoOverlay

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


class ViewerShortcuts:
    def __init__(self, viewer, control):
        self.viewer, self.control = viewer, control

    def set_shortcuts(self, parent):
        # Viewer Image Canvas Display On/Off
        toggle_view = QtWidgets.QShortcut(QKeySequence(Qt.Key_Space), parent)
        toggle_view.activated.connect(self.viewer.toggle_viewer)
        toggle_view_x = QtWidgets.QShortcut(QKeySequence(Qt.Key_X), parent)
        toggle_view_x.activated.connect(self.viewer.toggle_viewer)

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
                LOGGER.info('Dropped URL: %s', file_url)
                self.file_dropped.emit(file_url)


class ControllerWidget(FileDropWidget):
    logo_row_height = 35
    logo_margin = 4
    y_margin = 8
    height = 74

    def __init__(self, viewer):
        super(ControllerWidget, self).__init__(
            flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint,
            )

        self.viewer = viewer

        # Window
        self.setWindowTitle(f'{viewer.windowTitle()} - Controller')
        self.setWindowIcon(viewer.windowIcon())
        self.setStyleSheet("QWidget#not_me { background: rgba(100, 100, 100, 120); border-radius: 5px; }"
                           "QPushButton, QLineEdit, QComboBox, QLabel {"
                           "    max-height: 26px; margin: 5px;"
                           "    background-color: rgb(80, 80, 80); border: 1px solid rgb(50, 50, 50);"
                           "    border-radius: 5px; color: rgb(210, 210, 210);"
                           "}"
                           "QComboBox {"
                           "    padding: 0 10px;"
                           "}"
                           "QLabel#grabber_top {"
                           "    padding: 0; text-align: center; max-height: 35px; max-width: 35px; margin: 0;"
                           "    background: none; border: none;"
                           "}"
                           "QLabel#grabber {"
                           "    padding: 0; text-align: center; max-width: 120px; max-height: 26px; margin-left: 0;"
                           "}"
                           "QPushButton:pressed {"
                           "    background-color: rgb(84, 92, 98);"
                           "}"
                           "QPushButton#exit_btn {"
                           "    min-width: 26px; max-width: 26px; margin-right: 0;"
                           "}"
                           "QPushButton#fwd_btn {"
                           "    min-width: 100px;"
                           "}"
                           "QPushButton#bck_btn {"
                           "    min-width: 100px;"
                           "}"
                           "QPushButton#toggle_btn {"
                           "    min-width: 52px;"
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
                           "QSlider {"
                           "    min-width: 100px; max-width: 120px; height: 26px; margin-right: 5px;"
                           "    border-radius: 5px;"
                           "}"
                           "QSlider::groove:horizontal {"
                           "    border: 1px solid #999999; border-radius: 5px;"
                           "    height: 26px;"
                           "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);"
                           "}"
                           "QSlider::handle:horizontal {"
                           "    background: rgb(80, 80, 80);"
                           "    border: 1px solid rgb(50, 50, 50);"
                           "    width: 18px;"
                           "    margin: -2px 0;"
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
        self.top_layout = QtWidgets.QVBoxLayout(self)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(0)
        self.grabber_top = QtWidgets.QLabel('', self)
        self.grabber_top.setPixmap(QPixmap(Itemstyle.ICON_PATH['compare']))
        self.grabber_top.setScaledContents(True)
        self.grabber_top.setObjectName('grabber_top')
        self.top_layout.addWidget(self.grabber_top)
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
        self.slider.setObjectName('slider')
        self.slider.setRange(1, 11)
        self.slider.setValue(11)
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

        height = self.logo_row_height + viewer_height + self.height + self.logo_margin
        width = self.viewer.size().width()

        self.setGeometry(x, y, width, height)

    def _close_viewer(self):
        self.close()
        self.viewer.close()


class KnechtImageViewer(FileDropWidget):
    button_timeout = QTimer()
    button_timeout.setInterval(100)
    button_timeout.setSingleShot(True)

    shortcut_timeout = QTimer()
    shortcut_timeout.setInterval(50)
    shortcut_timeout.setSingleShot(True)

    slider_timeout = QTimer()
    slider_timeout.setInterval(50)
    slider_timeout.setSingleShot(True)

    dg_btn_timeout = QTimer()
    dg_btn_timeout.setInterval(1000)
    dg_btn_timeout.setSingleShot(True)

    dg_poll_timer = QTimer()
    dg_poll_timer.setInterval(500)

    DEFAULT_SIZE = (800, 450)
    DEFAULT_POS = (150, 150)

    MAX_SIZE = QSize(4096, 4096)

    MAX_SIZE_FACTOR = 2.5
    MIN_SIZE_FACTOR = 0.25
    SIZE_INCREMENT = 0.25

    ICON = Itemstyle.ICON_PATH['img']

    FILE_TYPES = ['.png', '.jpg', '.jpeg', '.tif', '.tga', '.hdr', '.exr']

    def __init__(self, app, ui):
        super(KnechtImageViewer, self).__init__(
            flags=Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
            )
        self.app, self.ui = app, ui
        self.setWindowIcon(QIcon(QPixmap(self.ICON)))
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AcceptDrops, True)
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
        self.img_size_factor = 1.0
        self.img_size = QSize(*self.DEFAULT_SIZE)

        # Save window position for drag
        self.oldPos = self.pos()

        self.setGeometry(*self.DEFAULT_POS, *self.DEFAULT_SIZE)
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
        self.img_canvas.setStyleSheet('QLabel#img_canvas {'
                                      'background: rgba(180, 180, 180, 180); border-radius: 5px;'
                                      '}')

        # Overlay
        self.overlay = InfoOverlay(self.img_canvas)
        self.shortcuts_shown = False

        # App logic
        self.path_dlg = SetDirectoryPath(app, ui,
                                         mode='file',
                                         line_edit=self.control.line_edit,
                                         tool_button=self.control.path_btn,
                                         parent=self)
        self.path_dlg.path_changed.connect(self.set_img_path)

        self.control.slider.sliderMoved.connect(self.start_opacity_slider_timeout)
        self.slider_timeout.timeout.connect(self.set_opacity_from_slider)
        self.control.slider.sliderReleased.connect(self.set_opacity_from_slider)

        self.control.size_box.currentIndexChanged.connect(self.combo_box_size)
        self.set_combo_box_to_current_factor()

        self.control.bck_btn.pressed.connect(self.iterate_bck)
        self.control.fwd_btn.pressed.connect(self.iterate_fwd)

        self.control.toggle_btn.pressed.connect(self.toggle_viewer)
        self.control.toggle_dg_btn.pressed.connect(self.dg_toggle_sync)

        self.shortcuts = ViewerShortcuts(self, self.control)
        self.shortcuts.set_shortcuts(self)
        self.shortcuts.set_shortcuts(self.control)

        self.file_dropped.connect(self.path_dropped)
        self.control.file_dropped.connect(self.path_dropped)

    def display_shortcut_overlay(self):
        if self.shortcuts_shown:
            return

        self.overlay.display_confirm(
            'Shortcuts<br>'
            '+/&#45; oder Q/E &#45; Bildanzeige vergößern/verkleinern<br>'
            '&lt;/&gt; oder A/D          &#45; Nächste/Vorherige Bilddatei im Ordner<br>'
            'STRG+/STRG&#45; oder W/S  &#45; Transparenz erhöhen/verringern<br><br>'
            'Leertaste oder X &#45; Bildanzeige ein&#45;/ausschalten<br>'
            'F &#45; DeltaGen Viewer Sync ein&#45;/ausschalten<br><br>'
            'Pfad auswählen oder Dateien in das Fenster ziehen.',
            ('[X]', None), immediate=True)

        self.shortcuts_shown = True

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
        self.set_img_path(Path(file_url))

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

        for idx, img_file in enumerate(self.img_dir.glob('*.*')):
            if f'{img_file.suffix}'.casefold() in self.FILE_TYPES:
                self.img_list.append(img_file)

        if current_file in self.img_list:
            current_idx = self.img_list.index(current_file)
            self.img_index = current_idx
            LOGGER.debug('Current file set to: %s', current_idx)

    def iterate_fwd(self):
        self.img_index += 1
        self.iterate_images()

    def iterate_bck(self):
        self.img_index -= 1
        self.iterate_images()

    def iterate_images(self):
        if not self.img_list or self.button_timeout.isActive():
            if not self.img_list:
                self.overlay.display('Kein unterstützen Bilddaten im Ordner gefunden oder '
                                     'kein Bildordner gewählt.', 3000)
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
            self.overlay.display_exit()
            self.overlay.display(f'<span style="font-size: 11pt;">'
                                 f'Datei <b>{img_path.name}</b> konnt nicht geladen werden!'
                                 f'</span>'
                                 , 5000, immediate=True)

        if self.current_img:
            self.img_canvas.setStyleSheet('background: rgba(0, 0, 0, 0);')
            self.img_canvas.setPixmap(self.current_img)
            self.img_size = self.current_img.size()
            self.change_viewer_size()

            self.overlay.display_exit()
            self.overlay.display(f'<span style="font-size: 11pt;">'
                                 f'{self.img_index + 1:02d}/{len(self.img_list):02d} - '
                                 f'<b>{img_path.name}</b> - '
                                 f'{self.img_size.width()}x{self.img_size.height()}px'
                                 f'</span>'
                                 , 1200, immediate=True)

        self.button_timeout.start()

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

    def start_opacity_slider_timeout(self):
        if not self.slider_timeout.isActive():
            self.slider_timeout.start()

    def set_opacity_from_slider(self):
        opacity = self.control.slider.value() * 0.095
        self.set_window_opacity(opacity)

    def set_window_opacity(self, opacity):
        if self.shortcut_timeout.isActive():
            return

        opacity = max(0.05, min(1.0, opacity))
        self.current_opacity = opacity
        self.setWindowOpacity(opacity)

        self.shortcut_timeout.start()

    # ------ VISIBILITY -------
    def toggle_viewer(self):
        if self.shortcut_timeout.isActive():
            return

        if self.windowOpacity() == 0.0:
            self.control.toggle_btn.setChecked(True)
            self.setWindowOpacity(self.current_opacity)
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
        self.display_shortcut_overlay()

    # ------ OVERRIDES -------
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
