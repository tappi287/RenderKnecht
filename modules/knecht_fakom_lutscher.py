"""knecht_fakom_lutscher for py_knecht. Provides Fakom Lutscher tools.Copyright (C) 2017 Stefan Tapper, All rights reserved.    This file is part of RenderKnecht Strink Kerker.    RenderKnecht Strink Kerker is free software: you can redistribute it and/or modify    it under the terms of the GNU General Public License as published by    the Free Software Foundation, either version 3 of the License, or    (at your option) any later version.    RenderKnecht Strink Kerker is distributed in the hope that it will be useful,    but WITHOUT ANY WARRANTY; without even the implied warranty of    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the    GNU General Public License for more details.    You should have received a copy of the GNU General Public License    along with RenderKnecht Strink Kerker.  If not, see <http://www.gnu.org/licenses/>."""import timeimport reimport xml.etree.ElementTree as Etfrom pathlib import Pathfrom PyQt5 import QtWidgets, QtCorefrom modules.app_globals import Msg, ItemColumn, PACKAGE_FILTER, HELPER_DIRfrom modules.knecht_log import init_loggingfrom modules.knecht_xml import XMLfrom modules.tree_methods import lead_zeros, update_tree_ids, generate_number_outside_setfrom modules.knecht_threads import ExcelConversionThreadLOGGER = init_logging(__name__)class FakomLutscher(QtCore.QObject):    # Signal for preset wizard    # Success:bool, Vplus file path:str or Path    wizard_fakom_signal = QtCore.pyqtSignal(bool, object)    create_fakom_items_signal = QtCore.pyqtSignal()    vplus_xml_signal = QtCore.pyqtSignal(object)    def __init__(self, fakom_path, vplus_path, app, create_pkg_ref_option: bool=False, parent=None, widget=None):        super(FakomLutscher, self).__init__()        self.fakom_path, self.vplus_path = fakom_path, vplus_path        self.create_pkg_ref = create_pkg_ref_option        self.ui = app.ui        self.parent = parent        self.widget = widget        self.thread = None        self.thread_obj = None        if not parent:            self.parent = self.ui        if not widget:            self.widget = self.ui.treeWidget_SrcPreset        self.xml = XML('', self.widget)        self.excel_conv_thread = None    def start(self):        # Prepare thread        self.thread = QtCore.QThread()        self.thread_obj = CreateFakomPresets(self.fakom_path, self.create_pkg_ref)        self.thread_obj.moveToThread(self.thread)        # Thread error connections        self.thread_obj.fakom_empty.connect(self.fakom_empty_error)        self.thread_obj.pos_pattern_error_signal.connect(self.pos_pattern_error)        self.thread_obj.pos_error.connect(self.pos_file_error)        # Thread result connections        self.thread_obj.created_items.connect(self.update_widget)        self.thread_obj.finish_signal.connect(self.thread_finished)        # Connections to thread        self.create_fakom_items_signal.connect(self.thread_obj.start)        self.vplus_xml_signal.connect(self.thread_obj.set_vplus_xml_file)        # Connect QThread signals        self.thread.started.connect(self.thread_obj.read_pos_xml)        self.thread.finished.connect(self.thread_finished)        # Start the thread        self.thread.start()        # Create excel thread and read V Plus Excel        self.read_excel()    def start_load_overlay(self):        self.widget.overlay.load_start()        self.widget.setEnabled(False)    def stop_load_overlay(self):        """ Will be called from V Plus Excel thread on abort """        # Enable widget and stop load indicator        self.widget.overlay.load_finished()        self.widget.setEnabled(True)        self.wizard_fakom_signal.emit(False, '')    def read_excel(self):        """ Create V Plus Excel thread """        self.excel_conv_thread = ExcelConversionThread(self, self.vplus_path, self.widget, fakom_reader=True)        self.excel_conv_thread.create_thread()        # Will return to -parse_xml()- when successful and finished        # Disable Widget and start load indicator        self.start_load_overlay()    def parse_xml(self, xml_file):        """ Receives V Plus Excel Xml file """        self.widget.overlay.load_start()        self.widget.setEnabled(False)        self.vplus_xml_signal.emit(xml_file)        # Clear src tree widget        self.widget.clear()        self.widget.info_overlay.display(Msg.FAKOM_THREAD_START, 2000, immediate=True)        self.create_fakom_items_signal.emit()    def thread_finished(self):        LOGGER.debug('FaKom thread finished.')        self.widget.info_overlay.display(Msg.FAKOM_THREAD_END, 3000, immediate=True)    def update_widget(self, fakom_xml):        """ Receives FaKom Xml Element which can then be parsed to create tree items """        self.xml.parse_element_to_tree_widget(fakom_xml)        if self.widget is self.ui.treeWidget_SrcPreset:            self.ui.sort_tree_widget.sort_all(self.widget)        self.wizard_fakom_signal.emit(True, self.vplus_path)        self.widget.overlay.load_finished()        self.widget.setEnabled(True)    def create_pkg_references(self, pkg_ref_items):        for __r in pkg_ref_items:            item_order, item_name, pkg_item, parent_item = __r            __parent_id = parent_item.text(ItemColumn.ID)            parent_item = self.widget.findItems(__parent_id, QtCore.Qt.MatchExactly, ItemColumn.ID)[0]            if not parent_item:                LOGGER.error('Error creating FaKom Items package reference! Aborting Package reference creation.')                break            ref_item = self.ui.find_reference_items.check_reference(item_order, pkg_item, parent_item)[0]            # Append package item at the end            ref_item.setText(ItemColumn.ORDER, item_order)            # Rename parent preset            new_name = parent_item.text(ItemColumn.NAME).replace(item_name, pkg_item.text(ItemColumn.VALUE))            parent_item.setText(ItemColumn.NAME, new_name)    def fakom_empty_error(self):        self.stop_load_overlay()        self.widget.info_overlay.display_confirm(Msg.FAKOM_EMPTY_ERROR, ('[X]', None))    def pos_file_error(self):        self.stop_load_overlay()    def pos_pattern_error(self):        """ Will also trigger pos_file_error """        LOGGER.error('The POS Xml document did not match any FaKom pattern: %s', self.fakom_path)        self.ui.warning_box(Msg.FAKOM_POS_ERR_TITLE, Msg.FAKOM_POS_ERR_MSG, Path(self.fakom_path).name,                            parent=self.parent)class CreateFakomPresets(QtCore.QObject):    fakom_empty = QtCore.pyqtSignal()    pos_error = QtCore.pyqtSignal()    pos_pattern_error_signal = QtCore.pyqtSignal()    created_items = QtCore.pyqtSignal(Et.Element)    finish_signal = QtCore.pyqtSignal()    # FaKom pattern list    FAKOM_PATTERN = list()    # FaKom Pattern as tuple    # (RegEx, Seat-Code-Index-Start, Seat-Code-Index-End, Color-index-start, Color-index-end)    # (str, int, int, int[optional], int[optional])    # 3DS Format eg. YM_N2M_on    FAKOM_PATTERN.append(('^.._..._on$', 3, 6))    # Edag is creative .._..._..._on eg. YM_N2M_7HA_on    FAKOM_PATTERN.append(('^.._..._..._on$', 3, 6))    # Edag is creative again and again .._..._... eg FZ_on_N5A_on    FAKOM_PATTERN.append(('^.._.._..._..$', -6, -3))    # Edag is creative again .._on_..._on_..._on eg. ML_on_7HA_on_N5W_on    FAKOM_PATTERN.append(('^.._on_..._on_..._on$', -6, -3))    # Edag #3 7HA_on_YH_on_N3U_on    FAKOM_PATTERN.append(('^..._on_.._on_..._on$', -6, -3, -12, -10))    # Topalsson .._... eg. FZ_N2T    FAKOM_PATTERN.append(('^.._...$', 3, 6))    # Topalsson .._..._... eg FZ_N5A_4D0    # multiple pattern in one file... Congrats Topson!    FAKOM_PATTERN.append(('^.._..._...$', 3, 6))    def __init__(self, fakom_path, create_pkg_ref_option):        super(CreateFakomPresets, self).__init__()        self.fakom_path = fakom_path        self.create_pkg_ref = create_pkg_ref_option        # Prepare read_node storage        self.fakom_set = dict()        self.fakom_item = dict()        self.trim_LUM, self.LUM, self.trim_VOS = set(), set(), set()        self.VOS, self.SIB, self.trim_SIB = set(), set(), set()        self.option_list = []        # Store VOS LUM SIB that only exist in packages        self.current_package = ('', '', '', '')  # (Id, Name, Model, Pkg_PR)        self.package_PR_items = dict()        # Store PR-Family and description        pr_family_key = ItemColumn.COLUMN_KEYS[ItemColumn.TYPE]        desc_key = ItemColumn.COLUMN_KEYS[ItemColumn.DESC]        self.pr_info = {            'PR-Code': {                pr_family_key: 'PR-Family', desc_key: 'Long PR code description'}}        # XML worker class        self.xml = XML('', None)        # Prepare Xml Element Tree that will be the thread result        # Set root element tag        self.xml.root = self.xml.dom_tags['root']        # Receive root Et.Element        self.fakom_xml_root = self.xml.root        # Create <variant_presets> Sub Element wih parent root        self.fakom_xml_variants = Et.SubElement(self.fakom_xml_root, self.xml.dom_tags['sub_lvl_1'])        self.vplus_xml = None        self.vplus_xml_file = None        # Prepare Item pseudo classes        self.PrItemNode.attrib = dict()        self.PresetItemNode.attrib = dict()        # Property storage        self.__item_id = 0        self.__item_id_pool = set()    @property    def item_id(self):        self.__item_id += 1        if self.__item_id in self.__item_id_pool:            a = 0            for a in generate_number_outside_set(self.__item_id_pool, start_val=self.__item_id):                if a:                    break            self.__item_id = a        self.__item_id_pool.add(self.__item_id)        return str(self.__item_id)    @item_id.setter    def item_id(self, val):        if val.isdigit():            self.__item_id_pool.add(int(val))    def set_vplus_xml_file(self, vplus_xml_file):        self.vplus_xml_file = vplus_xml_file    def start(self):        LOGGER.debug('FaKom thread starts item creation.')        self.vplus_xml = Et.parse(self.vplus_xml_file)        last_trim_parent = None        # Create an last empty/fake trim_setup because read_node will create last read trim/option-set        # after it encountered the next trim/options setup        for p in self.vplus_xml.iterfind('./*/preset[last()]/..'):            last_trim_parent = p        if not last_trim_parent:            self.fakom_empty.emit()        Et.SubElement(last_trim_parent, 'preset', attrib={            'name': 'None', 'value': 'None', 'type': 'trim_setup'})        # Iterate presets        xml_tree_iterator = self.vplus_xml.iterfind('./*//')        list(map(self.read_node, xml_tree_iterator))        LOGGER.debug('Option List: %s', self.option_list)        LOGGER.debug('Package Items: %s', self.package_PR_items)        # Create tree widget items        self.create_fakom_presets()        # Finished, send created items        self.created_items.emit(self.fakom_xml_root)        self.finish_signal.emit()    def update_pr_info(self, xml_node):        """            Store PR-Family and PR description            Return Xml node type, value, name        """        item_type = xml_node.attrib['type']        item_value = xml_node.attrib['value']        item_name = xml_node.attrib['name']        item_desc = ''        if 'description' in xml_node.attrib.keys():            item_desc = xml_node.attrib['description']        # Store PR-Code = {'type': PR-Family, 'description': PR description}        self.pr_info[item_name] = dict(type=item_type, description=item_desc)        # Return node attributes        return item_type, item_value, item_name    def read_node(self, node):        if 'type' in node.attrib.keys() and 'value' in node.attrib.keys():            node_type, node_value, node_name = self.update_pr_info(node)            LOGGER.debug('FaKom Reader iterate: %s - %s', node_type, node_name)        else:            return        # Store current package info        if node_type == 'package':            for __n in PACKAGE_FILTER:                # Filter Country specific packages                if __n.casefold() in node_name.casefold():                    return            if 'id' in node.attrib.keys():                pkg_id = node.attrib['id']                pkg_pr = node.attrib['value']                current_model = self.vplus_xml.find('./*/preset[@id="' + pkg_id + '"]/..')                if current_model:                    if 'value' in current_model.attrib.keys():                        current_model = current_model.attrib['value']                    else:                        return                self.current_package = (pkg_id, node_name, current_model, pkg_pr)        if node_type in ['trim_setup', 'options']:            # Check if previous preset item is present            if 'type' in self.fakom_item.keys():                # Trimline's LUM/VOS is available as option                if self.fakom_item['type'] == 'trim_setup':                    self.trim_LUM = self.LUM                    self.trim_VOS = self.VOS                    self.trim_SIB = self.SIB                elif self.fakom_item['type'] == 'options':                    self.LUM = self.LUM.union(self.trim_LUM)                    self.VOS = self.VOS.union(self.trim_VOS)                    self.SIB = self.SIB.union(self.trim_SIB)                # Create new trimline or option set                preset = {                    'value': self.fakom_item['value'], 'type': self.fakom_item['type'],                    'name': self.fakom_item['name'],                    'LUM': self.LUM, 'SIB': self.SIB, 'VOS': self.VOS}                # Append Trim or Options FaKom Set                self.option_list.append(preset)                # Reset LUM/SIB/VOS                self.LUM, self.SIB, self.VOS = set(), set(), set()                # Reset current package                self.current_package = ('', '', '', '')            self.fakom_item['value'] = node_value            self.fakom_item['type'] = node_type            # Keep trimline name            if node_type == 'trim_setup':                self.fakom_item['name'] = node_name            # Set option name if no trimline name present            if node_type == 'options' and 'name' not in self.fakom_item.keys():                self.fakom_item['name'] = node_name        self.add_pr_option((node_type, node_value, node_name))    def add_pr_option(self, node_values: tuple=('', '', '')):        """ self.read_node helper method """        node_type, node_value, node_name = node_values        pkg_id, pkg_name, model, pkg_pr = self.current_package        if node_type in ['LUM', 'SIB', 'VOS']:            if pkg_name:                self.package_PR_items[node_name] = {'name': pkg_name, 'id': pkg_id, 'model': model, 'value': pkg_pr}            # Add leather packages of trimline/options            if node_type == 'LUM':                self.LUM.add(node_name)            # Add seat trim variants of trimline/options            if node_type == 'SIB':                self.SIB.add(node_name)            # Add seat variant's of trimline/options            if node_type == 'VOS':                self.VOS.add(node_name)    def create_fakom_presets(self):        self.create_packages(self.fakom_xml_variants)        __preset_count = 0        for option_set in self.option_list:            # Prepare storage            preset = dict()            short_name = re.match('^\D\w+\s\D\w+\s\D\w+(\s\D\w+)?', option_set['name'])            if short_name:                short_name = short_name.group()            else:                short_name = option_set['name'][0:10]            preset['type'] = 'fakom_setup'            if option_set['type'] == 'options':                preset['type'] = 'fakom_option'            # Iterate color trim's            for color_set in sorted(self.fakom_set.items()):                # Extract color key, SIB set's, color_set = ('ZG', {'N7U', 'N3M'})                color_key, sib_set = color_set                sib_set = sib_set.intersection(option_set['SIB'])                # Iterate seat fabric/leather variant's                for SIB in sorted(sib_set):                    # Iterate front seat's                    for VOS in sorted(option_set['VOS']):                        # Iterate leather package's                        for LUM in sorted(option_set['LUM']):                            # Define color preset                            preset['name'] = '{} {}-{}-{}-{}'.format(short_name, color_key, SIB, VOS, LUM)                            preset['id'] = self.item_id                            preset['order'] = lead_zeros(preset['id'])                            preset['value'] = option_set['value']                            # Create color preset                            __values = self.xml.create_values_from_item_attrib(preset)                            __preset_item = self.xml.create_xml_tree_widget_item(__values, 'preset')                            __preset_count += 1                            __v = list()                            # Color variant                            __v += self.create_variant('000', color_key, __preset_item)                            # SIB variant                            __v += self.create_variant('001', SIB, __preset_item)                            # VOS variant                            __v += self.create_variant('002', VOS, __preset_item)                            # LUM variant                            __v += self.create_variant('003', LUM, __preset_item)                            # LOGGER.debug('Created Preset: %s - %s', __preset_item.get('name'), (SIB, VOS, LUM))                            for __e in __v:                                __preset_item.append(__e)                            self.fakom_xml_variants.append(__preset_item)        self.move_pkg_to_end(__preset_count + 10)        if __preset_count > 1000:            self.rewrite_order()    def rewrite_order(self):        for __e in self.fakom_xml_variants.iterfind('./preset'):            __e.attrib['order'] = f'{int(__e.attrib["order"]):04d}'    def move_pkg_to_end(self, order_value):        pkg_xml = self.fakom_xml_variants.findall('./preset[@type="package"]')        for __p in pkg_xml:            order_value += 1            __p.attrib['order'] = f'{order_value:03d}'    def create_packages(self, pkg_parent):        if not self.create_pkg_ref:            return        xml_pkgs = self.vplus_xml.iterfind("./*/preset[@type='package']")        for node in xml_pkgs:            if 'id' in node.attrib.keys():                # Update used Id's                self.item_id = node.attrib['id']            # Append package preset Elements to FaKom Xml            pkg_parent.append(node)    def create_variant(self, item_order, item_name, parent_item):        """ Parse item values to item columns """        __elements = list()        __variant = dict()        __variant['value'] = 'on'        for column_key in ItemColumn.COLUMN_KEYS:            if column_key == 'order':                __variant[column_key] = item_order            elif column_key == 'name':                __variant[column_key] = item_name            if item_name in self.pr_info.keys():                if column_key in self.pr_info[item_name].keys():                    __variant[column_key] = self.pr_info[item_name][column_key]        if self.create_pkg_ref:            __pkg_ref = self.create_variant_pkg_ref(item_order, item_name, parent_item)            if __pkg_ref is not None:                return [__pkg_ref]        # Create variant item        __values = self.xml.create_values_from_item_attrib(__variant)        __elements.append(self.xml.create_xml_tree_widget_item(__values, 'variant', parent_item))        return __elements    def create_variant_pkg_ref(self, item_order, item_name, parent_item):        if item_name not in self.package_PR_items.keys():            return        current_model = parent_item.attrib['value']        pkg_node = dict()        if not current_model:            return        pkg_model = self.package_PR_items[item_name]['model']        if pkg_model == current_model:            # Append pkg reference items at the end            pkg_node['order'] = item_order            # Matched package            pkg_node['reference'] = self.package_PR_items[item_name]['id']            pkg_node['name'] = self.package_PR_items[item_name]['name']            pkg_node['value'] = 'Referenz'            pkg_node['type'] = 'package'            # Change parent items name            __pkg_pr = self.package_PR_items[item_name]['value']            if __pkg_pr is not None:                parent_item.attrib['name'] = parent_item.attrib['name'].replace(item_name, __pkg_pr)            __values = self.xml.create_values_from_item_attrib(pkg_node)            # Create reference to package            return self.xml.create_xml_tree_widget_item(__values, 'reference', parent_item)    def read_pos_xml(self):        LOGGER.debug('FaKom thread starts parsing POS Xml document.')        # Parse POS Xml document        if not self.parse_pos_xml():            self.pos_error.emit()            self.finish_signal.emit()    def parse_pos_xml(self):        pos_xml_tree = None        try:            pos_xml_tree = Et.parse(self.fakom_path)        except Exception as e:            LOGGER.error('Parsing this Xml document failed: %s\n%s', self.fakom_path, e)        # Populate self.fakom_set        if pos_xml_tree:            self.iterate_action_lists(pos_xml_tree)        # Return False if no Fakom pattern was matched        if not self.fakom_set:            self.pos_pattern_error_signal.emit()            return False        return True    def iterate_action_lists(self, pos_xml_tree):        xml_action_lists = pos_xml_tree.findall('*actionList')        list(map(self.read_action_list, xml_action_lists))        LOGGER.debug('FaKoms: %s', self.fakom_set)    def read_action_list(self, node, result: str = '', color_key: str = '', sib_key: str = ''):        """ Read Xml's action lists and extract nodes matching pattern """        # Read actionList name        if 'name' in node.attrib.keys():            name = node.attrib['name']        else:            return        # Match FaKom pattern(s)        for pattern in self.FAKOM_PATTERN:            # FaKom RegEx pattern            fakom_regex_pattern = pattern[0]            # SIB string index            sib_index_start, sib_index_end = pattern[1], pattern[2]            # Color string index            if len(pattern) > 3:                color_key_idx_start, color_key_idx_end = pattern[3], pattern[4]            else:                color_key_idx_start, color_key_idx_end = 0, 2            # RegEx search            result = re.search(fakom_regex_pattern, name, flags=re.IGNORECASE)            if result:                # Extract Colortrim PR                color_key = result.string[color_key_idx_start:color_key_idx_end]                # Extract Seat PR                sib_key = result.string[sib_index_start:sib_index_end]                break        if not result:            return        # Add FaKom Variant        if color_key not in self.fakom_set.keys():            # Create set of SIB's inside color_key            self.fakom_set[color_key] = {sib_key}        else:            self.fakom_set[color_key].add(sib_key)    class PrItemNode:        attrib = dict()        tag = 'variant'    class PresetItemNode:        attrib = dict()        tag = 'preset'        children = list()