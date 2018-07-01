import lxml.etree as Et

from pathlib import Path
from modules.dictdiffer import DictDiffer


class PosDiff(object):
    def __init__(self, new_xml_path, old_xml_path):
        self.new_xml = PosXml(new_xml_path)
        self.old_xml = PosXml(old_xml_path)

        self.new = self.new_xml.xml_dict
        self.old = self.old_xml.xml_dict

        # Create actionList's difference
        action_diff = DictDiffer(self.new, self.old)

        # Newly added actionList's
        self.add_action_ls = self.__create_diff_action_lists(action_diff.added())
        # Removed actionList's
        self.rem_action_ls = self.__create_diff_action_lists(action_diff.removed())
        # Modified actionList's
        self.mod_action_ls = self.__create_diff_action_lists(action_diff.changed())

        # Newly added switches, removed switches, modified switches
        self.add_switches, self.rem_switches, self.mod_switches = \
            self.__create_diff_actors(self.new_xml.switches, self.old_xml.switches)
        self.add_looks, self.rem_looks, self.mod_looks = \
            self.__create_diff_actors(self.new_xml.looks, self.old_xml.looks)

    def __create_diff_action_lists(self, action_list_keys):
        action_lists = list()

        for als in action_list_keys:
            al = ActionList(als)
            new_action = self.new.get(als) or dict()
            old_action = self.old.get(als) or dict()

            diff = DictDiffer(new_action, old_action)

            for changed_keys in [diff.added(), diff.changed(), diff.removed()]:
                if changed_keys:
                    al.actors = (changed_keys, new_action, old_action)

            action_lists.append(al)

        return action_lists

    @staticmethod
    def __create_diff_actors(new_actor_dict, old_actor_dict):
        actor_diff = DictDiffer(new_actor_dict, old_actor_dict)
        return actor_diff.added(), actor_diff.removed(), actor_diff.changed()


class PosXml(object):
    def __init__(self, xml_file):
        self.xml_tree = None
        self.xml_dict = dict()
        self.switches = dict()
        self.looks = dict()
        self.xml_file = xml_file

        # Load the Xml content into a dictionary
        self.__load()

    def __load(self):
        """
        Parse the Xml file and store items in xml_dict:
            actionList[name]: {actor.text: {value: value.text, type: type.text}}
        """
        self.xml_tree = Et.parse(Path(self.xml_file).as_posix())

        for e in self.xml_tree.iterfind('*actionList'):
            name = e.get('name')
            self.xml_dict[name] = dict()

            # Add switch actors
            for a in e.iterfind("./*[@type='switch']"):
                actor = a.find('./actor').text
                value = a.find('./value').text
                self.xml_dict[name][actor] = {'value': value, 'type': 'switch'}
                self.update_actor_dict(self.switches, actor, value)

            # Add appearance actors
            for a in e.iterfind("./*[@type='appearance']"):
                actor = a.find('./actor').text
                value = a.find('./value').text
                self.xml_dict[name][actor] = {'value': value, 'type': 'appearance'}
                self.update_actor_dict(self.looks, actor, value)

    @staticmethod
    def update_actor_dict(actor_dict, actor, value):
        if actor not in actor_dict.keys():
            actor_dict[actor] = set()

        actor_dict[actor].add(value)


class ActionList(object):
    def __init__(self, name):
        self.name = name
        self.__actors = dict()

    @property
    def actors(self):
        return self.__actors

    @actors.setter
    def actors(self, val):
        actors, new_action, old_action = val

        for actor in actors:
            new_actor = new_action.get(actor) or dict(value=None, type=None)
            old_actor = old_action.get(actor) or dict(value=None, type=None)

            if actor not in self.__actors.keys():
                self.__actors[actor] = dict()

            self.__actors[actor].update(
                {
                    'new_value': new_actor.get('value'),
                    'type': new_actor.get('type') or old_actor.get('type'),
                    'old_value': old_actor.get('value')
                    }
                )

    @actors.deleter
    def actors(self):
        self.__actors = dict()
