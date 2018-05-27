"""
knecht_splash_screen for py_knecht. Displays animated Splash Screen

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

import time
from PyQt5.QtGui import QMovie, QPixmap, QPainter
from PyQt5.QtWidgets import QSplashScreen
from PyQt5 import QtCore


class MovieSplashScreen(QSplashScreen):

    def __init__(self, movie, parent=None):
        movie.jumpToFrame(0)
        pixmap = QPixmap(movie.frameRect().size())

        QSplashScreen.__init__(self or parent, pixmap, QtCore.Qt.WindowStaysOnTopHint)
        self.movie = movie
        self.movie.frameChanged.connect(self.repaint)

    def showEvent(self, event):
        self.movie.start()

    def hideEvent(self, event):
        self.movie.stop()

    def paintEvent(self, event):

        painter = QPainter(self)
        pixmap = self.movie.currentPixmap()
        self.setMask(pixmap.mask())
        painter.drawPixmap(0, 0, pixmap)

    def sizeHint(self):

        return self.movie.scaledSize()


def show_splash_screen_movie(app):
    movie = QMovie(str(':/anim/Splash_Screen.gif'))
    splash = MovieSplashScreen(movie, app)
    splash.show()

    start = time.time()

    while movie.state() == QMovie.Running and time.time() < start + 1.1:
        app.processEvents()

    return splash