"""
py_knecht - load/save a user session

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
import os
from pathlib import Path

from PyQt5 import QtCore

from modules.knecht_log import init_logging
from modules.knecht_xml import XML

LOGGER = init_logging(__name__)

_SESSION_PATH = Path(os.getenv('APPDATA')) / 'RenderKnecht' / 'RK_Session.xml'


class _TreeSession(object):
    def __init__(self, widget):
        self.name = widget.objectName()
        self.widget = widget
        self.xml = XML('', widget)


class TreeSessionManager(QtCore.QObject):
    # XML DOM / hierarchy tags
    session_xml_dom = {
        'root': 'knecht_session',
        }

    def __init__(self, app, ui):
        super(TreeSessionManager, self).__init__()
        self.app, self.ui = app, ui
        self.trees = list()

        for tree in self.ui.tree_widget_list:
            tree_session = _TreeSession(tree)
            self.trees.append(tree_session)

    def save_session_xml(self):
        session_xml = XML(_SESSION_PATH, None)
        session_xml.root = self.session_xml_dom['root']

        for tree_session in self.trees:
            # Read items from widget
            has_data = tree_session.xml.update_xml_tree_from_widget()

            # Skip empty treeWidgets
            if not has_data:
                continue

            # Create a sub element for every treeWidget inside Session Xml
            session_xml.xml_sub_element = session_xml.root, tree_session.name

            # Get the sub element of the current tree and append the current tree elements to it
            current_tree_element = session_xml.xml_sub_element
            current_tree_element.append(tree_session.xml.root)

        session_xml.save_tree()