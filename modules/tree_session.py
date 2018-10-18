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
from functools import partial

from PyQt5 import QtCore

from modules.tree_methods import tree_setup_header_format, iterate_tree_widget_items_flat, set_item_flags
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
        'settings': 'renderknecht_settings',
        'setting_tag': 'setting',
        }

    settings = {
        'unsaved_changes_present': False,
        'save_file': None,
        }
    
    # Xml tree setings will be loaded from
    load_xml = None

    # Deferred settings load signal
    load = QtCore.pyqtSignal()

    # Deferred settings load overlay
    load_ovr_timer = QtCore.QTimer()
    load_ovr_timer.setSingleShot(True)
    load_ovr_timer.setInterval(500)

    # Deferred initial session load time
    init_load_timer = QtCore.QTimer()
    init_load_timer.setSingleShot(True)
    init_load_timer.setInterval(100)

    # -- Auto Save --
    # Interval 5 Minutes - 300000ms
    auto_save_interval = 5000
    # Interval to postpone when user is active
    auto_save_post_interval = 5000

    auto_save_timer = QtCore.QTimer()
    auto_save_timer.setTimerType(QtCore.Qt.VeryCoarseTimer)

    def __init__(self, app, ui):
        super(TreeSessionManager, self).__init__()
        self.app, self.ui = app, ui
        self.tree_sessions = list()

        for tree in self.ui.tree_widget_list:
            tree_session = _TreeSession(tree)
            self.tree_sessions.append(tree_session)

        # Init auto save
        self.auto_save_timer.setInterval(self.auto_save_interval)
        self.auto_save_timer.timeout.connect(self.auto_save_session)
        self.auto_save_timer.start()

    def auto_save_session(self):
        if self.ui.idle:
            # If user is inactive, save
            self.auto_save_timer.setInterval(self.auto_save_interval)
            self.save_session()
        else:
            # If user is active, postpone auto-save
            self.ui.treeWidget_DestPreset.info_overlay.display(
                'Session wird bei nächster Inaktivität gespeichert.', 3000
                )
            self.auto_save_timer.start(self.auto_save_post_interval)

    def save_session(self):
        self.ui.treeWidget_DestPreset.info_overlay.display(Msg.SESSION_SAVING, 3000)

        session_xml = XML(_SESSION_PATH, None)
        session_xml.root = self.session_xml_dom['root']

        for tree_session in self.tree_sessions:
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
        self.save_settings(session_xml)

        session_xml.save_tree()
        LOGGER.debug('Saved tree contents to session file:\n%s', _SESSION_PATH.as_posix())

    def load_session(self):
        __xml = XML('', None)
        xml_file = Path(_SESSION_PATH)

        if not xml_file.exists():
            return

        try:
            self.load_xml = __xml.parse_xml_file(xml_file)
        except Exception as e:
            LOGGER.error('Error loading session data: %s', e)
            return

        # Move Variant Tree items out of orphan preset
        self.prepare_variants(self.load_xml)

        for tree_session in self.tree_sessions:
            name = tree_session.name

            tree_xml = self.load_xml.find(f'./{name}/')
            if tree_xml is not None:
                tree_session.xml.parse_element_to_tree_widget(tree_xml)
                LOGGER.debug('Loading session elements for %s.', tree_session.name)

                # Set item flags for editable widgets
                if tree_session.name != 'treeWidget_SrcPreset':
                    for item in iterate_tree_widget_items_flat(tree_session.widget):
                        set_item_flags(item)

            # Sort the tree widgets
            self.ui.sort_tree_widget.sort_all(tree_session.widget)

        # Sort treeWidget headers according to content
        tree_setup_header_format(self.ui.tree_widget_list)

        # Load settings after tree sorting is finished
        # otherwise unsaved changes will be overridden thru sorting
        if self.ui.sort_tree_widget.work_timer.isActive():
            # Sorting active, load settings when timer finishes
            self.load.connect(self.load_settings)
            self.ui.sort_tree_widget.work_timer.timeout.connect(
                self.load
                )
        else:
            # Sorting inactive, load settings
            self.load_settings()

        self.load_ovr_timer.timeout.connect(self.load_finished_overlay)
        self.load_ovr_timer.start()

    def load_finished_overlay(self):
        self.ui.treeWidget_SrcPreset.info_overlay.display(Msg.SESSION_LOADED, 3000)

    @staticmethod
    def prepare_variants(xml_tree):
        """
            VariantWidget elements get collected to orphan parent on save.
            Remove the orphan parent before loading the elements
        """
        variants = list()
        variants_xml = xml_tree.find('./treeWidget_Variants/')

        if variants_xml is None:
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

    def load_settings(self):
        self.load.disconnect()
        __settings = self.load_xml.find(f'./{self.session_xml_dom.get("settings")}')

        for e in __settings.iterfind(f'./{self.session_xml_dom.get("setting_tag")}'):
            for k, v in e.attrib.items():
                if v == 'True':
                    v = True
                elif v == 'False':
                    v = False

                self.settings.update({k: v})

        # Set settings
        self.ui.unsaved_changes_present = self.settings.get('unsaved_changes_present', False)
        LOGGER.debug('Session setting unsaved change: %s', self.ui.unsaved_changes_present)
        save_file = self.settings.get('save_file')

        if save_file:
            save_file = Path(save_file)

            if Path(save_file).exists() and Path(save_file).suffix == '.xml':
                self.ui.current_path = save_file.as_posix()
                # Set in load/save menu method
                self.app.menu.save_mgr.save_file = save_file.as_posix()
                # Update window title
                self.ui.set_window_title(save_file.name)

    def save_settings(self, session_xml):
        __settings = session_xml.root.find(f'./{self.session_xml_dom.get("settings")}')

        if __settings is None:
            LOGGER.debug('Settings tag not found, creating tag %s', self.session_xml_dom.get("settings"))
            session_xml.xml_sub_element = session_xml.root, self.session_xml_dom.get("settings")
            __settings = session_xml.xml_sub_element

        # Set current settings
        self.settings.update({'unsaved_changes_present': self.ui.unsaved_changes_present})
        self.settings.update({'save_file': Path(self.app.menu.save_mgr.save_file).as_posix()})

        # Add settings to session xml
        for k, v in self.settings.items():
            session_xml.xml_sub_element = __settings, self.session_xml_dom.get('setting_tag')
            __element = session_xml.xml_sub_element
            __element.set(k, str(v))
