from pathlib import Path
from lxml import etree
from datetime import datetime

from PyQt5 import QtWidgets

from modules.app_strings import Msg
from modules.knecht_xml import XML
from modules.knecht_log import init_logging
from modules.pos_schnuffi_xml_diff import PosXml

LOGGER = init_logging(__name__)


class ExportActionList(object):
    xml_dom = {'root': 'stateMachine', 'sub_lvl_1': 'stateEngine'}
    err_msg = Msg.POS_ERR_MSG_LS

    def __init__(self, pos_app, pos_ui):
        """ Export selected items as Xml ActionList """
        self.pos_app, self.pos_ui = pos_app, pos_ui
        self.err = self.pos_app.err_sig

    def export(self):
        widget = self.get_widget()
        if not widget:
            self.err.emit(self.err_msg[0])
            return None, None, None

        # Collect QTreeWidgetItems
        items = widget.selectedItems()
        if not items:
            self.err.emit(self.err_msg[1])
            return None, None, None

        # Set export file
        file = self.set_file()
        if not file:
            self.err.emit(self.err_msg[2])
            return None, None, None
        file = Path(file)
        LOGGER.debug('POS Schnuffi Export file set to %s', file.as_posix())

        action_list_names = self.collect_action_lists(items)
        LOGGER.debug('Found %s actionLists to export.', len(action_list_names))

        return action_list_names, file, widget

    def export_selection(self):
        """ Export the selected widget action list items as custom user Xml """
        action_list_names, file, widget = self.export()
        if not file or not action_list_names:
            return

        if not self.export_custom_xml(action_list_names, file):
            # break on error
            return

        self.pos_app.export_sig.emit()

    def export_updated_pos_xml(self):
        """
        Export an updated version of the old POS Xml:
            - updating selected action lists from new POS Xml, if in "changed" widget
            - adding selected action lists from new POS Xml, if in "NewXml_actionList" widget
        """
        action_list_names, file, widget = self.export()
        if not file or not action_list_names:
            return

        if widget is self.pos_ui.ModifiedWidget:
            if not self.update_old_pos_xml_with_changed_action_lists(action_list_names, file):
                return
        elif widget is self.pos_ui.actionListWidget:
            if not self.update_old_pos_xml_with_new_action_lists(action_list_names, file):
                return
        else:
            return

        self.pos_app.export_sig.emit()

    def update_old_pos_xml_with_new_action_lists(self, action_list_names, out_file):
        """
        Export an updated version of the old POS Xml, adding selected action lists
        from new POS Xml, if in "NewXml_actionList" widget
        """
        # Read old and new POS Xml and return as PosXml class objects
        pos_xml, new_xml = self.get_pos_xmls()

        if not pos_xml or not new_xml:
            return False

    def update_old_pos_xml_with_changed_action_lists(self, action_list_names, out_file):
        """
        Export an updated version of the old POS Xml, updating selected action lists with the
        content from the new POS Xml.
        """
        # Read old and new POS Xml and return as PosXml class objects
        pos_xml, new_xml = self.get_pos_xmls()
        if not pos_xml or not new_xml:
            return False

        # Prepare storage of updated POS Xml
        updated_xml = self.prepare_updated_pos_xml_export(pos_xml.xml_tree, out_file)
        updated_elements = set()

        for al_name in action_list_names:
            parent = updated_xml.xml_tree.find(f'*actionList[@name="{al_name}"]/..')
            old_action_list_elem = updated_xml.xml_tree.find(f'*actionList[@name="{al_name}"]')
            new_action_list_elem = new_xml.xml_tree.find(f'*actionList[@name="{al_name}"]')

            if parent is None or old_action_list_elem is None or new_action_list_elem is None:
                # Skip elements not present in both POS Xml's
                continue

            updated_elements.add(al_name)

            # Replace old action list
            al_index = parent.index(old_action_list_elem)
            parent.remove(old_action_list_elem)
            parent.insert(al_index, new_action_list_elem)

        if not updated_elements:
            # No elements to update found
            # ActionList needs to be available in old and new document
            # adding ActionList is not supported yet
            self.err.emit(self.err_msg[4])
            return False

        # Add info comment
        self.add_export_info_comment(updated_xml.root, updated_elements,
                                     self.pos_app.file_win.old_file_dlg.path,
                                     self.pos_app.file_win.new_file_dlg.path)

        # Try to write the POS mess as a file, this will fail with xml.etree
        LOGGER.info('Exporting POS Xml with the following action lists replaced:\n%s', updated_elements)
        try:
            updated_xml.save_tree()
            self.err.emit(Msg.POS_EXPORT_MSG.format(updated_xml.variants_xml_path.as_posix()))
        except Exception as e:
            self.err.emit(self.err_msg[5])
            LOGGER.error('POS Xml is malformed and could not be written/serialized.\n%s', e)
            return False

        return True

    def export_custom_xml(self, action_list_names: set, out_file):
        pos_xml, _ = self.get_pos_xmls()
        if not pos_xml:
            self.err.emit(self.err_msg[3])
            return False

        # Prepare export Xml
        xml, xml_elem = self.prepare_custom_xml_export(out_file)

        # Iterate Action Lists and collect matching xml elements
        for e in pos_xml.xml_tree.iterfind('*actionList'):
            name = e.get('name')

            if name in action_list_names:
                xml_elem.append(e)
        try:
            xml.save_tree()
            self.err.emit(Msg.POS_EXPORT_MSG.format(xml.variants_xml_path.as_posix()))
        except Exception as e:
            self.err.emit(self.err_msg[4])
            LOGGER.error('POS Xml is malformed and could not be written/serialized.\n%s', e)
            return False

        return True

    def prepare_custom_xml_export(self, xml_path):
        session_xml = XML(xml_path, None, no_knecht_tags=True)
        session_xml.root = self.xml_dom['root']

        session_xml.xml_sub_element = session_xml.root, self.xml_dom['sub_lvl_1']
        xml_elem = session_xml.xml_sub_element
        xml_elem.set('autoType', 'variant')
        return session_xml, xml_elem

    @staticmethod
    def prepare_updated_pos_xml_export(pos_xml_tree, updated_xml_path):
        """ Parse POS Xml tree to knecht_xml Xml tree """
        session_xml = XML(updated_xml_path, None, no_knecht_tags=True)
        session_xml.xml_tree = pos_xml_tree
        session_xml.root = session_xml.xml_tree.getroot()

        return session_xml

    def get_widget(self):
        return self.pos_ui.widget_with_focus()

    def set_file(self):
        """ open a file dialog and return the file name """
        file, file_type = QtWidgets.QFileDialog.getSaveFileName(
            self.pos_ui,
            Msg.SAVE_DIALOG_TITLE,
            self.pos_app.app.ui.current_path,
            Msg.SAVE_FILTER
            )

        return file

    def get_pos_xmls(self):
        """ Read old and new POS Xml and return as PosXml class objects """
        if self.pos_app.file_win:
            old_pos_xml_file = self.pos_app.file_win.old_file_dlg.path
            new_pos_xml_file = self.pos_app.file_win.new_file_dlg.path
        else:
            return None, None

        # Parse old and new xml file
        pos_xml = self.parse_pos_xml(old_pos_xml_file)
        if not pos_xml:
            self.err.emit(self.err_msg[3])
            return None, None
        new_xml = self.parse_pos_xml(new_pos_xml_file)
        if not new_xml:
            self.err.emit(self.err_msg[3])
            return None, None

        return pos_xml, new_xml

    @staticmethod
    def parse_pos_xml(xml_file_path: Path):
        # Parse to Xml
        if xml_file_path.exists():
            try:
                pos_xml = PosXml(xml_file_path)
                return pos_xml
            except Exception as e:
                LOGGER.debug('Error parsing POS Xml: %s', e)
                return
        else:
            return

    @staticmethod
    def collect_action_lists(items):
        """ Collect actionList names from QTreeWidgetItems """
        action_list_names = set()
        for i in items:
            if i.parent():
                continue  # Skip children
            action_list_names.add(i.text(0))

        return action_list_names

    @staticmethod
    def add_export_info_comment(element, updated_items, old_path, new_path):
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item_str = ''

        for item in updated_items:
            item_str += f'{item}, '

        msg_ls = [f' #1 modified with RenderKnecht POS Schnuffi on {current_date} ',
                  f' #2 actionList elements updated: {item_str[:-2]} ',
                  f' #3 updated actionList elements from source document: {Path(new_path).name} ',
                  f' #4 base document: {Path(old_path).name} ']

        for msg in msg_ls:
            element.addprevious(etree.Comment(msg))
