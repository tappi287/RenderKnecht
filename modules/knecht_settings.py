"""
knecht_settings for py_knecht. Reads and writes settings to user machine

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
import xml.etree.ElementTree as Et

_APPDATA_PATH = os.getenv('APPDATA')

_KNECHT_SETTINGS_PATH = os.path.join(_APPDATA_PATH, 'RenderKnecht')
_KNECHT_SETTINGS_FILE = os.path.join(_KNECHT_SETTINGS_PATH, 'settings.xml')

if not os.path.exists(_KNECHT_SETTINGS_PATH):
    try:
        os.mkdir(_KNECHT_SETTINGS_PATH)
    except Exception as e:
        print('Error writing settings file' + e)


class knechtSettings:
    app = dict(
        current_path='',
        render_path='',
        pos_old_path='',
        pos_new_path='',
        log_window=True,
        version='0.0.0',
        app_style='windowsvista',
        introduction_shown=False)

    dg = dict(
        viewer_size='1280 720',
        viewer_freeze=True,
        viewer_apply_bgr=False,
        viewer_bgr_color='',
        send_reset=True,
        check_variant=True,
        tree_state_check=False,
        convert_to_png=True,
        render_timeout=False,
        create_render_preset_dir=False)

    recent_files_set = set()

    @staticmethod
    def add_recent_file(setting_type, file, max_size=9):
        file = str(file)
        rem_entry = False

        # Remove previous existing entry
        for item in sorted(knechtSettings.recent_files_set):
            ord, setting_type, ex_file = item
            if file == ex_file:
                rem_entry = (ord, setting_type, file)
                break

        if rem_entry:
            knechtSettings.recent_files_set.discard(rem_entry)

        # order = len(settings.recent_files_set) + 1
        knechtSettings.recent_files_set.add(('-1', setting_type, file))

        # Re-order
        temp_set = set()
        for idx, item in enumerate(sorted(knechtSettings.recent_files_set)):
            order, setting_type, file = item
            temp_set.add((str(idx), setting_type, file))
            if idx > max_size: break

        knechtSettings.recent_files_set = temp_set

    @staticmethod
    def save_settings():
        root = Et.Element('renderknecht_app_settings')

        # App specific settings
        app_settings = Et.SubElement(root, 'app_settings')
        for k, v in knechtSettings.app.items():
            app_setting = Et.SubElement(app_settings, 'setting')
            app_setting.set(k, str(v))

        # Delta Gen specific settings
        delta_gen = Et.SubElement(root, 'delta_gen_settings')
        for k, v in knechtSettings.dg.items():
            delta_gen_setting = Et.SubElement(delta_gen, 'setting')
            delta_gen_setting.set(k, str(v))

        # Recent files
        recent_files_tag = Et.SubElement(root, 'recent_files')
        for item in knechtSettings.recent_files_set:
            order, type, file = item
            recent_file = Et.SubElement(recent_files_tag, 'file')
            recent_file.set('order', order)
            recent_file.set('type', type)
            recent_file.set('file', str(file))

        knechtSettings.save_tree(_KNECHT_SETTINGS_FILE, root)

    @staticmethod
    def load_settings():

        def set_settings(set_dict, k, v):
            if k in set_dict.keys():
                set_dict[k] = v
            else:
                return

            # Convert booleans
            if v == 'True':
                set_dict[k] = True
            if v == 'False':
                set_dict[k] = False

            # Make sure path's exists
            if k in ('current_path', 'render_path'):
                if not os.path.exists(v):
                    set_dict[k] = ''

        if not os.path.exists(_KNECHT_SETTINGS_FILE):
            # Create default settings if no settings found
            knechtSettings.save_settings()
        else:
            # Parse settings and update class dictonarys
            try:
                xml_tree = Et.parse(_KNECHT_SETTINGS_FILE)
            except Exception as e:
                print('Error parsing settings file: ' + e)
                return

            # App specific settings
            for node in xml_tree.findall('./app_settings//'):
                for k, v in node.attrib.items():
                    set_settings(knechtSettings.app, k, v)

            # Delta Gen specific settings
            for node in xml_tree.findall('./delta_gen_settings//'):
                for k, v in node.attrib.items():
                    set_settings(knechtSettings.dg, k, v)

            # Load recent files
            for node in xml_tree.findall('./recent_files//'):
                if 'order' in node.attrib.keys():
                    try:
                        order, type, file = node.attrib['order'], node.attrib[
                            'type'], node.attrib['file']
                        if os.path.exists(file):
                            knechtSettings.recent_files_set.add((order, type, file))
                    except Exception as e:
                        print('Error setting recent files ' + e)

    @staticmethod
    def save_tree(file, xml_element):
        """ Pretty print and save Xml to file """
        # BackUp exisiting file
        if os.path.exists(file):
            file_name, ext = os.path.splitext(file)

            bak_file = file_name + '.bak'

            # Remove existing bak file
            if os.path.exists(bak_file):
                try:
                    os.remove(bak_file)
                except Exception as e:
                    print('Error removing settings bak file: ' + e)

            # Rename current settings
            try:
                os.rename(file, bak_file)
            except Exception as e:
                print('Error creating bak file: ' + e)

        # Pretty print for save file
        knechtSettings.pretty_print_xml(xml_element)

        # Replace current ElementTree with pretty printed tree
        pretty_xmlTree = Et.ElementTree(xml_element)

        try:
            with open(file, 'wb') as f:
                pretty_xmlTree.write(f, encoding='UTF-8', xml_declaration=True)
        except Exception as e:
            print('Error writing settings file: ' + e)

    @staticmethod
    def pretty_print_xml(elem, level=0):
        """ Pretty XML print for better human readabilty """
        NEW_LINE = '\n'
        NEW_LEVEL = '\t'
        i = NEW_LINE + level * NEW_LEVEL

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + NEW_LEVEL
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                knechtSettings.pretty_print_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
