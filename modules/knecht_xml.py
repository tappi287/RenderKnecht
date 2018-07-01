"""
knecht_xml for py_knecht. Saves and loads XML with RenderKnecht Presets

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
import shutil
import lxml.etree as Et
from pathlib import Path

from PyQt5.QtWidgets import QTreeWidgetItem

from modules.app_globals import Msg, ItemColumn
from modules.knecht_log import init_logging
from modules.tree_methods import iterate_tree_widget_items_flat, lead_zeros

# Initialize logging for this module
LOGGER = init_logging(__name__)


class XML:
    """
    Reads Xml file and stores it inside ElementTree. Returns True or False on successful load / parse
    Pre-configured order:
    ['order', 'name', 'value', 'type', 'reference', 'id']

        QTreeWidgetItem.UserType

        * 1000 - preset
        * 1001 - variant
        * 1002 - reference
        * 1003 - render_preset
        * 1004 - render_setting
        * 1005 - seperator
    """
    # Xml tag as QTreeWidgetItem user type
    xmlTagDict = {
        'preset': 1000, 'variant': 1001, 'reference': 1002, 'render_preset': 1003,
        'render_setting': 1004, 'seperator': 1005, 'sub_seperator': 1006}

    xmlTypeDict = dict()
    for k, v in xmlTagDict.items():
        xmlTypeDict[v] = k

    DEFAULT_TREE_WIDGET_TYPE = 0  # QTreeWidgetItem::Type != UserType

    # XML DOM / hierarchy tags
    dom_tags = {
        'root': 'renderknecht_varianten', 'sub_lvl_1': 'variant_presets', 'sub_lvl_2': 'preset',
        'settings': 'renderknecht_settings', 'origin': 'origin'}

    def __init__(self, variants_xml_path, widget, no_knecht_tags: bool=False):
        """
        :param variants_xml_path: path to non-existing xml file
        :type variants_xml_path: Path or str
        :param widget: treeWidget to read from and parse xml to
        :type widget: QTreeWidget
        """
        self.no_knecht_tags = no_knecht_tags
        # Unique id per Tree
        self.id = 0

        # Xml File for this instance
        self.variants_xml_path = variants_xml_path

        # Tree widget belonging to this XML instance
        self.widget = widget

        # Prepare private class data handling attributes
        self.__preset_item = None
        self.__current_preset = None
        self.__variant_presets = None
        self.__orphan_preset = None
        self.__p_count = None

        # Prepare private attributes
        self.__root = None
        self.__xml_tree = None
        self.__xml_element = None
        self.__xml_sub_element = None

    @property
    def root(self):
        return self.__root

    @root.setter
    def root(self, val='root'):
        if type(val) is str:
            self.__root = Et.Element(val)
        elif type(val) is Et._ElementTree:
            self.__root = val.getroot()
        elif type(val) is Et._Element:
            self.__root = val

        if not self.no_knecht_tags:
            Et.SubElement(self.__root, self.dom_tags['origin'])
            Et.SubElement(self.__root, self.dom_tags['settings'])

    @property
    def xml_tree(self):
        return self.__xml_tree

    @xml_tree.setter
    def xml_tree(self, val):
        if type(val) is Et._Element:
            self.__xml_tree = Et.ElementTree(val)
        elif type(val) is Et._ElementTree:
            self.__xml_tree = val
        else:
            self.__xml_tree = self.parse_xml_file(val)

    @property
    def xml_element(self):
        return self.__xml_element

    @xml_element.setter
    def xml_element(self, *args):
        if not len(args):
            return

        if type(args[0]) is tuple:
            args = args[0]

        self.__xml_element = Et.Element(*args)

    @property
    def xml_sub_element(self):
        """
            :return: xml.etree.ElementTree.SubElement
        """
        return self.__xml_sub_element

    @xml_sub_element.setter
    def xml_sub_element(self, *args):
        """
        External use of Et.SubElement at least two arguments (parent, tag) required.
            :param val: parent, tag, attrib=dict()
            :return: xml.etree.ElementTree.SubElement
        """
        if not len(args):
            # 1 argument
            return

        if type(args[0]) is tuple:
            args = args[0]

        self.__xml_sub_element = Et.SubElement(*args)

    @staticmethod
    def parse_xml_file(file):
        return Et.parse(Path(file).as_posix())

    def _overwrite_root(self, val):
        """ only used to directly set root element if parsing from a treeWidget is not useful """
        self.__root = val

    def parse_element_to_tree_widget(self, et_element: Et.Element):
        """ Parse ElementTree to instance treeWidget
                :return: True on successful transfer to treeWidget
        """
        self.xml_tree = et_element
        LOGGER.debug('Parsing element to tree: %s', et_element.tag)
        return self.parse_xml_to_treewidget(xml_tree_exists=True)

    def parse_file(self, file):
        """ New file for this instance, parse it """
        # BackUp old file
        old_file = self.variants_xml_path

        # Set new file
        self.variants_xml_path = file

        # Parse it
        if self.parse_xml_to_treewidget():
            return True
        else:
            # Parse failed, restore old file
            self.variants_xml_path = old_file
            # Re-parse old file
            LOGGER.error('Restoring previous file: %s', old_file)
            self.parse_xml_to_treewidget()
            return False

    def parse_xml_as_element_tree(self):
        """ Parse Xml """
        try:
            self.xml_tree = self.variants_xml_path
            return True
        except Exception as e:
            LOGGER.error('Parsing this Xml document failed: %s\n%s', self.variants_xml_path, e)
            return False

    def parse_xml_to_treewidget(self, xml_tree_exists: bool=False):
        # Parse file and create self.xmlTree
        if not xml_tree_exists:
            if not self.parse_xml_as_element_tree():
                return

        current_element = self.xml_tree.find('.')
        if current_element.tag != self.dom_tags['root']:
            LOGGER.error('Can not load Xml document. Expected xml root tag: %s, received: %s',
                         self.dom_tags['root'], current_element.tag)
            return False

        # Iterate thru Xml with map instead of for loop, slightly faster
        # calls read_node on every iterable of xml
        try:
            # Clear
            self.__preset_item = None

            # Create Tree elements
            # xmlTree_iterator = self.xmlTree.iterfind('./' + self.dom_tags['sub_lvl_1'] + '//')
            xml_tree_iterator = self.xml_tree.iterfind('./*//')
            list(map(self.read_node, xml_tree_iterator))

            # Successfully parsed
            return True
        except Exception as e:
            LOGGER.error('Error parsing Xml:\n%s', e)
            return False

    def read_node(self, node):
        # Re-write order with leading zeros
        if 'order' in node.attrib.keys():
            node.set('order', lead_zeros(node.attrib['order']))

        # Backwards compatible, value stored in tag text
        if node.tag == 'variant' and node.text:
            node.set('value', node.text)

        if node.tag == 'preset':
            # Id counter
            self.id += 1

            # Set Id
            if 'id' not in node.attrib.keys():
                node.set('id', str(self.id))

            # Create preset item: node, parent
            self.__preset_item = self.create_tree_widget_item(node, self.widget)
        elif node.tag == 'render_preset':
            self.__preset_item = self.create_tree_widget_item(node, self.widget)
        elif node.tag == 'seperator':
            self.create_tree_widget_item(node, self.widget)
        elif node.tag == 'sub_seperator':
            self.create_tree_widget_item(node, self.__preset_item)
        elif node.tag == 'render_setting':
            self.create_tree_widget_item(node, self.__preset_item)
        elif node.tag in ['variant', 'reference']:
            if self.__preset_item:
                # Create variant / reference with parent: last preset_item
                self.create_tree_widget_item(node, self.__preset_item)
            else:
                # Parse orphans aswell for session load / variants widget
                self.create_tree_widget_item(node, self.widget)

    @staticmethod
    def create_tree_widget_item(node, parent=None):
        __values = XML.create_values_from_item_attrib(node.attrib)

        # Create tree widget item
        if parent:
            item = QTreeWidgetItem(parent, __values)
        else:
            item = QTreeWidgetItem(__values, XML.DEFAULT_TREE_WIDGET_TYPE)

        item.UserType = XML.xmlTagDict[node.tag]

        return item

    @staticmethod
    def create_values_from_item_attrib(attrib_dict):
        # List of ordered values to be stored in QTreeWidgetItem
        value_list = list()

        # Create ordered value list
        for key in ItemColumn.COLUMN_KEYS:
            if key in attrib_dict.keys():
                # Set column value
                value_list.append(attrib_dict[key])
            else:
                # Empty column
                value_list.append('')

        return value_list

    @staticmethod
    def create_xml_tree_widget_item(values, tag, xml_element_parent=None):
        attrib = dict()

        for value, key in zip(values, ItemColumn.COLUMN_KEYS):
            if value:
                attrib[key] = value

        __e = Et.Element(tag, attrib)

        if xml_element_parent is not None:
            __e = Et.SubElement(xml_element_parent, tag, attrib)

        return __e

    def update_xml_tree_from_widget(self):
        """ Update xmlTree from QTreeWidget items """
        # Create default Elements
        # renderknecht_varianten
        self.root = self.dom_tags['root']
        # variant_presets
        self.__variant_presets = Et.SubElement(self.root, self.dom_tags['sub_lvl_1'])

        has_data = self.read_all_from_widget()

        if has_data:
            # Overwrite current ElementTree
            self.xml_tree = self.root
            return self.xml_tree
        else:
            # No presets found
            return False

    def create_orphan_preset(self):
        """
            If orphan elements are found (variants | references not in a preset)
            store them in orphan preset.
        """
        attributes = dict(name=Msg.ORPHAN_PRESET_NAME, type=self.xmlTypeDict[1000], order='000')

        self.__orphan_preset = Et.SubElement(self.__variant_presets, self.xmlTypeDict[1000], attributes)

    def read_all_from_widget(self):
        """ Read all widget items and store in ET.SubElement """
        self.__p_count = 0
        self.__orphan_preset = None

        # Iterate all QTreeWidgetItem's
        list(map(self.read_item, iterate_tree_widget_items_flat(self.widget)))

        # Nothing to save, return False
        if self.__p_count == 0 and not self.__orphan_preset:
            return False
        return True

    def read_item(self, item):

        def read_item_attributes():
            # Attributes storage
            attrib_dict = dict()

            # Read attributes from QTreeWidgetItem columns
            for column, key in enumerate(ItemColumn.COLUMN_KEYS):
                # Skip empty fields
                if item.text(column):
                    attrib_dict[key] = item.text(column)

            return attrib_dict

        if item.UserType in [1000, 1003, 1005]:
            # Create Preset Element: parent, tag, attributes
            self.__current_preset = Et.SubElement(
                self.__variant_presets,             # Parent Element
                self.xmlTypeDict[item.UserType],    # Tag from UserType
                read_item_attributes(),             # Attributes to store
                )
            self.__p_count += 1
        else:
            # Make sure variant | reference item has a preset parent
            if item.parent():
                # Create Child Element variant or reference
                Et.SubElement(self.__current_preset, self.xmlTypeDict[item.UserType], read_item_attributes())
            else:
                # Save orphan in orphan_preset
                if not self.__orphan_preset:
                    self.create_orphan_preset()

                Et.SubElement(self.__orphan_preset, self.xmlTypeDict[item.UserType], read_item_attributes())

    @staticmethod
    def pretty_print_xml(elem, level=0):
        """ Pretty XML print for better human readabilty """
        new_line = '\n'
        new_level = '\t'
        i = new_line + level * new_level

        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + new_level
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                XML.pretty_print_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def save_tree(self, file=None):
        """ Pretty print and save Xml to file """
        if file:
            self.variants_xml_path = file

        # Replace current ElementTree with pretty printed
        self.xml_tree = self.root

        if os.path.exists(self.variants_xml_path):
            bak_file = str(self.variants_xml_path) + '.bak'
            try:
                shutil.copy(self.variants_xml_path, bak_file)
            except Exception as e:
                LOGGER.exception('Exception while saving Xml bak file.\n%s', e)

        with open(self.variants_xml_path, 'wb') as f:
            self.xml_tree.write(f, encoding='UTF-8', xml_declaration=True, pretty_print=True)

    def save_tree_as_string(self, xml_element, file=None):
        """ Save an malformed Xml Tree as string data which can not be serialized """
        if file:
            self.variants_xml_path = file

        if type(xml_element) is Et.ElementTree:
            xml_element = xml_element.getroot()

        self.pretty_print_xml(xml_element)

        # Convert Element to string
        xml_str = Et.tostring(xml_element, encoding='UTF-8').decode(encoding='utf-8')

        with open(self.variants_xml_path, 'w') as f:
            f.write(xml_str)
