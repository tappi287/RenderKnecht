"""
knecht_read_legacy_variants converts legacy .cmd variant preset files in XML Variant preset files.

Conversion is done by Convert-Varianten-to-xml.bat as it would be to errornus to interpret CMD files
in Python that were written with pure batch in mind(& REM Batch Comment -!%%!-).

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
import sys
from pathlib import Path
from pathlib import PureWindowsPath
import os
import subprocess
import xml.etree.ElementTree as ET
from modules.knecht_log import init_logging
from modules.app_globals import HELPER_DIR, TEMP_DIR
from modules.app_globals import convertVariantsScript

LOGGER = init_logging(__name__)

skipConvert = False
debug = False
"""
Make sure pyinstaller GUI --no-console works with subprocess
"""


# Create a set of arguments which make a ``subprocess.Popen`` (and
# variants) call work with or without Pyinstaller, ``--noconsole`` or
# not, on Windows and Linux. Typical use::
#
#   subprocess.call(['program_to_run', 'arg_1'], **subprocess_args())
#
# When calling ``check_output``::
#
#   subprocess.check_output(['program_to_run', 'arg_1'],
#                           **subprocess_args(False))
def subprocess_args(include_stdout=True):
    # The following is true only on Windows.
    if hasattr(subprocess, 'STARTUPINFO'):
        # On Windows, subprocess calls will pop up a command window by default
        # when run from Pyinstaller with the ``--noconsole`` option. Avoid this
        # distraction.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        # Windows doesn't search the path by default. Pass it an environment so
        # it will.
        env = os.environ
    else:
        si = None
        env = None

    # ``subprocess.check_output`` doesn't allow specifying ``stdout``::
    #
    #   Traceback (most recent call last):
    #     File "test_subprocess.py", line 58, in <module>
    #       **subprocess_args(stdout=None))
    #     File "C:\Python27\lib\subprocess.py", line 567, in check_output
    #       raise ValueError('stdout argument not allowed, it will be overridden.')
    #   ValueError: stdout argument not allowed, it will be overridden.
    #
    # So, add it only if it's needed.
    if include_stdout:
        ret = {'stdout': subprocess.PIPE}
    else:
        ret = {}

    # On Windows, running this from the binary produced by Pyinstaller
    # with the ``--noconsole`` option requires redirecting everything
    # (stdin, stdout, stderr) to avoid an OSError exception
    # "[Error 6] the handle is invalid."
    ret.update({
        'stdin': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'startupinfo': si,
        'env': env
    })
    return ret


def get_xml_elements_as_dict(xmlTree,
                             searchArg: str = '*',
                             order: str = 'order') -> list:
    """
        Gibt Attribute aller mit searchArg in xmlTree gefundenen Elemente in einer
        Liste von Dictonarys wieder aus.

        Optional kann ein Reihenfolge String order definiert werden.
        Wird dieser String als Attribut -nicht- gefunden,
        wird er im Dictonary mit dem Key 'order', nummeriert hinterlegt.
    """
    elementList = list()
    elementDict = dict()

    for idx, element in enumerate(xmlTree.findall(searchArg)):
        # Attribute des Elements als Dictonary speichern
        elementDict = element.attrib
        # Textinhalt des Elements mit Key 'value' hinzufügen, \n \t entfernen
        if element.text is not None:
            elementDict.update(
                value=element.text.replace('\n', '').replace('\t', ''))
        else:
            elementDict.update(value='')

        # Reihenfolge Integer mit Key 'order' hinterlegen, falls nicht in Attributen vorhanden
        if order not in elementDict.keys():
            elementDict.update(order=idx)

        # Falls order ausgelesen wurde, sicherstellen als Integer zu speichern(Sortierung)
        elementDict.update(order=int(elementDict['order']))

        elementList.append(elementDict)

    return elementList


def debugMsg(debugVar,
             attributes: str = '',
             attrb_desc: str = None,
             msgTitle: str = None):
    """ Gibt übergebene Attribute der übergebenen Variable ins log aus """
    if type(debugVar) is not dict: return

    debugStr = str()
    debug_attributes_desc = []
    debug_attributes_list = list(attributes.replace(' ', '').split(','))

    if attrb_desc:
        debug_attributes_desc = list(attrb_desc.replace(' ', '').split(','))

    if msgTitle: debugStr += '\n' + msgTitle + '\n'

    for d in sorted(debugVar):
        for idx, a in enumerate(debug_attributes_list):
            if len(debug_attributes_desc) >= idx and len(
                    debug_attributes_desc) != 0:
                if debug_attributes_desc[idx]:
                    debugStr += str(debug_attributes_desc[idx]) + ' '
            debugStr += str(debugVar[d][a])
            if idx + 1 != len(debug_attributes_list): debugStr += ' - '
        debugStr += '\n'

    LOGGER.debug(debugStr)


def convertVariants(convert_file=None):
    """

    Converts Variant*.cmd files to Variants*.xml files with
    Convert-Varianten-to-xml.bat
    Uses this batch file because it would be tricky to interpret batch comments and syntax from within Python.

    """
    global skipConvert

    # Wenn keine zur Konvertierende Datei übergeben wurde
    if not convert_file:
        # Pruefen ob XML bereits erstellt wurde
        for xmlFile in Path(HELPER_DIR).glob('Varianten*.xml'):
            if xmlFile:
                skipConvert = True
                variantsXmlPath = xmlFile
                LOGGER.info(
                    'Found existing XML Variant Preset file: %s Skipping conversion.',
                    xmlFile)
                return xmlFile

    #XML mit Batchscript erstellen aus altem RenderKnecht*.cmd Daten
    if not skipConvert:

        #Batchscript erstellt Xml und gibt vollständigen Dateipfad zurück
        LOGGER.info('Converter Script: %s \nDir to convert: %s',
                    str(convertVariantsScript),
                    str(PureWindowsPath(os.path.dirname(convert_file))))

        args = [
            str(convertVariantsScript),
            str(PureWindowsPath(os.path.dirname(convert_file)))
        ]

        # Start Convert Variants Batch Script
        variantsXmlPath = subprocess.Popen(args, **subprocess_args())

        # variantsXmlPath is subprocess.Popen, .stdout returns only the STDOUT
        variantsXmlPath = variantsXmlPath.stdout.read()

        #Batchscript Ausgabe in String konvertieren
        try:
            variantsXmlPath = variantsXmlPath.decode(
                encoding='utf-8', errors='strict')
            LOGGER.info('variantsXmlPath: %s', variantsXmlPath)
        except:
            LOGGER.info(
                'Variants XML String read back from Batch was not bytes: %s',
                variantsXmlPath)
            pass

        return variantsXmlPath


def read_xml_variants(variantsXmlPath):
    #XML lesen mit xml.etree.ElementTree.parse()
    try:
        variantsData = ET.parse(variantsXmlPath)
    except:
        LOGGER.debug('Error parsing Xml document: %s', variantsXmlPath)
        return

    #XML Baum einlesen mit .getroot()
    variantsXml = variantsData.getroot()

    #RenderKnecht Settings auslesen und in Dictonary speichern
    renderknecht_settings = {}
    for setting in get_xml_elements_as_dict(variantsXml,
                                            'renderknecht_settings/'):
        renderknecht_settings[setting['order']] = setting

    if debug:
        debugMsg(renderknecht_settings, 'name, value, type', 'Setting:, ,type:',
                 '---Legacy Settings---')

    #Presets auslesen
    renderknecht_presets = {}
    for p in get_xml_elements_as_dict(variantsXml,
                                      'variant_presets/'):  # p - Preset
        renderknecht_presets[p['order']] = p
        renderknecht_presets[p['order']].pop('value')
        renderknecht_presets[p['order']]['setup'] = {}

        # Varianten Elemente des aktuellen Presets auswählen
        searchString = 'variant_presets/preset[@name="' + p['name'] + '"]/'
        for v in get_xml_elements_as_dict(variantsXml,
                                          searchString):  # v - Variante
            renderknecht_presets[p['order']]['setup'].update({v['order']: v})

    #debugMsg(renderknecht_presets, 'order, name', None, '---Legacy Presets---')

    return renderknecht_presets
