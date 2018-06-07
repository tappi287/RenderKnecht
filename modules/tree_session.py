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
import time
from pathlib import Path

from PyQt5 import QtCore

from modules.tree_methods import tree_setup_header_format
from modules.knecht_log import init_logging
from modules.knecht_xml import XML
from modules.app_strings import Msg

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
        'root': 'knecht_session', 'origin': 'origin',
        }

    def __init__(self, app, ui):
        super(TreeSessionManager, self).__init__()
        self.app, self.ui = app, ui
        self.trees = list()

        for tree in self.ui.tree_widget_list:
            tree_session = _TreeSession(tree)
            self.trees.append(tree_session)

    def save_session(self):
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

        self.describe_origin(session_xml)
        session_xml.save_tree()
        LOGGER.debug('Saved tree contents to session file:\n%s', _SESSION_PATH.as_posix())

    def load_session(self):
        __xml = XML('', None)
        xml_file = Path(_SESSION_PATH)

        if not xml_file.exists():
            return

        try:
            xml_tree = __xml.parse_xml_file(xml_file)
        except Exception as e:
            LOGGER.error('Error loading session data: %s', e)
            return

        # Move Variant Tree items out of orphan preset
        self.prepare_variants(xml_tree)

        for tree_session in self.trees:
            name = tree_session.name

            tree_xml = xml_tree.find(f'./{name}/')
            if tree_xml:
                tree_session.xml.parse_element_to_tree_widget(tree_xml)
                LOGGER.debug('Loading session elements for %s.', tree_session.name)

            # Sort the tree widgets
            self.ui.sort_tree_widget.sort_all(tree_session.widget)

        # Sort treeWidget headers according to content
        tree_setup_header_format(self.ui.tree_widget_list)

    @staticmethod
    def prepare_variants(xml_tree):
        variants = list()
        variants_xml = xml_tree.find('./treeWidget_Variants/')

        if not variants_xml:
            return

        # Get all variants from orphan preset
        var_lvl = XML.dom_tags.get('sub_lvl_1')
        variant_presets = variants_xml.find(f'./{var_lvl}')
        orphan_preset = variant_presets.find('./')

        if not orphan_preset.attrib.get('name') == Msg.ORPHAN_PRESET_NAME:
            return

        for variant in orphan_preset.iterfind('./'):
            variants.append(variant)

        # Insert Variants one level above
        for v in variants:
            variant_presets.append(v)

        # Delete orphan preset
        variant_presets.remove(orphan_preset)

    @classmethod
    def describe_origin(cls, session_xml_cls):
        __origin = session_xml_cls.root.find(f'./{cls.session_xml_dom.get("origin")}')

        __o_txt = 'RenderKnecht Session on '+\
                  os.getenv('COMPUTERNAME', 'Unknown_System') + ' @ ' +\
                  time.strftime('%Y-%m-%d_%H:%M:%S')
        __origin.text = __o_txt
