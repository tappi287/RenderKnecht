"""
knecht_preset_editor_references module provides functionality for references

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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QTreeWidgetItem

from modules.app_globals import DEFAULT_TYPES, ItemColumn, Itemstyle, Msg
from modules.knecht_log import init_logging
from modules.tree_methods import VAR_LEVEL_ITEM_FLAGS, add_top_level_item
from modules.tree_methods import lead_zeros, object_is_tree_widget, update_tree_ids

# Initialize logging for this module
LOGGER = init_logging(__name__)


class FindReferenceItems:
    """
        Collect referenced presets recursivly for given reference item.
        .search returns items, GUI_message for recursion error or False
    """

    def __init__(self, ui, iter_tree):
        # Main Window app
        self.ui = ui

        # Instance iteration class, we will only need: .iterate_childs(parent_item)
        self.iterate_tree = iter_tree

        # Store preset items which contain recursive references
        # list entry is tuple: (preset or None, item)
        self.items_with_recursion_error = []

        self.search_destination = None

        # Destination item if name clash occurs
        self.name_clashing_item = None

        self.preset_recursion_list = []

        # Skip collection of variants
        self.only_report_preset_ids = True

    def set_ref_style(self, item, indicate_ref=True, column=ItemColumn.NAME):
        """ Visual indication of a reference preset item """
        font = item.font(column)

        if indicate_ref:
            font.setItalic(True)
            item.setIcon(column, self.ui.icon[Itemstyle.MAIN['link_intact']])
        else:
            font.setItalic(False)
            item.setIcon(column, self.ui.icon[Itemstyle.MAIN['empty']])

        item.setFont(column, font)

    def set_missing_style(self, item, highlight=True, c=ItemColumn.NAME):
        """ Visual indication of a missing reference variant item """
        if highlight:
            item.setForeground(c, QBrush(QColor(190, 90, 90)))
            item.setIcon(c, self.ui.icon[Itemstyle.MAIN['link_broken']])

            # highlight the parent item as well
            if item.parent():
                item.parent().setIcon(c, self.ui.icon[Itemstyle.MAIN['link_broken']])
                item.parent().setExpanded(True)
                item.parent().setForeground(c, QBrush(QColor(190, 90, 90)))
        else:
            item.setIcon(c, self.ui.icon[Itemstyle.MAIN['empty']])
            item.setForeground(c, QBrush(QColor(15, 15, 15)))

    def set_contains_ref_style(self, item, highlight=True, c=ItemColumn.NAME):
        """ Visual indication that preset contains referenced items """
        if highlight:
            item.setIcon(c, self.ui.icon[Itemstyle.MAIN['link_contained']])
        else:
            item.setIcon(c, self.ui.icon[Itemstyle.MAIN['empty']])

    def set_recursion_style(self, item, highlight=True, c=ItemColumn.NAME):
        if highlight:
            blue = QBrush(QColor(*Itemstyle.COLOR['BLUE']), Qt.SolidPattern)
            item.setBackground(c, blue)

            if item.parent():
                item.parent().setExpanded(True)
                item.parent().setBackground(c, blue)
        else:
            # Clear item background color
            if item.data(0, Qt.BackgroundRole) == None:
                item.setData(c, Qt.BackgroundRole, None)

            if item.parent():
                item.parent().setData(c, Qt.BackgroundRole, None)

    def iterate_and_style(self, items, set_style, column: int = ItemColumn.ID):
        """ Iterate provided items and call appropiate styling method """
        if items:
            ids = set()
            for i in items:
                set_style(i)
                ids.add(i.text(column))

            return ids

    def highlight_recursion_errors(self):
        """ Prompt user with recursion error and offer filter button """

        def filter_wizard_btn():
            filter_txt = 'id' + ', '.join(recursive_ids).replace(',', '')
            widget.filter_txt_widget.setText(filter_txt)

        if self.items_with_recursion_error:
            # Highlight references with recursion error
            recursive_ids = set(self.iterate_and_style(self.items_with_recursion_error, self.set_recursion_style))

            # Highlight reference
            self.set_missing_style(self.items_with_recursion_error[0])

            widget = self.items_with_recursion_error[0].treeWidget()

            # Request overlay message
            widget.info_overlay.display_confirm(Msg.REF_ERROR_OVR, (Msg.REF_ERROR_BTN_1, filter_wizard_btn),
                                                (Msg.REF_ERROR_BTN_2, None), immediate=True)

            LOGGER.debug('Presets with recursion error: %s', recursive_ids)

    def highlight_references(self, item_list, search_items: tuple = ([], [], [])):
        """
            Iterates thru provided items, searches their references and
            applies visual indication for references, presets containing references
            and references with missing links.
        """
        ref_items, missing_items, preset_ref = search_items
        search = ([], [], [])

        for i in item_list:
            # Read only Presets and References
            if i.UserType in [1000, 1002]:
                # Do not search default types read from excel
                if i.treeWidget() is self.ui.treeWidget_SrcPreset:
                    if i.text(ItemColumn.TYPE) in DEFAULT_TYPES:
                        break

                self.set_ref_style(i, False)
                self.set_contains_ref_style(i, False)
                self.set_missing_style(i, False)
                self.set_recursion_style(i, False)

                search = self.search_preset_for_references(i, i.treeWidget(), True)

            ref, missing, ref_pre = search
            ref_items += ref
            missing_items += missing
            preset_ref += ref_pre

        # Style references
        referenced_ids = self.iterate_and_style(ref_items, self.set_ref_style)

        # Style Presets containing References
        preset_contains_ref_id = self.iterate_and_style(preset_ref, self.set_contains_ref_style)

        # Style missing items
        missing_link_id = self.iterate_and_style(missing_items, self.set_missing_style, ItemColumn.REF)

        if referenced_ids:
            LOGGER.info("Referenced ID's: %s", referenced_ids)

            # Style valid references as non missing
            widget = ref_items[0].treeWidget()
            for current_id in referenced_ids:
                for i in widget.findItems(current_id, Qt.MatchRecursive, ItemColumn.REF):
                    self.set_missing_style(i, False)
                    self.set_recursion_style(i, False)

        self.highlight_recursion_errors()

        if missing_link_id:
            LOGGER.error("Item contains reference to missing item: %s", missing_link_id)

        if preset_contains_ref_id:
            LOGGER.info("Preset contains references: %s", preset_contains_ref_id)

        return ref_items, missing_items, preset_ref

    def search(self, ref_item):
        """ Perform standard search in User presets for Sending and Rendering """
        # Reset recursion list
        self.preset_recursion_list = []
        self.reference_items = []
        self.only_report_preset_ids = False
        self.ref_msg = False

        # Standard search will look in -User Presets-
        self.search_destination = self.ui.treeWidget_DestPreset

        # Perform recursive search, updates self.reference_items
        self.recursive_search(ref_item)

        return self.reference_items, self.ref_msg

    def search_preset_for_references(self, src_preset, dest, only_report_exisiting=False):
        """
            only_report_exisiting: false
            Search if provided preset's references already exist in User Widget.
            Otherwise search for references in Source Widget and report the missing ones.

            only_report_exisiting: true
            report existing references within same tree for provided preset
        """
        # Provided item is Preset or RenderPreset?
        if src_preset.UserType not in [1000, 1003]:
            return [], [], []

        # LOGGER.debug('Searching for references in: %s', src_preset.text(ItemColumn.NAME))

        # Reset recursion list
        self.preset_recursion_list = []
        self.items_with_recursion_error = []
        self.reference_items = []

        # Skip collection of variants
        self.only_report_preset_ids = True

        # Collect reference -IDs- from destination or widget
        self.search_destination = dest

        src_preset_items = []

        # Collect preset child items
        for item in self.iterate_tree.iterate_childs(src_preset):
            src_preset_items.append(item)
            self.recursive_search(item)

        if not src_preset_items:
            return [], [], []

        # Keep ID set -without- duplicates
        existing_ids = set(self.reference_items)
        self.reference_items = []

        # Add existing presets in destination
        if not only_report_exisiting:
            self.find_existing_ids(dest)
            existing_ids = existing_ids.union(self.reference_items)
            self.reference_items = []

        own_id_str = src_preset.text(ItemColumn.ID) or ''
        own_id = {own_id_str}

        if only_report_exisiting:
            # Collect only exisitng in dest
            source_ids = existing_ids
        else:
            # Collect reference -IDs- from source
            self.search_destination = self.ui.treeWidget_SrcPreset
            list(map(self.recursive_search, src_preset_items))

            # Keep ID set -without- duplicates
            source_ids = set(self.reference_items)

            self.reference_items = []

            # Collect items existing in Source but not in Dest
            source_ids = source_ids.difference(existing_ids.union(own_id))

        for id in source_ids:
            self.reference_items += self.search_destination.findItems(id, Qt.MatchExactly, ItemColumn.ID)

        if self.name_clashing_item:
            source_ids.add(self.name_clashing_item.text(ItemColumn.REF))

        # Collect items who reference a missing preset
        items_with_invalid_reference = []
        report_missing_ids = []
        preset_contains_ref = []
        valid_ids = source_ids.union(existing_ids)

        for item in src_preset_items:
            if item.UserType == 1002:
                if item.parent():
                    # Highlight presets containing references
                    preset_contains_ref.append(item.parent())

                id = item.text(ItemColumn.REF)

                if id not in valid_ids:
                    items_with_invalid_reference.append(item)
                    # Add parent item aswell
                    if item.parent():
                        items_with_invalid_reference.append(item.parent())
                    report_missing_ids.append(id)

        # Report Missing -IDs-
        # Update widgets's missing Id set
        self.search_destination.missing_ids = self.search_destination.missing_ids.union(report_missing_ids)
        self.search_destination.missing_ids = self.search_destination.missing_ids.difference(valid_ids)

        if report_missing_ids:
            # TODO Löschen der Referenz ID anbieten, Kopieren aus Source Tree unter Namensabgleich anbieten
            LOGGER.error("Missing Presets ID's: %s (referenced but missing) at %s", self.search_destination.missing_ids,
                self.ui.get_tree_name(self.search_destination))

        if self.items_with_recursion_error:
            self.highlight_recursion_errors()

        return self.reference_items, items_with_invalid_reference, preset_contains_ref

    def find_existing_ids(self, dest):
        presets = dest.findItems('*', (Qt.MatchWildcard), ItemColumn.ID)
        for preset in presets:
            self.reference_items.append(preset.text(ItemColumn.ID))

    def resolve_name_clash(self, name, id):
        def check_and_assign_id(n_item, col):
            if n_item.text(col) == id:
                n_item.setText(col, new_id)
                return True
            return False

        new_id = update_tree_ids(self.search_destination, self.ui,
                                 id, self.ui.treeWidget_SrcPreset)

        # Presets in destination widget that match Name
        dest_items = self.search_destination.findItems(
            name, Qt.MatchExactly | Qt.MatchRecursive, ItemColumn.NAME)

        # Assign new ID in destination
        for item in dest_items:
            # Assign new id to matched item with same Name and ID
            check_and_assign_id(item, ItemColumn.ID)
            # Assign new id to matched item with same Name and REF ID
            check_and_assign_id(item, ItemColumn.REF)

        LOGGER.warning('Reassigned new id %s to clashing item %s', new_id, name)
        self.ui.report_name_clash(name, id, new_id)

    def recursive_search(self, r_item):
        """ Recursive search for provided reference, collect to self.reference_items """
        reference_id = r_item.text(ItemColumn.REF)
        reference_name = r_item.text(ItemColumn.NAME)

        # Skip preset's eg render_presets without ID
        if reference_id == '':
            return
        if self.search_destination is None:
            return

        # Match preset items with id and name matching the reference variant
        presets = self.search_destination.findItems(reference_id, Qt.MatchExactly, ItemColumn.ID)

        # Iterate matched presets
        for r_preset in presets:
            # Check Name
            matched_name = r_preset.text(ItemColumn.NAME)
            if matched_name != reference_name:
                LOGGER.warning('ID %s: %s != %s', reference_id, matched_name, reference_name)
                self.resolve_name_clash(matched_name, reference_id)
                self.name_clashing_item = r_item

            # Recursion test, did we collect that reference already?
            if r_preset in self.preset_recursion_list:
                parent_id = r_item.parent().text(ItemColumn.ID)
                parent_name = r_item.parent().text(ItemColumn.NAME)
                r_item_name = r_item.text(ItemColumn.NAME)

                LOGGER.error('Reference recursion error: %s with Id %s referenced %s with Id %s back to itself!',
                    parent_name, parent_id, r_item_name, reference_id)

                # Pretty long Warning message for GUI
                self.ref_msg = Msg.REF_ERROR[0] + parent_name + Msg.REF_ERROR[1]
                self.ref_msg += parent_id + Msg.REF_ERROR[2] + r_item_name
                self.ref_msg += Msg.REF_ERROR[3] + reference_id + Msg.REF_ERROR[4]

                # Report recursive presets and references
                recursive_refs = self.search_destination.findItems(parent_id, Qt.MatchExactly | Qt.MatchRecursive,
                    ItemColumn.REF)
                self.items_with_recursion_error += recursive_refs
                self.items_with_recursion_error += presets
                self.items_with_recursion_error += [r_item.parent(), r_item]

                # Skip recursive references
                return

            # Iterate preset children
            if r_preset.childCount() > 0:
                for ref_variant in self.iterate_tree.iterate_childs(r_preset):
                    # Recursive search
                    if ref_variant.UserType == 1002:
                        # LOGGER.debug('Collecting recursive reference: %s Id %s',
                        # ref_variant.text(1), ref_variant.text(4))
                        self.preset_recursion_list.append(r_preset)
                        self.recursive_search(ref_variant)

                    # Only report preset Id
                    if self.only_report_preset_ids:
                        self.reference_items.append(r_preset.text(ItemColumn.ID))
                    # Add Variant
                    else:
                        self.reference_items.append(ref_variant)

    def check_reference(self, order, item, destination_item):
        """
            If preset item is moved onto another item, create a reference instead of copying the preset item.
            Returns True if item is reference, otherwise False
        """
        new_undo_items = []

        def create_reference(is_widget=True):
            # Reference target is item id
            reference_to_id = item.text(ItemColumn.ID)

            # Set reference values
            # ['order', 'name', 'value', 'type', 'reference', 'id']
            # the text_value msg.REFERENCE_NAME is only to inform the user
            # we will determine references later by UserType 1002
            value_list = [lead_zeros(order), item.text(ItemColumn.NAME), Msg.REFERENCE_NAME, item.text(ItemColumn.TYPE),
                          reference_to_id, '']

            # Create reference
            new_reference = QTreeWidgetItem(destination_item, value_list)
            new_reference.UserType = 1002
            new_reference.setFlags(VAR_LEVEL_ITEM_FLAGS)
            new_undo_items.append(new_reference)

            # Visual indicator
            if is_widget:
                destination_item.overlay.ref_created()
            else:
                try:
                    destination_item.treeWidget().overlay.ref_created()
                except AttributeError:
                    # Case were destination item is not yet assigned to a tree widget
                    pass

        def copy_missing_references(order, is_widget=True):
            # If preset contains references, make sure they exist in
            # destination Widget or copy them aswell + report missing references
            dest = destination_item

            if not is_widget:
                dest = destination_item.treeWidget()

            search_result = self.search_preset_for_references(item, dest)
            src_reference_presets, missing_references = search_result[0], search_result[1]

            for i in src_reference_presets:
                __i = i.text(ItemColumn.NAME)

            # Add missing presets that exist in source presets
            if src_reference_presets:
                log_id_list = []
                for n_item in src_reference_presets:
                    if n_item.text(ItemColumn.ID) not in dest.missing_ids:
                        if is_widget:
                            order += 1
                            n_item = add_top_level_item(destination_item, [order, n_item])
                            new_undo_items.append(n_item)
                        else:
                            preset_order = destination_item.treeWidget().topLevelItemCount() + 1
                            n_item = add_top_level_item(destination_item.treeWidget(), [preset_order, n_item])
                            new_undo_items.append(n_item)

                        self.set_ref_style(n_item)
                        log_id_list.append(n_item.text(ItemColumn.ID))
                    else:
                        dest.report_conflict(n_item)

                LOGGER.debug('Added missing items from source: %s', log_id_list)

                # Visual indicator
                dest.overlay.ref_created()

            # Highlight items that contain invalid references
            if missing_references:
                for m_item in missing_references:
                    self.set_ref_style(m_item)
                    self.set_missing_style(m_item)

        def copy_preset(item_to_copy):
            """
            If we just created a reference, make sure the ref source
            exists in destination.
            """
            item_id = item_to_copy.text(ItemColumn.ID)

            if item_to_copy.UserType == 1000:
                dest_presets = destination_item.treeWidget().findItems(item_id, Qt.MatchExactly, ItemColumn.ID)

                for preset in dest_presets:
                    if item_id in preset.text(ItemColumn.ID):
                        return

                order = destination_item.treeWidget().topLevelItemCount() + 1
                new_preset = add_top_level_item(destination_item.treeWidget(), [order, item_to_copy])
                new_undo_items.append(new_preset)
                LOGGER.debug('Coping preset id %s to fulfil just created reference.', item_id)

        if item.UserType in [1000, 1003]:
            if object_is_tree_widget(destination_item):
                copy_missing_references(order, True)

                if new_undo_items:
                    return new_undo_items
            else:
                # Create reference if item is preset
                create_reference(False)

                # Search preset to copy for references
                # LOGGER.debug('Search #1 in %s', item.text(ItemColumn.ID))
                # Copy references, referenced by new reference
                copy_missing_references(order, False)

                # Search destination preset for references
                # This will discover clashing names
                item = destination_item
                # LOGGER.debug('Search #2 in %s', item.text(ItemColumn.ID))
                copy_missing_references(order, False)

                if self.name_clashing_item:
                    item = destination_item
                    copy_missing_references(order, False)

                    # Name clash resolved, reset item
                    self.name_clashing_item = None

                # Copy item itself to dest if not already present
                copy_preset(item)

                if new_undo_items:
                    return new_undo_items

                return True

        return False
