"""
py_knecht QUB 9000 preset wizard result

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

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap

from modules.app_globals import Itemstyle, WIZARD_PAGE_RESULT
from modules.app_strings import QobMsg
from modules.gui_widgets import load_ui_file
from modules.knecht_log import init_logging
from modules.knecht_xml import XML
from modules.tree_methods import deep_copy_items, generate_number_outside_set, style_database_preset
from modules.tree_overlay import InfoOverlay

LOGGER = init_logging(__name__)


class ResultWizardPage(QtWidgets.QWizardPage):
    """
        --- Preset Wizard Result Page ---
        Populate FaKom Tree and let the user select the items he wants.
    """
    complete_timer = QtCore.QTimer()
    complete_timer.setSingleShot(True)
    complete_timer.setInterval(1000)

    preset_order = ['fakom_setup', 'fakom_option', 'trim_setup', 'options', 'package', 'preset']

    def __init__(self, parent):
        super(ResultWizardPage, self).__init__(parent)
        self.parent = parent
        self.used_ids = set()

        self.load_ui()
        self.tree_xml = None
        self.xml = XML('', self.treeWidget_Result)

        self.vplus = self.parent.vplus_xml.root
        self.fakom = self.parent.fakom_xml.root

        self.complete_timer.timeout.connect(self.delay_complete)

        # Property storage
        self.__item_id = 0
        self.__item_id_pool = set()

    @property
    def item_id_pool(self):
        return self.__item_id_pool

    @property
    def item_id(self):
        self.__item_id += 1

        if self.__item_id in self.__item_id_pool:
            a = 0

            for a in generate_number_outside_set(self.__item_id_pool, start_val=self.__item_id):
                if a:
                    break

            self.__item_id = a

        self.__item_id_pool.add(self.__item_id)

        return str(self.__item_id)

    @item_id.setter
    def item_id(self, val):
        if type(val) is set:
            for __v in val:
                self.__item_id_pool.add(int(__v))
        elif val.isdigit():
            self.__item_id_pool.add(int(val))

    def load_ui(self):
        load_ui_file(self, WIZARD_PAGE_RESULT)

        # Set logo pixmap
        logo = QPixmap(Itemstyle.ICON_PATH['qob_icon_sw'])
        logo = logo.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, logo)

        self.setTitle(QobMsg.result_title)
        self.setSubTitle(QobMsg.result_sub)
        self.treeWidget_Result.info_overlay = InfoOverlay(self.treeWidget_Result)

        self.saveBtn.pressed.connect(self.save_session_user)
        self.parent.save_empty.connect(self.save_empty)
        self.parent.save_error.connect(self.save_error)

    def initializePage(self):
        self.complete_timer.start()
        self.create_unused_options()

    def validatePage(self):
        try:
            self.create_reference_presets()
        except Exception as e:
            LOGGER.error('%s', e)
            self.treeWidget_Result.info_overlay.display_confirm(QobMsg.ref_preset_creation_error.format(e),
                                                                ('[X]', None), immediate=True)
            return False

        return True

    def isComplete(self):
        if self.complete_timer.isActive():
            return False

        return True

    def delay_complete(self):
        self.completeChanged.emit()

    def save_session_user(self):
        result = self.parent.session_data_mgr.user_save()

        if result:
            self.treeWidget_Result.info_overlay.display(QobMsg.user_saved_message.format(result), 6000)

    def save_empty(self):
        self.treeWidget_Result.info_overlay.display_confirm(QobMsg.user_save_empty, ('[X]', None), immediate=True)

    def save_error(self):
        self.treeWidget_Result.info_overlay.display_confirm(QobMsg.user_save_error, ('[X]', None), immediate=True)

    def iterate_preset_pages(self):
        for __page_id in self.parent.preset_pages_ids:
            yield self.parent.page(__page_id)

    @staticmethod
    def get_preset_options(pg):
        return pg.treeWidget_Opt.findItems('*', QtCore.Qt.MatchWildcard)

    @staticmethod
    def get_presets_pkgs(pg):
        return pg.treeWidget_Pkg.findItems('*', QtCore.Qt.MatchWildcard)

    @staticmethod
    def get_preset_content(pg):
        return pg.treeWidget_Preset.findItems('*', QtCore.Qt.MatchWildcard)

    @staticmethod
    def get_preset_content_ids(page):
        __t_id, __pkg_ids = str(), set()

        for __i in ResultWizardPage.get_preset_content(page):
            __id = __i.text(2)
            __t = __i.text(3)

            if 'trim_' in __t:
                __t_id = __id

            if 'package' in __t:
                __pkg_ids.add(__id)

        return __t_id, __pkg_ids

    @staticmethod
    def prepare_preset_xml(xml):
        """ Prepare renderknecht_variants Xml structure """
        xml.root = xml.dom_tags['root']
        __preset_xml = xml.root
        xml.xml_sub_element = __preset_xml, xml.dom_tags['sub_lvl_1']
        __variants = xml.xml_sub_element

        return __preset_xml, __variants

    def update_element_id(self, element, variants):
        __current_id = element.get('id')

        if int(__current_id) not in self.item_id_pool:
            self.item_id = __current_id
            return

        __new_id = self.item_id

        element.set('id', __new_id)

        # Update references to new id
        __search = f'./*/reference[@reference="{__current_id}"][@name="{element.get("name")}"]'
        for __ref in variants.iterfind(__search):
            __ref.set('reference', f'{__new_id}')

        LOGGER.debug('Updated %s, Old_ID: %s New_ID: %s', element.get('name'), __current_id, __new_id)

        return element

    def create_unused_options(self):
        # Prepare unused options Xml -> Tree
        self.xml.root = self.xml.dom_tags['root']
        self.xml.xml_sub_element = self.xml.root, self.xml.dom_tags['sub_lvl_1']
        self.tree_xml = self.xml.root

        __opt_items = dict()

        for page in self.iterate_preset_pages():
            __idx = page.idx
            __current_model = self.parent.fakom_presets[__idx].text(2)
            __current_model_name = page.preset_name['complete_model_name']

            if __current_model not in __opt_items.keys():
                __opt_items[__current_model] = dict(opt=set(), pkg=set(), name=__current_model_name)

            # Iterate options
            for __i in self.get_preset_options(page):
                __name = __i.text(0)

                if __name not in self.parent.used_pr_options:
                    __opt_items[__current_model]['opt'].add(__name)

            # Iterate packages
            for __i in self.get_presets_pkgs(page):
                __pkg_pr = __i.text(3)
                __pkg_name = __i.text(0)

                if __pkg_pr not in self.parent.used_pr_options:
                    __opt_items[__current_model]['pkg'].add(__pkg_name)

        # Populate tree widget
        self.treeWidget_Result.clear()

        for __m in __opt_items.keys():
            __item_name = f'{__opt_items[__m]["name"]} - ' \
                          f'{len(__opt_items[__m]["opt"])} Optionen - {len(__opt_items[__m]["pkg"])} Pakete ' \
                          f'nicht verwendet.'
            __model_item = QtWidgets.QTreeWidgetItem(self.treeWidget_Result, [__item_name])
            style_database_preset(__model_item, self.parent.ui, type_txt='trim_setup')

            for __o in __opt_items[__m]['opt']:
                __opt_item = QtWidgets.QTreeWidgetItem(__model_item, [__o])
                style_database_preset(__opt_item, self.parent.ui, type_txt='options')

            for __p in __opt_items[__m]['pkg']:
                __pkg_item = QtWidgets.QTreeWidgetItem(__model_item, [__p])
                style_database_preset(__pkg_item, self.parent.ui, type_txt='package')

        self.treeWidget_Trim.clear()

        for __t in self.parent.fakom_presets:
            if __t.text(3) == 'fakom_setup':
                __new_item = deep_copy_items([__t])[0]
                self.treeWidget_Trim.addTopLevelItem(__new_item)
                style_database_preset(__new_item, self.parent.ui, type_txt='fakom_setup')

    def create_reference_presets(self):
        # Prepare Xml elements
        xml = XML('', self.parent.ui.treeWidget_SrcPreset)
        preset_xml, variants = self.prepare_preset_xml(xml)

        # Collect preset content ID's and PR option names
        trim_ids, pkg_ids, fakom_ids, models = set(), set(), set(), set()

        for page in self.iterate_preset_pages():
            __idx = page.idx

            # Fakom Preset Id
            __f_id = self.parent.fakom_presets[__idx].text(1)
            __model = self.parent.fakom_presets[__idx].text(2)
            __preset_name = page.preset_name['name']

            __attrib = dict(name=__preset_name, value=__model, type='preset')
            xml.xml_sub_element = variants, 'preset', __attrib
            __preset = xml.xml_sub_element

            # Get Preset content
            # Trim Setup ID's, Package ID's, PR Option Names, Model
            __t_id, __p_ids = self.get_preset_content_ids(page)

            LOGGER.debug('__t_id %s, __p_ids %s', __t_id, __p_ids)

            # Update Elements to copy
            trim_ids.add(__t_id)
            fakom_ids.add(__f_id)
            pkg_ids = pkg_ids.union(__p_ids)
            models.add(__model)

            self.create_variants(xml, page, __preset, __model, __t_id, __f_id, pkg_ids)

        self.item_id = pkg_ids.union(trim_ids)
        LOGGER.debug('IDs in use: %s', self.item_id_pool)

        # Add trim setups
        for __t in trim_ids:
            __trim = self.vplus.find(f'./*/preset[@id="{__t}"]')

            variants.append(__trim)
            LOGGER.debug('Trim: %s of %s', __trim.get('id'), trim_ids)

            # Add options preset
            __options = self.vplus.find(f'./*/preset[@value="{__trim.get("value")}"][@type="options"]')
            if __options is not None:
                __options.set('id', self.item_id)
                variants.append(__options)

        # Add packages
        for __p in pkg_ids:
            __pkg = self.vplus.find(f'./*/preset[@id="{__p}"]')
            if __pkg is not None:
                variants.append(__pkg)

        # Add FaKom presets
        for __idx, __f in enumerate(fakom_ids):
            __fakom = self.fakom.find(f'./*/preset[@id="{__f}"]')
            self.update_element_id(__fakom, variants)

            variants.insert(__idx, __fakom)
            LOGGER.debug('FaKom: %s of %s', __fakom.get('id'), fakom_ids)

        # Create trim line preset per model
        self.create_trim_lines(models, xml, variants)

        # Order items
        self.update_preset_order(variants)

        # ReWrite Preset Id's
        for p in variants.iterfind('./preset[@type="preset"]'):
            p.set('id', self.item_id)

        # Undoable clear tree command
        self.parent.ui.treeWidget_SrcPreset.clear_tree()

        # Update Source tree widget in main GUI
        xml.parse_element_to_tree_widget(preset_xml)
        self.parent.ui.sort_tree_widget.sort_all(self.parent.ui.treeWidget_SrcPreset)

    def update_preset_order(self, variants):
        __order = 0

        for __s in self.preset_order:
            for __i in variants.iterfind(f'./preset[@type="{__s}"]'):
                __order += 1
                __i.set('order', f'{__order:03d}')

    def create_trim_lines(self, models, xml, variants):
        """ Create trim line presets """
        if not self.checkBoxCreateTrim.isChecked():
            return

        for __idx, __m in enumerate(models):
            for __p in variants.iterfind(f'./preset[@type="fakom_setup"][@value="{__m}"]'):
                name = f'{__p.get("name")}_{__m}-Serie'.replace(' ', '_')
                break
            else:
                __search = f'./*/preset[@value="{__m}"][@type="fakom_setup"]'

                __p = self.fakom.find(__search)
                if __p is not None:
                    name = f'{__p.get("name")}_{__m}-Serie'.replace(' ', '_')

                    # Create new Fakom preset
                    __p.set('order', '000')
                    self.update_element_id(__p, variants)
                    variants.append(__p)

                    LOGGER.debug('Creating new fakom_setup ID %s, %s', __p.get('id'), __p.get('name'))

            if __p is not None:
                # Create Trimline preset
                __attrib = dict(name=name, value=__m, type='preset')
                xml.xml_element = 'preset', __attrib
                __preset = xml.xml_element
                variants.insert(__idx, __preset)

                # Reference trim element
                __search = f'./*/preset[@value="{__m}"][@type="trim_setup"]'
                __trim = self.vplus.find(__search)
                xml.xml_sub_element = self.ref_xml_var(__trim, __preset, '000')

                # Reference FaKom element
                xml.xml_sub_element = self.ref_xml_var(__p, __preset, '001')

    @staticmethod
    def ref_xml_var(element, parent, order):
        """ Create reference variant to preset element """
        __attrib = dict(name=element.get('name'), reference=element.get('id'), type=element.get('type'),
                        value='Referenz', order=order)

        return parent, 'reference', __attrib

    def create_variants(self, xml, page, preset, model, trim_id, fakom_id, pkg_ids):
        """ Fill xml preset with variants """

        # Trim element
        __search = f'./*/preset[@id="{trim_id}"]'
        __trim = self.vplus.find(__search)
        xml.xml_sub_element = self.ref_xml_var(__trim, preset, '000')

        # FaKom element
        __search = f'./*/preset[@id="{fakom_id}"]'
        __fakom = self.fakom.find(__search)

        xml.xml_sub_element = self.ref_xml_var(__fakom, preset, '001')

        # Replace FaKom packages with Vplus packages
        self.replace_fakom_pkg(__fakom, pkg_ids)

        # Option elements
        __search = f'./*/preset[@value="{model}"][@type="options"]'
        __options = self.vplus.find(__search)
        __order = 1

        for __i in self.get_preset_content(page):
            __order += 1
            __name = __i.text(0)
            __id = __i.text(1)
            __type = __i.text(2)

            # Create package reference
            if __type == 'package':
                __search = f'./*/preset[@id="{__id}"]'
                pkg_ids.add(__id)
                __pkg = self.vplus.find(__search)
                xml.xml_sub_element = self.ref_xml_var(__pkg, preset, f'{__order:03d}')

            # Create option
            if __name in self.parent.used_pr_options:
                __o = __options.find(f'./variant[@name="{__name}"]')
                __o.attrib['order'] = f'{__order:03d}'
                preset.append(__o)

    def replace_fakom_pkg(self, fakom, pkg_ids):
        """ Avoid ID conflicts by replacing FaKom Lutscher packages with Vplus packages """
        # Replace FaKom packages with Vplus packages
        for __f in fakom.iterfind('.//'):
            __ref_id = __f.get('reference')

            if __ref_id:
                __search = f'./*/preset[@id="{__ref_id}"]'
                __fakom_pkg = self.fakom.find(__search)
                __pkg_pr = __fakom_pkg.get('value')
                __pkg = __fakom_pkg.get("name")

                __search = f'./*/preset[@name="{__pkg}"][@value="{__pkg_pr}"]'
                __pkg = self.vplus.find(__search)
                __pkg_id = __pkg.get('id')
                pkg_ids.add(__pkg_id)

                __f.set('reference', __pkg_id)
