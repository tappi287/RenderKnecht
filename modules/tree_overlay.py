"""
knecht_overlay module provides overlay functionality for the main GUI tree widgets

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
import re
import queue

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QMovie, QPainter, QPalette, QBrush, QColor, QFont, QEnterEvent, QRegion

from modules.knecht_log import init_logging
from modules.app_globals import Itemstyle

# Initialize logging for this module
LOGGER = init_logging(__name__)


class _OverlayWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(_OverlayWidget, self).__init__(parent)
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)

        self.setPalette(palette)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        try:
            height = parent.frameGeometry().height() + parent.header().height()
        except AttributeError:
            LOGGER.error('Overlay Parent has no attribute "header". Using frame height.')
            # Parent has no header
            height = parent.frameGeometry().height()

        self.setGeometry(0, 0, parent.frameGeometry().width(), height)

        # Add the QMovie object to the label
        self.movie_screen = QtWidgets.QLabel(self)
        self.movie_screen.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Expanding)

    def move_to_center(self, current_mov):
        """ Move Screen to center """
        mr = current_mov.currentPixmap().rect()
        w, h = mr.width(), mr.height()

        r = self.parent.rect()
        x, y = r.width() / 2, r.height() / 2

        x, y = x - (w / 2), y - (h / 2)

        self.movie_screen.setGeometry(x, y, w, h)
        self._updateParent()

    def generic_center(self):
        """ Moves Movie to Center of parent """
        w, h = 64, 64
        r = self.parent.rect()
        x, y = r.width() / 2, r.height() / 2

        x, y = x - (w / 2), y - (h / 2)
        self.movie_screen.setGeometry(x, y, w, h)
        self._updateParent()

    def update_position(self, pos):
        """ Receives position of drop events """
        self.movie_screen.setGeometry(pos.x() - 32, pos.y(), 64, 64)
        self._updateParent()

    def _updateParent(self):
        """ Resize self and update parent widget """
        original = self.parent.resizeEvent

        def resizeEventWrapper(event):
            original(event)
            self.resize(event.size())

        resizeEventWrapper._original = original
        self.parent.resizeEvent = resizeEventWrapper
        self.resize(self.parent.size())


class Overlay(_OverlayWidget):
    """ Draw animated icons at cursor position to indicate user actions like copy etc. """

    def __init__(self, parent):
        super(Overlay, self).__init__(parent)

        self.parent = parent

        # Setup overlay movies
        # ref_created, copy_created
        movies = [
            # 0
            ':/anim/link_animation.gif',
            # 1
            ':/anim/copy_animation.gif',
            # 2
            ':/anim/coffee_animation.gif',
            # 3
            ':/anim/save_animation.gif',
        ]
        self.mov = []

        for i, m in enumerate(movies):
            self.mov.append(QMovie(m))
            self.mov[i].setCacheMode(QMovie.CacheAll)
            self.mov[i].setSpeed(100)
            self.mov[i].finished.connect(self.movie_finished)

        self.movie_screen.setMovie(self.mov[0])
        self.movie_screen.setGeometry(5, 20, 64, 64)

        self.show()

    def ref_created(self):
        """ Visual indicator for reference created """
        self.movie_screen.setMovie(self.mov[0])
        self.movie_screen.show()
        self.mov[0].jumpToFrame(0)
        self.mov[0].start()

    def copy_created(self):
        """ Visual indicator for copy created """
        self.movie_screen.setMovie(self.mov[1])
        self.movie_screen.show()
        self.mov[1].jumpToFrame(0)
        self.mov[1].start()

    def load_start(self):
        """ Visual indicator for load operation """
        self.movie_screen.setMovie(self.mov[2])
        self.mov[2].jumpToFrame(0)

        self.move_to_center(self.mov[2])
        self.movie_screen.show()

        self.mov[2].start()

    def load_finished(self):
        self.movie_screen.hide()
        self.mov[2].stop()

    def save_anim(self):
        """ Visual indicator for save operation """
        self.movie_screen.setMovie(self.mov[3])
        self.mov[3].jumpToFrame(0)
        self.movie_screen.show()

        self.move_to_center(self.mov[3])
        self.mov[3].start()

    def movie_finished(self):
        self.movie_screen.hide()


class IntroOverlay(_OverlayWidget):
    finished_signal = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(IntroOverlay, self).__init__(parent)
        self.parent = parent

        self.intro_mov = QMovie(':/anim/Introduction.gif')
        self.intro_mov.setCacheMode(QMovie.CacheAll)
        self.intro_mov.finished.connect(self.finished)

    def intro(self):
        LOGGER.info('Playing introduction in %sx %sy %spx %spx',
                    self.parent.rect().x(), self.parent.rect().y(),
                    self.parent.rect().width(), self.parent.rect().height())

        self.movie_screen.setMovie(self.intro_mov)
        self.movie_screen.setGeometry(self.parent.rect())
        self._updateParent()
        self.movie_screen.show()
        self.show()

        self.intro_mov.jumpToFrame(0)
        self.intro_mov.start()

    def finished(self):
        self.movie_screen.hide()
        self.hide()
        self.finished_signal.emit()


class InfoOverlay(QtWidgets.QWidget):
    """ Provides an overlay area with additional information """
    # Overlay queue size
    queue_size = 8

    # Maximum message length
    max_length = 1500

    # Background appearance
    # will be rgba(0, 0, 0, opacity * bg_opacity)
    bg_opacity = 0.85  # Multiplier
    bg_style = 'background: rgba(50, 50, 50, {opacity:.0f});'

    # Text appearance
    # will be rgba(0, 0, 0, opacity)
    text_style = 'padding: 5px; color: rgba(211, 215, 209, {opacity});'

    # Default display duration
    display_duration = 800

    # Default opacity
    opacity = 255

    # Swap Layout Threshold
    # If mouse has not moved out of overlay region before this threshold ->swap layout
    swap_layout_threshold = 100
    swap_layout_threshold_buttons = 350

    def __init__(self, widget):
        super(InfoOverlay, self).__init__(widget)

        # Parent widget where overlay will be displayed
        self.widget = widget

        # Disable horizontal scrollbar
        self.widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Calc header margin
        self.header_height = self.widget.header().height()

        # Make widget transparent
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Setup widget Layout
        self.box_layout = QtWidgets.QHBoxLayout(self.widget)
        self.box_layout.setContentsMargins(0, self.header_height, 0, 0)
        self.box_layout.setSpacing(0)

        # StyleSheets
        self.bgr_style = self.bg_style.format(opacity=self.opacity * self.bg_opacity)
        self.txt_style = self.text_style.format(opacity=self.opacity)

        # Text Label
        self.txt_label = QtWidgets.QLabel(self)
        self.anim_lbl = QtCore.QPropertyAnimation(self.txt_label, b"geometry")
        self.txt_label.setWordWrap(True)
        self.txt_label.setOpenExternalLinks(True)
        font = QFont()
        font.setPointSize(9)
        font.setStyleStrategy(QFont.PreferDefault)
        self.txt_label.setFont(font)
        self.txt_label.style_opacity = self.opacity

        # Text Label layout
        self.box_layout.addWidget(self.txt_label, 0, QtCore.Qt.AlignBottom)
        self.txt_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Expanding)

        # Button box
        self.btn_box = QtWidgets.QFrame(self)
        self.anim_btn = QtCore.QPropertyAnimation(self.btn_box, b"geometry")
        self.btn_box_layout = QtWidgets.QHBoxLayout(self.btn_box)
        self.btn_box_layout.setContentsMargins(11, 0, 33, 0)
        self.box_layout.addWidget(self.btn_box, 0, QtCore.Qt.AlignRight)
        self.btn_box.hide()

        # Button list
        self.btn_list = list()

        # Init timer's
        self.display_timer = QtCore.QTimer()
        self.display_timer.setSingleShot(True)
        self.layout_timer = QtCore.QTimer()
        self.layout_timer.setSingleShot(True)
        self.swap_timer = QtCore.QTimer()
        self.swap_timer.setSingleShot(True)

        # Connect the timers
        self.setup_timers()

        # Create queue
        self.msg_q = queue.Queue(self.queue_size)

        # Dynamic properties
        self.txt_label.style_opacity = 0
        self.txt_label.duration = self.display_duration
        self.txt_label.top_aligned = True
        self.btn_box.active = False
        self.swap_layout()

        # Move layout if widget entered by mouse
        self.txt_label.installEventFilter(self)

        # Hide initial overlay
        self.update_opacity(0, True)
        self.show()

    def setup_timers(self):
        # Reset vertcal layout on timer
        self.layout_timer.timeout.connect(self.layout_timer_expired)

        # Timer connections
        # self.obj.start_timer.connect(self.start_timer)
        self.display_timer.timeout.connect(self.display_time_expired)

        # Layout swap threshold
        self.swap_timer.timeout.connect(self.swap_timer_expired)

    def eventFilter(self, QObject, QEvent):
        if QObject is self.txt_label:

            if QEvent.type() == QEnterEvent.Enter:
                if self.txt_label.style_opacity >= 1:
                    # Threshold with active buttons
                    if self.btn_box.active:
                        self.swap_timer.start(InfoOverlay.swap_layout_threshold_buttons)
                        return True

                    # Threshold without buttons
                    self.swap_timer.start(InfoOverlay.swap_layout_threshold)

                return True

            if QEvent.type() == QEnterEvent.Leave:
                # Mouse left overlay region
                if self.swap_timer.isActive():
                    self.swap_timer.stop()

                return True

            QEvent.ignore()
            return False

    def display(self,
                message: str = 'Information overlay',
                duration: int = display_duration,
                immediate: bool = False,
                *buttons):
        """ add new overlay message """
        if self.msg_q.full():
            return

        msg_check = self.check_msg_length(message, duration)
        if msg_check:
            # Split long messages
            message_list, new_duration = msg_check
            for message in message_list:
                self.msg_q.put((message, new_duration, buttons))
        else:
            # Single message
            self.msg_q.put((message, duration, buttons))

        if immediate:
            # Request immediate display by forcing a short timeout event
            self.stop_timer()

        if not self.display_timer.isActive():
            if not self.btn_box.active:
                self.display_next_entry()

    def display_confirm(self,
                        message: str = 'Confirm message',
                        *buttons,
                        immediate: bool = False) -> None:
        """ Add overlay message and buttons and wait for confirmation """
        self.display(message, self.display_duration, immediate, *buttons)

    def display_time_expired(self, was_btn_box=False):
        if self.msg_q.empty():
            if was_btn_box:
                self.update_opacity(0)
            else:
                self.update_opacity(0, show_anim=True)
            return

        if not self.btn_box.active:
            self.display_next_entry()

    def display_exit(self):
        """ Exit confirmation dialog with buttons """
        self.btn_box.active = False

        # Delete buttons
        if self.btn_list:
            for btn in self.btn_list:
                btn.deleteLater()

            self.btn_list = list()

        # Hide overlay
        self.display_time_expired(was_btn_box=True)

    def display_next_entry(self):
        """ Get next message from queue, check lenght and display it """
        q = self.msg_q.get()

        if q is not None:
            # Unpack tuple
            message, duration, buttons = q

            # Display animation on initial display event
            show_anim = False
            if self.txt_label.style_opacity == 0:
                show_anim = True

            # Create Buttons
            if buttons:
                for btn in buttons:
                    self.create_button(*btn)

            # Display message
            self.txt_label.setText(message)
            self.update_opacity(self.opacity, show_anim=show_anim)
            self.display_timer.start(duration)

    def create_button(self, txt: str = 'Button', callback=None):
        """ Dynamic button creation on request """
        new_button = QtWidgets.QPushButton(txt, self.btn_box)
        new_button.setStyleSheet(Itemstyle.DG_BTN_READY)
        self.btn_box_layout.addWidget(new_button, 0, QtCore.Qt.AlignRight)

        if callback is None:
            new_button.pressed.connect(self.display_exit)
        else:
            new_button.pressed.connect(callback)

        self.btn_box.active = True
        self.btn_list.append(new_button)

    def check_msg_length(self, message, duration):
        """ Check message length and split if nessecary """

        def split_long_message(new_message, lenght):
            """ Split longer messages into seperate messages and return as list """
            # TODO \n wird nicht korrekt gesplittet wenn kein whitespace \s vorkommt
            pattern = r'(.{,' + str(lenght) + r'})\s(.*$)'
            tmp_message_list = re.findall(pattern, new_message)

            # Result is [(result_1, result_2)], convert back to list
            tmp_message_list = tmp_message_list[0]
            tmp_message_list = list(tmp_message_list)

            return tmp_message_list

        if len(message) > self.max_length:
            # Split long messages
            message_list = split_long_message(message, self.max_length)

            # Shorten display duration per part
            new_duration = (duration / len(message_list)) * 1.4

            for msg_item in message_list:
                if self.msg_q.full():
                    LOGGER.debug('Overlay message queue full.')
                    self.display_next_entry()

            LOGGER.debug('Overlay message split: %s', message_list)
            return message_list, new_duration
        else:
            return False

    def update_opacity(self, opacity: int, show_anim: bool=False):
        """ called from worker thread for animated fade out """
        # Do not hide widget if Confirmation question displayed
        if self.btn_box.active:
            opacity = self.opacity
            self.btn_box.show()

            self.anim_lbl.stop()
            show_anim=False
        else:
            self.btn_box.hide()

        self.txt_label.setStyleSheet(self.bgr_style + self.txt_style)
        self.btn_box.setStyleSheet(self.bgr_style)
        self.txt_label.style_opacity = opacity

        if self.txt_label.style_opacity >= 1:
            self.txt_label.show()

            if show_anim:
                self.label_animation(0, 1, 90)
        else:
            if show_anim and not self.txt_label.top_aligned:
                self.label_animation(1, 0, 600)
            else:
                self.txt_label.hide()

    def label_animation(self, start_val, end_val, duration):
        if self.anim_lbl.state() == QtCore.QAbstractAnimation.Running:
            if end_val > 0:
                self.anim_lbl.stop()
            return

        rect = self.txt_label.frameGeometry()
        h = max(self.txt_label.sizeHint().height(), rect.height())
        start_height = h * start_val
        end_height = h * end_val
        start_rect = QtCore.QRect(rect.x(), rect.y() + end_height, rect.width(), rect.height())
        end_rect = QtCore.QRect(rect.x(), rect.y() + start_height, rect.width(), rect.height())

        self.anim_lbl.setDuration(duration)
        self.anim_lbl.setStartValue(start_rect)
        self.anim_lbl.setEndValue(end_rect)

        if end_val > 0:
            self.anim_lbl.setEasingCurve(QtCore.QEasingCurve.OutSine)
        else:
            self.anim_lbl.setEasingCurve(QtCore.QEasingCurve.InExpo)

        self.anim_lbl.start(QtCore.QPropertyAnimation.KeepWhenStopped)

        self.anim_lbl.finished.connect(self.anim_label_finished)

    def anim_label_finished(self):
        if self.txt_label.style_opacity == 0:
            self.txt_label.hide()

    def swap_layout(self):
        """ Swap Layout-Alignment from top to bottom """
        if not self.txt_label.top_aligned:
            self.txt_label.top_aligned = True
            self.box_layout.setAlignment(QtCore.Qt.AlignTop)

            # Reset vertical layout after timeout
            self.layout_timer.start(int(self.display_duration * 1.5))
        else:
            self.txt_label.top_aligned = False
            self.box_layout.setAlignment(QtCore.Qt.AlignBottom)

            self.layout_timer.stop()

        self.update_opacity(self.txt_label.style_opacity)

    def swap_timer_expired(self):
        """ Threshold expired -> swap layout """
        self.swap_layout()

    def layout_timer_expired(self):
        """ Resets vertical position of info overlay after timeout if overlay is invisible """
        if self.txt_label.top_aligned:
            if self.txt_label.style_opacity <= 1:
                self.swap_layout()
            else:
                self.layout_timer.start(
                    self.display_timer.remainingTime() + 150)

    def stop_timer(self):
        """ Restart timer with short timeout if it is currently active """
        if self.display_timer.isActive():
            self.display_timer.start(20)


class UnusedPainter:
    # Overlay height in pixels
    overlay_height = 25
    # Background appearance
    bg_color = (60, 60, 60)  # RGB
    bg_opacity = 0.7  # Multiplier
    bg_brush = QBrush(QColor(*bg_color, 255 * bg_opacity))
    """
    def resizeEvent(self, QResizeEvent):
        size = QResizeEvent.size()
        top = size.height() - self.txt_label.height()
        pos = QtCore.QPoint(0, top)

        size = QtCore.QSize(size.width(), self.txt_label.height())

        # self.lower_rect = QtCore.QRect(pos, size)
        # self.txt_label.setGeometry(self.lower_rect)
        # self.txt_label.setMinimumSize(self.txt_label.sizeHint())
    """
    """
    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.fillRect(self.lower_rect, self.bg_brush)
        self._update_parent()
    """
