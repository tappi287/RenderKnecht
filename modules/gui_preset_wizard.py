"""
py_knecht QUB 9000 preset wizard

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
import re
from pathlib import Path

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QPixmap
from functools import partial

from modules.gui_preset_wizard_page_presets import PresetWizardPage
from modules.gui_preset_wizard_page_fakom import FakomWizardPage
from modules.gui_preset_wizard_page_source import SourceWizardPage

from modules.knecht_log import init_logging
from modules.app_globals import UI_FILE_PRESET_WIZARD, PACKAGE_FILTER
from modules.app_globals import Itemstyle, HELPER_DIR
from modules.tree_overlay import Overlay
from modules.tree_filter_thread import TreeFilterThread, BgrAnimation
from modules.knecht_xml import XML
from modules.gui_widgets import load_ui_file
from modules.app_strings import QobMsg

LOGGER = init_logging(__name__)


class PresetWizard(QtWidgets.QWizard):
    """
        QOB 9000 - Preset Wizard
    """
    source_changed = QtCore.pyqtSignal()
    lock_fakom_tree = QtCore.pyqtSignal()
    load_fakom_tree = QtCore.pyqtSignal()
    load_preset_page = QtCore.pyqtSignal()
    save_empty = QtCore.pyqtSignal()
    save_error = QtCore.pyqtSignal()

    session_saved = QtCore.pyqtSignal()
    asked_dave_already = False

    max_preset_num = 99

    def __init__(self, parent, app):
        super(PresetWizard, self).__init__(parent)
        # Prepare ui elements
        self.ui, self.app = parent, app
        self.load_ui()

        # Prepare Xml reader / writer
        # Will be set up from Source Page
        self.src_widget = None
        self.fakom_xml, self.vplus_xml = None, None
        self.last_session_file = Path(HELPER_DIR / '_Image_Preset_Wizard_Session.xml')
        # Load session Xml elements
        self.fakom_tree_items = None
        self.preset_page_content = None

        # Prepare property data storage
        self.__fakom_presets = None
        self.__used_pr_options = set()
        self.__preset_pages_ids = set()
        self.__pkg_text_filter = PACKAGE_FILTER

        # Items marked to exclude by the user
        self.context_excluded_pr_families = set()

        # Overlay
        self.overlay = Overlay(self)

        # Prepare filter thread
        self.tree_filter_thread = TreeFilterThread()
        self.tree_filter_thread.create_thread()

        # Navigation Menu, hidden by default
        self.nav_menu = NavigationMenu(self)
        self.nav_button = QtWidgets.QPushButton('Navigation', self)
        self.nav_button.setMenu(self.nav_menu)
        self.setButton(QtWidgets.QWizard.CustomButton1, self.nav_button)

        # Prepare load save helper class
        self.session_data_mgr = LoadSaveWizardSession(self)

        # Page 1
        self.src_page = None
        self.setup_source_page()
        self.setup_fakom_page()
        self.setup_preset_page()

        self.currentIdChanged.connect(self.page_id_changed)

    @property
    def fakom_presets(self):
        return self.__fakom_presets

    @fakom_presets.setter
    def fakom_presets(self, val=list()):
        if val:
            self.__fakom_presets = val[:self.max_preset_num]

            if len(val) > self.max_preset_num:
                LOGGER.error(f'Maximum number of Wizard presets exceeded! '
                             f'Up to {self.max_preset_num} Presets supported.')

    @fakom_presets.deleter
    def fakom_presets(self):
        self.__fakom_presets = list()

    @property
    def pkg_text_filter(self):
        return self.__pkg_text_filter

    @pkg_text_filter.setter
    def pkg_text_filter(self, val: list=list()):
        self.__pkg_text_filter = val

    @property
    def used_pr_options(self):
        return self.__used_pr_options

    @used_pr_options.setter
    def used_pr_options(self, val: str):
        """ Update used PR options, "~ABC" deletes set member ABC """
        if val.startswith('~'):
            val = val[1:]
            self.__used_pr_options.discard(val)
        else:
            self.__used_pr_options.add(val)

        self.__used_pr_options.discard('')

    @used_pr_options.deleter
    def used_pr_options(self):
        self.__used_pr_options = set()

    @property
    def preset_pages_ids(self):
        return self.__preset_pages_ids

    @preset_pages_ids.setter
    def preset_pages_ids(self, val: int=0):
        self.__preset_pages_ids.add(val)

    @preset_pages_ids.deleter
    def preset_pages_ids(self):
        self.__preset_pages_ids = set()

    @staticmethod
    def get_elem_attribute(elem, attribute_name: str=''):
        if elem is not None:
            if attribute_name in elem.attrib.keys():
                return elem.attrib[attribute_name]

        return ''

    def load_ui(self):
        load_ui_file(self, UI_FILE_PRESET_WIZARD)

        # Banner pixmap
        # banner = QPixmap(Itemstyle.ICON_PATH['banner'])
        # banner = banner.scaled(1600, 196, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
        # self.setPixmap(QtWidgets.QWizard.BannerPixmap, banner)

        # Set logo pixmap
        logo = QPixmap(Itemstyle.ICON_PATH['qob_icon_sw'])
        logo = logo.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, logo)

        # Button labels
        self.setButtonText(QtWidgets.QWizard.NextButton, QobMsg.next_label)
        self.setButtonText(QtWidgets.QWizard.BackButton, QobMsg.back_label)
        self.setButtonText(QtWidgets.QWizard.FinishButton, QobMsg.finish_label)
        self.setButtonText(QtWidgets.QWizard.CancelButton, QobMsg.cancel_label)

    def page_id_changed(self, page_id):
        self.nav_menu.create_nav_menu_items(page_id)

    def setup_xml_read_write(self, tree_widget):
        self.src_widget = tree_widget

        # Prepare Xml storage of tree elements
        self.fakom_xml = XML('', self.src_widget)
        self.vplus_xml = XML('', self.src_widget)

    def setup_source_page(self):
        """ Wizard Page 1 """
        self.src_page = SourceWizardPage(self)
        self.addPage(self.src_page)

    def setup_fakom_page(self):
        """ Wizard Page 2 """
        fakom_page = FakomWizardPage(self)

        self.source_changed.connect(fakom_page.set_clear_fakom_tree)
        self.session_saved.connect(fakom_page.display_session_saved)
        self.lock_fakom_tree.connect(fakom_page.warn_fakom_changes)
        self.load_fakom_tree.connect(fakom_page.set_load_session_selection)
        self.load_preset_page.connect(fakom_page.set_load_preset_page_content)

        self.addPage(fakom_page)

    def setup_preset_page(self):
        """ Wizard Preset Pages """
        preset_page = PresetWizardPage(self, 0)
        self.addPage(preset_page)

    def iterate_fakom_xml(self, find_type: str= 'fakom'):
        for __node in self.fakom_xml.root.iterfind('./*/preset'):
            __type = self.get_elem_attribute(__node, 'type')

            if __type.startswith(find_type):
                yield __node

    def add_preset_contents_to_used_pr(self):
        """
            Adds choosen FaKom and Trimline preset content
            to used_pr_options
        """
        __read = self.get_elem_attribute
        __models = set()
        __references = set()

        # Add FaKom items to used PR options
        for __i in self.fakom_presets:
            __id = __i.text(1)

            for __e in self.fakom_xml.root.iterfind(f'./*/preset[@id="{__id}"]'):
                __models.add(__read(__e, 'value'))

                for __v in __e.iterfind('.//'):
                    __ref = __read(__v, 'reference')

                    if __ref:
                        __references.add(__ref)
                    else:
                        self.used_pr_options = __read(__v, 'name')

        # Add referenced package options
        __references.discard('')
        for __ref_id in __references:
            __ref_element = self.fakom_xml.root.find(f'./*/preset[@id="{__ref_id}"]')

            if __ref_element is not None:
                self.used_pr_options = __read(__ref_element, 'value')

                for __ref_variant in __ref_element.iterfind('.//'):
                    self.used_pr_options = __read(__ref_variant, 'name')

        # Add Trimline PR options to used PR
        for __m in __models:
            __search = f'./*/preset[@value="{__m}"][@type="trim_setup"]//'
            for __v in self.vplus_xml.root.iterfind(__search):
                self.used_pr_options = __read(__v, 'name')

        # Add text filtered packages to used PR
        __search = f'./*/preset[@type="package"]'
        __log_pkg = set()
        for __p in self.vplus_xml.root.iterfind(__search):
            __name = __read(__p, 'name')

            for __f in self.pkg_text_filter:
                # Match "abc" in "abc", "abc.", "abc ", but not "4abc", nor "abcde"
                filter_pattern = f'(?<![\w\d]){__f}(?![\w\d])'
                result = re.search(filter_pattern, __name, re.RegexFlag.IGNORECASE)

                if result:
                    # Add package PR
                    __pkg_pr = __read(__p, 'value')
                    self.used_pr_options = __pkg_pr
                    __log_pkg.add(__pkg_pr)
                    break

        LOGGER.debug('Text filtered Packages: %s', __log_pkg)

    def navigate_to_page(self, nav_id):
        LOGGER.debug('Navigation to page id %s requested.', nav_id)
        max_nav_range, __n = 300, 0

        while nav_id != self.currentId():
            __n += 1
            if nav_id < self.currentId():
                self.back()
            elif nav_id > self.currentId():
                self.next()

            if __n >= max_nav_range:
                LOGGER.error('Maximum navigation range exceeded.')
                break

    def ask_dave(self):
        if self.ui.question_box(title_txt=QobMsg.reject_title,
                                message=QobMsg.reject_msg,
                                parent=self):
            return True
        return False

    def reject(self):
        if self.ask_dave():
            return

        self.setResult(QtWidgets.QDialog.Rejected)
        self.asked_dave_already = True
        self.close()

    def closeEvent(self, close_event):
        if not self.asked_dave_already:
            if self.ask_dave():
                close_event.ignore()
                return

        self.tree_filter_thread.end_thread()
        close_event.accept()

    class TxtFiltering:

        def __init__(self, filter_thread, tree_widget, **kwargs):
            # super(TxtFiltering, self).__init__()
            self.filter_thread = filter_thread
            self.tree_widget = tree_widget
            self.column, self.pattern = 0, 2

            self.typing_timer = QtCore.QTimer()
            self.typing_timer.setSingleShot(True)
            self.typing_timer.setInterval(500)
            self.typing_timer.timeout.connect(self.filter_start)

            self.bgr_anim = BgrAnimation(tree_widget.filter_txt_widget, (255, 255, 255))

            if 'column' in kwargs.keys():
                self.column = kwargs['column']

            if 'pattern' in kwargs.keys():
                self.pattern = kwargs['pattern']

        def filter_txt(self):
            self.typing_timer.start()

        def filter_start(self):
            txt = self.tree_widget.filter_txt_widget.text()

            self.filter_thread.filter_items(self.column, txt, self.tree_widget, pattern=self.pattern)

            if txt:
                self.bgr_anim.active_pulsate(4)
            else:
                self.bgr_anim.blink()


class NavigationMenu(QtWidgets.QMenu):
    def __init__(self, parent):
        super(NavigationMenu, self).__init__(parent)
        self.parent, self.ui = parent, parent.ui

    def create_nav_menu_items(self, current_id):
        self.clear()

        for __a in sorted(self.parent.preset_pages_ids):
            __page = self.parent.page(__a)
            __pr, __pkg = __page.pr_count, __page.pkg_count
            __title = f'{__page.title()[:45]} \t {__pr:02d} Optionen / {__pkg:02d} Pakete'

            nav_item = QtWidgets.QAction(__title, self)
            nav_item.triggered.connect(partial(self.parent.navigate_to_page, __a))
            nav_item.setIcon(self.ui.icon[Itemstyle.TYPES['preset_ref']])

            if __a == current_id:
                nav_item.setText(f'#{__page.idx:03d} - {QobMsg.nav_item_current}')
                nav_item.setEnabled(False)

            self.addAction(nav_item)


class LoadSaveWizardSession:
    # XML DOM / hierarchy tags
    session_xml_dom = {
        'root': 'qob_9000_session',
        'fakom': 'fakom_tree', 'vplus': 'vplus_tree',
        'fakom_presets': 'fakom_presets',
        'pages': 'preset_pages', 'page': 'page', 'page_item': 'preset_item',
        'pkg_filter': 'pkg_text_filter', 'pkg_element': 'p'}

    def __init__(self, parent):
        self.parent = parent

    def create_session_xml(self):
        """
        Prepare saving of the fakom and vplus xml tree's into one xml document.
            :return: XML class
        """
        session_xml = XML('', self.parent.src_widget)
        session_xml.root = self.session_xml_dom['root']

        # root > fakom > renderknecht_varianten
        session_xml.xml_sub_element = session_xml.root, self.session_xml_dom['fakom']
        __fakom_element = session_xml.xml_sub_element
        __fakom_element.append(self.parent.fakom_xml.root)

        # root > vplus > renderknecht_varianten
        session_xml.xml_sub_element = session_xml.root, self.session_xml_dom['vplus']
        __vplus_element = session_xml.xml_sub_element
        __vplus_element.append(self.parent.vplus_xml.root)

        # root > parent.fakom_presets
        if self.parent.fakom_presets:
            session_xml.xml_sub_element = session_xml.root,\
                                          self.session_xml_dom['fakom_presets']
            __fakom_presets = session_xml.xml_sub_element
            self.create_fakom_preset_elements(__fakom_presets)

        # root > preset_pages
        if self.parent.preset_pages_ids:
            session_xml.xml_sub_element = session_xml.root, self.session_xml_dom['pages']
            __preset_pages = session_xml.xml_sub_element
            self.create_preset_pages_elements(__preset_pages)

        self.describe_origin(session_xml)
        __settings = session_xml.root.find(f'./{session_xml.dom_tags["settings"]}')

        # root > renderknecht_settings
        session_xml.xml_sub_element = __settings, self.session_xml_dom['pkg_filter']
        __pkg_filter = session_xml.xml_sub_element
        self.create_pkg_filter_elements(__pkg_filter)

        return session_xml

    def user_save(self):
        save_file, file_type = QtWidgets.QFileDialog.getSaveFileName(
            parent=self.parent, caption=QobMsg.save_dlg_title,
            directory=self.parent.ui.current_path, filter=QobMsg.save_dlg_filter)

        if not save_file:
            return False

        save_file = Path(save_file)

        if self.save_session(save_file):
            return save_file

        return False

    def save_session(self, file: Path=None):
        if self.parent.fakom_xml.root is None and self.parent.vplus_xml.root is None:
            self.parent.save_empty.emit()
            return False

        if not file:
            file = self.parent.last_session_file

        __session_xml = self.create_session_xml()

        try:
            __session_xml.save_tree(file)
        except Exception as e:
            LOGGER.error('Error saving wizard session\n%s', e)
            self.parent.save_error.emit()
            return False

        self.parent.overlay.save_anim()

        self.parent.session_saved.emit()
        LOGGER.info('Wizard Session saved: %s', file)
        return True

    def session_available(self):
        if self.parent.last_session_file.exists():
            return True
        else:
            return False

    def load_session(self, file: Path=None):
        self.parent.src_widget.clear()

        if not file:
            file = self.parent.last_session_file

        if not file.exists():
            LOGGER.error('Can not load non exsisting file: %s', file.name)
            return False

        # Load session Xml file and divide it back to fakom and vplus xml
        __fakom_xml_tree, __vplus_xml_tree, __fakom_presets, __preset_pages = self.parse_session_xml(file)

        if __fakom_xml_tree is None or __vplus_xml_tree is None:
            LOGGER.error('Unknown error loading wizard session. Parser returned empty values.')
            return False

        try:
            self.parent.fakom_xml._overwrite_root(__fakom_xml_tree)
            self.parent.vplus_xml._overwrite_root(__vplus_xml_tree)

            if __fakom_presets is not None:
                LOGGER.debug('Fakom Preset items: %s', len(__fakom_presets))
                self.parent.fakom_tree_items = __fakom_presets
                self.parent.load_fakom_tree.emit()

            if __preset_pages is not None:
                LOGGER.debug('Preset Page content: %s', len(__preset_pages))
                self.parent.preset_page_content = __preset_pages
                self.parent.load_preset_page.emit()

            LOGGER.debug('Wizard session loaded.')
        except Exception as e:
            LOGGER.error('Error loading wizard session:\n%s', e)
            return False

        return True

    def parse_session_xml(self, file):
        """
        Parse session Xml file and split back into fakom and vplus Xml Elements
            :param file: Path or String to Session Xml file
            :return: Fakom Xml Element, Vplus Xml Element
        """
        __xml = XML('', self.parent.src_widget)

        try:
            __session_xml_tree = __xml.parse_xml_file(file)
        except Exception as e:
            LOGGER.error('%s', e)
            return None, None, None, None

        __fakom_xml_tree = __session_xml_tree.find(f'./{self.session_xml_dom["fakom"]}/')

        __vplus_xml_tree = __session_xml_tree.find(f'./{self.session_xml_dom["vplus"]}/')

        __fakom_presets = __session_xml_tree.find(f'./{self.session_xml_dom["fakom_presets"]}')

        __preset_pages = __session_xml_tree.find(f'./{self.session_xml_dom["pages"]}')

        __settings = __session_xml_tree.find(f'./{__xml.dom_tags["settings"]}')

        __pkg_filter = None

        if __settings is not None:
            __pkg_filter = __settings.find(f'./{self.session_xml_dom["pkg_filter"]}')

        if __pkg_filter is not None:
            self.load_pkg_filter_elements(__pkg_filter)

        if __fakom_xml_tree is not None and __vplus_xml_tree is not None:
            return __fakom_xml_tree, __vplus_xml_tree, __fakom_presets, __preset_pages
        else:
            return None, None, None, None

    def load_pkg_filter_elements(self, pkg_elem):
        __filter_list = list()

        __filter_enabled = eval(pkg_elem.get('enabled', default='True'))
        self.parent.src_page.checkBoxCountryPkg.setChecked(__filter_enabled)

        for __p in pkg_elem.iterfind('.//'):
            __p = __p.text
            if __p:
                __filter_list.append(__p)

        self.parent.pkg_text_filter = __filter_list

    def create_pkg_filter_elements(self, pkg_elem):
        __xml = XML('', None)

        __filter_enabled = self.parent.src_page.checkBoxCountryPkg.isChecked()
        pkg_elem.set('enabled', str(__filter_enabled))

        for __f in self.parent.pkg_text_filter:
            if __f:
                __xml.xml_element = self.session_xml_dom['pkg_element']
                __e = __xml.xml_element
                __e.text = __f
                pkg_elem.append(__e)

    def describe_origin(self, xml):
        __origin = xml.root.find(f'./{xml.dom_tags["origin"]}')

        __o_txt = 'RenderKnecht-Preset-Wizard_' + time.strftime('%Y-%m-%d_%H:%M:%S')
        __origin.text = __o_txt

        __source = str(self.parent.vplus_xml.variants_xml_path)
        __origin.set('sourcedoc', __source)

    def create_fakom_preset_elements(self, presets_xml):
        __xml = XML('', None)
        __keys = ['name', 'id', 'model', 'type']

        for __i in self.parent.fakom_presets:
            __attrib = dict()
            for __a in range(0, 4):
                __attrib[__keys[__a]] = __i.text(__a)

            __xml.xml_element = 'preset', __attrib
            presets_xml.append(__xml.xml_element)

    def create_preset_pages_elements(self, pages_xml):
        __xml = XML('', None)

        for page_id in self.parent.preset_pages_ids:
            page = self.parent.page(page_id)

            if not page.id:
                # Page has not been initialized
                break

            __attrib = dict(id=str(page.id), idx=str(page.idx))
            __xml.xml_element = self.session_xml_dom['page'], __attrib
            __page_xml = __xml.xml_element

            # Iterate options
            for __i in page.treeWidget_Preset.findItems('*', QtCore.Qt.MatchWildcard):
                if __i.flags() & QtCore.Qt.ItemIsEnabled:
                    __name, __id, __type = __i.text(0), __i.text(1), __i.text(2)

                    if __type != 'package':
                        # PR Option
                        __attrib = dict(name=__name, type=__type)
                    else:
                        # Package
                        __attrib = dict(name=__name, id=__id, type=__type)

                    __xml.xml_sub_element = __page_xml, self.session_xml_dom['page_item'], __attrib

            pages_xml.append(__page_xml)
